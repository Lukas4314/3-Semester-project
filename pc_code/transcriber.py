import wave
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import threading
import time


class transcriber:
    def __init__(self, input_queue, output_queue):
        # Load model
        self.model = whisper.load_model("base.en")  # or "base.en" for better accuracy

        self.samplerate = 44100
        self.chunk_duration = 5      # seconds per processed chunk
        self.overlap_duration = 2.5  # seconds overlap
        self.samples_per_chunk = int(self.samplerate * self.chunk_duration)
        self.samples_overlap = int(self.samplerate * self.overlap_duration)
        
        # Queue for audio input
        self.input_queue = input_queue
        
        # Queue for transcription output
        self.output_queue = output_queue
        
        self.recorded_audio = []  # To accumulate audio data
        
        threading.Thread(target=self.transcribe_stream, daemon=True).start()

    def preprocess_segment(self, segment):
        segment = pad_or_trim(segment)  # trims/pads to 30s
        segment = segment.astype(np.float32)
        mel = log_mel_spectrogram(segment)
        return mel

    def transcribe_stream(self):
        buffer = np.zeros(0, dtype=np.float32)
        step = self.samples_per_chunk - self.samples_overlap

        while True:
            # Pull audio into buffer
            while not self.input_queue.empty():
                new_chunk = self.input_queue.get()
                #self.recorded_audio.append(new_chunk)
                buffer = np.append(buffer, new_chunk)
                
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
    def save_audio_to_wav(self, filename="output.wav"):
        # Concatenate all recorded audio chunks
        audio_data = np.concatenate(self.recorded_audio)
        # Normalize to int16 range
        audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        # Write to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_data.tobytes())
        print(f"Audio saved to {filename}")