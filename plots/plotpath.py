import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

WHEEL_RADIUS = 0.033
WHEEL_SEPARATION = 0.160


def compute_xy(df):
    t = pd.to_numeric(df["t_sec"], errors="coerce").to_numpy()
    t = t - t[0]

    left = pd.to_numeric(df["left_pos_rad"], errors="coerce").to_numpy()
    right = pd.to_numeric(df["right_pos_rad"], errors="coerce").to_numpy()

    m = np.isfinite(t) & np.isfinite(left) & np.isfinite(right)
    t, left, right = t[m], left[m], right[m]
    if len(t) < 2:
        raise RuntimeError("Not enough valid joint log rows to compute a path.")

    dL = np.diff(left)
    dR = np.diff(right)

    ds = WHEEL_RADIUS * (dL + dR) / 2.0
    dth = WHEEL_RADIUS * (dR - dL) / WHEEL_SEPARATION

    x = np.zeros(len(ds) + 1)
    y = np.zeros(len(ds) + 1)
    th = np.zeros(len(ds) + 1)

    for k in range(len(ds)):
        th_mid = th[k] + 0.5 * dth[k]
        x[k + 1] = x[k] + ds[k] * np.cos(th_mid)
        y[k + 1] = y[k] + ds[k] * np.sin(th_mid)
        th[k + 1] = th[k] + dth[k]

    return x, y


def read_observations(obs_path):
    obs = pd.read_csv(obs_path, sep=",", engine="python", encoding="utf-8-sig")
    obs_x = pd.to_numeric(obs["x_m"], errors="coerce").to_numpy()
    obs_y = pd.to_numeric(obs["y_m"], errors="coerce").to_numpy()
    m = np.isfinite(obs_x) & np.isfinite(obs_y)
    return obs_x[m], obs_y[m]


def list_observation_files(obs_folder):

    patterns = [
        os.path.join(obs_folder, "*.txt"),
        os.path.join(obs_folder, "*.csv"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files.sort()
    return files


def plot_compare_many(joint_log_path, obs_folder, connect_points=True):
    if not os.path.exists(joint_log_path):
        raise FileNotFoundError(f"Joint log not found: {joint_log_path}")

    obs_paths = list_observation_files(obs_folder)
    if not obs_paths:
        raise FileNotFoundError(f"No observation files found in: {obs_folder}")

    df = pd.read_csv(joint_log_path, sep=",", engine="python", encoding="utf-8-sig")
    x_enc, y_enc = compute_xy(df)

    plt.figure(figsize=(8, 5))

 
    for obs_path in obs_paths:
        try:
            obs_x, obs_y = read_observations(obs_path)
        except Exception as e:
            print(f"Skipping unreadable observation file {obs_path}: {e}")
            continue

        if connect_points:
            plt.plot(
                obs_x, obs_y,
                "-o",
                color="tab:orange",
                alpha=0.7,
                markersize=4,
                linewidth=1.5,
                zorder=1
            )
        else:
            plt.scatter(
                obs_x, obs_y,
                color="tab:orange",
                alpha=0.7,
                zorder=1
            )

 
    plt.plot(
        x_enc, y_enc,
        color="tab:blue",
        linewidth=3.0,
        zorder=10
    )

    plt.axis("equal")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Encoder path vs observed path")
    plt.grid(True, alpha=0.3)

   
    handles = [
        Line2D([0], [0], color="tab:blue", lw=3, label="Blue = Plotted encoder data"),
        Line2D([0], [0], color="tab:orange", lw=1.5, marker="o", markersize=4,
               label="Orange = Plotted observed data"),
    ]
    plt.legend(
    handles=handles,
    loc="best",
    fontsize=13,
    handlelength=3,
    handletextpad=1.0,
    borderpad=0.8
)


    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    obs_folder = os.path.join(BASE_DIR, "..", "observations")
    joint_file = os.path.join(obs_folder, "joint_states.txt")

    plot_compare_many(joint_file, obs_folder, connect_points=True)

