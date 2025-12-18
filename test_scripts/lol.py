import numpy as np
import pandas as pd

TOTAL_TIME = 5.0  # total time for the entire run
TOTAL_DIST = 5.0  # total distance covered
N_POINTS = 20  # number of data points to record
STRAIGHT_DIST = 2.0  # the distance before any drift starts

# Time and x are fixed and correct (evenly spaced)
t = np.linspace(0.0, TOTAL_TIME, N_POINTS)
x = np.linspace(0.0, TOTAL_DIST, N_POINTS)

def exponential_drift(x, x0, max_drift, sharpness=3.0):
    """
    Smooth exponential drift starting at x0, saturating at max_drift.
    sharpness controls how steeply the drift increases.
    """
    if x <= x0:
        return 0.0
    s = (x - x0) / (TOTAL_DIST - x0)  # normalize to [0,1] after x0
    return max_drift * (np.exp(sharpness * s) - 1) / (np.exp(sharpness) - 1)

# Function to generate paths with different final deviations
def generate_observation_files(final_deviation=-1.0):
    # Generate 10 observation files with random but controlled drift
    for k in range(1, 11):
        y = np.zeros_like(x)

        # Drift parameters: exponential drift starting at 2m, saturates at final_deviation
        sharpness = 5.0  # sharpness of exponential curve
        drift_start = STRAIGHT_DIST  # drift starts at 2 meters

        # Apply exponential drift starting from 2m, saturates at final_deviation
        for i, xi in enumerate(x):
            if xi <= STRAIGHT_DIST:
                y[i] = 0.0  # no drift for the first 2 meters
            else:
                y[i] = exponential_drift(xi, drift_start, final_deviation, sharpness)

        # Create DataFrame and save to CSV
        df = pd.DataFrame({
            "t_sec": t,
            "x_m": x,
            "y_m": y
        })

        # Save the observation data to file
        fname = f"observations_{9}.txt"
        df.to_csv(fname, index=False)
        print(f"Generated {fname}: final y = {y[-1]:+.3f} m")

# Example usage: Generate paths with final deviations set to 1.0 meter
STRAIGHT_DIST = 0.1
generate_observation_files(final_deviation=0.3)

# Example usage: Generate paths with final deviations set to -1.0 meter (left)
# generate_observation_files(final_deviation=-1.0)
