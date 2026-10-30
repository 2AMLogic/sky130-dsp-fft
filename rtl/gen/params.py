# SPDX-License-Identifier: Apache-2.0
"""Parameter file parsing and strict validation.

Format: ``key=value`` lines, ``#`` comments, list values comma-separated.
Every key is required; there are no defaults, so no value is hard-coded here.
"""
import hashlib

SCHEMA_KEYS = (
    "size", "architecture", "direction", "input_width", "output_width",
    "stage_widths", "twiddle_width", "complex_mult", "rounding",
    "output_order", "pipeline", "stall",
)
_INT_KEYS = ("size", "input_width", "output_width", "twiddle_width",
             "pipeline", "stall")
_ENUMS = {
    "architecture": ("r22sdf",),
    "direction": ("forward",),
    "complex_mult": ("3mult", "4mult"),
    "rounding": ("convergent", "truncate"),
    "output_order": ("natural", "bitrev"),
}
MAX_SIZE = 1024


class ParamError(ValueError):
    """Invalid parameter file; the message names the offending key."""


def _int(key, text):
    try:
        return int(text, 10)
    except ValueError:
        raise ParamError("%s: expected an integer, got %r" % (key, text))


def parse_params(text):
    raw = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise ParamError("line %d: expected key=value, got %r" % (lineno, line))
        key, value = (s.strip() for s in line.split("=", 1))
        if key not in SCHEMA_KEYS:
            raise ParamError("%s: unknown key (line %d)" % (key, lineno))
        if key in raw:
            raise ParamError("%s: duplicate key (line %d)" % (key, lineno))
        raw[key] = value
    for key in SCHEMA_KEYS:
        if key not in raw:
            raise ParamError("%s: required key is missing" % key)

    p = {}
    for key in _INT_KEYS:
        p[key] = _int(key, raw[key])
    for key, allowed in _ENUMS.items():
        if raw[key] not in allowed:
            raise ParamError("%s: unsupported value %r (supported: %s)"
                             % (key, raw[key], ", ".join(allowed)))
        p[key] = raw[key]
    p["stage_widths"] = [_int("stage_widths", s.strip())
                         for s in raw["stage_widths"].split(",")]
    _validate(p)
    return p


def log4(n):
    k = 0
    while 4 ** k < n:
        k += 1
    return k


def _validate(p):
    n = p["size"]
    if n < 4 or n > MAX_SIZE or 4 ** log4(n) != n:
        raise ParamError(
            "size: %d is not supported; use a power of 4 in 4..%d (the "
            "radix-2 tail stage for 8 or 32 is not implemented)" % (n, MAX_SIZE))
    nstage = 2 * log4(n)
    sw = p["stage_widths"]
    if len(sw) != nstage:
        raise ParamError("stage_widths: size %d needs %d entries, got %d"
                         % (n, nstage, len(sw)))
    if not 4 <= p["input_width"] <= 32:
        raise ParamError("input_width: must be in 4..32")
    if not 4 <= p["output_width"] <= 32:
        raise ParamError("output_width: must be in 4..32")
    if not 6 <= p["twiddle_width"] <= 24:
        raise ParamError("twiddle_width: must be in 6..24")
    prev = p["input_width"]
    for w in sw:
        if w < prev or w > 40:
            raise ParamError("stage_widths: entries must be non-decreasing "
                             "from input_width (%d) and at most 40, got %d"
                             % (p["input_width"], w))
        prev = w
    if p["output_width"] > sw[-1]:
        raise ParamError("output_width: %d exceeds the last stage width %d"
                         % (p["output_width"], sw[-1]))
    for key in ("pipeline", "stall"):
        if p[key] not in (0, 1):
            raise ParamError("%s: must be 0 or 1" % key)


def load_params(path):
    with open(path, "rb") as f:
        data = f.read()
    p = parse_params(data.decode("utf-8"))
    p["_sha256"] = hashlib.sha256(data).hexdigest()
    return p
