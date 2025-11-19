import numpy as np
import time

# GCC-PHAT quick rundown:
# 1. Take the FFT of all three signals.
# 2. Calculate the cross-correlation spectrum between pairs of signals.
# 3. Multiply by a PHAT weighting function to normalize the cross-correlation spectrum.
# 4. Take the inverse FFT of the normalized cross-correlation spectrum to get the cross-correlation function.
# 5. Find the peak in the cross-correlation function and make sure to convert the index to a signed lag value.
# 6. Calculate the TDOA from the location of the peak (after considering lag) in the cross-correlation function.

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
    idx = np.argmax(np.abs(corr))
    # convert index to signed lag
    if idx > N//2:
        return idx - N # if in the first half of the index convert wrapped-around negative lag
    else:
        return idx # if in the second half of the index keep it as normal positive lag

# 6.
def TDOA(cross_corr):
    tdoa = peak_lag(cross_corr)
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