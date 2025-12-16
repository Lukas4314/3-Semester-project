from mqttInterface import MQTTInterface
from pc_code.sound_localization.Triangulate import triangulate_from_sound
import time
import threading
import numpy as np
from scipy.io.wavfile import write
from consts import SAMPLE_RATE, SHOULD_LOG
import math
from logger import *

DRIVE_SPEED_M_S = 0.2              # m/s (sent as "speed")
TURN_RATE_RAD_S = 1.0               # rad/s (sent as "turn_rate")


class TurtleController:
	"""
	Sends GOAL commands over MQTT:
	  - {"distance": <meters>, "speed": <m/s optional>}
	  - {"turn_deg": <degrees>, "turn_rate": <rad/s optional>}
	  - {"stop": true}
	The robot-side node converts these goals into velocity commands on /cmd_vel.
	"""

	def __init__(self, mqtt_interface, queue1=None, queue2=None, queue3=None):
		self.mqtt_interface = mqtt_interface

		# Optional microphone queues (only needed if you call go_to_human)
		self.queue1 = queue1
		self.queue2 = queue2
		self.queue3 = queue3

		self.executing_thread = None
		self.stop_event = threading.Event()
		
		self.history = []



	def stop(self):
		print("Stopping the turtle")
		self.mqtt_interface.publish_stop()

	def move_forward(self, distance_m):
		print(f"Drive goal: +{distance_m:.3f} m")
		self.mqtt_interface.publish_distance(float(distance_m), speed=DRIVE_SPEED_M_S)

	def move_backward(self, distance_m):
		print(f"Drive goal: -{distance_m:.3f} m")
		self.mqtt_interface.publish_distance(-float(distance_m), speed=DRIVE_SPEED_M_S)

	def turn_left_deg(self, deg):
		print(f"Turn goal: +{deg:.1f} deg")
		self.mqtt_interface.publish_turn_deg(float(deg), turn_rate=TURN_RATE_RAD_S)

	def turn_right_deg(self, deg):
		print(f"Turn goal: {deg:.1f} deg")
		self.mqtt_interface.publish_turn_deg(-float(deg), turn_rate=TURN_RATE_RAD_S)

	# Convenience if you already have radians
	def turn_left_rad(self, radians):
		self.turn_left_deg(float(radians) * 180.0 / math.pi)

	def turn_right_rad(self, radians):
		self.turn_right_deg(float(radians) * 180.0 / math.pi)


	def go_to_human(self, start_index, end_index, distance):
		"""
		Uses queued mic data to triangulate a point, then turns and drives towards it.
		Requires queue1/queue2/queue3 in __init__.
		"""
		if self.queue1 is None or self.queue2 is None or self.queue3 is None:
			print("go_to_human() requires queue1, queue2, queue3 passed to TurtleController.")
			return


		mic1_data = []
		mic2_data = []
		mic3_data = []


		if SHOULD_LOG:
			center_chunk = (start_index + end_index) // 2
			chunk_sizes = [8, 4, 2] # Important to check largest to smallest
			start_index = center_chunk - chunk_sizes[0] // 2
			end_index = start_index + chunk_sizes[0]
   
			while not self.queue1.empty():
				message_index, new_chunk = self.queue1.get()
				if start_index <= message_index <= end_index:
					mic1_data.append(new_chunk)
			while not self.queue2.empty():
				message_index, new_chunk = self.queue2.get()
				if start_index <= message_index <= end_index:
					mic2_data.append(new_chunk)
			while not self.queue3.empty():
				message_index, new_chunk = self.queue3.get()
				if start_index <= message_index <= end_index:
					mic3_data.append(new_chunk)
		
	
			for size in chunk_sizes:
				current_mic1_data = mic1_data.copy()
				current_mic2_data = mic2_data.copy()
				current_mic3_data = mic3_data.copy()
				
				current_mic1_data = current_mic1_data[(len(mic1_data)-size)//2:len(mic1_data)-(len(mic1_data)-size)//2]
				current_mic2_data = current_mic2_data[(len(mic2_data)-size)//2:len(mic2_data)-(len(mic2_data)-size)//2]
				current_mic3_data = current_mic3_data[(len(mic3_data)-size)//2:len(mic3_data)-(len(mic3_data)-size)//2]
				Logger.current_samples_size = size
				current_mic1_data = np.concatenate(current_mic1_data)
				current_mic2_data = np.concatenate(current_mic2_data)
				current_mic3_data = np.concatenate(current_mic3_data)
	

				best_point, best_score = triangulate_from_sound(current_mic1_data, current_mic2_data, current_mic3_data, called_by_logger=True)
				
				angle = np.arctan2(best_point[1], best_point[0]) * 180 / np.pi
				distance_by_TDOA = np.sqrt(best_point[0]**2 + best_point[1]**2)
				
			

		if SHOULD_LOG:
			mic1_data = mic1_data[chunk_sizes[0]//2:len(mic1_data)-chunk_sizes[0]//2]
			mic2_data = mic2_data[chunk_sizes[0]//2:len(mic2_data)-chunk_sizes[0]//2]
			mic3_data = mic3_data[chunk_sizes[0]//2:len(mic3_data)-chunk_sizes[0]//2]
   
		else:
			# Collect chunks in range
			while not self.queue1.empty():
				message_index, new_chunk = self.queue1.get()
				if start_index <= message_index <= end_index:
					mic1_data.append(new_chunk)

			while not self.queue2.empty():
				message_index, new_chunk = self.queue2.get()
				if start_index <= message_index <= end_index:
					mic2_data.append(new_chunk)

			while not self.queue3.empty():
				message_index, new_chunk = self.queue3.get()
				if start_index <= message_index <= end_index:
					mic3_data.append(new_chunk)

		if len(mic1_data) < 1:
			print(f"No mic data in range {start_index}..{end_index}")
			return

		mic1_data = np.concatenate(mic1_data)
		mic2_data = np.concatenate(mic2_data)
		mic3_data = np.concatenate(mic3_data)

		# Debug WAVs
		write("actually_fed_to_gcc1.wav", SAMPLE_RATE, mic1_data.astype(np.int16))
		if mic2_data.size:
			write("actually_fed_to_gcc2.wav", SAMPLE_RATE, mic2_data.astype(np.int16))
		if mic3_data.size:
			write("actually_fed_to_gcc3.wav", SAMPLE_RATE, mic3_data.astype(np.int16))

		best_point, best_score = triangulate_from_sound(mic1_data, mic2_data, mic3_data)
		print(f"Best point: {best_point}, Best score: {best_score}")

		# best_point = (x, y) in meters in robot frame
		angle_rad = float(np.arctan2(best_point[1], best_point[0]))
		angle_deg = angle_rad * 180.0 / math.pi
		distance_m = float(np.sqrt(best_point[0] ** 2 + best_point[1] ** 2))

		print(f"Sound located at angle {angle_deg:.1f} deg and distance {distance_m:.3f} m")

		# Turn then drive (these are GOALS; robot-side will execute them)
		angle_rad = math.radians(angle_deg)
		if angle_deg >= 0:
			#self.turn_left_deg(angle_deg)
			self.execute_command("turn", "left", angle_rad)
		else:
			#self.turn_right_deg(abs(angle_deg))
			self.execute_command("turn", "right", angle_rad)
   
		if SHOULD_LOG:
			Logger.set_value(ACTUAL_TRIANGULATION_ANGLE, input("What is the correct angle (in degrees)?: "))
			Logger.set_value(ACTUAL_TRIANGULATION_DISTANCE, input("What is the correct distance (in meters)?: "))

   
   
		time.sleep(abs(angle_deg)/70)  #180 deg = 2,5 sec
		#self.move_forward(distance)
		self.execute_command("move", "forward", distance)


	def _run_in_thread(self, fn, *args):
		# Stop any previous execution and also stop the robot
		if self.executing_thread and self.executing_thread.is_alive():
			print("Stopping current action before executing new command.")
			self.stop_event.set()
			self.stop()  # IMPORTANT: actually stop robot motion
			self.executing_thread.join()
			self.stop_event.clear()

		self.executing_thread = threading.Thread(target=fn, args=args, daemon=True)
		self.executing_thread.start()

	
	def _estimate_duration(self, cmd):
		"""
		Rough time estimate since the robot-side goal executor does not ack completion.
		cmd is a dict like: {"action":"move"/"turn", "direction":..., "distance":...}
		"""
		a = cmd["action"]
		dist = float(cmd["distance"])

		if a == "move":
			base = abs(dist) / max(DRIVE_SPEED_M_S, 1e-6)
		elif a == "turn":
			base = abs(dist) / max(TURN_RATE_RAD_S, 1e-6)  # dist is radians in your pipeline
		else:
			base = 0.0

		# pad a bit for accel/latency
		return max(0.2, 1.2 * base)

	def _sleep_with_cancel(self, seconds):
		t0 = time.time()
		while time.time() - t0 < seconds:
			if self.stop_event.is_set():
				return False
			time.sleep(0.02)
		return True

	def _inverse_of(self, cmd):
		a = cmd["action"]
		d = cmd["direction"]
		dist = float(cmd["distance"])

		if a == "move":
			if d == "forward":
				return {"action": "move", "direction": "backward", "distance": dist}
			if d == "backward":
				return {"action": "move", "direction": "forward", "distance": dist}

		if a == "turn":
			if d == "left":
				return {"action": "turn", "direction": "right", "distance": dist}
			if d == "right":
				return {"action": "turn", "direction": "left", "distance": dist}

		return None

	def _execute_goal_blocking(self, cmd):
		"""
		Publish a single goal, then wait an estimated time (cancelable).
		"""
		if cmd["action"] == "move":
			if cmd["direction"] == "forward":
				self.move_forward(cmd["distance"])
			else:
				self.move_backward(cmd["distance"])

		elif cmd["action"] == "turn":
			# distance in radians (your parser returns radians for turns) :contentReference[oaicite:3]{index=3}
			if cmd["direction"] == "left":
				self.turn_left_rad(cmd["distance"])
			else:
				self.turn_right_rad(cmd["distance"])

		# wait until it's probably done
		return self._sleep_with_cancel(self._estimate_duration(cmd))

	def _return_last(self, n: int):
		n = max(0, int(n))
		if n == 0:
			return

		if not self.history:
			print("Return: history empty.")
			return

		# pop last n commands, undo them in the same order we pop (last command undone first)
		steps = min(n, len(self.history))
		to_undo = [self.history.pop() for _ in range(steps)]

		print(f"Returning {steps} command(s)...")

		for original in to_undo:
			if self.stop_event.is_set():
				return
			inv = self._inverse_of(original)
			if inv is None:
				print(f"Cannot invert: {original}")
				continue

			ok = self._execute_goal_blocking(inv)
			if not ok:
				return

		# optional: full stop at the end
		self.stop()

	def execute_command(self, action, direction=None, distance=None):
		"""
		Expected:
		  action="move", direction="forward"/"backward", distance=<meters>
		  action="turn", direction="left"/"right", distance=<radians>
		  action="stop"
		  action="return", distance=<count>
		"""
		if abs(distance) < 0.01:
			distance = 0
		print(f"Executing command: action={action}, direction={direction}, distance={distance}")
		if action == "stop":
			self._run_in_thread(self.stop)
			if SHOULD_LOG:
				self.executing_thread.join()
				Logger.set_value(ACTION, action)
				Logger.write_row()
			return

		if action == "return":
			count = 1 if distance is None else int(distance)
			self._run_in_thread(self._return_last, count)
			return

		if action == "move":
			if distance is None:
				print("move requires distance (meters)")
				return
			if direction == "forward":
				# record the forward move
				self.history.append({"action": "move", "direction": "forward", "distance": float(distance)})
				self._run_in_thread(self.move_forward, float(distance))
			elif direction == "backward":
				self.history.append({"action": "move", "direction": "backward", "distance": float(distance)})
				self._run_in_thread(self.move_backward, float(distance))
			else:
				print("move direction must be 'forward' or 'backward'")
			if SHOULD_LOG and False:
				self.executing_thread.join()
				Logger.set_value(DISTANCE_MOVED, input("How far did it move (in meters)?: "))
				Logger.set_value(DISTANCE_THOUGHT_IT_MOVED, distance)
				Logger.set_value(ACTION, action)
				Logger.write_row()
			return

		if action == "turn":
			if distance is None:
				print("turn requires distance (radians)")
				return
			radians = float(distance)
			if direction == "left":
				self.history.append({"action": "turn", "direction": "left", "distance": radians})
				self._run_in_thread(self.turn_left_rad, radians)
			elif direction == "right":
				self.history.append({"action": "turn", "direction": "right", "distance": radians})
				self._run_in_thread(self.turn_right_rad, radians)
			else:
				print("turn direction must be 'left' or 'right'")
			if SHOULD_LOG and False:
				self.executing_thread.join()
				Logger.set_value(ANGLE_ROTATED, input("How much did it turn (in degrees)?: "))
				Logger.set_value(ANGLE_THOUGHT_IT_ROTATED, distance*180/np.pi)
				Logger.set_value(ACTION, action)
				Logger.write_row()
			return

		print(f"Unknown action: {action}")


if __name__ == "__main__":
	MQTT_SERVER = "10.32.162.201"
	MQTT_PORT = 1883
	MQTT_TOPIC = "mqtt_vel"

	mqtt_interface = MQTTInterface(MQTT_SERVER, MQTT_PORT, MQTT_TOPIC)

	# If you don't use go_to_human, you can omit queues:
	turtle_controller = TurtleController(mqtt_interface)

	# Demo: drive 1m, turn 90deg left, stop
	turtle_controller.move_forward(1.0)
	time.sleep(1.0)

	turtle_controller.turn_left_deg(90)
	time.sleep(1.0)

	turtle_controller.stop()
	mqtt_interface.disconnect()