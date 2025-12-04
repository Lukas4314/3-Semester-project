import queue
import time
import itertools

import numpy as np
import sounddevice as sd
import string
from pc_code.stringToCommand import string_to_command
from pc_code.transcriber import transcriber


def main():
    # 1. Create queue and transcriber
    input_queue = queue.Queue()
    t = transcriber(input_queue)   # this starts transcribe_stream in a thread

    samplerate = t.samplerate      # from transcriber (e.g. 44100)
    channels = 1                   # mono

    # simple increasing message index: 0,1,2,3,...
    msg_counter = itertools.count()

    # 2. Define callback that pushes mic audio into the queue
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status, flush=True)
        # indata is float32 in [-1, 1], shape (frames, channels)
        mono = indata[:, 0]

        # convert to int16 like your transcriber expects
        audio_int16 = (mono * 32767).astype(np.int16)

        message_index = next(msg_counter)
        # push (message_index, chunk) into the transcriber's input queue
        input_queue.put((message_index, audio_int16))

    # 3. Open a live input stream
    print("🎤 Starting microphone stream. Speak into your mic. Say 'come here'. Ctrl+C to stop.")
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
                # get text + index range from transcriber
                start_index, end_index, new_transcription = t.getNewTranscription()
                if new_transcription != "":
                    print("Transcribed so far:", analysisstring + RED + new_transcription + RED_END)
                    analysisstring += new_transcription + " "
                else:
                    time.sleep(0.01)
                    continue

                # --- 1) test plain 'here' detection (for debugging) ---
                if "here" in new_transcription.lower().split():
                    print(">>> Heard the word here in this chunk")

                # --- 2) run your command parser as before ---
                command = string_to_command(analysisstring.strip())

                if command is not None and command["action"] == "come here":
                    print(">>> Detected command: COME HERE")
                    best_index = t.find_nearest_here(start_index, end_index)
                    print(">>> Estimated 'here' is around message_index:", best_index)
                    analysisstring = ""
                    continue

                if command is not None:
                    print("Recognized command:", command)
                    analysisstring = ""  # Reset after a valid command

        except KeyboardInterrupt:
            print("Exiting program.")


if __name__ == "__main__":
    main()
