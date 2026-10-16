# Fuel as the operation count for guest work

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: one hour.
- **Feeds:** `../specifications/002-the-progress-harness.md` (the fuel
  metric, the fuel deadline, the seed rule).
- **Machine (benchmark fact only):** Apple arm64, macOS 26.5,
  wasmtime-py 49.0.0, Python 3.14.2 host.

## The question

The constitution says tests count operations and never time (§4.9),
and that a build slower than the last without a stated reason is a
regression (§3). So the harness needs a count that stands in for
"how much work did the guest do". Is wasmtime's **fuel** that count?

**Fuel** is wasmtime's meter: the store starts with a budget, every
executed wasm operator spends from it, and the guest traps when it is
empty. Fuel spent is a count of executed instructions, not of time.

## What was run (EXECUTED)

Brett Cannon's `python-3.14.7-wasi_sdk-24.zip` (pinned in
`downloads/SHA256SUMS`, `2e064d3f…`, hash verified with
`shasum -a 256 -c`), unpacked under `build/brett-3.14.7/`. One guest
run per host process, so nothing is shared between runs. The probe:

```python
"""Fuel probe: one guest run per process. argv: python.wasm lib-dir fuel-limit seed-or-'-' guest-args..."""
import shutil, sys, tempfile
from pathlib import Path
import wasmtime as w
wasm, lib, limit, seed, *gargs = sys.argv[1:]
cfg = w.Config(); cfg.consume_fuel = True
eng = w.Engine(cfg); mod = w.Module.from_file(eng, wasm)
with tempfile.TemporaryDirectory() as root:
    shutil.copytree(lib, Path(root, "usr/local/lib/python3.14"))
    st = w.Store(eng); st.set_fuel(int(limit))
    wc = w.WasiConfig(); wc.argv = ["/usr/local/bin/python.wasm", *gargs]
    wc.env = [] if seed == "-" else [("PYTHONHASHSEED", seed)]
    wc.stdout_file = root + "/o"; wc.stderr_file = root + "/e"; wc.preopen_dir(root, "/")
    st.set_wasi(wc); lk = w.Linker(eng); lk.define_wasi()
    inst = lk.instantiate(st, mod); code, trap = 0, ""
    try: inst.exports(st)["_start"](st)
    except w.ExitTrap as e: code = e.code
    except w.Trap as e: code, trap = None, str(e).splitlines()[0]
    print(f"exit={code} fuel={int(limit) - st.get_fuel()} trap={trap!r} out={Path(root, 'o').read_text()[:40]!r}")
```

Command, one line per row below:
`uv run -q --with wasmtime==49.0.0 python -I fuel_probe2.py
build/brett-3.14.7/python.wasm build/brett-3.14.7/lib/python3.14
<limit> <seed> -c <code>`. Output:

```
seed0 pass #1: exit=0 fuel=165629282 trap='' out=''
seed0 pass #2: exit=0 fuel=165629358 trap='' out=''
seed0 pass #3: exit=0 fuel=165629386 trap='' out=''
seed0 json #1: exit=0 fuel=1140920728 trap='' out='[["a", 5], ["b", 2], ["c", 1], ["d", 1],'
seed0 json #2: exit=0 fuel=1140920700 trap='' out='[["a", 5], ["b", 2], ["c", 1], ["d", 1],'
seed0 json #3: exit=0 fuel=1140920620 trap='' out='[["a", 5], ["b", 2], ["c", 1], ["d", 1],'
random pass #1: exit=0 fuel=165443782 trap='' out=''
random pass #2: exit=0 fuel=164916331 trap='' out=''
spin, cap 2e9: exit=None fuel=2000000000 trap='error while executing at wasm backtrace:' out=''
spin, cap 2e9 again: exit=None fuel=2000000000 trap='error while executing at wasm backtrace:' out=''
```

## Findings

1. **With a fixed hash seed, fuel is close to exact.** `-c pass` spent
   165,629,282 to 165,629,386 across three processes: a spread of 104,
   or 6 parts in ten million. The JSON job spent 1,140,920,620 to
   1,140,920,728: a spread of 108, or 1 in ten million. (EXECUTED)
2. **Without a fixed seed it is not.** Hash randomization changes dict
   and set layouts. Two unseeded `pass` runs differ by 527,451, about
   0.3%. An earlier in-process run of the same probe gave the same
   picture. (EXECUTED)
3. **`-I` ignores `PYTHONHASHSEED`.** Isolated mode implies `-E`, so a
   harness that wants a fixed seed passes the variable and does not
   pass `-I`. (READ: CPython's command-line documentation for `-I` and
   `-E`; not separately executed here.)
4. **A fuel cap is a deterministic deadline.** A spinning guest with a
   cap of 2,000,000,000 trapped after spending exactly the cap, twice.
   A test can bound a runaway guest by fuel, never by a clock.
   (EXECUTED)
5. **The residual spread is small and not zero.** INFERRED: the guest
   still reads the clock (`clock_time_get`) and formats what it reads,
   so a few dozen instructions move. A ratchet on fuel therefore needs
   a tolerance.
6. **A reactor built with an isolated config cannot be seeded.** The
   spike's reactor entry calls `PyConfig_InitIsolatedConfig` (READ:
   `recipes/vfs_main.c`), which ignores the environment, so its hash
   seed is random on every `_initialize`. Its fuel will carry the
   unseeded spread of finding 2, about 0.3%. INFERRED: a tolerance of
   1% is about three times that spread, holds for seeded and unseeded
   binaries alike, and still catches any slowdown worth a reason.
7. **Fuel is per wasmtime version.** Fuel costs are wasmtime's own
   accounting, not a wasm standard. INFERRED: fuel numbers compare only
   between runs on the same wasmtime version; the harness records the
   version and refuses to compare across it.

## What it decides

- The harness meters every guest run with fuel and records the number
  as a metric per check.
- Guest runs in the harness set `PYTHONHASHSEED=0` and do not pass `-I`
  when they measure.
- Runaway guests are stopped by a fuel cap, not a timer.
- The fuel ratchet's tolerance is 1%, compared only on equal
  wasmtime versions.

## What it does not decide

A snapshot binary bakes its hash secret into the snapshot at build
time (INFERRED from finding 7 of the spike memo: the interpreter is
initialized inside Wizer). Whether that matters for the published
snapshot is a question for the snapshot's own specification, not for
the harness.

## One line

Fuel, with a fixed hash seed, counts guest work to about one part in
ten million, so the harness can ratchet speed without ever reading a
clock.
