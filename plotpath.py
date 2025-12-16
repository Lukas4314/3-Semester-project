import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

WHEEL_RADIUS = 0.033
WHEEL_SEPARATION = 0.160


def compute_xy(df):
    # robot time -> relative seconds
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

    # time length must match x/y length
    t2 = t[: len(x)]
    return t2, x, y


def read_observations(obs_path):
    # observations_20.txt format:
    # t_sec,x_m,y_m
    obs = pd.read_csv(obs_path, sep=",", engine="python", encoding="utf-8-sig", skip_blank_lines=True)

    obs_t = pd.to_numeric(obs["t_sec"], errors="coerce").to_numpy()
    obs_x = pd.to_numeric(obs["x_m"], errors="coerce").to_numpy()
    obs_y = pd.to_numeric(obs["y_m"], errors="coerce").to_numpy()

    m = np.isfinite(obs_t) & np.isfinite(obs_x) & np.isfinite(obs_y)
    obs_t, obs_x, obs_y = obs_t[m], obs_x[m], obs_y[m]

    return obs_t, obs_x, obs_y


def interp_xy(t_src, x_src, y_src, t_query):
    # interpolate encoder path (x(t), y(t)) at observation times
    t_query = np.asarray(t_query, dtype=float)

    # clamp to available time range
    t0, t1 = float(t_src[0]), float(t_src[-1])
    tq = np.clip(t_query, t0, t1)

    xq = np.interp(tq, t_src, x_src)
    yq = np.interp(tq, t_src, y_src)
    return xq, yq


def plot_compare(joint_log_path, obs_path, show_full_encoder=True, connect_points=True):
    if not os.path.exists(joint_log_path):
        raise FileNotFoundError(f"Joint log not found: {joint_log_path}")
    if os.path.getsize(joint_log_path) == 0:
        raise RuntimeError(f"Joint log is empty: {joint_log_path}")
    if not os.path.exists(obs_path):
        raise FileNotFoundError(f"Observation file not found: {obs_path}")

    df = pd.read_csv(joint_log_path, sep=",", engine="python", encoding="utf-8-sig", skip_blank_lines=True)
    t_enc, x_enc, y_enc = compute_xy(df)

    obs_t, obs_x, obs_y = read_observations(obs_path)

    if len(obs_t) != 20:
        print(f"Warning: observation file has {len(obs_t)} valid points (you wanted 20).")

    # encoder path sampled at the same 20 observation times
    enc_x_20, enc_y_20 = interp_xy(t_enc, x_enc, y_enc, obs_t)

    plt.figure()

    if show_full_encoder:
        plt.plot(x_enc, y_enc, label="encoders (full path)")

    # observed 20 points
    if connect_points:
        plt.plot(obs_x, obs_y, "-o", label="observed (20 points)")
    else:
        plt.scatter(obs_x, obs_y, label="observed (20 points)")


    plt.axis("equal")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.legend()
    plt.title("Observed (20) vs Encoder path sampled to same 20 times")
    plt.show()


if __name__ == "__main__":
    joint_file = r"joint_states.txt"   # <-- change
    obs_file = r"observations.txt"             # <-- change

    plot_compare(joint_file, obs_file, show_full_encoder=True, connect_points=True)
