from mqqtInterface import MQTTInterface
from pc_code.sound_localization.Triangulate import triangulate_from_sound
import time
import threading
import numpy as np
from scipy.io.wavfile import write
from consts import SAMPLE_RATE, SHOULD_LOG
from logger import *

SPEED = 0.2 # meaning when 1 is written it is 1 meter per second
ANGULAR_SPEED = 1 # meaning when 1 is written it is 1 degree per second


class TurtleController:
	# We need to implement threading in the future so the robot can move and receieve new commands at the same time
	def __init__(self, mqtt_interface, queue1, queue2, queue3):
		self.mqtt_interface = mqtt_interface
		self.executing_thread = None
		self.stop_event = threading.Event()
		self.queue1 = queue1
		self.queue2 = queue2
		self.queue3 = queue3

	def set_forward_speed(self, speed):
		print(f"Setting forward speed to {speed}")
		self.mqtt_interface.publish_command(speed, 0.0)

	def set_turn_speed(self, angular_speed):
		print(f"Setting turn speed to {angular_speed}")
		self.mqtt_interface.publish_command(0.0, angular_speed)

	def move_forward(self, distance):
		print(f"Moving forward at speed {SPEED}")
		self.set_forward_speed(SPEED)
		self.sleep(distance / SPEED)
		if self.stop_event.is_set():
			return
		self.set_forward_speed(0.0)

	def move_backward(self, distance):
		print(f"Moving backward at speed {SPEED}")
		self.set_forward_speed(-SPEED)
		self.sleep(distance / SPEED)
		if self.stop_event.is_set():
			return
		self.set_forward_speed(0.0)

	def turn_counter_clockwise(self, amount_deg):
		print(f"Turning counter-clockwise at angular speed {ANGULAR_SPEED}")
		self.set_turn_speed(ANGULAR_SPEED)
		self.sleep(amount_deg / ANGULAR_SPEED)
		if self.stop_event.is_set():
			return
		self.set_turn_speed(0.0)

	def turn_clockwise(self, amount_deg):
		print(f"Turning clockwise at angular speed {ANGULAR_SPEED}")
		self.set_turn_speed(-ANGULAR_SPEED)
		self.sleep(amount_deg / ANGULAR_SPEED)
		if self.stop_event.is_set():
			return
		self.set_turn_speed(0.0)

	def stop(self):
		print("Stopping the turtle")
		self.mqtt_interface.publish_command(0.0, 0.0)

	def sleep(self, duration):
		sleep_interval = 0.1
		num_intervals = int(duration / sleep_interval)
		for _ in range(num_intervals):
			if self.stop_event.is_set():
				break
			time.sleep(sleep_interval)
	
	def go_to_human(self, start_index, end_index):
		mic1_data = []
		mic2_data = []
		mic3_data = []
		
		while not self.queue1.empty():
			message_index, new_chunk = self.queue1.get()
			if start_index <= message_index <= end_index:
				mic1_data.append(new_chunk)
			else:
				#print(f"index: {message_index} not in range {start_index} to {end_index}")
				pass
		while not self.queue2.empty():
			message_index, new_chunk = self.queue2.get()
			if start_index <= message_index <= end_index:
				mic2_data.append(new_chunk)
				
		while not self.queue3.empty():
			message_index, new_chunk = self.queue3.get()
			if start_index <= message_index <= end_index:
				mic3_data.append(new_chunk)
		
		if len(mic1_data) < 1:
			print(f"No data received from microphones in the specified range {start_index} to {end_index}.")
			return
		
		if len(mic1_data) >= 1:
			mic1_data = np.concatenate(mic1_data)
			mic2_data = np.concatenate(mic2_data)
			mic3_data = np.concatenate(mic3_data)        
		
		write("actually_fed_to_gcc1.wav", SAMPLE_RATE, mic1_data.astype(np.int16))
		write("actually_fed_to_gcc2.wav", SAMPLE_RATE, mic2_data.astype(np.int16))
		write("actually_fed_to_gcc3.wav", SAMPLE_RATE, mic3_data.astype(np.int16))
		
		best_point, best_score = triangulate_from_sound(mic1_data, mic2_data, mic3_data)
		print(f"Best point: {best_point}, Best score: {best_score}")
		angle = np.arctan2(best_point[1], best_point[0]) * 180 / np.pi
		distance = np.sqrt(best_point[0]**2 + best_point[1]**2)
		
		print(f"Sound located at angle {angle} degrees and distance {distance} meters")
		
		self.turn_counter_clockwise(angle)
		time.sleep(0.5)
		self.move_forward(distance)

	def execute_command(self, action, direction, distance):
		if self.executing_thread and self.executing_thread.is_alive():
			print("Stopping current action before executing new command.")
			self.stop_event.set()
			self.executing_thread.join()
			self.stop_event.clear()
			
		if action == "stop":
			self.executing_thread = threading.Thread(target=self.stop)
			self.executing_thread.start()
			if SHOULD_LOG:
				self.executing_thread.join()
   
		elif action == "move":
			if direction == "forward":
				self.executing_thread = threading.Thread(target=self.move_forward, args=(distance,))
			elif direction == "backward":
				self.executing_thread = threading.Thread(target=self.move_backward, args=(distance,))
				self.executing_thread.start()
			self.executing_thread.start()
			if SHOULD_LOG:
				self.executing_thread.join()
				Logger.set_value(DISTANCE_MOVED, input("How far did it move (in meters)?: "))
				Logger.set_value(DISTANCE_THOUGH_IT_MOVED, distance)


		elif action == "turn":
			if direction == "left":
				self.executing_thread = threading.Thread(target=self.turn_counter_clockwise, args=(distance,))
				self.executing_thread.start()
			elif direction == "right":
				self.executing_thread = threading.Thread(target=self.turn_clockwise, args=(distance,))
				self.executing_thread.start()
			if SHOULD_LOG:
				self.executing_thread.join()
				Logger.set_value(DISTANCE_MOVED, input("How far did it move (in meters)?: "))
				Logger.set_value(DISTANCE_THOUGH_IT_MOVED, distance)



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