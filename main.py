import string
import sounddevice as sd
import queue
import time
from mqqtInterface import MQTTInterface
from turtleController import TurtleController
from stringToCommand import string_to_command
from transcriber import transcriber


def main():
    #MQTT_SERVER = "10.32.162.201"
    #MQTT_PORT = 1883
    #MQTT_TOPIC = "mqtt_vel"
    
    #mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    #turtleController = TurtleController(mqtt_interface)
    
    transcriber_instance = transcriber()

    try:
        analysisstring = ""
        while True:
            new_transcription = transcriber_instance.getNewTranscription()
            if new_transcription != "":
                analysisstring += new_transcription
                print("Transcribed so far:", analysisstring)
            else:
                time.sleep(0.1)
                continue

            command = string_to_command(analysisstring.strip())
            if command is not None:
                print("Recognized command:", command)
                analysisstring = ""  # Reset after a valid command
                #turtleController.execute_command(command["action"], command["direction"], command["distance"])
                    
    except KeyboardInterrupt:
        print("Exiting program.")
        #mqtt_interface.client.loop_stop()
        #mqtt_interface.client.disconnect()


if __name__ == "__main__":

    main()
