import pc_code.sound_localization.gccPhat as gcc
from pc_code.sound_localization.gccPhatByMatlab import gccphat_matlab
import pc_code.sound_localization.smallestIntegral as smallestIntegral
import numpy as np
import matplotlib.pyplot as plt
from consts import SHOULD_PLOT, SAMPLE_RATE, SHOULD_LOG
from logger import *
import logger
# Triangulate by searching a 3D grid for the best match to TDOA estimates

def microphone_placement():
    #mic_positions = np.array([
    #    [0.0, -0.1155, 0.0],    # Mic 1
    #    [-0.1, 0.057, 0.0],     # Mic 2
    #    [0.1, 0.057, 0.0]       # Mic 3
    #])
    
    #mic_positions = np.array([
    #    [0.0, 0.1155, 0.0],    # Mic 1
    #    [0.1, -0.057, 0.0],     # Mic 2
    #    [-0.1, -0.057, 0.0]       # Mic 3
    #])
    
    mic_positions = np.array([
        [-1.0, 0.0, 0.0],    # Mic 1
        [0.5, 0.866, 0.0],     # Mic 2
        [0.5, -0.866, 0.0]       # Mic 3
    ])
    
    mic_positions *= 0.3
    return mic_positions

def get_distance_between_mic_in_point_direction(point, mic_positions):
    dist1 = np.linalg.norm(point - mic_positions[0])
    dist2 = np.linalg.norm(point - mic_positions[1])
    dist3 = np.linalg.norm(point - mic_positions[2])

    # If a12 is positive mic2 is closer than mic1
    a12 = dist1 - dist2
    a13 = dist1 - dist3
    a23 = dist2 - dist3

    return a12, a13, a23

def calculate_score(a12, a13, a23, measured_d1, measured_d2, measured_d3):
    score = 0.0
    score += (a12 - measured_d1) ** 2
    score += (a13 - measured_d2) ** 2
    score += (a23 - measured_d3) ** 2
    return score

def create_grid(search_range=15.0, grid_size=0.2):
    # Axes
    x_vals = np.arange(-search_range, search_range + grid_size, grid_size)
    y_vals = np.arange(-search_range, search_range + grid_size, grid_size)
    z_vals = np.arange(0.0, 2.0 + grid_size, grid_size)

    # 3D grid
    X, Y, Z = np.meshgrid(x_vals, y_vals, z_vals, indexing='ij')

    # Cylinder mask in XY plane
    xy_r = np.sqrt(X**2 + Y**2)
    inside_cylinder = xy_r <= search_range

    mask = inside_cylinder

    # Stack into (N, 3)
    points = np.column_stack((X[mask], Y[mask], Z[mask]))

    # Return as list of vectors (if your downstream expects list)
    return [points[i] for i in range(points.shape[0])]

def find_all_possible_sound_positions(mic_positions, tdoa_estimates, speed_of_sound=343.0):
    measured_d1 = tdoa_estimates[0] * speed_of_sound  # mic1 - mic2
    measured_d2 = tdoa_estimates[1] * speed_of_sound  # mic1 - mic3
    measured_d3 = tdoa_estimates[2] * speed_of_sound  # mic2 - mic3

    grid_points = create_grid()
    grid_points_scores = []

    for point in grid_points:
        a12, a13, a23 = get_distance_between_mic_in_point_direction(point, mic_positions)
        score = calculate_score(a12, a13, a23, measured_d1, measured_d2, measured_d3)
        grid_points_scores.append((point, score))

    return grid_points_scores

def find_sound_origin(mic_positions, tdoa_estimates, speed_of_sound=343.0):
    grid_points_scores = find_all_possible_sound_positions(mic_positions, tdoa_estimates, speed_of_sound)

    sorted_grid_points_scores = sorted(grid_points_scores, key=lambda x: x[1])

    for point, score in sorted_grid_points_scores:
        x, y, z = point
        dist = np.sqrt(x**2 + y**2)
        if dist > 0.5:  # Ignore points too close to the microphones
            return point, score
    print("All points too close to microphones, returning best point anyway.")
    return sorted_grid_points_scores[0], sorted_grid_points_scores[0][1]


def plot_microphone_data(mic_1, mic_2, mic_3, name="microphone_signals"):
    # Plotting all three microphone signals for visualization in same plot for comparison with different colors
    plt.figure(figsize=(12, 6))
    plt.plot(mic_1, label='Microphone 1', alpha=0.7)
    plt.plot(mic_2, label='Microphone 2', alpha=0.7)
    plt.plot(mic_3, label='Microphone 3', alpha=0.7)
    plt.title('Microphone Signals')
    plt.legend(loc='upper right')
    plt.savefig(f"{name}.png")
    if SHOULD_PLOT:
        plt.show()


