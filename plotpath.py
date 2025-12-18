import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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


def plot_compare_many(joint_log_path, obs_paths, connect_points=True):
    if not os.path.exists(joint_log_path):
        raise FileNotFoundError(f"Joint log not found: {joint_log_path}")

    df = pd.read_csv(joint_log_path, sep=",", engine="python", encoding="utf-8-sig")
    x_enc, y_enc = compute_xy(df)

    plt.figure(figsize=(8, 5))

    # ---- Observation paths FIRST (ORANGE, behind) ----
    first_obs = True
    for obs_path in obs_paths:
        if not os.path.exists(obs_path):
            print(f"Skipping missing observation file: {obs_path}")
            continue

        obs_x, obs_y = read_observations(obs_path)

        label = "Observations" if first_obs else None
        first_obs = False

        if connect_points:
            plt.plot(
                obs_x,
                obs_y,
                "-o",
                color="tab:orange",
                alpha=0.7,
                markersize=4,
                linewidth=1.5,
                zorder=1,
                label=label
            )
        else:
            plt.scatter(
                obs_x,
                obs_y,
                color="tab:orange",
                alpha=0.7,
                zorder=1,
                label=label
            )

    # ---- Encoder path LAST (BLUE, on top) ----
    plt.plot(
        x_enc,
        y_enc,
        color="tab:blue",
        linewidth=3.0,
        zorder=10,
        label="Encoder path"
    )

    plt.axis("equal")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Encoder path vs observations")
    #plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    joint_file = r"joint_states.txt"

    obs_files = [
        r"observations_1.txt",
        r"observations_2.txt",
        r"observations_3.txt",
        r"observations_4.txt",
        r"observations_5.txt",
        r"observations_6.txt",
        r"observations_7.txt",
        r"observations_8.txt",
        r"observations_9.txt",
        r"observations_10.txt",
    ]

    plot_compare_many(joint_file, obs_files, connect_points=True)
