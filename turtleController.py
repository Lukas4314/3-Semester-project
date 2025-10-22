from mqqtInterface import MQTTInterface
import time

class TurtleController:
    def __init__(self, mqtt_interface):
        self.mqtt_interface = mqtt_interface

    def move_forward(self, speed):
        print(f"Moving forward at speed {speed}")
        self.mqtt_interface.publish_command(speed, 0.0)

    def turn(self, angular_speed):
        print(f"Turning at angular speed {angular_speed}")
        self.mqtt_interface.publish_command(0.0, angular_speed)
    
    def stop(self):
        print("Stopping the turtle")
        self.mqtt_interface.publish_command(0.0, 0.0)

if __name__ == "__main__":

    # Define MQTT connection details
    MQTT_SERVER = "10.32.162.201"
    MQTT_PORT = 1883
    MQTT_TOPIC = "mqtt_vel"
    
    mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)
    turtle_controller = TurtleController(mqtt_interface)
    
    turtle_controller.move_forward(1.0)
    time.sleep(1)
    turtle_controller.turn(0.5)
    time.sleep(1)
    turtle_controller.stop()
    mqtt_interface.disconnect()