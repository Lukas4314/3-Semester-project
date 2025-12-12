#!/usr/bin/env python3
import json
import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import JointState
import paho.mqtt.client as mqtt

# TurtleBot3 Burger defaults
BURGER_MAX_LIN_VEL = 0.22
BURGER_MAX_ANG_VEL = 2.84

WHEEL_RADIUS = 0.033      # meters
WHEEL_SEPARATION = 0.160  # meters (Burger)


def constrain(x, lo, hi):
    return max(lo, min(hi, x))


def check_linear_limit_velocity(v):
    return constrain(v, -BURGER_MAX_LIN_VEL, BURGER_MAX_LIN_VEL)


def check_angular_limit_velocity(w):
    return constrain(w, -BURGER_MAX_ANG_VEL, BURGER_MAX_ANG_VEL)


class MqttToCmdVelNode(Node):
    def __init__(self):
        super().__init__("mqtt_to_cmd_vel")

        # Publish TwistStamped on /cmd_vel (unchanged format)
        self.publisher = self.create_publisher(TwistStamped, "cmd_vel", 10)

        # Joint feedback
        self.left_pos = None
        self.right_pos = None
        self.create_subscription(JointState, "joint_states", self._js_cb, 10)

        # Goal state
        self.active = False
        self.mode = None          # "distance" or "turn"
        self.goal_value = 0.0     # meters (distance) or radians (turn)
        self.start_left = 0.0
        self.start_right = 0.0

        # Motion parameters (can be overridden per MQTT message)
        self.lin_speed = 0.10     # m/s
        self.turn_rate = 0.60     # rad/s

        # PI sync for straight driving (distance mode)
        self.kp_sync = 2.0
        self.ki_sync = 0.2
        self.i_term = 0.0
        self.i_limit = 1.0

        self.last_ctrl_time = time.time()

        # Control timer (50 Hz)
        self.timer = self.create_timer(0.02, self._control_loop)

        # MQTT setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        mqtt_server = "127.0.0.1"
        mqtt_port = 1883
        self.mqtt_topic = "mqtt_vel"

        self.mqtt_client.connect(mqtt_server, mqtt_port, 60)
        self.mqtt_client.loop_start()
        self.mqtt_client.subscribe(self.mqtt_topic)

        self.get_logger().info(f"Subscribed to MQTT topic: {self.mqtt_topic}")

    # ---------- ROS helpers ----------

    def _js_cb(self, js: JointState):
        """Store latest wheel positions in radians."""
        try:
            li = js.name.index("wheel_left_joint")
            ri = js.name.index("wheel_right_joint")
            self.left_pos = js.position[li]
            self.right_pos = js.position[ri]
        except Exception:
            # fallback: assume first two
            if len(js.position) >= 2:
                self.left_pos = js.position[0]
                self.right_pos = js.position[1]

    def _publish_cmd_vel(self, lin_x: float, ang_z: float):
        """Publish TwistStamped to /cmd_vel."""
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ""
        msg.twist.linear.x = float(lin_x)
        msg.twist.linear.y = 0.0
        msg.twist.linear.z = 0.0
        msg.twist.angular.x = 0.0
        msg.twist.angular.y = 0.0
        msg.twist.angular.z = float(ang_z)
        self.publisher.publish(msg)

    def _stop(self):
        """Stop immediately and cancel any active goal."""
        self._publish_cmd_vel(0.0, 0.0)
        self.active = False
        self.mode = None
        self.i_term = 0.0

    # ---------- MQTT callbacks ----------

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.get_logger().info("Connected to MQTT broker successfully.")
        else:
            self.get_logger().error(f"Failed to connect to MQTT broker, return code: {rc}")

    def on_message(self, client, userdata, msg):
        """
        ACCEPTED MQTT PAYLOADS ONLY:

          Stop:
            {"stop": true}

          Drive distance (meters):
            {"distance": 1.0, "speed": 0.12}   # speed optional

          Turn in place (degrees):
            {"turn_deg": 180, "turn_rate": 0.8}  # turn_rate optional

       
        """
        try:
            payload = json.loads(msg.payload.decode())

            # ---- STOP ----
            if payload.get("stop", False) is True:
                self.get_logger().info("STOP command received.")
                self._stop()
                return

            # Need joint_states for goals
            if self.left_pos is None or self.right_pos is None:
                self.get_logger().error("No /joint_states yet. Start turtlebot3_node and try again.")
                return

            # ---- Distance goal ----
            if "distance" in payload:
                self.mode = "distance"
                self.goal_value = float(payload["distance"])  # meters

                spd = float(payload.get("speed", self.lin_speed))
                self.lin_speed = constrain(abs(spd), 0.0, BURGER_MAX_LIN_VEL)

            # ---- Turn goal ----
            elif "turn_deg" in payload:
                self.mode = "turn"
                self.goal_value = math.radians(float(payload["turn_deg"]))  # radians

                rate = float(payload.get("turn_rate", self.turn_rate))
                self.turn_rate = constrain(abs(rate), 0.0, BURGER_MAX_ANG_VEL)

            else:
                self.get_logger().error(
                    "MQTT payload must be one of:\n"
                    "  {'stop': true}\n"
                    "  {'distance': <meters>, 'speed': <m/s optional>}\n"
                    "  {'turn_deg': <degrees>, 'turn_rate': <rad/s optional>}"
                )
                return

            # Start goal tracking
            self.start_left = self.left_pos
            self.start_right = self.right_pos
            self.i_term = 0.0
            self.last_ctrl_time = time.time()
            self.active = True

            unit = "m" if self.mode == "distance" else "rad"
            self.get_logger().info(f"New goal: mode={self.mode}, value={self.goal_value:.3f} {unit}")

        except json.JSONDecodeError:
            self.get_logger().error("Failed to decode JSON from MQTT message.")
        except Exception as e:
            self.get_logger().error(f"on_message error: {e}")

    # ---------- Control loop for goals ----------

    def _control_loop(self):
        if not self.active:
            return

        if self.left_pos is None or self.right_pos is None:
            self.get_logger().error("Lost /joint_states. Stopping.")
            self._stop()
            return

        now = time.time()
        dt = now - self.last_ctrl_time
        if dt <= 0.0:
            dt = 0.02
        self.last_ctrl_time = now

        dL = self.left_pos - self.start_left    # rad
        dR = self.right_pos - self.start_right  # rad

        if self.mode == "distance":
            traveled = WHEEL_RADIUS * (dL + dR) / 2.0  # meters

            # Stop condition (forward/backward)
            if (self.goal_value >= 0 and traveled >= self.goal_value) or \
               (self.goal_value < 0 and traveled <= self.goal_value):
                self.get_logger().info(f"Distance reached. traveled={traveled:.3f} m")
                self._stop()
                return

            # PI wheel-sync: keep dL ~= dR (straight)
            err = dL - dR
            self.i_term += err * dt
            self.i_term = constrain(self.i_term, -self.i_limit, self.i_limit)

            correction = (self.kp_sync * err) + (self.ki_sync * self.i_term)

            lin = self.lin_speed if self.goal_value >= 0 else -self.lin_speed
            lin = check_linear_limit_velocity(lin)

            ang = -correction
            ang = check_angular_limit_velocity(ang)

            self._publish_cmd_vel(lin, ang)

        elif self.mode == "turn":
            # Estimate yaw from wheel difference
            yaw = WHEEL_RADIUS * (dR - dL) / WHEEL_SEPARATION  # rad

            if (self.goal_value >= 0 and yaw >= self.goal_value) or \
               (self.goal_value < 0 and yaw <= self.goal_value):
                self.get_logger().info(f"Turn reached. yaw={yaw:.3f} rad")
                self._stop()
                return

            ang = self.turn_rate if self.goal_value >= 0 else -self.turn_rate
            ang = check_angular_limit_velocity(ang)

            self._publish_cmd_vel(0.0, ang)


def main(args=None):
    rclpy.init(args=args)
    node = MqttToCmdVelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.mqtt_client.loop_stop()
        node._stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
