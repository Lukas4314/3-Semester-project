import numpy as np

def gccphat_matlab(x, xref):
    """
    Simplified GCC-PHAT delay estimator.
    
    Parameters
    ----------
    x : ndarray (N, M)
        Input signal(s).
    xref : ndarray (N, M) or (N,)
        Reference signal(s). If 1-D, broadcast to all channels.

    Returns
    -------
    tau : ndarray (M,)
        Estimated delays for each channel.
    r12 : ndarray (2N-1, M)
        Cross-correlation values.
    lags : ndarray (2N-1,)
        Corresponding lags (fs = 1).
    """

    x = np.asarray(x)
    xref = np.asarray(xref)

    # Ensure 2D
    if x.ndim == 1:
        x = x[:, None]
    if xref.ndim == 1:
        xref = xref[:, None]

    N, M = x.shape

    # Broadcast single-column reference
    if xref.shape[1] == 1 and M > 1:
        xref = np.repeat(xref, M, axis=1)

    # Must match
    assert xref.shape == x.shape, "xref must match x in shape or be a single column."

    # GCC-PHAT parameters
    Ncorr = 2*N - 1
    NFFT = int(2 ** np.ceil(np.log2(Ncorr)))

    # Lags (fs = 1)
    lags = np.arange(-(Ncorr - 1)//2, (Ncorr - 1)//2 + 1)

    # Compute GCC-PHAT
    r12 = _priv_gccphat(x, xref, NFFT, Ncorr)

    # Pick delay from peak
    idx = np.argmax(np.abs(r12), axis=0)
    tau = lags[idx]

    return tau[0], r12, lags


def _priv_gccphat(x, xref, NFFT, Ncorr):
    """Internal GCC-PHAT implementation."""
    X = np.fft.fft(x, n=NFFT, axis=0)
    Xref = np.fft.fft(xref, n=NFFT, axis=0)

    R = X * np.conj(Xref)

    R_phat = np.exp(1j * np.angle(R))

    r_temp = np.fft.ifft(R_phat, axis=0)
    r_temp = np.fft.fftshift(r_temp, axes=0)

    mid = NFFT // 2
    start = mid - (Ncorr - 1)//2
    end = mid + (Ncorr - 1)//2 + 1

    return r_temp[start:end, :]


if __name__ == "__main__":
    # Create simple delayed signals
    N = 1024
    x = np.random.randn(N)
    delay = 5
    xref = np.roll(x, delay)

    tau, r, lags = gccphat_matlab(x, xref)

    print("Estimated delay:", tau)

