# GCC-PHAT quick rundown:
# 1. Take the FFT of all three signals.
# 2. Calculate the cross-correlation spectrum between pairs of signals.
# 3. Multiply by a PHAT weighting function to normalize the cross-correlation spectrum.
# 4. Take the inverse FFT of the normalized cross-correlation spectrum to get the cross-correlation function.
# 5. Find the peak in the cross-correlation function and make sure to convert the index to a signed lag value.
# 6. Calculate the TDOA from the location of the peak (after considering lag) in the cross-correlation function.

import numpy as np
import time
from matplotlib import pyplot as plt
import scipy.signal
import scipy.io.wavfile as wavfile
from consts import SAMPLE_RATE, SHOULD_PLOT, SHOULD_LOG
import logger
# 35.7
# 28.8


# 1. Take the FFT of all three signals.
def FFT(testarray):
	if SHOULD_PLOT == True and False:
		N = len(testarray)
		fft_freqs = np.fft.fftfreq(N, d=1/SAMPLE_RATE)
		fft_vals = np.fft.fft(testarray)
		pos_mask = fft_freqs >= 0
		plt.figure(figsize=(10,5))
		plt.plot(fft_freqs[pos_mask], fft_vals[pos_mask])
		plt.title("Frekvensdomæne - FFT af signal")
		plt.xlabel("Frekvens (Hz)")
		plt.ylabel("Amplitude")
		plt.grid(True)
		plt.show()
	return np.fft.fft(testarray, n=2*len(testarray))

# 1.5 Apply telephone band filter
def filter_telephone_band(fftarray):
	N = len(fftarray)
	lowcut = 100
	highcut = 3400
	fft_freqs = np.fft.fftfreq(N, d=1/SAMPLE_RATE)


	filter_mask = ((np.abs(fft_freqs) >= lowcut) & (np.abs(fft_freqs) <= highcut)).astype(float)
	fft_filtered = fftarray * filter_mask
 

	
	if SHOULD_PLOT == True and False:
		pos_mask = fft_freqs >= 0 
		plt.figure(figsize=(10, 5))
		plt.plot(fft_freqs[pos_mask], np.abs(fft_filtered[pos_mask]))
		plt.title("Filtered Spectrum (After Frequency-Domain Band-pass)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")
		plt.grid(True)
		plt.tight_layout()
		plt.show()
	
	return fft_filtered #output is the filterd fftarray


# 2. Calculate the cross-correlation spectrum between pairs of signals.
def GCC(fft1, fft2):
	return fft1 * np.conj(fft2)

# 3. Multiply by a PHAT weighting function to normalize the cross-correlation spectrum, here the weighting is 1.
def phat_weight(R, weight, eps=1e-8):
	mag = np.abs(R)
	mag = np.power(mag, weight)
	return R / (mag + eps)

# 4. Take the inverse FFT of the normalized cross-correlation spectrum to get the cross-correlation function.
def IFFT(R_phat):
	return np.fft.ifft(R_phat)

# 5. Find the peak in the cross-correlation function and make sure to convert the index to a signed lag value.
def peak_lag(corr):
	"""
	Find the peak lag in cross-correlation.
	Returns: lag in samples where positive lag means signal2 is delayed relative to signal1
	"""
	N = len(corr)
	corr_real = np.real(corr)  # Use real part for peak detection
	
	# Find the peak index
	idx = np.argmax(corr_real)
	
	# Convert to signed lag
	if idx > N // 2:
		lag = idx - N  # Negative lag
	else:
		lag = idx      # Positive lag
	
	return lag

# 6. Calculate the TDOA from the location of the peak (after considering lag) in the cross-correlation function.
def TDOA(cross_corr):
	return peak_lag(cross_corr)

