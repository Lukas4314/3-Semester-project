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
from consts import SAMPLE_RATE, SHOULD_PLOT
# 35.7
# 28.8


# 1. Take the FFT of all three signals.
def FFT(testarray):
    if SHOULD_PLOT == True:
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
    return np.fft.fft(testarray)#, n=2*len(testarray))

# 1.5 Apply telephone band filter
def filter_telephone_band(fftarray):
    N = len(fftarray)
    lowcut = 300
    highcut = 1000

    fft_freqs = np.fft.fftfreq(N, d=1/SAMPLE_RATE)
    filter_mask = ((np.abs(fft_freqs) >= lowcut) & (np.abs(fft_freqs) <= highcut)).astype(float)
    fft_filtered = fftarray * filter_mask 
    pos_mask = fft_freqs >= 0 
    if SHOULD_PLOT == True:
        plt.figure(figsize=(10, 5))
        plt.plot(fft_freqs[pos_mask], np.abs(fft_filtered[pos_mask]))
        plt.title("Filtered Spectrum (After Frequency-Domain Band-pass)")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Magnitude")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    return fftarray * filter_mask #output is the filterd fftarray

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

def PHAT_GCC_TDOA(signal1, signal2):
    """
    Calculate TDOA between signal1 and signal2.
    Returns: tdoa in samples where positive value means signal2 arrives AFTER signal1
    """
    if not hasattr(PHAT_GCC_TDOA, "counter"):
        PHAT_GCC_TDOA.counter = 0
        
    fft1 = FFT(signal1)
    fft2 = FFT(signal2)
    #fft1 = filter_telephone_band(fft1)
    #fft2 = filter_telephone_band(fft2)
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
    
    PHAT_GCC_TDOA.counter += 1
    
    if SHOULD_PLOT == True:
        plt.plot(R_phat)
        plt.title("GCC-PHAT spectrum")
        plt.show()
    cross_corr = IFFT(R_phat)
    tdoa = TDOA(cross_corr)
    
    return tdoa

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