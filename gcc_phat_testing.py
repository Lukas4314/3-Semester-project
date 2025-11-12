import numpy as np
import math
import time

def next_pow2(n):
    p = 1
    while p < n:
        p <<= 1
    return p

def gcc_phat(sig, refsig, fs, max_tau=None, interp=8, eps=1e-8):
    """GCC-PHAT; returns (tau_seconds, peak_abs, second_peak_abs)."""
    sig = np.asarray(sig, dtype=float)
    refsig = np.asarray(refsig, dtype=float)
    ncorr = sig.size + refsig.size - 1
    base_nfft = next_pow2(max(1, ncorr))
    nfft = base_nfft * interp

    SIG = np.fft.fft(sig, n=nfft)
    REF = np.fft.fft(refsig, n=nfft)
    R = SIG * np.conj(REF)

    denom = np.abs(R)
    denom[denom < eps] = eps
    R /= denom

    cc = np.fft.ifft(R)
    cc = np.fft.fftshift(cc)
    cc = np.real(cc)

    center = nfft // 2
    if max_tau is None:
        max_shift = center
    else:
        max_shift = int(min(center, np.ceil(max_tau * fs * interp)))

    search = cc[center - max_shift : center + max_shift + 1]
    if search.size == 0:
        return 0.0, 0.0, 0.0

    abs_search = np.abs(search)
    peak = int(np.argmax(abs_search))
    peak_val = abs_search[peak]
    # second highest (for confidence)
    if abs_search.size > 1:
        sec_val = np.max(np.delete(abs_search, peak))
    else:
        sec_val = 0.0

    # parabolic interpolation on magnitude for sub-sample correction
    dp = 0.0
    L = len(abs_search)
    if 1 <= peak <= (L - 2):
        y0 = abs_search[peak - 1]; y1 = abs_search[peak]; y2 = abs_search[peak + 1]
        den = (y0 - 2.0 * y1 + y2)
        if den != 0.0:
            dp = 0.5 * (y0 - y2) / den

    shift_idx = (peak - max_shift) + dp
    tau = float(shift_idx) / (fs * interp)
    return tau, float(peak_val), float(sec_val)

def time_xcorr_tau(sig, refsig, fs, max_tau=None, interp=8):
    """Time-domain cross-correlation (via FFT) with parabolic interp. Returns tau_seconds."""
    sig = np.asarray(sig, dtype=float)
    refsig = np.asarray(refsig, dtype=float)
    ncorr = sig.size + refsig.size - 1
    base_nfft = next_pow2(max(1, ncorr))
    nfft = base_nfft * interp

    SIG = np.fft.fft(sig, n=nfft)
    REF = np.fft.fft(refsig, n=nfft)
    R = SIG * np.conj(REF)  # no PHAT
    cc = np.fft.ifft(R)
    cc = np.fft.fftshift(cc)
    cc = np.real(cc)

    center = nfft // 2
    if max_tau is None:
        max_shift = center
    else:
        max_shift = int(min(center, np.ceil(max_tau * fs * interp)))

    search = cc[center - max_shift : center + max_shift + 1]
    if search.size == 0:
        return 0.0

    peak = int(np.argmax(search))
    # parabolic interpolation on real values
    dp = 0.0
    L = len(search)
    if 1 <= peak <= (L - 2):
        y0 = search[peak - 1]; y1 = search[peak]; y2 = search[peak + 1]
        den = (y0 - 2.0 * y1 + y2)
        if den != 0.0:
            dp = 0.5 * (y0 - y2) / den

    shift_idx = (peak - max_shift) + dp
    tau = float(shift_idx) / (fs * interp)
    return tau

def fractional_delay(x, tau_seconds, fs):
    """Apply fractional delay via frequency-domain phase shift."""
    n = len(x)
    N = 1
    while N < 2 * n:
        N <<= 1
    X = np.fft.fft(x, n=N)
    freqs = np.fft.fftfreq(N, 1.0 / fs)
    X_shifted = X * np.exp(-2j * np.pi * freqs * tau_seconds)
    y = np.fft.ifft(X_shifted, n=N)
    return np.real(y[:n])

