"""Seeded, deterministic SQNR vector sets (draft spec, PR #6 "SQNR vector set").

The set definitions live only in VECTOR_SETS; a spec change edits that table.
Samples are signed integers (I and Q each in [-full_scale, full_scale]) so the
same frames feed the double-precision reference and a later fixed-point model.
"""

import math

import numpy as np

N_DEFAULT = 256
WIDTH_DEFAULT = 16
FRAMES_PER_SET = 100

# kind "random": uniform I/Q, amplitude `fraction` of full scale; frames are
# split evenly over `seeds`, one generator per seed.
# kind "tone": complex tone at bin N/8 + `bin_offset` (non-coherent), random
# phase per frame from a generator seeded with `seed`.
VECTOR_SETS = {
    "random50": {"kind": "random", "fraction": 0.5, "seeds": range(1, 11)},
    "random70": {"kind": "random", "fraction": 0.7, "seeds": range(11, 21)},
    "tone50": {"kind": "tone", "fraction": 0.5, "bin_offset": 0.3, "seed": 1},
    "tone90": {"kind": "tone", "fraction": 0.9, "bin_offset": 0.3, "seed": 1},
}


def full_scale(width: int) -> int:
    """Largest positive code of a signed `width`-bit component."""
    return (1 << (width - 1)) - 1


def _quantise(x: np.ndarray, width: int) -> np.ndarray:
    fs = full_scale(width)
    return np.clip(np.rint(x), -fs, fs)


def generate_frames(
    name: str,
    n: int = N_DEFAULT,
    width: int = WIDTH_DEFAULT,
    frames: int = FRAMES_PER_SET,
) -> np.ndarray:
    """Return a (frames, n) complex128 array of integer-valued I/Q samples."""
    spec = VECTOR_SETS[name]
    amp = spec["fraction"] * full_scale(width)
    out = np.empty((frames, n), dtype=np.complex128)
    if spec["kind"] == "random":
        seeds = list(spec["seeds"])
        rngs = {s: np.random.default_rng(s) for s in seeds}
        for i in range(frames):
            rng = rngs[seeds[i % len(seeds)]]
            re = rng.uniform(-amp, amp, n)
            im = rng.uniform(-amp, amp, n)
            out[i] = _quantise(re, width) + 1j * _quantise(im, width)
    elif spec["kind"] == "tone":
        rng = np.random.default_rng(spec["seed"])
        k = n / 8 + spec["bin_offset"]
        t = np.arange(n)
        for i in range(frames):
            phase = rng.uniform(0, 2 * math.pi)
            z = amp * np.exp(1j * (2 * math.pi * k * t / n + phase))
            out[i] = _quantise(z.real, width) + 1j * _quantise(z.imag, width)
    else:
        raise ValueError(f"unknown vector-set kind {spec['kind']!r}")
    return out
