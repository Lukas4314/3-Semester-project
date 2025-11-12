import numpy as np
import math

# GCC-PHAT implementation
def gcc_phat(sig, refsig, fs, max_tau=None, interp=8, eps=1e-8):
    """
    Compute TDOA between sig and refsig using GCC-PHAT.
    Returns tau (seconds, positive if sig lags refsig) and cross-correlation array.
    """
    n = sig.shape[0] + refsig.shape[0]
    nfft = 1
    while nfft < n:
        nfft <<= 1
    nfft *= interp

    SIG = np.fft.rfft(sig, n=nfft)
    REF = np.fft.rfft(refsig, n=nfft)
    R = SIG * np.conj(REF)

    # PHAT weighting
    denom = np.abs(R)
    denom[denom < eps] = eps
    R /= denom

    cc = np.fft.irfft(R, n=nfft)

    max_shift = int(nfft // 2)
    if max_tau is not None:
        max_shift = min(max_shift, int(np.ceil(max_tau * fs * interp)))

    # Recenter cross-correlation: keep [-max_shift, +max_shift]
    cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))

    shift = np.argmax(np.abs(cc)) - max_shift
    tau = shift / float(fs * interp)
    return tau, cc


def tdoa_to_angle(tau, d, c=343.0):
    # tau * c / d = cos(theta) for plane-wave far-field assumption
    val = (tau * c) / d
    val = np.clip(val, -1.0, 1.0)
    theta = math.degrees(math.acos(val))
    return theta


if __name__ == "__main__":
    # Simulation parameters
    fs = 16000
    duration = 0.5  # seconds
    t = np.arange(0, duration, 1 / fs)

    # Source: broadband pulse (windowed white noise) for sharp correlation
    np.random.seed(2)
    src = (np.random.randn(t.shape[0]) * np.hanning(t.shape[0]))

    # Microphone geometry
    d = 0.2  # distance between mics in meters (20 cm)
    c = 343.0  # speed of sound (m/s)

    # Choose a true angle (0..180 degrees). 0 deg -> cos=1 -> max positive tau
    true_angle_deg = 30.0
    true_angle_rad = math.radians(true_angle_deg)

    # For plane wave arriving with angle theta relative to baseline, TDOA = (d * cos theta) / c
    true_tau = (d * math.cos(true_angle_rad)) / c

    # Create mic signals: assume mic0 is reference, mic1 is delayed by +true_tau (sig1 lags ref)
    # Use fractional delay to simulate sub-sample delays
    def fractional_delay(x, tau_seconds, fs):
        n = len(x)
        N = 1
        while N < 2 * n:
            N <<= 1
        X = np.fft.rfft(x, n=N)
        freqs = np.fft.rfftfreq(N, 1.0/fs)
        # apply phase shift
        X_shifted = X * np.exp(-2j * np.pi * freqs * tau_seconds)
        y = np.fft.irfft(X_shifted, n=N)
        return y[:n]

    sig0 = src
    sig1 = fractional_delay(src, true_tau, fs)

    # Add some noise
    noise_power = 0.001
    sig0 += np.sqrt(noise_power) * np.random.randn(*sig0.shape)
    sig1 += np.sqrt(noise_power) * np.random.randn(*sig1.shape)

    # Run GCC-PHAT
    max_tau = d / c  # maximum possible delay magnitude
    est_tau, cc = gcc_phat(sig1, sig0, fs, max_tau=max_tau, interp=8)

    est_angle = tdoa_to_angle(est_tau, d, c=c)

    print(f"True tau: {true_tau:.6f} s ({true_tau * 1000:.3f} ms)")
    print(f"Estimated tau: {est_tau:.6f} s ({est_tau * 1000:.3f} ms)")
    print(f"True angle: {true_angle_deg:.2f} deg")
    print(f"Estimated angle: {est_angle:.2f} deg")

    # Try with a few noisy trials
    trials = 5
    errs = []
    for i in range(trials):
        sig0n = sig0 + np.sqrt(noise_power) * np.random.randn(*sig0.shape)
        sig1n = sig1 + np.sqrt(noise_power) * np.random.randn(*sig1.shape)
        tau_i, _ = gcc_phat(sig1n, sig0n, fs, max_tau=max_tau, interp=8)
        ang_i = tdoa_to_angle(tau_i, d, c=c)
        errs.append(abs(ang_i - true_angle_deg))
    print(f"Mean absolute angle error over {trials} trials: {np.mean(errs):.3f} deg")