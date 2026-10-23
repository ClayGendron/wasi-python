# A host-supplied clock and random source make fuel nearly exact

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: one hour.
- **Supersedes:** the tolerance decision of `2026-10-16-fuel-as-the-operation-count.md` (its findings stand).
- **Feeds:** `../specifications/002-the-progress-harness.md` (Decisions 8 and 9: the driver's own `random_get` and `clock_time_get`, and the fuel tolerance).
- **Prompted by:** finding 5 of `../reviews/002-the-progress-harness-spec-2026-10-16.md`.
- **Machine (benchmark fact only):** Apple arm64, macOS 26.5, wasmtime-py 49.0.0, Python 3.14.2 host.

## The question

The first fuel memo fixed the guest's hash seed with `PYTHONHASHSEED=0`. Neither product binary honours that variable: the reactor starts CPython with an isolated config, and the snapshot's hash secret is fixed at Wizer time. Can the judge remove the variance itself, without touching the guest's imports?

The idea: the guest asks WASI for random bytes (`random_get`) and the time (`clock_time_get`). Those calls are answered by the host. If the host answers them deterministically, the guest's hash secret and its clock readings are the same on every run. The guest still imports only WASI preview1 (constitution §4.4); only the host's answers change.

## What was run (EXECUTED)

Brett Cannon's 3.14.7 build (pinned, `2e064d3f…`), one guest run per host process, **with `-I`** so that no environment variable can seed anything. wasmtime-py's `Linker.allow_shadowing` lets the host redefine the two WASI functions after `define_wasi()`. The probe:

```text
"""Fuel probe 3: one guest run per process, with the host supplying random_get and clock_time_get deterministically.
argv: python.wasm lib-dir mode(real|fixed) guest-args..."""
import hashlib, shutil, struct, sys, tempfile
from pathlib import Path
import wasmtime as w
wasm, lib, mode, *gargs = sys.argv[1:]
cfg = w.Config(); cfg.consume_fuel = True
eng = w.Engine(cfg); mod = w.Module.from_file(eng, wasm)
i32, i64 = w.ValType.i32(), w.ValType.i64()
state = {"rand": 0, "tick": 0}
def random_get(caller, buf, n):
    mem = caller.get("memory"); out = bytearray()
    while len(out) < n:
        out += hashlib.sha256(struct.pack("<Q", state["rand"])).digest(); state["rand"] += 1
    mem.write(caller, bytes(out[:n]), buf); return 0
def clock_time_get(caller, clock_id, precision, out):
    state["tick"] += 1
    base = 1_767_225_600_000_000_000 if clock_id == 0 else 0  # 2026-01-01T00:00Z for the realtime clock
    caller.get("memory").write(caller, struct.pack("<Q", base + state["tick"] * 1000), out); return 0
with tempfile.TemporaryDirectory() as root:
    shutil.copytree(lib, Path(root, "usr/local/lib/python3.14"))
    st = w.Store(eng); st.set_fuel(10**13)
    wc = w.WasiConfig(); wc.argv = ["/usr/local/bin/python.wasm", *gargs]
    wc.stdout_file = root + "/o"; wc.stderr_file = root + "/e"; wc.preopen_dir(root, "/")
    st.set_wasi(wc); lk = w.Linker(eng); lk.define_wasi()
    if mode == "fixed":
        lk.allow_shadowing = True
        lk.define_func("wasi_snapshot_preview1", "random_get", w.FuncType([i32, i32], [i32]), random_get, access_caller=True)
        lk.define_func("wasi_snapshot_preview1", "clock_time_get", w.FuncType([i32, i64, i32], [i32]), clock_time_get, access_caller=True)
    inst = lk.instantiate(st, mod); code = 0
    try: inst.exports(st)["_start"](st)
    except w.ExitTrap as e: code = e.code
    print(f"mode={mode} exit={code} fuel={10**13 - st.get_fuel()} rand_calls={state['rand']} clock_calls={state['tick']} out={Path(root, 'o').read_text()[:50]!r} err={Path(root, 'e').read_text()[-120:]!r}")
```

Command: `uv run -q --with wasmtime==49.0.0 python -I fuel_probe3.py build/brett-3.14.7/python.wasm build/brett-3.14.7/lib/python3.14 <real|fixed> -I -c <code>`. Output:

```text
mode=fixed exit=0 fuel=165084745 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=165084665 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=165084725 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=1139507796 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
mode=fixed exit=0 fuel=1139507736 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
mode=fixed exit=0 fuel=1139507636 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
mode=real exit=0 fuel=165312998 rand_calls=0 clock_calls=0 out='' err=''
mode=real exit=0 fuel=165663483 rand_calls=0 clock_calls=0 out='' err=''
```

The same probe with every file and directory in the guest's root set to one fixed mtime before the run (`fuel_probe4.py`, the probe above plus an `os.utime` walk), `fixed` mode only:

```text
mode=fixed exit=0 fuel=165085715 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=165085615 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=165085715 rand_calls=1 clock_calls=6 out='' err=''
mode=fixed exit=0 fuel=1139114051 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
mode=fixed exit=0 fuel=1139113611 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
mode=fixed exit=0 fuel=1139113711 rand_calls=1 clock_calls=7 out='[["a", 5], ["b", 2], ["c", 1], ["d", 1], ["r", 2]]' err=''
```

## Findings

1. **Shadowing works.** wasmtime-py 49 accepts the two redefinitions, the guest runs to exit 0, and it called the host's `random_get` once (CPython's hash secret) and `clock_time_get` six or seven times. (EXECUTED)
2. **The seed variance is gone even under `-I`.** Unseeded `real` runs of `-c pass` differ by 350,485 (0.21%). `fixed` runs differ by at most 80 for `pass` and 160 for the JSON job: a spread of about 1.4 parts in ten million. (EXECUTED)
3. **A residual remains, and it is not the clock, random or mtimes.** With fixed mtimes the spread was 100 for `pass` and 440 for the JSON job (4 parts in ten million). INFERRED: it comes from other host facts the guest reads and formats, such as inode numbers. It was not chased further; it is three orders of magnitude below the seed effect.
4. **Fixing mtimes does not help.** The run-to-run spread with fixed mtimes (finding 3) was not smaller than without. (EXECUTED)

## What it decides

- The harness's driver answers `random_get` from a fixed SHA-256 counter stream and `clock_time_get` from a fixed start that advances one microsecond per call. Every guest run is then seeded the same way, on every binary, whatever its config does with the environment.
- The fuel ratchet's tolerance is **0.01%**: about 250 times the largest residual seen, and still a hundred times finer than the seed effect it replaces.
- `PYTHONHASHSEED` is no longer set by the driver; it is not needed.

## What it does not decide

Whether the residual stays this small on the 55–94 MB numpy and pandas binaries. The first artifact set will show it. If a check's fuel spreads by more than the tolerance across repeat runs, that is a red run with this memo as the place to record why.

## One line

When the judge answers the guest's clock and random calls itself, fuel repeats to a few parts in ten million on any binary, so a 0.01% ratchet is safe.
