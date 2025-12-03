import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

# --- Load WAV file ---
filename = "output.wav"  
samplerate, data = wavfile.read(filename)

# If stereo → use one channel
if data.ndim == 2:
    data = data[:, 0]

data = data.astype(float)

# --- FFT ---
N = len(data)
fft_vals = np.fft.fft(data)
fft_freqs = np.fft.fftfreq(N, d=1/samplerate)
print(fft_vals)

# --- Create frequency-domain band-pass filter ---
lowcut = 300
highcut = 3400

# Mask: 1 inside band, 0 outside
filter_mask = ((np.abs(fft_freqs) >= lowcut) & (np.abs(fft_freqs) <= highcut)).astype(float)

# --- Plot the filter (only positive frequencies) ---
pos_mask = fft_freqs >= 0
plt.figure(figsize=(10, 4))
plt.plot(fft_freqs[pos_mask], filter_mask[pos_mask])
plt.title("Frequency-domain Filter Mask (300–3600 Hz)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Filter Gain")
plt.ylim(-0.1, 1.1)
plt.grid(True)
plt.tight_layout()
plt.show()

# --- Apply the filter in the frequency domain ---
fft_filtered = fft_vals * filter_mask

# --- Plot filtered magnitude spectrum ---
plt.figure(figsize=(10, 5))
plt.plot(fft_freqs[pos_mask], np.abs(fft_filtered[pos_mask]))
plt.title("Filtered Spectrum (After Frequency-Domain Band-pass)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.grid(True)
plt.tight_layout()
plt.show()

# --- OPTIONAL: convert back to time domain and save ---
filtered_time = np.fft.ifft(fft_filtered).real

# Normalize and convert to int16 for WAV storage
filtered_time_norm = filtered_time / np.max(np.abs(filtered_time))
filtered_time_int16 = (filtered_time_norm * 32767).astype(np.int16)

wavfile.write("output_filtered.wav", samplerate, filtered_time_int16)
print("Saved filtered audio as output_filtered.wav")
