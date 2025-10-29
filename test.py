import sounddevice as sd
import numpy as np


samplerate = 16000  # Hertz

# ---- Record audio ----
duration = 5  # seconds
print(f"Recording for {duration} seconds...")
audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
sd.wait()
print("Recording finished!")
