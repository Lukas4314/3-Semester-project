import gcc_phat_testing as gcc

import numpy as np
import time

def calculate_error(pos, mic_positions, d1, d2):
    """
    Calculate how well a position explains the TDOA measurements
    Lower error = better match to measurements
    """
    dist0 = np.linalg.norm(pos - mic_positions[0])
    dist1 = np.linalg.norm(pos - mic_positions[1])
    dist2 = np.linalg.norm(pos - mic_positions[2])
    
    # Error between predicted and measured distance differences
    error1 = (dist1 - dist0 - d1)**2  # mic1 - mic0 difference
    error2 = (dist2 - dist0 - d2)**2  # mic2 - mic0 difference
    
    return error1 + error2

def triangulate_coordinate_descent(mic_positions, tdoa_estimates, speed_of_sound=343.0, steps=1000):
    d1 = tdoa_estimates[0] * speed_of_sound
    d2 = tdoa_estimates[1] * speed_of_sound
    
    print(f"Distance differences: d1={d1:.3f}m, d2={d2:.3f}m")
    
    pos = np.mean(mic_positions, axis=0)
    initial_error = calculate_error(pos, mic_positions, d1, d2)
    print(f"Initial position: {pos}, initial error: {initial_error:.6f}")
    
    initial_step = 0.1
    final_step = 0.01
    
    for step in range(steps):
        current_step = initial_step * (final_step / initial_step) ** (step / steps)
        current_error = calculate_error(pos, mic_positions, d1, d2)
        
        # Test 8 directions: 4 cardinal + 4 diagonal
        directions = [
            np.array([current_step, 0]),        # right
            np.array([-current_step, 0]),       # left  
            np.array([0, current_step]),        # up
            np.array([0, -current_step]),       # down
            np.array([current_step, current_step]),    # up-right
            np.array([current_step, -current_step]),   # down-right
            np.array([-current_step, current_step]),   # up-left
            np.array([-current_step, -current_step])   # down-left
        ]
        
        # Test all directions and pick the best
        best_new_pos = pos
        best_new_error = current_error
        
        for direction in directions:
            new_pos = pos + direction
            new_error = calculate_error(new_pos, mic_positions, d1, d2)
            
            if new_error < best_new_error:
                best_new_error = new_error
                best_new_pos = new_pos
        
        # Only move if we found a better position
        if best_new_error < current_error:
            pos = best_new_pos
        
        if step % 10 == 0:
            print(f"Step {step}: position={pos}, error={best_new_error:.6f}, step_size={current_step:.4f}")
    
    final_error = calculate_error(pos, mic_positions, d1, d2)
    print(f"Final position: {pos}, final error: {final_error:.6f}")
    return pos

def pairwise_to_reference_tdoa(tdoa_12, tdoa_13, tdoa_23):
    """
    Convert pairwise TDOAs to TDOAs relative to mic0
    Returns: [t1-t0, t2-t0] in seconds
    """
    return np.array([-tdoa_12, -tdoa_13])  # Using mic1 as reference

if __name__ == "__main__":
    # Create random source signal instead of sinusoidal
    signal_length = 5 * 44100
    source_signal = np.random.randn(signal_length)  # Gaussian random noise
    
    # Define 3-microphone triangle (in meters)
    mic_positions = np.array([
        [0.0, 0.0],    # Mic 0 - bottom left
        [0.1, 0.0],    # Mic 1 - bottom right  
        [0.05, 0.0866]    # Mic 2 - top (equilateral triangle with 0.1m sides)
    ])
    
    # True sound source position for testing (in meters)
    true_position = np.array([1.2, 0.8])
    
    # Calculate true time delays based on geometry
    sampling_rate = 44100
    speed_of_sound = 343.0
    distances = np.linalg.norm(mic_positions - true_position, axis=1)
    true_delays_samples = ((distances - distances[0]) / speed_of_sound) * sampling_rate
    
    print("=== SETUP ===")
    print(f"Microphone positions: {mic_positions}")
    print(f"True sound source: {true_position}")
    print(f"True distances to mics: {distances}")
    print(f"True delays in samples: {true_delays_samples}")
    
    # Create delayed signals (mic0 is reference)
    test_array1 = source_signal.copy()  # mic0 - no delay
    test_array2 = np.roll(source_signal, int(true_delays_samples[1]))  # mic1
    test_array3 = np.roll(source_signal, int(true_delays_samples[2]))  # mic2
    
    print("\n=== GCC-PHAT PROCESSING ===")
    start_time = time.time()

    tdoa_12 = gcc.PHAT_GCC_TDOA(test_array1, test_array2) / sampling_rate  # in seconds
    tdoa_13 = gcc.PHAT_GCC_TDOA(test_array1, test_array3) / sampling_rate  # in seconds
    tdoa_23 = gcc.PHAT_GCC_TDOA(test_array2, test_array3) / sampling_rate  # in seconds
    
    gcc_time = time.time() - start_time
    
    print(f"TDOA 1-2: {tdoa_12:.6f}s ({tdoa_12 * 1000:.2f}ms)")
    print(f"TDOA 1-3: {tdoa_13:.6f}s ({tdoa_13 * 1000:.2f}ms)")
    print(f"TDOA 2-3: {tdoa_23:.6f}s ({tdoa_23 * 1000:.2f}ms)")
    print(f"GCC-PHAT time: {gcc_time:.3f}s")
    
    print("\n=== TRIANGULATION ===")
    # Convert to reference frame
    tdoa_reference = pairwise_to_reference_tdoa(tdoa_12, tdoa_13, tdoa_23)
    print(f"TDOAs relative to mic0: {tdoa_reference} seconds")
    
    # Triangulate using coordinate descent!
    triangulate_time_start = time.time()
    estimated_position = triangulate_coordinate_descent(mic_positions, tdoa_reference)
    triangulate_time_end = time.time() - triangulate_time_start
    
    print("\n=== RESULTS ===")
    print(f"True position:      {true_position}")
    print(f"Estimated position: {estimated_position}")
    error_distance = np.linalg.norm(true_position - estimated_position)
    print(f"Error: {error_distance * 100:.1f} cm")
    print(f"Triangulation time: {triangulate_time_end * 1000:.1f} ms")
    
    # Calculate what ideal triangulation would give
    ideal_tdoas = (distances[1:] - distances[0]) / speed_of_sound
    ideal_position = triangulate_coordinate_descent(mic_positions, ideal_tdoas)
    ideal_error = np.linalg.norm(true_position - ideal_position)
    print(f"\nWith perfect TDOAs: {ideal_position} (error: {ideal_error * 100:.1f} cm)")