def triangulate_from_sound(mic1_data, mic2_data, mic3_data, called_by_logger = False):
    
    plot_microphone_data(mic1_data, mic2_data, mic3_data)
    
    cutoff = 2000
    fs = SAMPLE_RATE
    filtered_mic1_data = smallestIntegral.apply_lowpass_filter(mic1_data, cutoff, fs)
    filtered_mic2_data = smallestIntegral.apply_lowpass_filter(mic2_data, cutoff, fs)
    filtered_mic3_data = smallestIntegral.apply_lowpass_filter(mic3_data, cutoff, fs)
    plot_microphone_data(filtered_mic1_data, filtered_mic2_data, filtered_mic3_data, name="filtered_microphone_signals")
    
    
    """
    with open("mic0_data.txt", "w") as f:
        f.write("[")
        for item in mic0_data:
            f.write(f"{item}, ")
        f.write("]")
    with open("mic1_data.txt", "w") as f:
        f.write("[")
        for item in mic1_data:
            f.write(f"{item}, ")
        f.write("]")
    with open("mic2_data.txt", "w") as f:
        f.write("[")
        for item in mic2_data:
            f.write(f"{item}, ")
        f.write("]")
    """
    
    
    # Calculate TDOA estimates using GCC-PHAT


    
    tdoa_12 = gcc.PHAT_GCC_TDOA(mic1_data, mic2_data)  # If positive, mic2 is after mic1
    tdoa_13 = gcc.PHAT_GCC_TDOA(mic1_data, mic3_data)  # If positive, mic3 is after mic1
    tdoa_23 = gcc.PHAT_GCC_TDOA(mic2_data, mic3_data)  # If positive, mic3 is after mic2
    

    if SHOULD_LOG:
        weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        filter_states = ["WITHOUT_FILTER", "WITH_FILTER"]
        
        for filter_state in filter_states:
            # Test all weights
            for weight in weights:
                if filter_state == "WITHOUT_FILTER":
                    tdoa_12_log = gcc.PHAT_GCC_TDOA(mic1_data, mic2_data, telephone_band_filter=False, phat_weight_value=weight)
                    tdoa_13_log = gcc.PHAT_GCC_TDOA(mic1_data, mic3_data, telephone_band_filter=False, phat_weight_value=weight)
                    tdoa_23_log = gcc.PHAT_GCC_TDOA(mic2_data, mic3_data, telephone_band_filter=False, phat_weight_value=weight)
                else:
                    tdoa_12_log = gcc.PHAT_GCC_TDOA(mic1_data, mic2_data, telephone_band_filter=True, phat_weight_value=weight)
                    tdoa_13_log = gcc.PHAT_GCC_TDOA(mic1_data, mic3_data, telephone_band_filter=True, phat_weight_value=weight)
                    tdoa_23_log = gcc.PHAT_GCC_TDOA(mic2_data, mic3_data, telephone_band_filter=True, phat_weight_value=weight)
                # Log this combination
                weight_int = int(weight * 10)
                sample_size_name = str(Logger.current_samples_size)+ "K"


                const_name = f"TDOA_PHAT_WEIGHT_{weight_int:02d}_{sample_size_name}_SAMPLES_{filter_state}"
                try:
                    
                    TDOAs = [tdoa_12_log, tdoa_13_log, tdoa_23_log]
                    

                    column_key = getattr(logger, const_name)
                    Logger.set_value(column_key, f"{TDOAs[0]};{TDOAs[1]};{TDOAs[2]}")
                except AttributeError:
                    print(f"Warning: Logger constant {const_name} not found")

    tdoa_estimates = [tdoa_12, tdoa_13, tdoa_23]
    if not called_by_logger:
        print(f"TDOA Estimates (seconds): {tdoa_estimates}")
    mic_positions = microphone_placement()

    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

    return best_point, best_score

