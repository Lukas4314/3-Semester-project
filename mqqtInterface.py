import wave
import paho.mqtt.client as mqtt
import json
import time
import numpy as np
import ast
import struct
import queue
from consts import SAMPLE_RATE

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
            bigInt16 = arr[1]
            smallInt16 = arr[0]
            arr = arr[2:]

            # Convert to unsigned 16-bit integers
            big_u = np.uint16(bigInt16)
            small_u = np.uint16(smallInt16)

            # Combine into a 32-bit unsigned integer
            message_index = (int(big_u) << 16) | int(small_u)

            message_index = (big_u << 16) | small_u
            
            output_queue.put((message_index, arr))
            self.recorded_data.append(arr)
            
        self.client.subscribe(self.topic)
        self.client.on_message = on_message
        self.client.loop_start()
    
    def listen_and_clone_into_2_outputs(self, output_queue1, output_queue2):
        def on_message(client, userdata, msg):
            
            # number of int16 values
            count = len(msg.payload) // 2  

            values = struct.unpack('<' + 'h'*count, msg.payload)
            arr = np.array(values, dtype=np.int16)
            
            
            bigInt16 = arr[1]
            smallInt16 = arr[0]
            arr = arr[2:]

            # Convert to unsigned 16-bit integers
            big_u = np.uint16(bigInt16)
            small_u = np.uint16(smallInt16)

            # Combine into a 32-bit unsigned integer
            message_index = (int(big_u) << 16) | int(small_u)
            
            #arr = arr[1::2]
            output_queue1.put((message_index, arr))
            output_queue2.put((message_index, arr))
            self.recorded_data.append(arr)
            
        self.client.subscribe(self.topic)
        self.client.on_message = on_message
        self.client.loop_start()
    
    def listen_into_2_outputs(self, output_queue1, output_queue2):
        def on_message(client, userdata, msg):
            
            # number of int16 values
            count = len(msg.payload) // 2  

            values = struct.unpack('<' + 'h'*count, msg.payload)
            arr = np.array(values, dtype=np.int16)

            bigInt16 = arr[1]
            smallInt16 = arr[0]
            arr = arr[2:]

            # Convert to unsigned 16-bit integers
            big_u = np.uint16(bigInt16)
            small_u = np.uint16(smallInt16)

            # Combine into a 32-bit unsigned integer
            message_index = (int(big_u) << 16) | int(small_u)
            
            
            
            output_queue1.put((message_index, arr[0::2]))
            output_queue2.put((message_index, arr[1::2]))
            self.recorded_data.append(arr[1::2])
            
        self.client.subscribe(self.topic)
        self.client.on_message = on_message
        self.client.loop_start()    
    
    
    def listen_into_3_outputs(self, output_queue1, output_queue2, output_queue3):
        def on_message(client, userdata, msg):
            
            # number of int16 values
            count = len(msg.payload) // 2  

            values = struct.unpack('<' + 'h'*count, msg.payload)
            arr = np.array(values, dtype=np.int16)

            arr1 = arr[0::3]
            arr2 = arr[1::3]
            arr3 = arr[2::3]

            print(f"Lengths: {len(arr1)}, {len(arr2)}, {len(arr3)}")
            
            bigInt16_1 = arr1[1]
            smallInt16_1 = arr1[0]
            arr1 = arr1[2:]
            
            bigInt16_2 = arr2[1]
            smallInt16_2 = arr2[0]
            arr2 = arr2[2:]

            bigInt16_3 = arr3[1]
            smallInt16_3 = arr3[0]
            arr3 = arr3[2:]

            bigInt16 = arr[1]
            smallInt16 = arr[0]
            arr = arr[2:]

            # Convert to unsigned 16-bit integers
            big_u = np.uint16(bigInt16)
            small_u = np.uint16(smallInt16)

            # Combine into a 32-bit unsigned integer
            message_index = (int(big_u) << 16) | int(small_u)
            
            
            
            output_queue1.put((message_index, arr[0::2]))
            output_queue2.put((message_index, arr[1::2]))
            self.recorded_data.append(arr[1::2])
            
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
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        print(f"Audio saved to {filename}")


if __name__ == "__main__":
    # Define MQTT connection details
    MQTT_SERVER = "10.250.34.201"
    MQTT_PORT = 1883
    MQTT_TOPIC = "DUMMY"
    mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    time.sleep(3)
    qeueie1 = queue.Queue()
    qeueie2 = queue.Queue()
    mqtt_interface.listen_and_clone_into_2_outputs(qeueie1, qeueie2)

    try:
        while True:
            if not qeueie1.empty():
                index, data = qeueie1.get()
                print(f"Queue 1 - Message index: {index}, Data length: {len(data)}")

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        mqtt_interface.disconnect()
