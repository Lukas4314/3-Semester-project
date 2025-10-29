import paho.mqtt.client as mqtt
import json
import time

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
    
    def disconnect(self):
        self.publish_command(0.0, 0.0)
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker.")



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