def calculate_localization_errors(true_point, estimated_point, mic_positions=None):
    """
    Calculate various error metrics between true and estimated sound source positions.
    
    Parameters:
    - true_point: numpy array [x, y, z] of true position
    - estimated_point: numpy array [x, y, z] of estimated position
    - mic_positions: optional, for calculating angular error relative to array center
    
    Returns:
    Dictionary with all error metrics
    """
    errors = {}
    
    # 1. Euclidean distance error (absolute position error)
    errors['position_error_m'] = np.linalg.norm(estimated_point - true_point)
    
    # 2. Individual coordinate errors
    errors['x_error_m'] = estimated_point[0] - true_point[0]
    errors['y_error_m'] = estimated_point[1] - true_point[1]
    errors['z_error_m'] = estimated_point[2] - true_point[2]
    
    # 3. Distance from origin (radial distance)
    true_distance = np.linalg.norm(true_point[:2])  # Ground distance (ignore z)
    est_distance = np.linalg.norm(estimated_point[:2])
    errors['radial_distance_error_m'] = est_distance - true_distance
    errors['true_radial_distance_m'] = true_distance
    errors['est_radial_distance_m'] = est_distance
    
    # 4. Relative error (percentage)
    if true_distance > 0:
        errors['radial_distance_error_percent'] = (errors['radial_distance_error_m'] / true_distance) * 100
    else:
        errors['radial_distance_error_percent'] = float('inf')
    
    # 5. Angular errors (azimuth and elevation)
    # Azimuth: angle in XY plane (0° = positive X axis, 90° = positive Y axis)
    true_azimuth = np.degrees(np.arctan2(true_point[1], true_point[0])) % 360
    est_azimuth = np.degrees(np.arctan2(estimated_point[1], estimated_point[0])) % 360
    
    # Azimuth difference (handles wrap-around at 360°)
    azimuth_diff = abs(est_azimuth - true_azimuth)
    errors['azimuth_error_deg'] = min(azimuth_diff, 360 - azimuth_diff)
    errors['true_azimuth_deg'] = true_azimuth
    errors['est_azimuth_deg'] = est_azimuth
    
    # Elevation: angle from horizontal (0° = horizontal, 90° = straight up)
    true_elevation = np.degrees(np.arctan2(true_point[2], np.linalg.norm(true_point[:2])))
    est_elevation = np.degrees(np.arctan2(estimated_point[2], np.linalg.norm(estimated_point[:2])))
    
    errors['elevation_error_deg'] = abs(est_elevation - true_elevation)
    errors['true_elevation_deg'] = true_elevation
    errors['est_elevation_deg'] = est_elevation
    
    # 6. Angular error in 3D space (angle between vectors from origin)
    if np.linalg.norm(true_point) > 0 and np.linalg.norm(estimated_point) > 0:
        cos_angle = np.dot(true_point, estimated_point) / (np.linalg.norm(true_point) * np.linalg.norm(estimated_point))
        # Clamp to avoid numerical issues
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        errors['angular_error_3d_deg'] = np.degrees(np.arccos(cos_angle))
    else:
        errors['angular_error_3d_deg'] = float('nan')
    
    # 7. Error relative to microphone array (if mic_positions provided)
    if mic_positions is not None:
        # Calculate array center
        array_center = np.mean(mic_positions, axis=0)
        
        # Vectors from array center to points
        true_vec = true_point - array_center
        est_vec = estimated_point - array_center
        
        # Distance from array center
        errors['true_distance_from_array_m'] = np.linalg.norm(true_vec)
        errors['est_distance_from_array_m'] = np.linalg.norm(est_vec)
        errors['distance_from_array_error_m'] = errors['est_distance_from_array_m'] - errors['true_distance_from_array_m']
        
        # Angular error relative to array
        if errors['true_distance_from_array_m'] > 0 and errors['est_distance_from_array_m'] > 0:
            cos_angle_array = np.dot(true_vec, est_vec) / (errors['true_distance_from_array_m'] * errors['est_distance_from_array_m'])
            cos_angle_array = np.clip(cos_angle_array, -1.0, 1.0)
            errors['angular_error_from_array_deg'] = np.degrees(np.arccos(cos_angle_array))
        else:
            errors['angular_error_from_array_deg'] = float('nan')
    
    return errors

