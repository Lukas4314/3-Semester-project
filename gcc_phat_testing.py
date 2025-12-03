# GCC-PHAT quick rundown:
# 1. Take the FFT of all three signals.
# 2. Calculate the cross-correlation spectrum between pairs of signals.
# 3. Multiply by a PHAT weighting function to normalize the cross-correlation spectrum.
# 4. Take the inverse FFT of the normalized cross-correlation spectrum to get the cross-correlation function.
# 5. Find the peak in the cross-correlation function and make sure to convert the index to a signed lag value.
# 6. Calculate the TDOA from the location of the peak (after considering lag) in the cross-correlation function.

import numpy as np
import time
from matplotlib import pyplot
import scipy.signal
# 35.7
# 28.8


# 1. Take the FFT of all three signals.
def FFT(testarray):
    return np.fft.fft(testarray)

# 1.5 Apply telephone band filter
def filter_telephone_band(fftarray):
    N = len(fftarray)
    samplerate = 44100
    lowcut = 300
    highcut = 3600

    fft_freqs = np.fft.fftfreq(N, d=1/samplerate)

    filter_mask = ((np.abs(fft_freqs) >= lowcut) & (np.abs(fft_freqs) <= highcut)).astype(float)
    return fftarray * filter_mask #outot is the filterd fftarray

# 2. Calculate the cross-correlation spectrum between pairs of signals.
def GCC(fft1, fft2):
    return fft1 * np.conj(fft2)

# 3. Multiply by a PHAT weighting function to normalize the cross-correlation spectrum, here the weighting is 1.
def phat_weight(R, eps=1e-8):
    mag = np.abs(R)
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
    return -peak_lag(cross_corr)

