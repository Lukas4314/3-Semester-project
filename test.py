from pc_code.sound_localization.gccPhat import test_gcc_phat, PHAT_GCC_TDOA, create_delayed_signals
from pc_code.sound_localization.gccPhatByMatlab import gccphat_matlab
#from pc_code.transcriber import transcriber
from pc_code.sound_localization.Triangulate import test123, triangulate_from_sound, find_sound_origin, microphone_placement
import numpy as np
from scipy.io.wavfile import write
import re
from consts import SAMPLE_RATE


use_fake_data = False

if not use_fake_data:
    I2S0 = np.array([])
    I2S1 = np.array([])

    with open("test_I2S0_44k.txt", "r") as f:
        for line in f:
            text = line.split(" ")
            for num in text:
                num = num.replace(",", "")
                if num.strip() != "":
                    I2S0 = np.append(I2S0, float(num.strip()))
                    
    with open("test_I2S1_44k.txt", "r") as f:
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


else:
    duration = 0.1  # seconds
    signal_length = int(SAMPLE_RATE * duration)

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




write("mic_1.wav", SAMPLE_RATE, mic_1.astype(np.int16))
write("mic_2.wav", SAMPLE_RATE, mic_2.astype(np.int16))
write("mic_3.wav", SAMPLE_RATE, mic_3.astype(np.int16))


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