def print_errors(true_point, estimated_point, mic_positions=None):
    """Pretty print all error metrics"""
    errors = calculate_localization_errors(true_point, estimated_point, mic_positions)
    
    print("=" * 60)
    print("LOCALIZATION ERROR ANALYSIS")
    print("=" * 60)
    
    print(f"\nTrue position:      [{true_point[0]:.3f}, {true_point[1]:.3f}, {true_point[2]:.3f}] m")
    print(f"Estimated position: [{estimated_point[0]:.3f}, {estimated_point[1]:.3f}, {estimated_point[2]:.3f}] m")
    
    print("\n" + "=" * 60)
    print("POSITION ERRORS")
    print("=" * 60)
    print(f"Total position error: {errors['position_error_m']:.3f} m")
    print(f"X error: {errors['x_error_m']:.3f} m")
    print(f"Y error: {errors['y_error_m']:.3f} m")
    print(f"Z error: {errors['z_error_m']:.3f} m")
    
    print("\n" + "=" * 60)
    print("DISTANCE FROM ORIGIN")
    print("=" * 60)
    print(f"True radial distance: {errors['true_radial_distance_m']:.3f} m")
    print(f"Estimated radial distance: {errors['est_radial_distance_m']:.3f} m")
    print(f"Radial distance error: {errors['radial_distance_error_m']:.3f} m")
    if 'radial_distance_error_percent' in errors and errors['radial_distance_error_percent'] != float('inf'):
        print(f"Relative error: {errors['radial_distance_error_percent']:.1f} %")
    
    print("\n" + "=" * 60)
    print("ANGULAR ERRORS (FROM ORIGIN)")
    print("=" * 60)
    print(f"True azimuth: {errors['true_azimuth_deg']:.1f}°")
    print(f"Estimated azimuth: {errors['est_azimuth_deg']:.1f}°")
    print(f"Azimuth error: {errors['azimuth_error_deg']:.1f}°")
    print(f"\nTrue elevation: {errors['true_elevation_deg']:.1f}°")
    print(f"Estimated elevation: {errors['est_elevation_deg']:.1f}°")
    print(f"Elevation error: {errors['elevation_error_deg']:.1f}°")
    print(f"\nTotal 3D angular error: {errors['angular_error_3d_deg']:.1f}°")
    
    if mic_positions is not None:
        print("\n" + "=" * 60)
        print("RELATIVE TO MICROPHONE ARRAY")
        print("=" * 60)
        print(f"True distance from array: {errors['true_distance_from_array_m']:.3f} m")
        print(f"Estimated distance from array: {errors['est_distance_from_array_m']:.3f} m")
        print(f"Distance error from array: {errors['distance_from_array_error_m']:.3f} m")
        print(f"Angular error from array: {errors['angular_error_from_array_deg']:.1f}°")
    
    print("\n" + "=" * 60)
        
