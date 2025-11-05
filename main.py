import string
import sounddevice as sd
import queue
import time
from mqqtInterface import MQTTInterface
from pc_code.turtleController import TurtleController
from pc_code.stringToCommand import string_to_command
from pc_code.transcriber import transcriber
from consts import MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL, MQTT_TOPIC_AUD



def main():
    mqtt_interface_vel = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL)
    mqtt_interface_aud = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_AUD)
    turtleController = TurtleController(mqtt_interface_vel)


    audio_queue = queue.Queue()

    mqtt_interface_aud.listen(audio_queue)
    transcriber_instance = transcriber(audio_queue)
    
    
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
        mqtt_interface_aud.client.loop_stop()
        mqtt_interface_vel.client.loop_stop()


        mqtt_interface_aud.client.disconnect()
        mqtt_interface_vel.client.disconnect()        
        
        transcriber_instance.save_audio_to_wav()
        #mqtt_interface_aud.save_to_wav()


if __name__ == "__main__":

    main()
