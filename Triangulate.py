import gcc_phat_testing as gcc
import numpy as np
import time
import sys

def get_tdoa_seconds(sig1, sig2, sampling_rate, debug=False):
    raw_lag = gcc.PHAT_GCC_TDOA(sig1, sig2)
    if debug:
        print(f"  Raw lag: {raw_lag} samples")
    return raw_lag / sampling_rate

def calculate_error_with_absolute_distance(pos, mic_positions, d1, d2, d3, approx_distance=1.0, distance_weight=0.1):
    """
    Improved error function that includes absolute distance constraint
    """
    dist0 = np.linalg.norm(pos - mic_positions[0])
    dist1 = np.linalg.norm(pos - mic_positions[1])
    dist2 = np.linalg.norm(pos - mic_positions[2])
    
    # TDOA errors (relative distances)
    pred_d1 = dist1 - dist0
    pred_d2 = dist2 - dist0  
    pred_d3 = dist2 - dist1
    
    error1 = (pred_d1 - d1)**2
    error2 = (pred_d2 - d2)**2
    error3 = (pred_d3 - d3)**2
    
    # Absolute distance error (penalize positions that are too close/far)
    # Use the average distance to all mics as reference
    avg_distance = (dist0 + dist1 + dist2) / 3.0
    distance_error = (avg_distance - approx_distance)**2
    
    # Combine errors (you can adjust the weight)
    total_error = error1 + error2 + error3 + distance_weight * distance_error
    
    return total_error

def triangulate_from_start(mic_positions, tdoa_01, tdoa_02, tdoa_12, start_pos, 
                          speed_of_sound=343.0, steps=200, learning_rate=0.1, approx_distance=1.0):
    d1 = tdoa_01 * speed_of_sound
    d2 = tdoa_02 * speed_of_sound
    d3 = tdoa_12 * speed_of_sound
    
    pos = start_pos.copy()
    
    for step in range(steps):
        current_error = calculate_error_with_absolute_distance(pos, mic_positions, d1, d2, d3, approx_distance)
        eps = 1e-6
        grad_x = (calculate_error_with_absolute_distance(pos + [eps, 0], mic_positions, d1, d2, d3, approx_distance) - current_error) / eps
        grad_y = (calculate_error_with_absolute_distance(pos + [0, eps], mic_positions, d1, d2, d3, approx_distance) - current_error) / eps
        pos = pos - learning_rate * np.array([grad_x, grad_y])
        learning_rate *= 0.995
    
    final_error = calculate_error_with_absolute_distance(pos, mic_positions, d1, d2, d3, approx_distance)
    return pos, final_error

def find_sound_source(mic_positions, signals, sampling_rate, speed_of_sound=343.0, approx_distance=1.0):
    print("=== MEASURING TDOAs ===")
    tdoa_01 = get_tdoa_seconds(signals[0], signals[1], sampling_rate, debug=True)
    tdoa_02 = get_tdoa_seconds(signals[0], signals[2], sampling_rate, debug=True)
    tdoa_12 = get_tdoa_seconds(signals[1], signals[2], sampling_rate, debug=True)
    
    print(f"TDOA measurements:")
    print(f"  Mic1 - Mic0: {tdoa_01:.6f}s ({tdoa_01 * 1000:.2f}ms)")
    print(f"  Mic2 - Mic0: {tdoa_02:.6f}s ({tdoa_02 * 1000:.2f}ms)")
    print(f"  Mic2 - Mic1: {tdoa_12:.6f}s ({tdoa_12 * 1000:.2f}ms)")
    
    # Convert to distance differences
    dist_diff_01 = tdoa_01 * speed_of_sound
    dist_diff_02 = tdoa_02 * speed_of_sound  
    dist_diff_12 = tdoa_12 * speed_of_sound
    
    print(f"\nDistance differences:")
    print(f"  d1 (mic1-mic0): {dist_diff_01:.4f}m")
    print(f"  d2 (mic2-mic0): {dist_diff_02:.4f}m")
    print(f"  d3 (mic2-mic1): {dist_diff_12:.4f}m")
    
    print(f"\nUsing approximate distance constraint: {approx_distance:.1f}m")
    print("\n=== TRIANGULATION ===")
    center = np.mean(mic_positions, axis=0)
    best_position = None
    best_error = float('inf')
    
    # Test starting positions at the expected distance
    test_distances = [approx_distance * 0.7, approx_distance, approx_distance * 1.3]
    angles = np.linspace(0, 2*np.pi, 16)  # Test many directions
    
    for distance in test_distances:
        for angle in angles:
            direction = np.array([np.cos(angle), np.sin(angle)])
            start_pos = center + direction * distance
            candidate, error = triangulate_from_start(mic_positions, tdoa_01, tdoa_02, tdoa_12, 
                                                    start_pos, approx_distance=approx_distance)
            if error < best_error:
                best_error = error
                best_position = candidate
    
    return best_position, best_error, (tdoa_01, tdoa_02, tdoa_12)

