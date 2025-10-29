import sounddevice as sd
import queue
import time
from mqqtInterface import MQTTInterface
from pc_code.turtleController import TurtleController
from pc_code.stringToCommand import string_to_command
from pc_code.transcriber import transcriber

def main():
    MQTT_SERVER = "10.32.162.201"
    MQTT_PORT = 1883
    MQTT_TOPIC_VEL = "mqtt_vel"
    MQTT_TOPIC_AUD = "mqtt_aud"
    
    mqtt_interface_vel = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL)
    mqtt_interface_aud = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_AUD)
    turtleController = TurtleController(mqtt_interface_vel)

    audio_queue = queue.Queue()
    transcribed_queue = queue.Queue()

    mqtt_interface_aud.listen(audio_queue)
    transcriber_instance = transcriber(audio_queue, transcribed_queue)
    
    
    try:
        whisperResponse = "" 
        while True:
            while transcribed_queue.empty():
                time.sleep(0.1)
            while not transcribed_queue.empty():
                whisperResponse += transcribed_queue.get()
                whisperResponse += " "
            
            command = string_to_command(whisperResponse)
            if command is not None:
                whisperResponse = ""  # Clear after successful command parsing
                turtleController.execute_command(command["action"], command["direction"], command["distance"])
                    
    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface_aud.client.loop_stop()
        mqtt_interface_vel.client.loop_stop()
        
        mqtt_interface_aud.client.disconnect()
        mqtt_interface_vel.client.disconnect()

if __name__ == "__main__":
    main()