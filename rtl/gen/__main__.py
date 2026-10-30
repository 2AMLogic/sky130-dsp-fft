# SPDX-License-Identifier: Apache-2.0
"""CLI: python3 -m rtl.gen PARAMS_FILE OUT_DIR  (run from the repo root)."""
import sys

from .emit import write_rtl
from .params import ParamError, load_params


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: python3 -m rtl.gen PARAMS_FILE OUT_DIR\n")
        return 2
    try:
        params = load_params(argv[1])
    except ParamError as e:
        sys.stderr.write("error: %s\n" % e)
        return 1
    for name in write_rtl(params, argv[2]):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
