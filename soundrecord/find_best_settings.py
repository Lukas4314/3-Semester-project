import itertools
import math
import numpy as np
from scipy.io import wavfile
import whisper
import torch
import torchaudio
from stringToCommand import string_to_command  # your parser

SAMPLE_RATE = 22050


# -----------------------------
# Preprocessing identical to your transcriber
# -----------------------------
def preprocess_segment(segment: np.ndarray, orig_sr: int, device: torch.device):
    """
    int16 → float32 → torch → resample → pad_or_trim → log_mel_spectrogram
    Runs log-mel on GPU if device is CUDA.
    """
    from whisper.audio import pad_or_trim, log_mel_spectrogram

    # Convert int16 → float32 [-1,1]
    if segment.dtype == np.int16:
        segment = segment.astype(np.float32) / 32768.0
    else:
        segment = segment.astype(np.float32)

    audio = torch.from_numpy(segment)

    # Resample to 16000 (Whisper native) - often CPU, that's fine
    if orig_sr != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=16000)
        audio = resampler(audio)

    # Whisper expects exactly ~30s window
    audio = pad_or_trim(audio)

    # Move to GPU (or stay CPU) so mel can be computed on the same device
    audio = audio.to(device)

    # Convert to mel spectrogram (GPU if audio is on CUDA)
    mel = log_mel_spectrogram(audio)
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
                tol = 0.01  # 1 cm
            elif exp_unit == "radians":
                tol = math.radians(1)  # ~1 degree
            else:
                tol = max(0.1 * abs(exp_dist), 0.001)

            if diff <= tol:
                score += 0.3

    return score


# -----------------------------
# Main evaluation function (multi-file)
# -----------------------------
@torch.no_grad()
def find_best_whisper_settings_for_files(audio_files, expected_commands):
    """
    audio_files: list[str] of wav paths
    expected_commands: dict[str, dict] mapping filename -> expected command dict
    """
    # Pick device + load model onto it
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    model = whisper.load_model("base.en").to(device)
    use_fp16 = (device.type == "cuda")
    torch.set_grad_enabled(False)

    # ---- Precompute mels for all clips once ----
    mels = []
    exp_cmds = []

    for path in audio_files:
        if path not in expected_commands:
            raise ValueError(f"No expected command defined for file: {path}")

        sr, data = wavfile.read(path)
        if data.ndim == 2:
            data = data.mean(axis=1).astype(np.int16)
        data = data.astype(np.int16)

        mel = preprocess_segment(data, orig_sr=sr, device=device)
        mels.append(mel)
        exp_cmds.append(expected_commands[path])

        print(f"Loaded+preprocessed: {path} @ {sr} Hz")

    # ---- Grid over DecodingOptions ----
    TEMPS = [0.0, 0.1, 0.3, 0.5]
    BEAMS = [None, 2, 4, 8]
    BEST_OF = [1, 2, 3]
    PATIENCE = [None, 0.0, 0.5, 1.0]
    LENGTH_PEN = [None, 0.0, 0.1, 0.2]

    LANG = "en"
    TASK = "transcribe"

    total_cfgs = len(TEMPS) * len(BEAMS) * len(BEST_OF) * len(PATIENCE) * len(LENGTH_PEN)
    total_decodes = total_cfgs * len(audio_files)
    print(f"\nTesting {total_cfgs} configs × {len(audio_files)} clips = {total_decodes} decode calls\n")

    results = []
    idx = 0

    for temp, beam, best_of, pat, lp in itertools.product(
        TEMPS, BEAMS, BEST_OF, PATIENCE, LENGTH_PEN
    ):
        idx += 1
        cfg_name = f"cfg_{idx}_temp{temp}_beam{beam}_bestof{best_of}_pat{pat}_lenpen{lp}"

        opt_kwargs = {
            "fp16": use_fp16,          # True on CUDA, False on CPU
            "language": LANG,
            "task": TASK,
            "temperature": temp,
            "without_timestamps": True,
        }

        # Beam search vs sampling
        if beam is not None:
            opt_kwargs["beam_size"] = beam
            if pat is not None:
                opt_kwargs["patience"] = pat
            if lp is not None:
                opt_kwargs["length_penalty"] = lp
        else:
            if temp > 0.0 and best_of > 1:
                opt_kwargs["best_of"] = best_of

        opt_kwargs = {k: v for k, v in opt_kwargs.items() if v is not None}
        options = whisper.DecodingOptions(**opt_kwargs)

        # Evaluate this config across all clips
        total_score = 0.0
        per_clip = []

        for path, mel, exp in zip(audio_files, mels, exp_cmds):
            result = whisper.decode(model, mel, options)
            transcript = result.text
            pred_cmd = string_to_command(transcript)
            score = command_score(pred_cmd, exp)

            total_score += score
            per_clip.append({
                "file": path,
                "text": transcript,
                "pred_cmd": pred_cmd,
                "score": score,
            })

        avg_score = total_score / len(mels)
        print(f"{cfg_name} -> avg_score={avg_score:.3f}")

        results.append({
            "cfg": cfg_name,
            "avg_score": avg_score,
            "params": opt_kwargs,
            "per_clip": per_clip,
        })
                                        
    # Sort and print
    results.sort(key=lambda r: r["avg_score"], reverse=True)

    print("\nBEST SETTINGS (TOP 10)")
    for r in results[:10]:
        print(f"{r['cfg']}  avg_score={r['avg_score']:.3f}")

    best = results[0]
    print("\nBEST OVERALL:")
    print("Config:", best["cfg"])
    print("Params:", best["params"])
    print("Avg   :", best["avg_score"])

    print("\nPer-clip details for BEST:")
    for d in best["per_clip"]:
        print(f"\n--- {d['file']} ---")
        print("Transcript:", d["text"])
        print("Pred cmd  :", d["pred_cmd"])
        print("Score     :", f"{d['score']:.3f}")


# -----------------------------
# Run test
# -----------------------------
if __name__ == "__main__":
    # Define your filenames here:
    audio_files = [
        "go backwards 10cm_mhvvee3l.wav",
        "go forward 10cm_mhvv8b3i.wav",
        "turn left 20 degrees_mhvw41el.wav",
        "turn right 40 degrees_mhvw58q4.wav",
        "go forward 50cm_mhvvd39t.wav",
    ]

    # Define expected parsed commands for each file:
    expected_commands = {
        "go backwards 10cm_mhvvee3l.wav": {
            "action": "move",
            "direction": "backward",
            "distance": 0.10,
            "unit": "meters",
        },
        "go forward 10cm_mhvv8b3i.wav": {
            "action": "move",
            "direction": "forward",
            "distance": 0.10,
            "unit": "meters",
        },
        "turn left 20 degrees_mhvw41el.wav": {
            "action": "turn",
            "direction": "left",
            "distance": 20,
            "unit": "radians",
        },
        "turn right 40 degrees_mhvw58q4.wav": {
            "action": "turn",
            "direction": "right",
            "distance": 40,
            "unit": "radians",
        },
        "go forward 50cm_mhvvd39t.wav": {
            "action": "move",
            "direction": "forward",
            "distance": 0.5,
            "unit": "meters",
        },
    }

    find_best_whisper_settings_for_files(audio_files, expected_commands)
