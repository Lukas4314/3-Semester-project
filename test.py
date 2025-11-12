from whisper.audio import pad_or_trim, log_mel_spectrogram
import whisper

model = whisper.load_model("base.en")

SOUND_PATH = "debug_segment.wav"




options = whisper.DecodingOptions(fp16=False, language="en")
mel = log_mel_spectrogram(pad_or_trim(whisper.load_audio(SOUND_PATH)))

# Save the mel spectrogram for inspection
import numpy as np
np.save("debug_mel.npy", mel.numpy())

result = whisper.decode(model, mel, options)
print(result.text)