import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
import paho.mqtt.client as mqtt
import json

BURGER_MAX_LIN_VEL = 0.22
BURGER_MAX_ANG_VEL = 2.84

def constrain(input_vel, low_bound, high_bound):
    if input_vel < low_bound:
        input_vel = low_bound
    elif input_vel > high_bound:
        input_vel = high_bound
    else:
        input_vel = input_vel
    
    return input_vel

def check_linear_limit_velocity(velocity):
    return constrain(velocity, -BURGER_MAX_LIN_VEL, BURGER_MAX_LIN_VEL)
    


def check_angular_limit_velocity(velocity):
    return constrain(velocity, -BURGER_MAX_ANG_VEL, BURGER_MAX_ANG_VEL)
    


class MqttToCmdVelNode(Node):
    def __init__(self):
        super().__init__('mqtt_to_cmd_vel')
        
        # Create a ROS2 publisher to publish on the cmd_vel topic
        self.publisher = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        
        # MQTT client setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Define MQTT connection details
        mqtt_server = "127.0.0.1"  # Alternatively replace with your MQTT server address
        mqtt_port = 1883           # Replace with your MQTT server port
        mqtt_topic = "mqtt_vel"    # Replace with the MQTT topic to subscribe to
        
        # Connect to the MQTT broker
        self.mqtt_client.connect(mqtt_server, mqtt_port, 60)
        
        # Start the MQTT client loop in a non-blocking way
        self.mqtt_client.loop_start()
        
        # Subscribe to the MQTT topic
        self.mqtt_client.subscribe(mqtt_topic)
        
        self.get_logger().info(f"Subscribed to MQTT topic: {mqtt_topic}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.get_logger().info("Connected to MQTT broker successfully.")
        else:
            self.get_logger().error("Failed to connect to MQTT broker, return code: %d", rc)

    def on_message(self, client, userdata, msg):
        try:
            # Assuming the MQTT message payload is a JSON with 'linear' and 'angular' fields
            payload = json.loads(msg.payload.decode())

            #Check if messages fit within constraints
            linear_vel = check_linear_limit_velocity(payload['linear']['x'])
            angular_vel = check_angular_limit_velocity(payload['angular']['z'])
            
            # Create a Twist message
            twist_msg = TwistStamped()
            twist_msg.header.stamp = self.get_clock().now().to_msg()
            twist_msg.header.frame_id = ""
            twist_msg.twist.linear.x = float(linear_vel)
            twist_msg.twist.angular.z = float(angular_vel)
            
            # Publish to cmd_vel topic
            self.publisher.publish(twist_msg)
            self.get_logger().info(f"Published cmd_vel: linear={twist_msg.twist.linear.x}, angular={twist_msg.twist.angular.z}")
        
        except json.JSONDecodeError:
            self.get_logger().error("Failed to decode JSON from MQTT message.")
        except KeyError as e:
            self.get_logger().error(f"Missing expected key in MQTT message: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = MqttToCmdVelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.mqtt_client.loop_stop()  # Stop the MQTT loop
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()