import itertools
import math
import numpy as np
from scipy.io import wavfile
import whisper
import torch
import torchaudio
from stringToCommand import string_to_command  # your parser


SAMPLE_RATE = 22050   # whatever your project uses (not critical here)


# -----------------------------
# Preprocessing identical to your transcriber
# -----------------------------
def preprocess_segment(segment: np.ndarray, orig_sr: int):
    """
    Same as your transcriber pipeline:
    int16 → float32 → torch → resample → pad_or_trim → log_mel_spectrogram
    """
    from whisper.audio import pad_or_trim, log_mel_spectrogram

    # Convert int16 → float32 [-1,1]
    if segment.dtype == np.int16:
        segment = segment.astype(np.float32) / 32768.0
    else:
        segment = segment.astype(np.float32)

    segment = torch.from_numpy(segment)

    # Resample to 16000 (Whisper native)
    if orig_sr != 16000:
        resampler = torchaudio.transforms.Resample(
            orig_freq=orig_sr, new_freq=16000
        )
        segment = resampler(segment)

    # Pad or trim to Whisper's required 30s window
    segment = pad_or_trim(segment)

    # Convert to mel spectrogram
    mel = log_mel_spectrogram(segment)
    return mel


# -----------------------------
# Command scoring
# -----------------------------
def command_score(pred_cmd, expected_cmd):
    """
    Scores final parsed command, not raw text.
    0.0 = bad, 1.0 = perfect.
    """
    if pred_cmd is None:
        return 0.0

    score = 0.0

    # Action exact match
    if pred_cmd.get("action") == expected_cmd.get("action"):
        score += 0.4

    # Direction exact match
    if pred_cmd.get("direction") == expected_cmd.get("direction"):
        score += 0.3

    # Distance + unit match with tolerance
    exp_dist = expected_cmd.get("distance")
    exp_unit = expected_cmd.get("unit")
    pred_dist = pred_cmd.get("distance")
    pred_unit = pred_cmd.get("unit")

    if exp_dist is None or exp_unit is None:
        # caller doesn't care about distance/unit
        score += 0.3
    else:
        if pred_unit == exp_unit and pred_dist is not None:
            diff = abs(pred_dist - exp_dist)

            if exp_unit == "meters":
                tol = 0.01   # 1 cm
            elif exp_unit == "radians":
                tol = math.radians(1)  # ~1 degree
            else:
                tol = max(0.1 * abs(exp_dist), 0.001)

            if diff <= tol:
                score += 0.3

    return score


# -----------------------------
# Main evaluation function
# -----------------------------
def find_best_whisper_settings_for_file(audio_path, expected_command):
    # Load model once – FIXED to base.en
    model = whisper.load_model("base.en")

    # Load file as int16 mono
    sr, data = wavfile.read(audio_path)
    if data.ndim == 2:
        data = data.mean(axis=1).astype(np.int16)
    data = data.astype(np.int16)

    print(f"Loaded audio @ {sr} Hz")

    # Preprocess using SAME pipeline as your transcriber
    mel = preprocess_segment(data, orig_sr=sr)

    # -----------------------------
    # Big search grid over DecodingOptions (base.en only)
    # -----------------------------
    TEMPS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0]
    BEAMS = [None, 2, 4, 8, 12, 16]
    BEST_OF = [1, 2, 3, 5, 8]          # only used in sampling mode (no beam, temp > 0)
    PATIENCE = [None, 0.0, 0.5, 1.0, 2.0]
    LENGTH_PEN = [None, 0.0, 0.1, 0.2, 0.5]

    LANG = "en"
    TASK = "transcribe"

    rough_count = 0
    for temp, beam, best_of, pat, lp in itertools.product(
        TEMPS, BEAMS, BEST_OF, PATIENCE, LENGTH_PEN
    ):
        rough_count += 1
    print(f"About to iterate over ~{rough_count} parameter tuples (not all use best_of/patience)\n")

    results = []
    idx = 0

    for temp, beam, best_of, pat, lp in itertools.product(
        TEMPS, BEAMS, BEST_OF, PATIENCE, LENGTH_PEN
    ):
        idx += 1
        cfg_name = (
            f"cfg_{idx}_temp{temp}_beam{beam}_bestof{best_of}_"
            f"pat{pat}_lenpen{lp}"
        )

        print(f"\n=== Testing {cfg_name} ===")

        # Base decoding options – model-level behavior fixed
        opt_kwargs = {
            "fp16": False,
            "language": LANG,
            "task": TASK,
            "temperature": temp,
            "without_timestamps": True,
        }

        # Beam search vs sampling:
        if beam is not None:
            # Beam search mode: set beam_size, optionally patience & length_penalty
            opt_kwargs["beam_size"] = beam

            if pat is not None:
                # patience only valid when beam_size is set
                opt_kwargs["patience"] = pat

            if lp is not None:
                opt_kwargs["length_penalty"] = lp

            # NO best_of in beam search
        else:
            # Sampling mode: no beam_size, no patience
            # length_penalty is technically for beam, but we can ignore/set only when beam is not None,
            # so we do nothing here.
            if temp > 0.0 and best_of > 1:
                # best_of only in sampling + temperature > 0
                opt_kwargs["best_of"] = best_of
            # if temp == 0.0 → greedy: do NOT set best_of at all

        # Strip out None fields just in case (we only added non-None above)
        opt_kwargs = {k: v for k, v in opt_kwargs.items() if v is not None}

        options = whisper.DecodingOptions(**opt_kwargs)

        # Decode
        result = whisper.decode(model, mel, options)
        transcript = result.text
        print(f"Transcript: {transcript}")

        # Parse into robot command
        pred_cmd = string_to_command(transcript)
        print(f"Parsed cmd: {pred_cmd}")

        # Score against expected_command
        score = command_score(pred_cmd, expected_command)
        print(f"Cmd score: {score:.3f}")

        results.append({
            "cfg": cfg_name,
            "score": score,
            "text": transcript,
            "cmd": pred_cmd,
            "params": opt_kwargs,
        })

    # Sort results
    results.sort(key=lambda r: r["score"], reverse=True)

    print("\n========== BEST SETTINGS (TOP 20) ==========")
    for r in results[:20]:
        print(f"{r['cfg']}  score={r['score']:.3f}  cmd={r['cmd']}")

    print("\nBEST OVERALL:")
    best = results[0]
    print("Config:", best["cfg"])
    print("Params:", best["params"])
    print("Score :", best["score"])
    print("Cmd   :", best["cmd"])
    print("Text  :", best["text"])


# -----------------------------
# Run test
# -----------------------------
if __name__ == "__main__":
    audio_path = "go backwards 10cm_mhvvee3l.wav"

    # What you EXPECT after parsing whisper output:
    expected_command = {
        "action": "move",
        "direction": "backward",
        "distance": 0.10,   # 10 cm in meters
        "unit": "meters",
    }

    find_best_whisper_settings_for_file(audio_path, expected_command)