def PHAT_GCC_TDOA(signal1, signal2, telephone_band_filter = False):
	"""
	Calculate TDOA between signal1 and signal2.
	Returns: tdoa in samples where positive value means signal2 arrives AFTER signal1
	"""
	if not hasattr(PHAT_GCC_TDOA, "counter"):
		PHAT_GCC_TDOA.counter = 0

	fft1 = FFT(signal1)
	fft2 = FFT(signal2)
	
	if telephone_band_filter == True:
		fft1 = filter_telephone_band(fft1)
		fft2 = filter_telephone_band(fft2)
	
	R = GCC(fft1, fft2)
	
	if SHOULD_LOG:
		weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
		filter_states = ["WITHOUT_FILTER", "WITH_FILTER"]
		
		for filter_state in filter_states:
			# Apply or skip filter
			if filter_state == "WITH_FILTER":
				filtered_fft1 = filter_telephone_band(fft1)
				filtered_fft2 = filter_telephone_band(fft2)
			else:
				filtered_fft1 = fft1
				filtered_fft2 = fft2
			
			R = GCC(filtered_fft1, filtered_fft2)
			
			# Test all weights
			for weight in weights:
				R_phat = phat_weight(R, weight=weight)
				cross_corr = IFFT(R_phat)
				tdoa = TDOA(cross_corr)
				
				# Log this combination
				weight_int = int(weight * 10)
				sample_size_name = ""
				if logger.Logger.current_samples_size is 2048:
					sample_size_name = "2k"
				elif logger.Logger.current_samples_size is 4096:
					sample_size_name = "4k"
				elif logger.Logger.current_samples_size is 8192:
					sample_size_name = "8k"


				const_name = f"TDOA_PHAT_WEIGHT_{weight_int:02d}_{sample_size_name}_SAMPLES_{filter_state}"
				try:
					column_key = getattr(logger, const_name)
					logger.Logger.set_value(column_key, tdoa)
				except AttributeError:
					print(f"Warning: Logger constant {const_name} not found")
		return tdoa

	R_phat = phat_weight(R, weight=1.0)
	"""
	fig = plt.figure()
	plt.subplot(2, 1, 1)
	plt.plot(np.abs(R))
	plt.title("GCC-PHAT Magnitude Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Magnitude")
	
	plt.subplot(2, 1, 2)
	plt.plot(np.angle(R))
	plt.title("GCC-PHAT Phase Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Phase (radians)")
	plt.savefig(f"gcc_phat_before_weight{PHAT_GCC_TDOA.counter}.png")    
	
	
	fig = plt.figure()
	plt.subplot(2, 1, 1)
	plt.plot(np.abs(R_phat))
	plt.title("GCC-PHAT Magnitude Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Magnitude")
	
	plt.subplot(2, 1, 2)
	plt.plot(np.angle(R_phat))
	plt.title("GCC-PHAT Phase Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Phase (radians)")
	plt.savefig(f"gcc_phat_after_weight{PHAT_GCC_TDOA.counter}.png")
	"""
	PHAT_GCC_TDOA.counter += 1
	
	
	cross_corr = IFFT(R_phat)
		
	tdoa = TDOA(cross_corr)

	if SHOULD_PLOT:
	
		frequency_axis = np.linspace(0, SAMPLE_RATE, len(fft1))

		# ------------------------------
		# 0. Original Signals
		# ------------------------------
		fig = plt.figure(figsize=(10,5))
		time_axis = np.arange(len(signal1)) / SAMPLE_RATE
		plt.plot(time_axis, signal1, label="Signal 1", alpha=0.7)
		plt.plot(time_axis, signal2, label="Signal 2", alpha=0.7)
		plt.title("Original Time-Domain Signals")
		plt.xlabel("Time (s)")
		plt.ylabel("Amplitude")
		plt.legend()
		plt.grid(True)
		plt.tight_layout()
		#plt.show()



		# ------------------------------
		# 1. FFTs BEFORE FILTERING
		# ------------------------------
		fig = plt.figure(figsize=(10,8))

		plt.subplot(2,1,1)
		plt.plot(frequency_axis, np.abs(fft1))
		plt.title("Signal 1 FFT Magnitude")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.subplot(2,1,2)
		plt.plot(frequency_axis, np.abs(fft2))
		plt.title("Signal 2 FFT Magnitude")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.tight_layout()
		#plt.show()


		# ------------------------------
		# 2. FILTERED FFTs
		# ------------------------------
		fig = plt.figure(figsize=(10,8))

		plt.subplot(2,1,1)
		plt.plot(frequency_axis, np.abs(fft1))
		plt.title("Filtered FFT (Signal 1)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.subplot(2,1,2)
		plt.plot(frequency_axis, np.abs(fft2))
		plt.title("Filtered FFT (Signal 2)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.tight_layout()
		#plt.show()


		# ------------------------------
		# 3. GCC BEFORE PHAT WEIGHTING
		# ------------------------------
		fig = plt.figure(figsize=(10,8))

		plt.subplot(2,1,1)
		plt.plot(frequency_axis, np.abs(R))
		plt.title("GCC Magnitude (Before PHAT)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.subplot(2,1,2)
		plt.plot(frequency_axis, np.angle(R))
		plt.title("GCC Phase (Before PHAT)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Phase (rad)")

		plt.tight_layout()
		#plt.show()


		# ------------------------------
		# 4. GCC AFTER PHAT WEIGHTING
		# ------------------------------
		fig = plt.figure(figsize=(10,8))

		plt.subplot(2,1,1)
		plt.plot(frequency_axis, np.abs(R_phat))
		plt.title("GCC-PHAT Magnitude (After Weighting)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Magnitude")

		plt.subplot(2,1,2)
		plt.plot(frequency_axis, np.angle(R_phat))
		plt.title("GCC-PHAT Phase (After Weighting)")
		plt.xlabel("Frequency (Hz)")
		plt.ylabel("Phase (rad)")

		plt.tight_layout()
		#plt.show()


		# ------------------------------
		# 5. CROSS-CORRELATION (TIME DOMAIN)
		# ------------------------------
		fig = plt.figure(figsize=(10,5))
		plt.plot(np.real(cross_corr))
		plt.title("Cross-Correlation (IFFT of GCC-PHAT)")
		plt.xlabel("Lag (samples)")
		plt.ylabel("Correlation")
		plt.grid(True)

		# Add TDOA as text annotation
		plt.text(0.05, 0.95, f"TDOA: {tdoa:.2f} samples",
         transform=plt.gca().transAxes,
         fontsize=12, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))


		plt.tight_layout()
		plt.show()

	
	
	return tdoa

def verify_signals(signal1, signal2, expected_lag, tolerance=2):
	"""Verify that signals have the expected delay relationship"""
	actual_lag = PHAT_GCC_TDOA(signal1, signal2)
	
	print(f"VERIFICATION:")
	print(f"  Expected lag: {expected_lag} samples")
	print(f"  Measured lag: {actual_lag} samples")
	print(f"  Error: {abs(actual_lag - expected_lag)} samples")
	
	if abs(actual_lag - expected_lag) <= tolerance:
		print("PASS: Lag measurement is correct")
	else:
		print("FAIL: Lag measurement is incorrect")
	print()
	return actual_lag

def verify_telephone_signals(signal1, signal2, expected_lag, tolerance=2):
	"""Verify that signals have the expected delay relationship"""
	actual_lag = PHAT_GCC_TDOA(signal1, signal2, debug=True)
	
	print(f"VERIFICATION:")
	print(f"  Expected lag: {expected_lag} samples")
	print(f"  Measured lag: {actual_lag} samples")
	print(f"  Error: {abs(actual_lag - expected_lag)} samples")
	
	if abs(actual_lag - expected_lag) <= tolerance:
		print("PASS: Lag measurement is correct")
	else:
		print("FAIL: Lag measurement is incorrect")
	print()
	return actual_lag

def create_delayed_signals(base_signal, delays_samples, signal_length):
	"""
	Create delayed signals with proper handling
	delays_samples: array of delays for each signal [delay0, delay1, delay2]
	"""
	signals = []
	for delay in delays_samples:
		# Create delayed signal by rolling, here delay is - because roll normally shifts right and wraps around, so a roll of 5 would mean a tdoa of -5.
		delayed_sig = np.roll(base_signal, -delay)
		
		# Handle wrap-around by zero-padding the beginning
		if delay > 0:
			delayed_sig[:delay] = 0
		elif delay < 0:
			delayed_sig[delay:] = 0
			
		signals.append(delayed_sig[:signal_length])
	
	return signals

def visualize_signals_with_delays(signals, tdoa_samples, sample_rate=SAMPLE_RATE):
	"""
	Visualize the three signals and their measured delays
	
	Parameters:
	- signals: list of 3 numpy arrays (the actual signals)
	- tdoa_samples: dict with 'tdoa_01', 'tdoa_02', 'tdoa_12' in samples
	- sample_rate: sample rate in Hz
	"""
	import matplotlib.pyplot as plt
	
	fig, axes = plt.subplots(3, 1, figsize=(14, 8))
	
	time = np.arange(len(signals[0])) / sample_rate
	colors = ['blue', 'green', 'purple']
	
	# Find the peak of the first signal to use as reference
	peak_idx_0 = np.argmax(np.abs(signals[0]))
	peak_time_0 = peak_idx_0 / sample_rate * 1000  # in ms
	
	for i, (ax, signal, color) in enumerate(zip(axes, signals, colors)):
		ax.plot(time * 1000, signal, color=color, linewidth=1.5)
		ax.set_ylabel(f'Mic {i}', fontsize=12)
		ax.grid(True, alpha=0.3)
		ax.set_xlim(0, len(signal) / sample_rate * 1000)
		
		# Add red reference line at Mic 0's peak
		if i == 0:
			ax.axvline(peak_time_0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Reference Peak')
			ax.legend()
		else:
			# Add reference line and delayed line
			ax.axvline(peak_time_0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Ref (Mic 0)')
			
			# Calculate delay for this mic relative to mic 0
			if i == 1:
				delay_samples = tdoa_samples['tdoa_01']
			else:  # i == 2
				delay_samples = tdoa_samples['tdoa_02']
			
			delay_ms = delay_samples / sample_rate * 1000
			delayed_peak_time = peak_time_0 + delay_ms
			
			ax.axvline(delayed_peak_time, color='orange', linestyle='--', linewidth=2, alpha=0.7, label=f'Delayed Peak ({delay_samples} samples)')
			ax.legend()
	
	# Add labels
	axes[0].set_title('Three Microphone Signals with GCC-PHAT Delays', fontsize=14)
	axes[2].set_xlabel('Time / ms', fontsize=12)
	axes[1].set_ylabel('Amplitude', fontsize=12)
	
	# Add delay information as text
	delay_text = (f"Measured TDOAs:\n"
				  f"Mic1 vs Mic0: {tdoa_samples['tdoa_01']} samples ({tdoa_samples['tdoa_01']/sample_rate*1000:.4f} ms)\n"
				  f"Mic2 vs Mic0: {tdoa_samples['tdoa_02']} samples ({tdoa_samples['tdoa_02']/sample_rate*1000:.4f} ms)\n"
				  f"Mic2 vs Mic1: {tdoa_samples['tdoa_12']} samples ({tdoa_samples['tdoa_12']/sample_rate*1000:.4f} ms)")
	
	fig.text(0.02, 0.98, delay_text, transform=fig.transFigure, 
			 fontsize=25, verticalalignment='top',
			 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
	
	plt.tight_layout()
	plt.subplots_adjust(top=0.92)
	plt.show()

def PHAT_GCC_TDOA_with_correlation(signal1, signal2):
	"""
	Calculate TDOA between signal1 and signal2 and return the cross-correlation.
	Returns: (tdoa in samples, cross_correlation array)
	where positive TDOA means signal2 arrives AFTER signal1
	"""
	if not hasattr(PHAT_GCC_TDOA_with_correlation, "counter"):
		PHAT_GCC_TDOA_with_correlation.counter = 0
		
	fft1 = FFT(signal1)
	fft2 = FFT(signal2)
	R = GCC(fft1, fft2)
	R_phat = phat_weight(R)
	
	fig = plt.figure()
	plt.subplot(2, 1, 1)
	plt.plot(np.abs(R))
	plt.title("GCC-PHAT Magnitude Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Magnitude")
	
	plt.subplot(2, 1, 2)
	plt.plot(np.angle(R))
	plt.title("GCC-PHAT Phase Spectrum")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Phase (radians)")
	plt.savefig(f"gcc_phat_before_weight{PHAT_GCC_TDOA_with_correlation.counter}.png")    
	
	fig = plt.figure()
	plt.subplot(2, 1, 1)
	plt.plot(np.abs(R_phat))
	plt.title("GCC-PHAT Magnitude Spectrum (After PHAT Weighting)")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Magnitude")
	
	plt.subplot(2, 1, 2)
	plt.plot(np.angle(R_phat))
	plt.title("GCC-PHAT Phase Spectrum (After PHAT Weighting)")
	plt.xlabel("Frequency (Hz)")
	plt.ylabel("Phase (radians)")
	plt.savefig(f"gcc_phat_after_weight{PHAT_GCC_TDOA_with_correlation.counter}.png")
	
	PHAT_GCC_TDOA_with_correlation.counter += 1
	
	if SHOULD_PLOT == True:
		plt.plot(R_phat)
		plt.title("GCC-PHAT spectrum")
		plt.show()
	
	cross_corr = IFFT(R_phat)
	tdoa = TDOA(cross_corr)
	
	return tdoa, cross_corr

def visualize_cross_correlations(signals, sample_rate=SAMPLE_RATE):
	"""
	Visualize the cross-correlation functions for all microphone pairs.
	Shows where the peak (maximum correlation) occurs for each pair.
	
	Parameters:
	- signals: list of 3 numpy arrays (the actual signals)
	- sample_rate: sample rate in Hz
	"""
	import matplotlib.pyplot as plt
	
	# Calculate cross-correlations for all pairs
	pairs = [(0, 1), (0, 2), (1, 2)]
	pair_names = ['Mic0 vs Mic1', 'Mic0 vs Mic2', 'Mic1 vs Mic2']
	
	fig, axes = plt.subplots(3, 1, figsize=(14, 10))
	
	for (i, j), (ax, pair_name) in zip(pairs, zip(axes, pair_names)):
		# Get cross-correlation using the full computation
		fft1 = np.fft.fft(signals[i])
		fft2 = np.fft.fft(signals[j])
		R = fft1 * np.conj(fft2)
		R_phat = phat_weight(R)
		cross_corr = IFFT(R_phat)
		cross_corr_real = np.real(cross_corr)
		
		# Find peak
		N = len(cross_corr_real)
		peak_idx = np.argmax(cross_corr_real)
		
		# Convert to signed lag
		if peak_idx > N // 2:
			lag = peak_idx - N
		else:
			lag = peak_idx
		
		# Convert index to time in milliseconds
		lag_ms = lag / sample_rate * 1000
		
		# Create lag axis (centered)
		lag_samples = np.arange(-N//2, N//2)
		lag_ms_axis = lag_samples / sample_rate * 1000
		
		# Shift cross-correlation for proper lag visualization
		cross_corr_shifted = np.roll(cross_corr_real, N//2)
		
		# Plot
		ax.plot(lag_ms_axis, cross_corr_shifted, linewidth=2, color='steelblue')
		ax.axvline(lag_ms, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'Peak at {lag} samples ({lag_ms:.4f} ms)')
		ax.axhline(0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
		ax.axvline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
		
		ax.set_ylabel('Correlation', fontsize=12)
		ax.set_title(f'{pair_name} - Cross-Correlation Function', fontsize=13, fontweight='bold')
		ax.grid(True, alpha=0.3)
		ax.legend(fontsize=11)
	
	axes[2].set_xlabel('Time Delay / ms', fontsize=12)
	fig.suptitle('GCC-PHAT Cross-Correlation Output (Peak shows TDOA)', fontsize=14, fontweight='bold')
	
	plt.tight_layout()
	plt.show()

def test_gcc_phat():
	"""
	print("=== TEST 1: Basic delay verification ===")
	filename = "output.wav"  
	SAMPLE_RATE, data = wavfile.read(filename)
	base = data[0:1000]
	signal0 = base
	signal1 = np.roll(base, 5)
	signal2 = np.roll(base, 10)
	
	tdoa01 = PHAT_GCC_TDOA(signal0, signal1)
	print(tdoa01)
	tdoa02 = PHAT_GCC_TDOA(signal0, signal2)
	print(tdoa02)
	tdoa12 = PHAT_GCC_TDOA(signal1, signal2)
	print(tdoa12)
	"""

	
	# Simple test with known delays
	signal_length = 44100  # 1 second
	base_signal = np.random.randn(signal_length)
	
	# Test case 1: signal2 delayed by 10 samples relative to signal1
	test_signal1 = base_signal.copy()
	test_signal2 = np.roll(base_signal, 10)
	test_signal2[:10] = 0  # Clear wrap-around
	
	verify_signals(test_signal1, test_signal2, 10)
	
	# Test case 2: signal2 advanced by 5 samples relative to signal1
	test_signal1 = np.roll(base_signal, 5)
	test_signal1[:5] = 0
	test_signal2 = base_signal.copy()
	
	verify_signals(test_signal1, test_signal2, -5)
	
	print("=== TEST 2: Three microphone simulation ===")
	# Simulate three microphones with a sound source
	sampling_rate = 44100
	duration = 0.1  # seconds
	signal_length = int(sampling_rate * duration)
	
	# Create a more realistic signal (chirp + noise)
	t = np.linspace(0, duration, signal_length)
	base_signal = np.sin(2 * np.pi * 1000 * t) * np.exp(-100 * t)  # Decaying chirp
	base_signal += 0.1 * np.random.randn(signal_length)  # Add noise
	
	# Define true delays in samples (simulating sound arriving at different times)
	# Let's say sound arrives at: mic0 at 100 samples, mic1 at 110 samples, mic2 at 105 samples
	true_delays = np.array([100, 110, 105])  # in samples
	
	# Create signals with these delays
	signals = create_delayed_signals(base_signal, true_delays, signal_length)
	
	print("True delays (samples):")
	print(f"  Mic0: {true_delays[0]}, Mic1: {true_delays[1]}, Mic2: {true_delays[2]}")
	print("True TDOAs (signal_j - signal_i):")
	print(f"  TDOA_01 (mic1 - mic0): {true_delays[1] - true_delays[0]}")
	print(f"  TDOA_02 (mic2 - mic0): {true_delays[2] - true_delays[0]}")
	print(f"  TDOA_12 (mic2 - mic1): {true_delays[2] - true_delays[1]}")
	print()
	
	# Measure TDOAs
	print("Measured TDOAs:")
	tdoa_01 = PHAT_GCC_TDOA(signals[0], signals[1])  # mic1 vs mic0
	tdoa_02 = PHAT_GCC_TDOA(signals[0], signals[2])  # mic2 vs mic0
	tdoa_12 = PHAT_GCC_TDOA(signals[1], signals[2])  # mic2 vs mic1
	
	print("=== SUMMARY ===")
	print("Pair       | Expected | Measured | Error")
	print("-----------|----------|----------|------")
	print(f"Mic1-Mic0  | {true_delays[1]-true_delays[0]:8} | {tdoa_01:8} | {abs(tdoa_01 - (true_delays[1]-true_delays[0])):5}")
	print(f"Mic2-Mic0  | {true_delays[2]-true_delays[0]:8} | {tdoa_02:8} | {abs(tdoa_02 - (true_delays[2]-true_delays[0])):5}")
	print(f"Mic2-Mic1  | {true_delays[2]-true_delays[1]:8} | {tdoa_12:8} | {abs(tdoa_12 - (true_delays[2]-true_delays[1])):5}")
	
	# Verify the signs make physical sense
	print("\n=== PHYSICAL INTERPRETATION ===")
	if tdoa_01 > 0:
		print(f"Mic1 arrives {tdoa_01} samples AFTER Mic0")
	else:
		print(f"Mic1 arrives {abs(tdoa_01)} samples BEFORE Mic0")
		
	if tdoa_02 > 0:
		print(f"Mic2 arrives {tdoa_02} samples AFTER Mic0")
	else:
		print(f"Mic2 arrives {abs(tdoa_02)} samples BEFORE Mic0")
		
	if tdoa_12 > 0:
		print(f"Mic2 arrives {tdoa_12} samples AFTER Mic1")
	else:
		print(f"Mic2 arrives {abs(tdoa_12)} samples BEFORE Mic1")
		
	print("\n\n =======================================================================")
	print ("\n=== TEST 3: Telephone band filtered signals ===")
	print("True delays (samples):")
	print(f"  Mic0: {true_delays[0]}, Mic1: {true_delays[1]}, Mic2: {true_delays[2]}")
	print("True TDOAs (signal_j - signal_i):")
	print(f"  TDOA_01 (mic1 - mic0): {true_delays[1] - true_delays[0]}")
	print(f"  TDOA_02 (mic2 - mic0): {true_delays[2] - true_delays[0]}")
	print(f"  TDOA_12 (mic2 - mic1): {true_delays[2] - true_delays[1]}")
	print()

	# Visualize the signals with their delays
	print("\n=== VISUALIZING SIGNALS WITH DELAYS ===")
	measured_offsets = {
		'tdoa_01': tdoa_01,
		'tdoa_02': tdoa_02,
		'tdoa_12': tdoa_12
	}
	visualize_signals_with_delays(signals, measured_offsets)

"""
if __name__ == "__main__":
	# First I need to fast fourier transform three signal given by arrays.
	test_array1 = np.random.randn(5*44100)
	test_array2 = np.roll(test_array1.copy(), 5)
	test_array3 = np.roll(test_array1.copy(), 10)

	beforetime = time.time()
	fft_result1 = FFT(test_array1)
	fft_result2 = FFT(test_array2)
	fft_result3 = FFT(test_array3)

	afterprint = time.time()
	# print(afterprint-aftertime)

	# Next I calculate the cross-correlation in frequency domain. For three microphones, I have three pairs.
	R_12 = GCC(fft_result1, fft_result2)
	R_23 = GCC(fft_result2, fft_result3)
	R_13 = GCC(fft_result1, fft_result3)

	# Next I multiply by the PHAT weighting function.
	R_12_phat = phat_weight(R_12)
	R_23_phat = phat_weight(R_23)
	R_13_phat = phat_weight(R_13)

	# Next I take the IFFT to get the cross-correlation functions.
	cross_corr_12 = IFFT(R_12_phat)
	cross_corr_23 = IFFT(R_23_phat)
	cross_corr_13 = IFFT(R_13_phat)

	endtime = time.time()

	# Finally, I find the peak in the cross-correlation functions to estimate the time delays.
	tdoa_12 = TDOA(cross_corr_12)
	tdoa_23 = TDOA(cross_corr_23)
	tdoa_13 = TDOA(cross_corr_13)
	print("TDOA between mic 1 and 2:", tdoa_12)
	print("TDOA between mic 2 and 3:", tdoa_23)
	print("TDOA between mic 1 and 3:", tdoa_13)
"""