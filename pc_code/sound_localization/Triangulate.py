import pc_code.sound_localization.gccPhat as gcc
from pc_code.sound_localization.gccPhatByMatlab import gccphat_matlab
import pc_code.sound_localization.smallestIntegral as smallestIntegral
import numpy as np
import matplotlib.pyplot as plt
from consts import SHOULD_PLOT, SAMPLE_RATE
# Triangulate by searching a 3D grid for the best match to TDOA estimates

def microphone_placement():
    #mic_positions = np.array([
    #    [0.0, -0.1155, 0.0],    # Mic 1
    #    [-0.1, 0.057, 0.0],     # Mic 2
    #    [0.1, 0.057, 0.0]       # Mic 3
    #])
    
    mic_positions = np.array([
        [0.0, 0.1155, 0.0],    # Mic 1
        [0.1, -0.057, 0.0],     # Mic 2
        [-0.1, -0.057, 0.0]       # Mic 3
    ])
    
    mic_positions *= 44.5/11.55  # Scale to actual size
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

def create_grid(search_range=10.0, grid_size=0.1):
    x_vals = np.arange(-search_range, search_range, grid_size)
    y_vals = np.arange(-search_range, search_range, grid_size)
    z_vals = np.arange(0, 2.0, grid_size)  # Assume ground level to 2m height
    grid_points = []
    for x in x_vals:
        for y in y_vals:
            for z in z_vals:
                grid_points.append(np.array([x, y, z]))
    return grid_points

def find_all_possible_sound_positions(mic_positions, tdoa_estimates, speed_of_sound=343.0):
    measured_d1 = tdoa_estimates[0]/ SAMPLE_RATE * speed_of_sound  # mic1 - mic2
    measured_d2 = tdoa_estimates[1]/ SAMPLE_RATE * speed_of_sound  # mic1 - mic3
    measured_d3 = tdoa_estimates[2]/ SAMPLE_RATE * speed_of_sound  # mic2 - mic3

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


def triangulate_from_sound(mic1_data, mic2_data, mic3_data):
    
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
    
    """
    allowed_max_tdoa = 160
    
    good_tdoa_01 = None
    good_tdoa_02 = None
    good_tdoa_12 = None
    
    tdoa_01, r_01, lags_01 = gccphat_matlab(mic0_data, mic1_data)
    tdoa_02, r_02, lags_02 = gccphat_matlab(mic0_data, mic2_data)
    tdoa_12, r_12, lags_12 = gccphat_matlab(mic1_data, mic2_data)
    # 01
    r_temp = r_01.copy()
    for _ in range(len(lags_01)):

        idx = np.argmax(np.abs(r_temp))
        tau = lags_01[idx]

        if abs(tau) < allowed_max_tdoa:
            good_tdoa_01 = tau
            break

        # zero out the peak that caused the invalid tau
        r_temp[idx] = 0


    # 02
    r_temp = r_02.copy()
    for _ in range(len(lags_02)):

        idx = np.argmax(np.abs(r_temp))
        tau = lags_02[idx]

        if abs(tau) < allowed_max_tdoa:
            good_tdoa_02 = tau
            break

        r_temp[idx] = 0


    # 12
    r_temp = r_12.copy()
    for _ in range(len(lags_12)):

        idx = np.argmax(np.abs(r_temp))
        tau = lags_12[idx]

        if abs(tau) < allowed_max_tdoa:
            good_tdoa_12 = tau
            break

        r_temp[idx] = 0

    
    
    print(f"Previous TDOA Estimates: {tdoa_01}, {tdoa_02}, {tdoa_12}")
    print(f"Good TDOA Estimates: {good_tdoa_01}, {good_tdoa_02}, {good_tdoa_12}")
   
    tdoa_01 = good_tdoa_01
    tdoa_02 = good_tdoa_02
    tdoa_12 = good_tdoa_12
    
    
    
    
    integral_tdoa_01 = smallestIntegral.get_TDOA(filtered_mic0_data, filtered_mic1_data, name="integral_tdoa_01")
    integral_tdoa_02 = smallestIntegral.get_TDOA(filtered_mic0_data, filtered_mic2_data, name="integral_tdoa_02")
    integral_tdoa_12 = smallestIntegral.get_TDOA(filtered_mic1_data, filtered_mic2_data, name="integral_tdoa_12")
    
    print(f"Integral TDOA Estimates: {integral_tdoa_01}, {integral_tdoa_02}, {integral_tdoa_12}")
    
    print(f"TDOA Estimates: {tdoa_01}, {tdoa_02}, {tdoa_12}")
    
    # Printing which micophones are closer based on TDOA signs
    if (tdoa_01 < 0):
        print("Mic 0 is before Mic 1")
    elif (tdoa_01 > 0):
        print("Mic 1 is before Mic 0")
    else:
        print("Mic 0 and Mic 1 are at the same time")
    
    if (tdoa_02 < 0):
        print("Mic 0 is before Mic 2")
    elif (tdoa_02 > 0):
        print("Mic 2 is before Mic 0")
    else:
        print("Mic 0 and Mic 2 are at the same time")

    if (tdoa_12 < 0):
        print("Mic 1 is before Mic 2")
    elif (tdoa_12 > 0):
        print("Mic 2 is before Mic 1")
    else:
        print("Mic 1 and Mic 2 are at the same time")
    
    """
    tdoa_estimates = [tdoa_12, tdoa_13, tdoa_23]
    mic_positions = microphone_placement()

    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

    return best_point, best_score
        
