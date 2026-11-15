"""The one append-only evidence-record writer and its timestamp format.

Every recorded figure in `measurements/` is append-only evidence: a record is
added, never edited or dropped (`measurements/README.md`; `CLAUDE.md`'s
"recorded results are append-only evidence"). This module is the single
implementation of that write, so the invariant is stated once and tested once
(`test_records.py`) instead of resting on copy-pasted writers -- the one copy
that wrote a committed evidence file (`verification/test_fft256_smoke.py`) had
no test before this consolidation.

The serialisation is `json.dumps(..., indent=2) + "\\n"`, byte-for-byte the
format the committed evidence files already use: a re-indent here would
rewrite every record wholesale on the file's next append.
"""

import datetime
import json
from pathlib import Path


def utc_stamp() -> str:
    """The evidence files' `date_utc` format, defined once."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_record(path, rec: dict) -> dict:
    """Append `rec` to `path`'s `{"records": [...]}` file and return `rec`.

    Append-only: the earlier records are read back and rewritten untouched --
    never edited, reordered or dropped. A missing file starts as
    `{"records": []}`. The file is written `indent=2` with a trailing newline,
    the byte format the committed evidence files already use.
    """
    path = Path(path)
    data = json.loads(path.read_text()) if path.exists() else {"records": []}
    data["records"].append(rec)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return rec


def parse_record_argv(argv: list, usage: str):
    """The sweep CLIs' shared argv shape: `[<params-file>]` or
    `[<params-file>, --record, <json>]`.

    Returns `(positional, record_path)`, with `record_path` None unless
    `--record` was given. Raises `ValueError(usage)` on any other shape, so
    each CLI prints its own usage line and exits 2.
    """
    rec_path = None
    if len(argv) == 3 and argv[1] == "--record":
        argv, rec_path = argv[:1], argv[2]
    if len(argv) != 1:
        raise ValueError(usage)
    return argv, rec_path
