import sounddevice as sd
import numpy as np
from pydub import AudioSegment
from datetime import datetime
import os


DURATION = 5         
SAMPLERATE = 44100   
CHANNELS = 1          
BITRATE = "192k"     
OUTPUT_FOLDER = r"C:\Users\runek\Documents\3. semester\projektgit\3-Semester-project\soundrecord"


os.makedirs(OUTPUT_FOLDER, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, f"recording_{timestamp}.mp3")


data = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=CHANNELS, dtype="int16")
sd.wait()


audio = AudioSegment(
    data.tobytes(),
    sample_width=2,
    frame_rate=SAMPLERATE,
    channels=CHANNELS
)
audio.export(OUTPUT_FILE, format="mp3", bitrate=BITRATE)
