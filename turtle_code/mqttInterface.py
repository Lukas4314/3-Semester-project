import paho.mqtt.client as mqtt
import json
import time
import numpy as np
import ast
import struct
import queue

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



    def publish_buffer(self, buffer):
        # Publish raw buffer data as a JSON array
        self.client.publish(self.topic, json.dumps(buffer), qos=1)
    
    
    def disconnect(self):
        self.publish_command(0.0, 0.0)
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker.")
