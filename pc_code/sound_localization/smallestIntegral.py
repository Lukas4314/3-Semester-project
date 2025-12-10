import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt


def apply_lowpass_filter(sig, cutoff_freq, fs):

    nyquist = 0.5 * fs
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(5, normal_cutoff, btype='low', analog=False)
    filtered_sig = filtfilt(b, a, sig)
    return filtered_sig


def get_TDOA(sig, refsig, search_area = 60, name="integralTDOA"):
    # Pad signals to avoid looping around
    
    scores = {}
    
    for i in range(-search_area, search_area + 1):
        sig = np.roll(sig, i)
        
        # Only take out of the seach area so the roll does not screw it over
        diff = sig[search_area:-search_area] - refsig[search_area:-search_area]
        score = np.sum(np.abs(diff))
        scores[i] = score
    
    best_shift = min(scores, key=scores.get)
    
    fig = plt.figure(name)
    plt.plot(list(scores.keys()), list(scores.values()))
    fig.savefig(f"{name}.png")
    
    
    return best_shift