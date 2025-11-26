import wave
import paho.mqtt.client as mqtt
import json
import time
import numpy as np
import ast
import struct



class MQTTInterface:
    def __init__(self, server, port, topic):
        # Initialize the MQTT client
        self.server = server
        self.port = port
        self.topic = topic
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.connect(self.server, self.port, 60)
        self.client.loop_start()
        
        
        # TEMPRORARY:
        self.recorded_data = []

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to MQTT broker successfully")
        else:
            print(f"Failed to connect to MQTT broker")

    def publish_command(self, linear_x, angular_z):
        # Prepare the payload to match a Twist message structure
        payload = {
            "linear": {
                "x": linear_x,
                "y": 0.0,
                "z": 0.0
            },
            "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": angular_z
            }
        }
    
        # Publish the payload to the MQTT topic
        self.client.publish(self.topic, json.dumps(payload), qos=1)
        print(f"Published to {self.topic}: {payload}")

    def publish_buffer(self, buffer):
        # Publish raw buffer data as a JSON array
        self.client.publish(self.topic, json.dumps(buffer), qos=1)
    
    def listen(self, output_queue):
        def on_message(client, userdata, msg):
            
            # number of int16 values
            count = len(msg.payload) // 2  

            values = struct.unpack('<' + 'h'*count, msg.payload)
            arr = np.array(values, dtype=np.int16)
            output_queue.put(arr)
            self.recorded_data.append(arr)
            

        self.client.subscribe(self.topic)
        self.client.on_message = on_message
        self.client.loop_start()
    
    def disconnect(self):
        self.publish_command(0.0, 0.0)
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker.")

    def save_to_wav(self, filename="output.wav"):
        # Normalize to int16 range
        audio_data = np.concatenate(self.recorded_data).astype(np.int16)
        # Write to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(44100)
            wf.writeframes(audio_data.tobytes())
        print(f"Audio saved to {filename}")


if __name__ == "__main__":
    # Define MQTT connection details
    MQTT_SERVER = "10.32.162.201"
    MQTT_PORT = 1883
    MQTT_TOPIC = "mqtt_vel"
    mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    time.sleep(3)

    try:
        mqtt_interface.publish_command(1.0, 0.5)
        time.sleep(2)
        mqtt_interface.publish_command(0.0, 0.0)
        time.sleep(2)
        mqtt_interface.publish_command(0.4, 0)
        time.sleep(2)
        mqtt_interface.publish_command(1, 6)

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        mqtt_interface.disconnect()
