import sounddevice as sd
from whisper.audio import pad_or_trim, log_mel_spectrogram
import queue
import time
from mqqtInterface import MQTTInterface
from turtleController import TurtleController
from stringToCommand import string_to_command, execute_command
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
        while True:
            while whisper_queue.empty():
                time.sleep(0.1)
            whisperResponse = "" 
            while not whisper_queue.empty():
                whisperResponse += whisper_queue.get()
            
            
            command = string_to_command(whisperResponse)
            if command is not None:
                if 'last_command' in locals() and command == last_command:
                    continue  # Skip executing the same command again
                turtleController.execute_command(command["action"], command["direction"], command["distance"])
            
            last_command = command
        
    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface.client.loop_stop()
        mqtt_interface.client.disconnect()

    
    


if __name__ == "__main__":
    main()