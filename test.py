from pc_code.sound_localization.gccPhat import test_gcc_phat, PHAT_GCC_TDOA, create_delayed_signals
from pc_code.sound_localization.gccPhatByMatlab import gccphat_matlab
#from pc_code.transcriber import transcriber
from pc_code.sound_localization.Triangulate import test123, triangulate_from_sound, find_sound_origin, microphone_placement
import numpy as np
from scipy.io.wavfile import write
import re
from consts import SAMPLE_RATE




"""
sample_rate = 144000

I2S0 = np.array([])
I2S1 = np.array([])

with open("test_I2S0.txt", "r") as f:
    for line in f:
        text = line.split(" ")
        for num in text:
            num = num.replace(",", "")
            if num.strip() != "":
                I2S0 = np.append(I2S0, float(num.strip()))
                
with open("test_I2S1.txt", "r") as f:
    for line in f:
        text = line.split(" ")
        for num in text:
            num = num.replace(",", "")
            if num.strip() != "":
                I2S1 = np.append(I2S1, float(num.strip()))
                
I2S0 = I2S0[2:]
I2S1 = I2S1[2:]
print("Loaded data lengths:", len(I2S0), len(I2S1))

# Get every second sample
mic_1 = I2S0[::2]
mic_2 = I2S0[1::2]
mic_3 = I2S1

# Fake dummy data
t = np.linspace(0, 5, 5 * SAMPLE_RATE, endpoint=False)
mic_1 = np.sin(t * 440 * 2 * np.pi)  + np.sin(t * 4677 * 2 * np.pi) + np.sin(t * 43 * 2 * np.pi) + np.sin(t * 4543 * 2 * np.pi) + np.sin(t * 880 * 2 * np.pi) + np.sin(t * 990 * 2 * np.pi) + np.sin(t * 1100 * 2 * np.pi)
mic_2 = np.roll(mic_1, 20)  # Shifted version of mic_1
mic_3 = np.roll(mic_1, 10)  # Shifted version

mic_1 = mic_1 + np.random.normal(0, 0.1, t.shape)
mic_2 = mic_2 + np.random.normal(0, 0.1, t.shape)
mic_3 = mic_3 + np.random.normal(0, 0.1, t.shape)


# Apply frequency noise
mic_1 = mic_1 + 0.3 * np.sin(2 * np.pi * 2443 * t + 0.5) + 0.3 * np.sin(2 * np.pi * 233 * t + 0.2) + 0.2 * np.sin(2 * np.pi * 6543 * t + 1) + 0.1 * np.sin(2 * np.pi * 33 * t) + 0.05 * np.sin(2 * np.pi * 5678 * t) + 0.025 * np.sin(2 * np.pi * 18000 * t)
mic_2 = mic_2 + 0.3 * np.sin(2 * np.pi * 2443 * t + 0.5) + 0.3 * np.sin(2 * np.pi * 324 * t + 0.2) + 0.2 * np.sin(2 * np.pi * 4345 * t + 1) + 0.1 * np.sin(2 * np.pi * 432 * t) + 0.05 * np.sin(2 * np.pi * 4567 * t) + 0.025 * np.sin(2 * np.pi * 54433 * t)
mic_3 = mic_3 + 0.3 * np.sin(2 * np.pi * 432 * t + 0.5) + 0.3 * np.sin(2 * np.pi * 2334 * t + 0.2) + 0.2 * np.sin(2 * np.pi * 234 * t + 1) + 0.1 * np.sin(2 * np.pi * 6776 * t) + 0.05 * np.sin(2 * np.pi * 76 * t) + 0.025 * np.sin(2 * np.pi * 6566 * t)
"""

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

mic_1 = signals[0]
mic_2 = signals[1]
mic_3 = signals[2]

print("Mic data lengths:", len(mic_1), len(mic_2), len(mic_3))


print("GCC-PHAT TDOA estimates:")
print(PHAT_GCC_TDOA(mic_1, mic_2))
print(PHAT_GCC_TDOA(mic_1, mic_3))
print(PHAT_GCC_TDOA(mic_2, mic_3))

print("GCC-PHAT MATLAB estimates:")
print(gccphat_matlab(mic_1, mic_2)[0])
print(gccphat_matlab(mic_1, mic_3)[0])
print(gccphat_matlab(mic_2, mic_3)[0])

mic_positions = microphone_placement()

best_point, _ = triangulate_from_sound(mic0_data=mic_1, mic1_data=mic_2, mic2_data=mic_3)
#best_point, _ = find_sound_origin(mic_positions, [-105, -359, 192])

print("Estimated source location (x, y):", best_point)
print("Estimated angle (degrees):", np.degrees(np.arctan2(best_point[1], best_point[0])))



