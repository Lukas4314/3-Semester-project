from turtle_code.microphoneInterface import MicrophoneInterface
from mqqtInterface import MQTTInterface
import queue
import time
import numpy as np
from consts import LOCALHOST, MQTT_PORT, MQTT_TOPIC_AUD

def main():
    mqtt_interface_aud = MQTTInterface(LOCALHOST, MQTT_PORT, MQTT_TOPIC_AUD)

    audio_queue = queue.Queue()
    mic_interface = MicrophoneInterface(audio_queue)

    buffer = np.zeros(0, dtype=np.float32)
    samplerate = 44100
    chunk_duration = 5
    samples_per_chunk = int(samplerate * chunk_duration)

    try: 
        while True:
            while audio_queue.empty():
                time.sleep(0.1)
            
            while not audio_queue.empty():
                #print(audio_queue.qsize())
                audio_data = audio_queue.get()
                buffer = np.append(buffer, audio_data)
            # If enough new audio for one step
            while len(buffer) >= samples_per_chunk:
                segment = buffer[:samples_per_chunk]
                print("Transcribing segment...")
                
                mqtt_interface_aud.publish_buffer(segment.tolist())

    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface_aud.client.loop_stop()
        mqtt_interface_aud.client.disconnect()

if __name__ == "__main__":
    main()