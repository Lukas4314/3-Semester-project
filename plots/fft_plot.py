import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

# --- Indlæs WAV-fil (skal ligge i samme mappe som dette script) ---
filename = "output.wav"
samplerate, data = wavfile.read(filename)

# Hvis stereo → vælg én kanal
if data.ndim == 2:
    data = data[:, 0]

# --- FFT ---
N = len(data)
fft_vals = np.fft.fft(data)
fft_freqs = np.fft.fftfreq(N, d=1/samplerate)

# Kun positive frekvenser (reelle signaler har symmetrisk FFT)
mask = fft_freqs >= 0
fft_vals = np.abs(fft_vals[mask])
fft_freqs = fft_freqs[mask]

# --- Plot frekvensspektrum ---
plt.figure(figsize=(10,5))
plt.plot(fft_freqs, fft_vals)
plt.title("Frekvensdomæne – FFT af input.wav")
plt.xlabel("Frekvens (Hz)")
plt.ylabel("Amplitude")
plt.grid(True)
plt.show()
