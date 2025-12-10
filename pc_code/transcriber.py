from email.mime import audio
import string
import sounddevice as sd
import numpy as np
import whisper
from whisper.audio import pad_or_trim, log_mel_spectrogram
import threading
import time
import queue
import wave
import torch
import torchaudio
from consts import SAMPLE_RATE, USE_GPU
from math import floor, ceil
#for debbing
import os
from scipy.io.wavfile import write



class transcriber:
	def __init__(self, input_queue):  
		if USE_GPU == True:
			print("Using GPU for transcription.")
			# Enforce GPU-only
			if not torch.cuda.is_available():
				raise RuntimeError("CUDA GPU is required, but torch.cuda.is_available() == False")
			self.device = "cuda"

		
		# Load model
		if USE_GPU:
			self.model = whisper.load_model("base.en", device=self.device)
		else:
			self.model = whisper.load_model("base.en")  # or "base.en" for better accuracy



		self.samplerate = SAMPLE_RATE
		self.chunk_duration = 5      # seconds per processed chunk
		self.overlap_duration = 2.5  # seconds overlap
		self.samples_per_chunk = int(self.samplerate * self.chunk_duration)
		self.samples_overlap = int(self.samplerate * self.overlap_duration)
		# Audio queue
		self.input_queue = input_queue
		self.output_queue = queue.Queue()
		self.last_string = ""
		self.recorded_audio = []  # To accumulate audio data
		self.lock = threading.Lock()
		self.whisper_lock = threading.Lock()

		self.start_index = float('inf')
		self.end_index = float('-inf')

		
		
		self.resampler = None
		if self.samplerate != 16000:
			self.resampler = torchaudio.transforms.Resample(
				orig_freq=self.samplerate,
				new_freq=16000
		)
		
		
		threading.Thread(target=self.transcribe_stream, daemon=True).start()
		
	def append_without_overlap(self, new):
		"""
		Append only the non-overlapping part of 'new' to 'existing'.
		Works even if 'new' contains the entire 'existing' text again.
		"""
		# Trim whitespace
		self.last_string = self.last_string.strip()

		for punctuation in string.punctuation:
			self.last_string = self.last_string.replace(punctuation, "")
			new = new.replace(punctuation, "")

		new = new.strip()
		new = new.lower()
		
		# If new already contains existing entirely, just replace it
		if new.startswith(self.last_string):
			self.last_string = new
			return new

		# Find overlap from the end of existing and start of new
		max_overlap = min(len(self.last_string), len(new))
		overlap_length = 0

		for i in range(1, max_overlap + 1):
			if self.last_string.endswith(new[:i]):
				overlap_length = i

		self.last_string = new
		
		return new[overlap_length:]


	def preprocess_segment(self, segment):
		"""
		Convert a 44.1 kHz NumPy audio segment to Whisper-compatible log-Mel spectrogram.
		"""

		# Convert from int16 to float32 in -1.0 to 1.0 range
		if segment.dtype == np.int16:
			#segment = segment.astype(np.float32)
			segment = segment.astype(np.float32) / 32768.0
		else:
			segment = segment.astype(np.float32)

		# Convert to float32 tensor
		if USE_GPU:
			segment = torch.from_numpy(segment).float()
		else:
			segment = torch.from_numpy(segment)
		
		
		
		segment = self.resampler(segment)


		# Pad or trim to 30s (Whisper default)
		segment = pad_or_trim(segment)


		# Move to GPU
		if USE_GPU:
			segment = segment.to(self.device)


		# Compute log-Mel spectrogram
		mel = log_mel_spectrogram(segment)
		
		return mel
	
	
	def whisperoutput(self, segment):
		with self.whisper_lock:
			mel = self.preprocess_segment(segment)
			if USE_GPU:
				options = whisper.DecodingOptions(fp16=True, language="en")
			else:
				options = whisper.DecodingOptions(fp16=False, language="en")
			result = whisper.decode(self.model, mel, options)
			return result.text
	
	def find_nearest_here(self, start_index, end_index):
		end_found = False
		satisfied = False
		factor = 0.25
		fine_tuning_cut_size = 1 #after "here" found we 
		context_buffer = 15  # to avoid cutting too close to the word (later cutted out again)
		start = None
		end = None
		start_index = start_index - ceil(self.samples_overlap/1024)
		offset = None
		print(f"Searching for here between {start_index} and {end_index}")
		for i, (msg_idx, chunk) in enumerate(self.recorded_audio):
			if start_index == msg_idx:
				print(f"found start at index {i}")
				start = i
			if end_index == msg_idx:
				print(f"found end at index {i}")
				end = i
		
		
		if start is None or end is None:
			print("kunne ikke finde")
			print(f"start: {start_index}, end: {end_index}")
			return None
		
		
		offset = end_index - end

		print(f"Initial start: {start}, end: {end}")
		count = 0
		
		
		while True:
			count += 1
			print(f"Searching for here between {start} and {end} - iteration {count}")
			specified_data = self.recorded_audio[start : end + 1]
			segment = np.concatenate([chunk for _, chunk in specified_data])
			
			debug_fname = f"debug_segment_iteration_{count}_interval_{start}_{end}.wav"
			print("Saving debug wav:", debug_fname)
			write(os.path.join("debug_segments", debug_fname), self.samplerate, segment.astype(np.int16))
			# Remove-Item "debug_segments\*" -Recurse -Force

			text = self.whisperoutput(segment)
			text = text.strip().lower().replace(".", "")
			print(text)
			if not end_found:
				if "here" in text.split() and satisfied == False:
					end -= ((end - start) * factor) 
					end = floor(end)
				elif "here" in text.split() and satisfied == True:
					end_found = True
					end += context_buffer
					satisfied = False
				else:
					end += fine_tuning_cut_size
					satisfied = True
			else:
				if "here" in text.split() and satisfied == False:
					start += (end - start) * factor
					start = floor(start)
				elif "here" in text.split() and satisfied == True:
					self.output_queue.queue.clear()
					end -= context_buffer
					print("Final here found between indices:", start, "and", end, "offset:", offset)
					return floor((start + end) / 2) + offset
				else:
					start -= fine_tuning_cut_size
					satisfied = True
  
	def transcribe_stream(self):
		buffer = np.zeros(0, dtype=np.int16)
		step = self.samples_per_chunk - self.samples_overlap
		stamp_queue = queue.Queue()

		while True:
			# Pull audio into buffer
			while not self.input_queue.empty():
				message_index, new_chunk = self.input_queue.get()
				
				with self.lock:
					if message_index < self.start_index:
						self.start_index = message_index
					if message_index > self.end_index:
						self.end_index = message_index
				#print(f"Updated indices: start={self.start_index}, end={self.end_index}")
				
				#stamp_queue.put(message_index)
				
				self.recorded_audio.append((message_index, new_chunk))
				buffer = np.append(buffer, new_chunk)
				
			while len(buffer) >= self.samples_per_chunk:
				segment = buffer[:self.samples_per_chunk]
				
				result = self.whisperoutput(segment)
				
		
				#print("Raw transcription result:", result.text)
				# Handle transcription output
				result_after_append =self.append_without_overlap(result)
				self.output_queue.put(result_after_append)
				
				# Slide buffer window (keep overlap)
				buffer = buffer[step:]
			stamp_queue.empty()
			time.sleep(0.1)

	def getNewTranscription(self):
		"""Retrieve new transcription text if available."""
		texts = []
		while texts == []:
			while not self.output_queue.empty():
				texts.append(self.output_queue.get())
			time.sleep(0.01) # kan jeg bare blokkere her????
		with self.lock:
			start_index = self.start_index
			end_index = self.end_index
			self.start_index = float('inf')
			self.end_index = float('-inf')
			print(f"Current indices: start={start_index}, end={end_index}")

			
			return start_index, end_index, " ".join(texts)



