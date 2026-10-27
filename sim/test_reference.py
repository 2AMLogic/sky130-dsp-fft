"""Tests for the SQNR vector sets and double-precision reference.

Run through `make -C verification sqnr-ref`. REF_MUTANT selects a deliberately
wrong reference so the negative control reuses the same test.
"""

import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference  # noqa: E402
import vectors  # noqa: E402


def _swap_iq(x):
    x = np.asarray(x, dtype=np.complex128)
    return reference.reference_fft(x.imag + 1j * x.real)


def _wrong_scale(x):
    return 2.0 * reference.reference_fft(x)


MUTANTS = {"": reference.reference_fft, "swap_iq": _swap_iq, "wrong_scale": _wrong_scale}
REF_FFT = MUTANTS[os.environ.get("REF_MUTANT", "")]


def test_same_seed_is_byte_identical():
    for name in vectors.VECTOR_SETS:
        a = vectors.generate_frames(name)
        b = vectors.generate_frames(name)
        assert a.tobytes() == b.tobytes(), f"{name}: vectors not deterministic"
    assert vectors.generate_frames("random50").tobytes() != vectors.generate_frames("random70").tobytes()


def test_vectors_inside_amplitude():
    for name, spec in vectors.VECTOR_SETS.items():
        for width in (8, 16):
            fs = vectors.full_scale(width)
            f = vectors.generate_frames(name, n=64, width=width, frames=20)
            assert f.shape == (20, 64)
            for part in (f.real, f.imag):
                assert np.all(part == np.rint(part)), f"{name}: non-integer samples"
                assert np.max(np.abs(part)) <= spec["fraction"] * fs + 0.5, f"{name}: amplitude exceeds set"
                assert np.max(np.abs(part)) <= fs, f"{name}: clipped past input width"


def test_default_frame_count_and_boundary_seeds():
    assert vectors.generate_frames("random50").shape == (100, 256)
    seeds = [s for spec in vectors.VECTOR_SETS.values() for s in spec.get("seeds", [])]
    assert min(seeds) == 1 and max(seeds) == 20 and len(set(seeds)) == 20


def test_reference_matches_numpy():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(256) + 1j * rng.standard_normal(256)
    assert np.allclose(REF_FFT(x), np.fft.fft(x), atol=1e-9), "Reference FFT differs from numpy.fft.fft"
    imp = np.zeros(8, dtype=complex)
    imp[1] = 1
    assert np.allclose(REF_FFT(imp), np.exp(-2j * np.pi * np.arange(8) / 8)), "Reference FFT differs from numpy.fft.fft"


def test_sqnr_self_and_injected_error():
    f = vectors.generate_frames("random50", frames=1)[0]
    ref = reference.reference_fft(f)
    assert reference.sqnr_db(ref, ref) == math.inf
    err = np.full_like(ref, 0.5 + 0.5j)  # |e|^2 = 0.5 per bin
    expect = 10 * math.log10(np.sum(np.abs(ref) ** 2) / (0.5 * len(ref)))
    got = reference.sqnr_db(ref, ref + err)
    assert abs(got - expect) < 1e-9, f"SQNR {got} != analytic {expect}"


def test_sqnr_of_quantised_candidate():
    # Rounding FFT output to integers: error power ~ 2 * (1/12) per bin.
    frames = vectors.generate_frames("random50", frames=10)

    def cand(f):
        y = reference.reference_fft(f)
        return np.rint(y.real) + 1j * np.rint(y.imag)

    got = reference.set_sqnr_db(frames, cand)
    sig = np.mean([np.mean(np.abs(reference.reference_fft(f)) ** 2) for f in frames])
    expect = 10 * math.log10(sig / (2 / 12))
    assert abs(got - expect) < 1.5, f"quantised SQNR {got:.2f} dB not near {expect:.2f} dB"


def test_all_zero_frame_is_explicit():
    z = np.zeros(16, dtype=complex)
    try:
        reference.sqnr_db(z, z)
    except ValueError:
        return
    raise AssertionError("all-zero reference must raise ValueError")


def test_reference_agrees_with_independent_scoring():
    # The negative control: scoring numpy's FFT against REF_FFT must be near-exact.
    frames = vectors.generate_frames("tone50", frames=5)
    got = reference.set_sqnr_db(frames, np.fft.fft, fft=REF_FFT)
    assert got > 200, f"Reference FFT differs from numpy.fft.fft (SQNR {got:.1f} dB)"


def main() -> int:
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
