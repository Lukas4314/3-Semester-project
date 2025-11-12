import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import os
import threading
import keyboard
from datetime import datetime, timezone

fs = 16000
folder = "recordings"
os.makedirs(folder, exist_ok=True)

print("Recording Press 'K' to stop.")

recorded_frames = []
stop_flag = threading.Event()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    recorded_frames.append(indata.copy())
    if stop_flag.is_set():
        raise sd.CallbackStop()

with sd.InputStream(samplerate=fs, channels=1, callback=audio_callback, dtype='int16'):
    keyboard.wait('k')
    stop_flag.set()

print("Recording stopped.")

audio_data = np.concatenate(recorded_frames, axis=0)


basename = input("Enter a name for this recording (without extension): ").strip() or "recording"


epoch_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
base36_time = np.base_repr(epoch_ms, 36).lower()  

filename = f"{basename}_{base36_time}.wav"
wav_path = os.path.join(folder, filename)


write(wav_path, fs, audio_data)
print(f"Saved recording to: {wav_path}")
