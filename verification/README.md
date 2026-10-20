# verification

RTL lint, cocotb simulation and a Yosys smoke synthesis, proven on a
**placeholder** module (`rtl/placeholder/placeholder_add.sv`, a registered
adder with valid/ready handshakes). The placeholder is not part of the design;
generated RTL replaces it once the generator is chosen.

## Cold start

Prerequisites (versions pinned in [`toolchain.json`](toolchain.json)):
Icarus Verilog, Verilator, Yosys, Python, `make`, and the sky130 PDK at the
pinned `ciel` revision (`ciel enable --pdk sky130 f6eeac7d...`, installed under
`$PDK_ROOT/ciel/sky130/versions/<revision>/`; default `PDK_ROOT=~/.ciel`).

```sh
python3 -m venv .venv
.venv/bin/pip install -r verification/requirements.txt
cd verification
make all      # check-tools, lint, sim, negctl
make synth    # Yosys smoke -> ../measurements/synth-placeholder.json
```

| Target | What it does |
|---|---|
| `check-tools` | fails unless installed versions equal the pins in `toolchain.json` |
| `lint` | `verilator --lint-only -Wall` on `rtl/placeholder/`; any warning fails |
| `sim` | cocotb test: 2000 random vectors with random valid/ready stalls, checked against the Python model |
| `negctl` | runs the same test on `mutants/placeholder_add_mutant.sv` (carry dropped); succeeds only if the test **fails with** `DUT output differs from Python model` (`NEGCTL_EXPECT`), so a compile error or crash does not count |
| `synth` | Yosys maps to `sky130_fd_sc_hd` at the `tt_025C_1v80` liberty corner and writes the cell count with tool versions and PDK revision |

`synth` is manual (not in CI). The record in `measurements/` is evidence of the
flow, not a design result; do not overwrite it for a different module, add a
new record.

## CI

`.github/workflows/rtl-ci.yml` runs `lint`, `sim` and `negctl` on every push
and pull request. CI installs the runner's packaged Icarus and Verilator, which
may differ from the pinned versions, so it skips `check-tools`; the version pin
is enforced by `make all` and `make synth` locally.
