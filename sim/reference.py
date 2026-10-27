"""Double-precision reference FFT and SQNR.

Every SQNR figure this module produces is *simulated* (a model against double
precision), never *measured* on silicon.

The reference is an unscaled forward radix-2 FFT in natural order, i.e.
X[k] = sum_n x[n] exp(-2j*pi*n*k/N). A candidate must be returned at the same
scale (undo any block-floating or 1/N scaling before scoring).
"""

import numpy as np


def reference_fft(x: np.ndarray) -> np.ndarray:
    """Forward FFT of one frame in complex128, natural order; N a power of 2."""
    x = np.asarray(x, dtype=np.complex128)
    n = x.shape[-1]
    if n < 1 or n & (n - 1):
        raise ValueError(f"FFT length must be a power of two, got {n}")
    # Bit-reversal permutation, then in-place decimation-in-time stages.
    bits = n.bit_length() - 1
    idx = np.array([int(format(i, f"0{bits}b")[::-1], 2) if bits else 0 for i in range(n)])
    a = x[..., idx].copy()
    size = 2
    while size <= n:
        half = size // 2
        w = np.exp(-2j * np.pi * np.arange(half) / size)
        a = a.reshape(*a.shape[:-1], n // size, size)
        top = a[..., :half].copy()
        bot = a[..., half:] * w
        a[..., :half] = top + bot
        a[..., half:] = top - bot
        a = a.reshape(*a.shape[:-2], n)
        size *= 2
    return a


def sqnr_db(x_ref: np.ndarray, x_cand: np.ndarray) -> float:
    """10*log10(sum|X_ref|^2 / sum|X - X_ref|^2) for one frame.

    Returns +inf when the candidate equals the reference exactly. An all-zero
    reference has no defined SQNR and raises ValueError.
    """
    x_ref = np.asarray(x_ref, dtype=np.complex128)
    x_cand = np.asarray(x_cand, dtype=np.complex128)
    if x_ref.shape != x_cand.shape:
        raise ValueError(f"shape mismatch: {x_ref.shape} vs {x_cand.shape}")
    sig = float(np.sum(np.abs(x_ref) ** 2))
    if sig == 0.0:
        raise ValueError("SQNR undefined: reference frame is all zero")
    err = float(np.sum(np.abs(x_cand - x_ref) ** 2))
    if err == 0.0:
        return float("inf")
    return 10.0 * float(np.log10(sig / err))


def set_sqnr_db(frames: np.ndarray, candidate, fft=reference_fft) -> float:
    """Per-set figure: the minimum SQNR over frames.

    `candidate` maps a frame to its FFT output (the fixed-point model plugs in
    here); `fft` is the double-precision reference.
    """
    return min(sqnr_db(fft(f), candidate(f)) for f in frames)
