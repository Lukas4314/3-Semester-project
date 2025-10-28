import string
import sounddevice as sd
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import queue
import threading
import time
import stringToCommand
import wave


class transcriber:
    def __init__(self):
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
        self.output_queue = queue.Queue()
        threading.Thread(target=self.transcribe_stream, daemon=True).start()
        threading.Thread(target=self.record_audio, daemon=True).start()
        # Start audio recording

        self.total_string = ""
        self.recorded_audio = []  # To accumulate audio data

        
    def append_without_overlap(self, new):
        """
        Append only the non-overlapping part of 'new' to 'existing'.
        Works even if 'new' contains the entire 'existing' text again.
        """
        # Trim whitespace
        self.total_string = self.total_string.strip()

        for punctuation in string.punctuation:
            self.total_string = self.total_string.replace(punctuation, "")
            new = new.replace(punctuation, "")

        new = new.strip()

        # If new already contains existing entirely, just replace it
        if new.startswith(self.total_string):
            self.total_string = new
            return new

        # Find overlap from the end of existing and start of new
        max_overlap = min(len(self.total_string), len(new))
        overlap_length = 0

        for i in range(1, max_overlap + 1):
            if self.total_string.endswith(new[:i]):
                overlap_length = i

        self.total_string += new[overlap_length:]
        return new[overlap_length:]


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

    def transcribe_stream(self, save_audio=True):
        buffer = np.zeros(0, dtype=np.float32)
        step = self.samples_per_chunk - self.samples_overlap

        while True:
            # Pull audio into buffer
            while not self.q.empty():
                new_chunk = self.q.get()
                buffer = np.append(buffer, new_chunk)
                if save_audio:
                    self.recorded_audio.append(new_chunk)

            # If enough new audio for one step
            while len(buffer) >= self.samples_per_chunk:
                segment = buffer[:self.samples_per_chunk]

                # Preprocess and decode
                mel = self.preprocess_segment(segment)
                options = whisper.DecodingOptions(fp16=False, language="en")
                result = whisper.decode(self.model, mel, options)
                
                # Handle transcription output
                resultafterappend =self.append_without_overlap(result.text)
                self.output_queue.put(resultafterappend)

                # Slide buffer window (keep overlap)
                buffer = buffer[step:]

            time.sleep(0.1)

    def getNewTranscription(self):
        """Retrieve new transcription text if available."""
        texts = []
        while not self.output_queue.empty():
            texts.append(self.output_queue.get())
        return " ".join(texts)
        

    def save_audio_to_wav(self, filename="output.wav"):
        """Combine float32 chunks into a WAV file."""
        audio = np.concatenate(self.recorded_audio)
        # Convert from float32 (-1.0 to 1.0) to int16
        audio_int16 = np.int16(audio * 32767)
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_int16.tobytes())
        print(f"Audio saved to {filename}")



