import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import threading
import time


class transcriber:
    def __init__(self, input_queue, output_queue):
        # Load model
        self.model = whisper.load_model("base.en")  # or "base.en" for better accuracy

        self.chunk_duration = 5      # seconds per processed chunk
        self.overlap_duration = 2.5  # seconds overlap
        self.samples_per_chunk = int(self.samplerate * self.chunk_duration)
        self.samples_overlap = int(self.samplerate * self.overlap_duration)
        
        # Queue for audio input
        self.input_queue = input_queue
        
        # Queue for transcription output
        self.output_queue = output_queue
        
        threading.Thread(target=self.transcribe_stream, daemon=True).start()

    def preprocess_segment(self, segment):
        segment = pad_or_trim(segment)  # trims/pads to 30s
        mel = log_mel_spectrogram(segment)
        return mel

    def transcribe_stream(self):
        buffer = np.zeros(0, dtype=np.float32)
        step = self.samples_per_chunk - self.samples_overlap

        while True:
            # Pull audio into buffer
            while not self.input_queue.empty():
                new_chunk = self.input_queue.get()
                buffer = np.append(buffer, new_chunk)

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