def test123():
    mic_positions = microphone_placement()
    point = np.array([1.9738428371, 0.881273731, 1.776132172])  # Example true position
    tdoa_estimates = [np.linalg.norm(point - mic_positions[0])/343-np.linalg.norm(point - mic_positions[1])/343, np.linalg.norm(point - mic_positions[0])/343-np.linalg.norm(point - mic_positions[2])/343, np.linalg.norm(point - mic_positions[1])/343-np.linalg.norm(point - mic_positions[2])/343]
    
    print(f"True point: {point}")
    print(f"TDOA estimates (seconds): {tdoa_estimates}")
    
    # Check several candidate grid points
    candidates = [
        np.array([1.8, 0.8, 1.6]),  # What you found
        np.array([1.9, 0.8, 1.7]),  # Another candidate
        np.array([2.0, 0.9, 1.8]),  # Another candidate
        np.array([1.9, 0.9, 1.7]),  # Another candidate
        np.array([2.0, 0.8, 1.8]),  # Another candidate
    ]
    
    for candidate in candidates:
        a12, a13, a23 = get_distance_between_mic_in_point_direction(candidate, mic_positions)
        measured_d1 = tdoa_estimates[0] * 343.0
        measured_d2 = tdoa_estimates[1] * 343.0
        measured_d3 = tdoa_estimates[2] * 343.0
        
        score = calculate_score(a12, a13, a23, measured_d1, measured_d2, measured_d3)
        print(f"Candidate {candidate}: score = {score:.10f}")
    
    grid_points_scores = find_all_possible_sound_positions(mic_positions, tdoa_estimates)

    print("Calculating...")
    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

    print("best_point:", best_point, "best_score:", best_score)
    
    # find best point (keep for overlay)
    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

     # After getting best_point from your algorithm:
    print_errors(point, best_point, mic_positions)
    
    # Or compare specific points:
    point_est = np.array([1.8, 0.8, 1.6])
    print_errors(point, point_est, mic_positions)

    # prepare arrays of all grid points and scores
    coords = np.array([p for p, s in grid_points_scores])
    scores = np.array([s for p, s in grid_points_scores])

    # 3D scatter of all grid points colored by score (lower = better)
    fig = plt.figure(figsize=(12,6))
    ax = fig.add_subplot(1,2,1, projection='3d')
    sc = ax.scatter(coords[:,0], coords[:,1], coords[:,2],
                    c=scores, cmap='viridis_r', s=6, marker='o')  # viridis_r so low score = bright

    # Origin point and simple axes lines
    ax.scatter(0, 0, 0, c='black', s=40, marker='o')
    ax.plot([0, np.max(coords[:,0])], [0, 0], [0, 0], 'k-', alpha=0.3)
    ax.plot([0, 0], [0, np.max(coords[:,1])], [0, 0], 'k-', alpha=0.3)
    ax.plot([0, 0], [0, 0], [0, np.max(coords[:,2])], 'k-', alpha=0.3)

    # Plot BEST point FIRST (will be in background)
    ax.scatter(best_point[0], best_point[1], best_point[2], 
            c='white', edgecolors='k', marker='o', s=60, zorder=2)

    # Plot TRUE point SECOND (will be on top) with larger size and higher zorder
    ax.scatter(point[0], point[1], point[2], 
            c='red', marker='x', s=120, linewidths=2, zorder=3)

    # Inline labels near points (with small offset for readability)
    dx = 0.02 * (np.max(coords[:,0]) - np.min(coords[:,0]) + 1e-6)
    dy = 0.02 * (np.max(coords[:,1]) - np.min(coords[:,1]) + 1e-6)
    dz = 0.02 * (np.max(coords[:,2]) - np.min(coords[:,2]) + 1e-6)
    ax.text(point[0] + dx, point[1] + dy, point[2] + dz, "true", color='red', fontsize=10)
    ax.text(best_point[0] + dx, best_point[1] + dy, best_point[2] + dz, "best", color='black', fontsize=10)

    ax.set_xlabel('x (m)', fontsize=25, labelpad=20); ax.set_ylabel('y (m)', fontsize=25, labelpad=15); ax.set_zlabel('z (m)', fontsize=25, labelpad=15)
    ax.tick_params(axis='both', labelsize=25)
    ax.tick_params(axis='z', labelsize=25)
    # Optional: equalish aspect by box extents
    ax.set_box_aspect([np.ptp(coords[:,0]) + 1e-6, np.ptp(coords[:,1]) + 1e-6, np.ptp(coords[:,2]) + 1e-6])

    # CLEAN UP Z-AXIS TICKS - Only show 0 and 2
    # Get current z-ticks
    z_ticks = ax.get_zticks()
    # Keep only ticks near 0 and 2 (or create custom ticks)
    ax.set_zticks([0, 2])
    # Optionally format them nicely
    ax.set_zticklabels(['0', '2'], fontsize=25)

    cbar = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.12)
    cbar.set_label('score (m^2)', fontsize=25, labelpad=15)
    cbar.ax.tick_params(labelsize=20)

    ax2 = fig.add_subplot(1,2,2)
    sc2 = ax2.scatter(coords[:,0], coords[:,1], c=scores, cmap='viridis_r', s=6)

    # Origin marker and axes lines
    ax2.scatter(0, 0, c='black', s=140, marker='o')
    ax2.axhline(0, color='k', linewidth=0.5, alpha=0.5)
    ax2.axvline(0, color='k', linewidth=0.5, alpha=0.5)

    # Plot BEST point FIRST for 2D plot too
    ax2.scatter(best_point[0], best_point[1], 
                c='white', edgecolors='k', marker='o', s=160, zorder=2)

    # Plot TRUE point SECOND with higher zorder
    ax2.scatter(point[0], point[1], 
                c='red', marker='x', s=200, linewidths=2, zorder=3)

    # Inline labels near points (small offset)
    dx2 = 0.02 * (np.max(coords[:,0]) - np.min(coords[:,0]) + 1e-6)
    dy2 = 0.02 * (np.max(coords[:,1]) - np.min(coords[:,1]) + 1e-6)
    ax2.text(point[0] + dx2, point[1] + dy2, "true", color='red', fontsize=30, ha='left', va='bottom')
    ax2.text(best_point[0] + dx2, best_point[1] + dy2, "best", color='black', fontsize=30, ha='left', va='top')

    ax2.set_xlabel('x (m)', fontsize=25); ax2.set_ylabel('y (m)', fontsize=25)
    ax2.tick_params(axis='both', labelsize=25)
    cbar2 = fig.colorbar(sc2, ax=ax2, label='score (m^2)')
    cbar2.set_label('score (m^2)', fontsize=25, labelpad=15)
    cbar2.ax.tick_params(labelsize=20)

    plt.subplots_adjust(left=0.05, right=0.95, wspace=0.15)
    plt.show()