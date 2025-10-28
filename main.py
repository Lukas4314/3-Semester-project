import sounddevice as sd
import queue
import time
from mqqtInterface import MQTTInterface
from turtleController import TurtleController
from stringToCommand import string_to_command
from transcriber import transcriber


def append_without_overlap(existing, new):
    """
    Append 'new' to 'existing' while avoiding duplicate overlap.
    Example:
        existing = "drive forward"
        new = "drive forward 5 meters"
        returns "drive forward 5 meters"
    """
    for i in range(len(new)):
        # Check if existing ends with the current slice of new
        if existing.endswith(new[:i]):
            return existing + new[i:]
    return existing + new


def main():
    #MQTT_SERVER = "10.32.162.201"
    #MQTT_PORT = 1883
    #MQTT_TOPIC = "mqtt_vel"
    
    #mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    #turtleController = TurtleController(mqtt_interface)
    
    whisper_queue = queue.Queue()
    transcriber_instance = transcriber(whisper_queue)

    try:
        whisperResponse = "" 
        while True:
            while whisper_queue.empty():
                time.sleep(0.1)
            
            while not whisper_queue.empty():
                new_chunk = whisper_queue.get().strip()
                whisperResponse = append_without_overlap(whisperResponse.strip(), new_chunk)
                whisperResponse += " "
            
            command = string_to_command(whisperResponse.strip())
            if command is not None:
                print("Recognized command:", command)
                whisperResponse = ""  # Reset after a valid command
                #turtleController.execute_command(command["action"], command["direction"], command["distance"])
                    
    except KeyboardInterrupt:
        print("Exiting program.")
        #mqtt_interface.client.loop_stop()
        #mqtt_interface.client.disconnect()


if __name__ == "__main__":

    main()
