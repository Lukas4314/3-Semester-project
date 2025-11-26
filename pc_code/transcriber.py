from email.mime import audio
import string
import sounddevice as sd
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import threading
import time
import queue
import wave
import torch
import torchaudio

class transcriber:
    def __init__(self, input_queue):
        # Load model
        self.model = whisper.load_model("base.en")  # or "base.en" for better accuracy

        self.samplerate = 44100
        self.chunk_duration = 5      # seconds per processed chunk
        self.overlap_duration = 2.5  # seconds overlap
        self.samples_per_chunk = int(self.samplerate * self.chunk_duration)
        self.samples_overlap = int(self.samplerate * self.overlap_duration)
        # Audio queue
        self.input_queue = input_queue
        self.output_queue = queue.Queue()
        self.total_string = ""
        self.recorded_audio = []  # To accumulate audio data
        threading.Thread(target=self.transcribe_stream, daemon=True).start()

        
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
        new = new.lower()
        
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


    def preprocess_segment(self, segment):
        """
        Convert a 44.1 kHz NumPy audio segment to Whisper-compatible log-Mel spectrogram.
        """

        # Convert from int16 to float32 in -1.0 to 1.0 range
        if segment.dtype == np.int16:
            #segment = segment.astype(np.float32)
            segment = segment.astype(np.float32) / 32768.0
        else:
            segment = segment.astype(np.float32)

        # Convert to float32 tensor
        segment = torch.from_numpy(segment)

        # Resample to 16 kHz if needed
        if self.samplerate != 16000:
            resampler = torchaudio.transforms.Resample(
                orig_freq=self.samplerate, new_freq=16000
            )
            segment = resampler(segment)

        # Pad or trim to 30s (Whisper default)
        segment = pad_or_trim(segment)

        # Compute log-Mel spectrogram
        mel = log_mel_spectrogram(segment)
        
        return mel

    def transcribe_stream(self):
        buffer = np.zeros(0, dtype=np.int16)
        step = self.samples_per_chunk - self.samples_overlap

        while True:
            # Pull audio into buffer
            while not self.input_queue.empty():
                new_chunk = self.input_queue.get()
                self.recorded_audio.append(new_chunk)
                buffer = np.append(buffer, new_chunk)
                
            while len(buffer) >= self.samples_per_chunk:
                segment = buffer[:self.samples_per_chunk]
                
                # Preprocess and decode
                mel = self.preprocess_segment(segment)
                

                options = whisper.DecodingOptions(fp16=False, language="en")
                result = whisper.decode(self.model, mel, options)

                print("Segment transcription:", result.text)

                # Handle transcription output
                result_after_append =self.append_without_overlap(result.text)
                self.output_queue.put(result_after_append)

                # Slide buffer window (keep overlap)
                buffer = buffer[step:]

            time.sleep(0.1)

    def getNewTranscription(self):
        """Retrieve new transcription text if available."""
        texts = []
        while not self.output_queue.empty():
            texts.append(self.output_queue.get())
        return " ".join(texts)
        

    def save_list_to_wav(self, audio_list, filename="output.wav"):
        # Concatenate all recorded audio chunks
        audio = np.concatenate(audio_list)
        audio_int16 = np.int16(audio * 32767)
        # Normalize to int16 range
        # Write to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_int16.tobytes())
        print(f"Audio saved to {filename}")


    def save_audio_to_wav(self, filename="output.wav"):
        self.save_list_to_wav(self.recorded_audio, filename)