def test123():
    mic_positions = microphone_placement()
    point = np.array([-1.9738428371, -0.881273731, 1.776132172])  # Example true position
    tdoa_estimates = [np.linalg.norm(point - mic_positions[1])/343-np.linalg.norm(point - mic_positions[0])/343, np.linalg.norm(point - mic_positions[2])/343-np.linalg.norm(point - mic_positions[0])/343, np.linalg.norm(point - mic_positions[2])/343-np.linalg.norm(point - mic_positions[1])/343]
    grid_points_scores = find_all_possible_sound_positions(mic_positions, tdoa_estimates)

    print("Calculating...")
    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

    print("best_point:", best_point, "best_score:", best_score)
    
    # find best point (keep for overlay)
    best_point, best_score = find_sound_origin(mic_positions, tdoa_estimates)

    # prepare arrays of all grid points and scores
    coords = np.array([p for p, s in grid_points_scores])
    scores = np.array([s for p, s in grid_points_scores])

    # 3D scatter of all grid points colored by score (lower = better)
    fig = plt.figure(figsize=(12,6))
    ax = fig.add_subplot(1,2,1, projection='3d')
    sc = ax.scatter(coords[:,0], coords[:,1], coords[:,2],
                    c=scores, cmap='viridis_r', s=6, marker='o')  # viridis_r so low score = bright
    ax.scatter(point[0], point[1], point[2], c='red', marker='x', s=80, label='true')
    ax.scatter(best_point[0], best_point[1], best_point[2], c='white', edgecolors='k', marker='o', s=60, label='best')
    ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.set_zlabel('z (m)')
    ax.legend()
    cbar = fig.colorbar(sc, ax=ax, shrink=0.6)
    cbar.set_label('score (m^2)')

    # top-down (XY) view colored by score and show best vs true
    ax2 = fig.add_subplot(1,2,2)
    sc2 = ax2.scatter(coords[:,0], coords[:,1], c=scores, cmap='viridis_r', s=6)
    ax2.scatter(point[0], point[1], c='red', marker='x', s=60, label='true')
    ax2.scatter(best_point[0], best_point[1], c='white', edgecolors='k', marker='o', s=60, label='best')
    ax2.set_xlabel('x (m)'); ax2.set_ylabel('y (m)')
    ax2.legend()
    fig.colorbar(sc2, ax=ax2, label='score (m^2)')

    plt.tight_layout()
    plt.show()