def create_test_signals_improved(true_position, mic_positions, sampling_rate, duration=0.3, add_noise=True):
    """Create test signals with better geometry"""
    signal_length = int(sampling_rate * duration)
    
    # Create a broadband signal
    t = np.linspace(0, duration, signal_length)
    base_signal = np.random.randn(signal_length)
    
    # Add a window to reduce edge effects
    window = np.hanning(signal_length)
    base_signal = base_signal * window
    
    if add_noise:
        base_signal += 0.1 * np.random.randn(signal_length)
    
    # Calculate true time delays based on geometry
    speed_of_sound = 343.0
    distances = np.linalg.norm(mic_positions - true_position, axis=1)
    time_delays = distances / speed_of_sound
    
    # Convert to sample delays (make mic0 the reference)
    sample_delays = (time_delays - time_delays[0]) * sampling_rate
    sample_delays = sample_delays.astype(int)
    
    print(f"True geometric delays (samples relative to mic0):")
    print(f"  Mic0: {sample_delays[0]} (reference)")
    print(f"  Mic1: {sample_delays[1]}")
    print(f"  Mic2: {sample_delays[2]}")
    print(f"True time delays: {time_delays}")
    print(f"True distances: {distances}")
    print(f"Average distance: {np.mean(distances):.2f}m")
    
    # Create delayed signals
    signals = []
    
    for delay in sample_delays:
        delayed_signal = np.roll(base_signal, delay)
        if delay > 0:
            delayed_signal[:delay] = 0
        elif delay < 0:
            delayed_signal[delay:] = 0
        signals.append(delayed_signal)
    
    return signals, distances, time_delays

if __name__ == "__main__":
    # Use a LARGER microphone array for better geometry
    mic_positions = np.array([
        [0.0, 0.0],    # Mic 0 - bottom left
        [0.1, 0.0],    # Mic 1 - bottom right  
        [0.05, 0.0866]    # Mic 2 - top (equilateral triangle with 0.1m sides)
    ])
    
    # Use a position that creates more distinct TDOAs
    true_position = np.array([1.0, 0.8])
    sampling_rate = 44100
    
    print("=== IMPROVED SOUND SOURCE LOCALIZATION WITH DISTANCE CONSTRAINT ===")
    print(f"Microphone positions: {mic_positions}")
    print(f"True sound source: {true_position}")
    print(f"Sampling rate: {sampling_rate} Hz")
    
    """# Create test signals
    signals, true_distances, true_time_delays = create_test_signals_improved(
        true_position, mic_positions, sampling_rate, duration=0.3
    )

    # Calculate expected TDOAs
    expected_tdoa_01 = (true_distances[1] - true_distances[0]) / 343.0
    expected_tdoa_02 = (true_distances[2] - true_distances[0]) / 343.0
    expected_tdoa_12 = (true_distances[2] - true_distances[1]) / 343.0
    """
    
    expected_tdoa_01 = (np.linalg.norm(mic_positions[1]-true_position) - np.linalg.norm(mic_positions[0]-true_position)) / 343.0
    expected_tdoa_02 = (np.linalg.norm(mic_positions[2]-true_position) - np.linalg.norm(mic_positions[0]-true_position)) / 343.0
    expected_tdoa_12 = (np.linalg.norm(mic_positions[2]-true_position) - np.linalg.norm(mic_positions[1]-true_position)) / 343.0
    
    print(f"Expected TDOAs from geometry:")
    print(f"  Mic1-Mic0: {expected_tdoa_01:.6f}s ({expected_tdoa_01 * sampling_rate:.1f} samples)")
    print(f"  Mic2-Mic0: {expected_tdoa_02:.6f}s ({expected_tdoa_02 * sampling_rate:.1f} samples)")
    print(f"  Mic2-Mic1: {expected_tdoa_12:.6f}s ({expected_tdoa_12 * sampling_rate:.1f} samples)")

    
    
    
    
    center = np.mean(mic_positions, axis=0)
    best_position = None
    best_error = float('inf')
    
    # Test starting positions at the expected distance
    test_distances = [approx_distance * 0.7, approx_distance, approx_distance * 1.3]
    angles = np.linspace(0, 2*np.pi, 16)  # Test many directions
    
    
    
    
    
    
    
    # Locate the sound source
    estimated_position, error, tdoas = find_sound_source(mic_positions, signals, sampling_rate, approx_distance=approx_distance)
    
    
    
    
    
    
    
    
    sys.exit(0)
    
    print("\n=== RESULTS ===")
    print(f"True position:      {true_position}")
    print(f"Estimated position: {estimated_position}")
    
    error_distance = np.linalg.norm(true_position - estimated_position)
    print(f"Localization error: {error_distance * 100:.1f} cm")
    print(f"Triangulation time: {triangulation_time * 1000:.1f} ms")
    print(f"Final error metric: {error:.6f}")
    
    # Detailed analysis
    print("\n=== DETAILED ANALYSIS ===")
    est_distances = np.linalg.norm(mic_positions - estimated_position, axis=1)
    
    print("True vs Estimated distances:")
    print("Mic | True Dist | Est Dist  | Error")
    print("----|-----------|-----------|------")
    for i in range(3):
        true_d = true_distances[i]
        est_d = est_distances[i]
        err = abs(true_d - est_d)
        print(f"{i}   | {true_d:.4f}   | {est_d:.4f}   | {err:.4f}")
    
    # Verify distance differences
    est_dist_diffs = [est_distances[1]-est_distances[0], 
                     est_distances[2]-est_distances[0],
                     est_distances[2]-est_distances[1]]
    
    meas_dist_diffs = [tdoas[0] * 343.0, tdoas[1] * 343.0, tdoas[2] * 343.0]
    
    print("\nDistance differences comparison:")
    print("Pair       | Measured | Estimated | Error")
    print("-----------|----------|-----------|------")
    pairs = [("Mic1-Mic0", 0), ("Mic2-Mic0", 1), ("Mic2-Mic1", 2)]
    for name, idx in pairs:
        meas = meas_dist_diffs[idx]
        est = est_dist_diffs[idx]
        err = abs(meas - est)
        print(f"{name:10} | {meas:8.4f} | {est:9.4f} | {err:.4f}")