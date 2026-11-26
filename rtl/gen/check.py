# SPDX-License-Identifier: Apache-2.0
"""Read-only comparison of generated RTL with a fresh generation."""

from pathlib import Path

from .emit import generate


def regen_difference(params, outdir):
    """Return the first difference from a fresh regen, or None if the trees match."""
    fresh = generate(params)
    directory = Path(outdir)
    have = {path.name for path in directory.iterdir()}
    if have != fresh.keys():
        return (f"{directory}: unexpected files {sorted(have - fresh.keys())}, "
                f"missing files {sorted(fresh.keys() - have)}")
    for name, body in fresh.items():
        path = directory / name
        if path.read_bytes() != body.encode("utf-8"):
            return f"{path} differs from a fresh regen"
    return None