def PHAT_GCC_TDOA(signal1, signal2, debug=False):
    """
    Calculate TDOA between signal1 and signal2.
    Returns: tdoa in samples where positive value means signal2 arrives AFTER signal1
    """
    fft1 = FFT(signal1)
    fft2 = FFT(signal2)
    fft1 = filter_telephone_band(fft1)
    fft2 = filter_telephone_band(fft2)
    R = GCC(fft1, fft2)
    R_phat = phat_weight(R)
    pyplot.plot(R_phat)
    pyplot.title("GCC-PHAT spectrum")
    pyplot.show()
    cross_corr = IFFT(R_phat)
    
    if debug:
        corr_real = np.real(cross_corr)
        N = len(cross_corr)
        
        # Find top peaks
        peak_indices = np.argsort(corr_real)[-5:][::-1]
        peak_values = corr_real[peak_indices]
        peak_lags = [idx if idx <= N//2 else idx - N for idx in peak_indices]
        
        print(f"DEBUG GCC-PHAT:")
        print(f"  Signal length: {len(signal1)}")
        print(f"  Top correlation peaks:")
        for i, (idx, lag, val) in enumerate(zip(peak_indices, peak_lags, peak_values)):
            print(f"    Peak {i+1}: Index {idx}, Lag {lag}, Value {val:.6f}")
        
        tdoa = TDOA(cross_corr)
        print(f"  Selected TDOA: {tdoa} samples")
        print(f"  Interpretation: signal2 arrives {tdoa} samples {'AFTER' if tdoa > 0 else 'BEFORE'} signal1")
        print()
    
    return TDOA(cross_corr)

def TELEPHONE_PHAT_GCC_TDOA(signal1, signal2, debug=False):
    filtered_signal1 = filter_telephone_band(signal1, fs=44100)
    filtered_signal2 = filter_telephone_band(signal2, fs=44100)
    fft1 = FFT(filtered_signal1)
    fft2 = FFT(filtered_signal2)
    R = GCC(fft1, fft2)
    R_phat = phat_weight(R)
    pyplot.plot(R_phat)
    pyplot.title("Telephone band filtered GCC-PHAT spectrum")
    pyplot.show()
    cross_corr = IFFT(R_phat)
    
    if debug:
        corr_real = np.real(cross_corr)
        N = len(cross_corr)
        
        # Find top peaks
        peak_indices = np.argsort(corr_real)[-5:][::-1]
        peak_values = corr_real[peak_indices]
        peak_lags = [idx if idx <= N//2 else idx - N for idx in peak_indices]
        
        print(f"DEBUG TELEPHONE GCC-PHAT:")
        print(f"  Signal length: {len(signal1)}")
        print(f"  Top correlation peaks:")
        for i, (idx, lag, val) in enumerate(zip(peak_indices, peak_lags, peak_values)):
            print(f"    Peak {i+1}: Index {idx}, Lag {lag}, Value {val:.6f}")
        
        tdoa = TDOA(cross_corr)
        print(f"  Selected TDOA: {tdoa} samples")
        print(f"  Interpretation: signal2 arrives {tdoa} samples {'AFTER' if tdoa > 0 else 'BEFORE'} signal1")
        print()
    
    return TDOA(cross_corr)

def verify_signals(signal1, signal2, expected_lag, tolerance=2):
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

def verify_telephone_signals(signal1, signal2, expected_lag, tolerance=2):
    """Verify that signals have the expected delay relationship"""
    actual_lag = TELEPHONE_PHAT_GCC_TDOA(signal1, signal2, debug=True)
    
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
        # Create delayed signal by rolling
        delayed_sig = np.roll(base_signal, delay)
        
        # Handle wrap-around by zero-padding the beginning
        if delay > 0:
            delayed_sig[:delay] = 0
        elif delay < 0:
            delayed_sig[delay:] = 0
            
        signals.append(delayed_sig[:signal_length])
    
    return signals

if __name__ == "__main__":
    print("=== TEST 1: Basic delay verification ===")
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
    base_signal = np.sin(2 * np.pi * 1000 * t) * np.exp(-5 * t)  # Decaying chirp
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
    tdoa_01 = PHAT_GCC_TDOA(signals[0], signals[1], debug=True)  # mic1 vs mic0
    tdoa_02 = PHAT_GCC_TDOA(signals[0], signals[2], debug=True)  # mic2 vs mic0
    tdoa_12 = PHAT_GCC_TDOA(signals[1], signals[2], debug=True)  # mic2 vs mic1
    
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
    """
    print("\n\n =======================================================================")
    print ("\n=== TEST 3: Telephone band filtered signals ===")
    print("True delays (samples):")
    print(f"  Mic0: {true_delays[0]}, Mic1: {true_delays[1]}, Mic2: {true_delays[2]}")
    print("True TDOAs (signal_j - signal_i):")
    print(f"  TDOA_01 (mic1 - mic0): {true_delays[1] - true_delays[0]}")
    print(f"  TDOA_02 (mic2 - mic0): {true_delays[2] - true_delays[0]}")
    print(f"  TDOA_12 (mic2 - mic1): {true_delays[2] - true_delays[1]}")
    print()
    
    # Measure TDOAs
    print("Measured TDOAs:")
    tdoa_01 = TELEPHONE_PHAT_GCC_TDOA(signals[0], signals[1], debug=True)  # mic1 vs mic0
    tdoa_02 = TELEPHONE_PHAT_GCC_TDOA(signals[0], signals[2], debug=True)  # mic2 vs mic0
    tdoa_12 = TELEPHONE_PHAT_GCC_TDOA(signals[1], signals[2], debug=True)  # mic2 vs mic1
    
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
    """
"""

# 1.
def FFT(testarray):
    fft_result = np.fft.fft(testarray)
    return fft_result

# 2.
def GCC(fft1, fft2):
    cross_spectrum = fft1 * np.conj(fft2)
    return cross_spectrum

# 3. Here I use PHAT weighting, which means beta = 1, so we get the sharpest TDOA (Time Difference Of Arrival) estimate .
def phat_weight(R, eps=1e-8):
    mag = np.abs(R)
    return R / (mag + eps)

# 4.
def IFFT(R_phat):
    cross_correlation = np.fft.ifft(R_phat)
    return cross_correlation

# 5.
# Before I calculate the TDOA I need interpretable values from the cross-correlation functions.
# Example my samplesize is 5*44100 = 220500, but I get the number 220495, which doesnt mean a delay of 220495 samples, but instead a delay of -5 samples.
# So I need to convert the index of the peak to a signed lag value.
def peak_lag(corr):
    N = len(corr)
    corr_mag = np.abs(corr)
    idx = np.argmax(corr_mag)
    # convert index to signed lag
    if idx >= N//2:
        lag = idx - N  # Negative delay
    else:
        lag = idx      # Positive delay
    
    return -lag

# 6.
def TDOA(cross_corr):
    tdoa = peak_lag(cross_corr)
    return tdoa

# A function that combines all steps for use in triangulation.
def PHAT_GCC_TDOA(signal1, signal2):
    fft1 = FFT(signal1)
    fft2 = FFT(signal2)
    R = GCC(fft1, fft2)
    R_phat = phat_weight(R)
    cross_corr = IFFT(R_phat)
    
    # ADD COMPREHENSIVE DEBUG:
    corr_mag = np.abs(cross_corr)
    
    # Find top 10 peaks to see what's available
    peak_indices = np.argsort(corr_mag)[-10:][::-1]  # Top 10 peaks
    peak_values = corr_mag[peak_indices]
    peak_lags = [idx if idx <= len(corr_mag)//2 else idx - len(corr_mag) 
                for idx in peak_indices]
    
    print(f"DEBUG GCC-PHAT:")
    print(f"  Signal length: {len(signal1)}")
    print(f"  Top 5 correlation peaks:")
    for i, (idx, lag, val) in enumerate(zip(peak_indices[:5], peak_lags[:5], peak_values[:5])):
        print(f"    {i+1}. Index {idx}, Lag {lag}, Value {val:.6f}")
    
    tdoa = TDOA(cross_corr)
    print(f"  Selected lag: {tdoa}")
    print()
    
    return tdoa

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