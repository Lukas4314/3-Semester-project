#!/usr/bin/env python3
import json
import math
import time
import csv
from pathlib import Path

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

        # ---- Known physical drift compensation (feed-forward) ----
        # Positive angular.z = turn left, negative = turn right.
        # If your robot drifts LEFT during "distance", use a small NEGATIVE value.
        self.known_drift_ang = -0.02  # rad/s (START SMALL and tune)

        # Simple accel / decel profile (distance mode)
        self.ramp_up_time = 0.4       # seconds to reach full linear speed
        self.decel_distance = 0.1     # meters from goal where we start slowing down
        self.ramp_start_time = None

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

        # ---- JointState logging (TXT / CSV) ----
        log_dir = Path("/home/pi/rb3_ws/src/mqtt_2_cmd_pkg/mqtt_2_cmd_pkg")
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_path = log_dir / f"joint_states_{int(time.time())}.txt"
        self.log_f = open(self.log_path, "w", newline="")
        self.log_csv = csv.writer(self.log_f)

        self.log_csv.writerow([
            "t_sec",
            "left_pos_rad",
            "right_pos_rad",
            "traveled_m",
            "yaw_rad",
            "active",
            "mode"
        ])
        self.log_f.flush()

        # Log only every N joint_state messages
        self.log_every_n = 20
        self._js_count = 0

        self.get_logger().info(f"JointState logging to: {self.log_path}")
        self.get_logger().info(f"Logging every {self.log_every_n} joint_states messages")
        self.get_logger().info(f"Straight drift feed-forward angular.z = {self.known_drift_ang:.4f} rad/s")

    # ---------- ROS helpers ----------

    def _js_cb(self, js: JointState):
        """Update wheel positions every message, but log only every N messages."""

        # -------- always update left/right wheel positions --------
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

        # Count messages and only log every Nth
        self._js_count += 1
        if (self._js_count % self.log_every_n) != 0:
            return

        # -------- timestamp (ROS time preferred) --------
        if js.header.stamp.sec != 0 or js.header.stamp.nanosec != 0:
            t_sec = js.header.stamp.sec + js.header.stamp.nanosec * 1e-9
        else:
            t_sec = time.time()

        # -------- derived quantities (only meaningful during motion) --------
        traveled = ""
        yaw = ""

        if self.left_pos is not None and self.right_pos is not None and self.active:
            dL = self.left_pos - self.start_left
            dR = self.right_pos - self.start_right
            traveled = WHEEL_RADIUS * (dL + dR) / 2.0
            yaw = WHEEL_RADIUS * (dR - dL) / WHEEL_SEPARATION

        # -------- write one line to TXT (CSV format) --------
        self.log_csv.writerow([
            f"{t_sec:.9f}",
            "" if self.left_pos is None else f"{self.left_pos:.9f}",
            "" if self.right_pos is None else f"{self.right_pos:.9f}",
            "" if traveled == "" else f"{traveled:.9f}",
            "" if yaw == "" else f"{yaw:.9f}",
            int(self.active),
            "" if self.mode is None else self.mode
        ])
        self.log_f.flush()

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
        self.ramp_start_time = None

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
            self.active = True
            self.ramp_start_time = time.time()

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

            # Target speed sign
            sign = 1.0 if self.goal_value >= 0 else -1.0
            target_speed = self.lin_speed * sign

            # ---- Ramp UP (time-based) ----
            if self.ramp_start_time is None:
                self.ramp_start_time = time.time()
            t = time.time() - self.ramp_start_time
            ramp_up = min(t / self.ramp_up_time, 1.0) if self.ramp_up_time > 0 else 1.0

            # ---- Ramp DOWN (distance-based) ----
            remaining = abs(self.goal_value - traveled)
            if self.decel_distance > 0 and remaining < self.decel_distance:
                ramp_down = remaining / self.decel_distance
            else:
                ramp_down = 1.0

            # ---- Final commanded speed ----
            scale = min(ramp_up, ramp_down)
            lin = target_speed * scale
            lin = check_linear_limit_velocity(lin)

            # ---- Feed-forward correction for known physical drift ----
            # If robot drifts LEFT, use a small NEGATIVE angular.z to bias right.
            self._publish_cmd_vel(lin, self.known_drift_ang)

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
        try:
            node.mqtt_client.loop_stop()
        except Exception:
            pass

        try:
            node._stop()
        except Exception:
            pass

        try:
            node.log_f.close()
        except Exception:
            pass

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
