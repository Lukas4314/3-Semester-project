from turtle_code.microphoneInterface import MicrophoneInterface
from mqqtInterface import MQTTInterface
import queue
import time

def main():
    MQTT_SERVER = "127.0.0.1"
    MQTT_PORT = 1883
    MQTT_TOPIC_AUD = "mqtt_aud"

    mqtt_interface_aud = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_AUD)

    audio_queue = queue.Queue()
    mic_interface = MicrophoneInterface(audio_queue)

    try: 
        while True:
            while audio_queue.empty():
                time.sleep(0.1)
            
            while not audio_queue.empty():
                audio_data = audio_queue.get()
                mqtt_interface_aud.publish_buffer(audio_data)


    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface_aud.client.loop_stop()
        mqtt_interface_aud.client.disconnect()













if __name__ == "__main__":
    main()