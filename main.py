import string
import sounddevice as sd
import queue
import time
from mqttInterface import MQTTInterface
from pc_code.turtleController import TurtleController
from pc_code.stringToCommand import string_to_command
from pc_code.transcriber import transcriber
from consts import MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL, MQTT_TOPIC_AUD1, MQTT_TOPIC_AUD0, RED, RED_END, SHOULD_LOG, MQTT_TOPIC_BATCH
from logger import *


def main():
    # Remove-Item "debug_segments\*" -Recurse -Force
    mqtt_interface_vel = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL)
    mqtt_interface_aud0 = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_AUD0)
    mqtt_interface_aud1 = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_AUD1)
    mqtt_interface_aud = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_BATCH)

    audio_queue0 = queue.Queue()
    audio_queue1 = queue.Queue()
    audio_queue2 = queue.Queue()
    audio_queue2_clone = queue.Queue()
    
    turtleController = TurtleController(mqtt_interface_vel, audio_queue0, audio_queue1, audio_queue2)

    mqtt_interface_aud0.listen_into_2_outputs(audio_queue0, audio_queue1)
    mqtt_interface_aud1.listen_and_clone_into_2_outputs(audio_queue2, audio_queue2_clone)
    transcriber_instance = transcriber(audio_queue2_clone)
    
    if SHOULD_LOG:
        Logger.initialize(Logger.get_all_logger_keys())
    
    try:
        analysisstring = ""
        while True:
            start_index, end_index, new_transcription = transcriber_instance.getNewTranscription()
            if new_transcription != "":
                print(f"Transcribed so far:", analysisstring + RED + new_transcription + RED_END)
                analysisstring += new_transcription + " "
                
            else:
                time.sleep(0.01)
                continue

            command = string_to_command(analysisstring.strip())
            
            if command is not None:
                
                if command["action"] == "come here":
                    best_index = transcriber_instance.find_nearest_here(start_index, end_index)
                    offset  = 2
                    start_buffer = 0
                    end_buffer = 0
                    turtleController.go_to_human(start_index = best_index - start_buffer + offset, end_index = best_index + end_buffer + offset)
                else:
                    print("Recognized command:", command)
                    analysisstring = ""  # Reset after a valid command
                    turtleController.execute_command(command["action"], command["direction"], command["distance"])
                
                if SHOULD_LOG:
                    Logger.set_value(ATTEMPS_AT_TALKING_BEFORE_REGESTERING, input("How many tries before registering the command? (1 is good, 0 if it is skitzophrenic): "))
                    Logger.set_value(ACTION, command["action"])
                    Logger.write_row()
                    
    except KeyboardInterrupt:
        print("Exiting program.")
        mqtt_interface_aud0.client.loop_stop()
        mqtt_interface_aud1.client.loop_stop()
        mqtt_interface_vel.client.loop_stop()


        mqtt_interface_aud0.client.disconnect()
        mqtt_interface_aud1.client.disconnect()
        mqtt_interface_vel.client.disconnect()
        
        #transcriber_instance.save_audio_to_wav()
        mqtt_interface_aud0.save_to_wav("audio_aud0.wav")
        mqtt_interface_aud1.save_to_wav("audio_aud1.wav")
    finally:
        if SHOULD_LOG:
            Logger.close()

if __name__ == "__main__":

    main()
