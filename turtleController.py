from mqqtInterface import MQTTInterface
import time


SPEED = 0.2 # meaning when 1 is written it is 1 meter per second
ANGULAR_SPEED = 1 # meaning when 1 is written it is 1 degree per second


class TurtleController:
    # We need to implement threading in the future so the robot can move and receieve new commands at the same time
    def __init__(self, mqtt_interface):
        self.mqtt_interface = mqtt_interface

    def set_forward_speed(self, speed):
        print(f"Setting forward speed to {speed}")
        self.mqtt_interface.publish_command(speed, 0.0)

    def set_turn_speed(self, angular_speed):
        print(f"Setting turn speed to {angular_speed}")
        self.mqtt_interface.publish_command(0.0, angular_speed)

    def move_forward(self, distance):
        print(f"Moving forward at speed {SPEED}")
        self.set_forward_speed(SPEED)
        time.sleep(distance / SPEED)
        self.set_forward_speed(0.0)

    def move_backward(self, distance):
        print(f"Moving backward at speed {SPEED}")
        self.set_forward_speed(-SPEED)
        time.sleep(distance / SPEED)
        self.set_forward_speed(0.0)

    def turn_counter_clockwise(self, amount_deg):
        print(f"Turning counter-clockwise at angular speed {ANGULAR_SPEED}")
        self.set_turn_speed(ANGULAR_SPEED)
        time.sleep(amount_deg / ANGULAR_SPEED)
        self.set_turn_speed(0.0)

    def turn_clockwise(self, amount_deg):
        print(f"Turning clockwise at angular speed {ANGULAR_SPEED}")
        self.set_turn_speed(-ANGULAR_SPEED)
        time.sleep(amount_deg / ANGULAR_SPEED)
        self.set_turn_speed(0.0)

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