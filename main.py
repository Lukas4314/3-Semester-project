import sounddevice as sd
import queue
import time
from mqqtInterface import MQTTInterface
from turtleController import TurtleController
from stringToCommand import string_to_command
from transcriber import transcriber

def main():
    MQTT_SERVER = "10.32.162.201"
    MQTT_PORT = 1883
    MQTT_TOPIC = "mqtt_vel"
    
    mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    turtleController = TurtleController(mqtt_interface)
    
    whisper_queue = queue.Queue()
    transcriber_instance = transcriber(whisper_queue)
    try:
        whisperResponse = "" 
        while True:
            while whisper_queue.empty():
                time.sleep(0.1)
            while not whisper_queue.empty():
                whisperResponse += whisper_queue.get()
                whisperResponse += " "
            
            
            command = string_to_command(whisperResponse)
            if command is not None:
                whisperResponse = ""  # Clear after successful command parsing
                turtleController.execute_command(command["action"], command["direction"], command["distance"])
                    
    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface.client.loop_stop()
        mqtt_interface.client.disconnect()
        transcriber_instance.save_audio_to_wav("recorded_audio.wav")

    
    


if __name__ == "__main__":
    main()