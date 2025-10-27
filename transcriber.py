import sounddevice as sd
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import queue
import threading
import time
import stringToCommand


class transcriber:
    def __init__(self, output_queue):
        # Load model
        self.model = whisper.load_model("base.en")  # or "base.en" for better accuracy

        # Constants
        self.samplerate = 16000
        self.chunk_duration = 5      # seconds per processed chunk
        self.overlap_duration = 2.5  # seconds overlap
        self.samples_per_chunk = int(self.samplerate * self.chunk_duration)
        self.samples_overlap = int(self.samplerate * self.overlap_duration)
        # Audio queue
        self.q = queue.Queue()
        self.output_queue = output_queue
        threading.Thread(target=self.transcribe_stream, daemon=True).start()
        threading.Thread(target=self.record_audio, daemon=True).start()
        # Start audio recording
        
        

    def record_audio(self):
        with sd.InputStream(channels=1, samplerate=self.samplerate, callback=self.callback):
            while True:
                sd.sleep(1000)

    def callback(self, indata, frames, time_, status):
        self.q.put(indata[:, 0].copy())

    def preprocess_segment(self, segment):
        segment = pad_or_trim(segment)  # trims/pads to 30s
        mel = log_mel_spectrogram(segment)
        return mel

    def transcribe_stream(self):
        buffer = np.zeros(0, dtype=np.float32)
        step = self.samples_per_chunk - self.samples_overlap

        while True:
            # Pull audio into buffer
            while not self.q.empty():
                buffer = np.append(buffer, self.q.get())

            # If enough new audio for one step
            while len(buffer) >= self.samples_per_chunk:
                segment = buffer[:self.samples_per_chunk]

                # Preprocess and decode
                mel = self.preprocess_segment(segment)
                options = whisper.DecodingOptions(fp16=False, language="en")
                result = whisper.decode(self.model, mel, options)
                print(f"Transcribed: {result.text}")
                self.output_queue.put(result.text)

                # Slide buffer window (keep overlap)
                buffer = buffer[step:]

            time.sleep(0.1)