def estimate_angle_from_taus(mic_x, taus, c):
    """Estimate angle (deg) from per-mic TDOAs relative to center reference.
       Returns list of per-pair angle estimates and their mean."""
    ref_idx = np.argmin(np.abs(mic_x))  # choose mic nearest x==0 as reference
    angles = []
    for i, tau in enumerate(taus):
        if i == ref_idx:
            continue
        dx = mic_x[i] - mic_x[ref_idx]
        if abs(dx) < 1e-12:
            continue
        val = (tau * c) / dx
        val = max(-1.0, min(1.0, val))
        mag = math.degrees(math.acos(abs(val)))
        sign = 1.0 if (tau * dx) >= 0 else -1.0
        angles.append(sign * mag)
    return angles, (float(np.mean(angles)) if angles else None)

if __name__ == "__main__":
    # simulation params
    fs = 16000
    duration = 0.3
    t = np.arange(0, duration, 1.0 / fs)
    N = len(t)

    # 3-mic linear array (meters)
    d = 0.05
    mic_x = np.array([-d, 0.0, d])

    c = 343.0
    true_angle_deg = 30.0
    theta = math.radians(true_angle_deg)
    # far-field TDOAs relative to array origin (we will compare relative to ref)
    taus_true = (mic_x - 0.0) * math.cos(theta) / c

    # source: short pulse (good cross-correlation peak)
    src = np.zeros(N)
    src_start = 100
    pulse_len = 120
    src[src_start:src_start + pulse_len] = np.hanning(pulse_len)

    # create delayed mic signals
    signals = [fractional_delay(src, tau, fs) for tau in taus_true]

    # add noise
    noise_power = 1e-4
    rng = np.random.RandomState(1)
    signals_noisy = [s + np.sqrt(noise_power) * rng.randn(*s.shape) for s in signals]

    # reference index = center mic
    ref_idx = 1
    ref = signals_noisy[ref_idx]

    # estimate per-mic TDOAs relative to ref using PHAT and time-domain fallback
    max_tau = np.max(np.abs(taus_true)) * 2.0
    est_taus_phat = []
    phat_peaks = []
    for i, s in enumerate(signals_noisy):
        if i == ref_idx:
            est_taus_phat.append(0.0); phat_peaks.append((0.0,0.0)); continue
        tau_phat, peak_val, sec_val = gcc_phat(s, ref, fs, max_tau=max_tau, interp=8)
        est_taus_phat.append(tau_phat); phat_peaks.append((peak_val, sec_val))

    # time-domain (non-PHAT) estimates
    est_taus_time = []
    for i, s in enumerate(signals_noisy):
        if i == ref_idx:
            est_taus_time.append(0.0); continue
        tau_time = time_xcorr_tau(s, ref, fs, max_tau=max_tau, interp=8)
        est_taus_time.append(tau_time)

    # decide per-pair which to trust: if PHAT peak >> second peak use PHAT, else fallback to time-domain
    chosen_taus = []
    for i in range(len(est_taus_phat)):
        ph_peak, ph_sec = phat_peaks[i]
        if ph_peak > 5.0 * (ph_sec + 1e-12):  # confidence threshold
            chosen_taus.append(est_taus_phat[i])
        else:
            chosen_taus.append(est_taus_time[i])

    # compute angles
    angles_phat, mean_phat = estimate_angle_from_taus(mic_x, est_taus_phat, c)
    angles_time, mean_time = estimate_angle_from_taus(mic_x, est_taus_time, c)
    angles_chosen, mean_chosen = estimate_angle_from_taus(mic_x, chosen_taus, c)

    # print results
    print(f"True angle: {true_angle_deg:.2f} deg")
    print("True taus (s):", ["{:.6e}".format(x) for x in taus_true])
    print("PHAT taus (s):", ["{:.6e}".format(x) for x in est_taus_phat])
    print("PHAT peak/sec:", ["{:.3f}/{:.3f}".format(a,b) for a,b in phat_peaks])
    print("Time-domain taus (s):", ["{:.6e}".format(x) for x in est_taus_time])
    print("Per-pair angle PHAT (deg):", ["{:.2f}".format(a) for a in angles_phat])
    print("Per-pair angle Time (deg):", ["{:.2f}".format(a) for a in angles_time])
    print("Per-pair angle Chosen (deg):", ["{:.2f}".format(a) for a in angles_chosen])
    print("Mean angle PHAT:", f"{mean_phat:.2f}" if mean_phat is not None else "None")
    print("Mean angle Time:", f"{mean_time:.2f}" if mean_time is not None else "None")
    print("Mean angle Chosen:", f"{mean_chosen:.2f}" if mean_chosen is not None else "None")