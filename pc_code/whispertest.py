import queue
import time

import numpy as np
import sounddevice as sd

from transcriber import transcriber
from stringToCommand import string_to_command


def main():
    # 1. Create queue and transcriber
    input_queue = queue.Queue()
    t = transcriber(input_queue)   # this starts transcribe_stream in a thread

    samplerate = t.samplerate      # 44100
    channels = 1                   # mono

    # 2. Define callback that pushes mic audio into the queue
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status, flush=True)
        # indata is shape (frames, channels)
        # convert to float32 1D mono
        audio = indata[:, 0].astype(np.float32)
        # push into the transcriber's input queue
        input_queue.put(audio)

    # 3. Open a live input stream
    print("🎤 Starting microphone stream. Speak into your mic. Ctrl+C to stop.")
    with sd.InputStream(
        samplerate=samplerate,
        channels=channels,
        callback=audio_callback,
        blocksize=0,   # let sounddevice choose
    ):
        try:
            RED = "\033[31m"
            RED_END = "\033[0m"
            analysisstring = ""
            while True:
                new_transcription = t.getNewTranscription()
                if new_transcription != "":
                    print(f"Transcribed so far:", analysisstring + RED + new_transcription + RED_END)
                    analysisstring += new_transcription + " "
                    
                else:
                    time.sleep(0.01)
                    continue

                command = string_to_command(analysisstring.strip())
                
                if command is not None:
                    print("Recognized command:", command)
                    analysisstring = ""  # Reset after a valid command
                #elif len(analysisstring.split()) > 50:
                    # Prevent analysisstring from growing indefinitely
                    #analysisstring = " ".join(analysisstring.split()[25:])
                    
                    
        except KeyboardInterrupt:
            print("Exiting program.")


if __name__ == "__main__":
    main()
