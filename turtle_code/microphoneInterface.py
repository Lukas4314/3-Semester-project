import sounddevice as sd
import numpy as np
import threading
import wave

class MicrophoneInterface:
    def __init__(self, output_queue, microphone_name = "USB THING"):
        # Temporary
        
        if microphone_name == "USB THING":
            pass
            #print("PLEASE SET THE CORRECT MICROPHONE STANDARD AND THEN DELETE THIS CODE")
            #raise NotImplementedError("Microphone selection needs to be implemented properly.")
        
        # Constant
        self.samplerate = 16000
        # Audio queue
        self.q = output_queue
        threading.Thread(target=self.record_audio, daemon=True).start()
        
        # Start audio recording
        self.recorded_audio = []  # To accumulate audio data

    def record_audio(self):
        device_index = None
        for i, dev in enumerate(sd.query_devices()):
                if "USB" in dev['name'] and dev['max_input_channels'] > 0:
                        device_index = i
                        samplerate = int(dev['default_samplerate'])
                        print(f"Using device {i}: {dev['name']} with samplerate {samplerate}")
                        self.samplerate = samplerate
                        break
        with sd.InputStream(device=device_index, channels=1, samplerate=self.samplerate, callback=self.callback):
            while True:
                sd.sleep(1000)

    def callback(self, indata, frames, time_, status):
        self.q.put(indata[:, 0].copy())
        self.recorded_audio.append(indata[:, 0].copy())

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