import sounddevice as sd
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import queue
import threading
import time

# Load model
model = whisper.load_model("base.en")  # or "base.en" for better accuracy

# Constants
samplerate = 16000
chunk_duration = 5      # seconds per processed chunk
overlap_duration = 2.5  # seconds overlap
samples_per_chunk = int(samplerate * chunk_duration)
samples_overlap = int(samplerate * overlap_duration)

# Audio queue
q = queue.Queue()

def callback(indata, frames, time_, status):
    q.put(indata[:, 0].copy())

def preprocess_segment(segment):
    segment = pad_or_trim(segment)  # trims/pads to 30s
    mel = log_mel_spectrogram(segment)
    return mel

def transcribe_stream():
    buffer = np.zeros(0, dtype=np.float32)
    step = samples_per_chunk - samples_overlap

    while True:
        # Pull audio into buffer
        while not q.empty():
            buffer = np.append(buffer, q.get())

        # If enough new audio for one step
        while len(buffer) >= samples_per_chunk:
            segment = buffer[:samples_per_chunk]

            # Preprocess and decode
            mel = preprocess_segment(segment)
            options = whisper.DecodingOptions(fp16=False, language="en")
            result = whisper.decode(model, mel, options)
            print(f">>> {result.text.strip()}")

            # Slide buffer window (keep overlap)
            buffer = buffer[step:]

        time.sleep(0.1)

# Start audio recording
stream = sd.InputStream(callback=callback, channels=1, samplerate=samplerate)
threading.Thread(target=transcribe_stream, daemon=True).start()

with stream:
    print("Listening with overlap... (press Ctrl+C to stop)")
    while True:
        time.sleep(1)
