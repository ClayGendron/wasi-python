# Review of 080 — 071's recursion checks count deterministic fuel, and its guard's unit tests stand alone (spec and build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I reviewed 071 (its spec, its build and its delta). I wrote none of 080: not its spec, its code, its notes or its evidence. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/080-deterministic-recursion-fuel` at `596655c`, on main `23f1c4f`. Commits: `9bfffba` (spec), `d5f7984` (item 1), `dcd7e4c` (item 2) and `596655c` (notes, and the evidence under the memo's `v4/`). The diff touches two checks in `tests/checks/test_v1_2_hostile_guest.py`, two unit tests in `tests/unit/test_runner_async.py`, the spec and the evidence (READ, `git diff --stat`).
- **Ran (EXECUTED).** Nothing was written in a git tree. For Linux I used `git archive` copies of both commits (`tree-23f1c4f/`, `tree-596655c/`) and a copy of the set (`set/`). Scripts and logs are in `probes/` beside this file:
  - **The fast tier.** `uv run pytest -m "not slow" -n 3` in the worktree, with `WASI_PYTHON_ARTIFACTS=build/sets/s-c50ca51fae5eb55b` (`fast-n3.log`, `fast-n3-latest.json`).
  - **Five runs.** `five_some.py`: five runs of seven rows, through `wasi_python.run` and through the driver. `pdmap_guest.py` and `pdmap_shared.py`: pandas' row, eight runs in fresh workdirs and twelve in one workdir. `frompyfunc_env.py`: the risen row against `run`'s base environment.
  - **Linux, `wp040-arm64` and `wp040-amd64`, CPython 3.14.2, the locked dependencies, before and after:**
    - `order.sh`: the own-runner shard's first five files in order; `test_runner_async.py` alone, with and without pytest's faulthandler plugin; and the whole suite;
    - `order2.sh`: the shard's 15 files in order;
    - `units-arm64.log`: the serial unit tier;
    - `culprit*.sh` and `triple.sh`: which order turns the guard against real-engine tests.

## What holds

- **The fast tier reproduces the notes (EXECUTED).** `475/550 pass · 1 gap · 23 blocked · 0 fail · 51 deselected (unit suite 1267/1275, 8 skipped)`; `1742 passed, 31 skipped, 1 xfailed`; ratchet against `9dad163977`: lost 0, gained 0, grew 1. The one growth is `[np-frompyfunc-snapshot]`, 779,725,038 → 779,990,064.
- **Item 1 makes the fuel deterministic (EXECUTED, `five_some.txt`).**

  | row | through `run`, spread over five runs | through the driver |
  |---|---|---|
  | `repr` (plain) | 678,087 (0.39%) | 0 |
  | `heapq` (plain) | 975,174 (0.55%, more than the notes' 0.45%) | 0 |
  | `heapq` (snapshot) | 0 | 0 |
  | `np-frompyfunc` (snapshot) | 0 | 0 |
  | `pd-map` (snapshot) | 606,246 (0.013%) | 17 (see N1) |
  | `lxml-target` (snapshot) | 2,503 | 0 |
  | the deep pickle (snapshot) | 0 | 0 |

  Every row's outcome line is the same on both paths (`__repr__` 214, `heapq` 244, `np-frompyfunc` 53, `pd-map` 160, lxml 67, pickle 0), so the depths, and the floors the checks hold, are untouched.
- **Item 1 loses no coverage that matters (READ).**
  - **The engine.** The driver makes the runner's metered engine: fuel, epoch interruption and 512 KiB (`guest.engine()`). 071's criterion 5 holds both engines to exactly those three settings and nothing else (`test_the_runner_states_its_wasm_stack` asserts the whole dict of attributes set, for both of `_engine`'s engines; `test_the_guest_driver_makes_the_runners_engine` the same for the driver). A runner change that grew frames through a new config setting would fail there.
  - **The window.** It is in the binary, so it is the same on both paths.
  - **What `run` adds over the driver** is its linker, its epoch callback, its environment and its `.cwasm` cache: none of them changes how deep a guest recursion goes (INFERRED; EXECUTED above, the same depths).
  - **What still runs through `run`.** 071's criterion 2 (`__repr__`, both binaries, the exact "used 112 kB" message), criterion 4 (the limits, metered) and criterion 11 (the fault-handler orders). So the product path still meets recursion raising on both binaries. One small gap: F2.
- **The restated values (EXECUTED).** 34 fall and 2 rise; `[np-frompyfunc-snapshot]` rises +265,026 and is deterministic on both paths (0 spread each). Its cause is the driver's environment, as the notes say, and more exactly (`frompyfunc_env.txt`):
  - laying `run`'s base environment (`TMPDIR=/tmp`, `PYTHONTZPATH=`) over the driver's makes `repr` cost exactly what `run` gives (+26,348 both);
  - the numpy rows differ beyond that, from the driver's seeded `random_get` and stepped clock against `run`'s host entropy, which reseeds `numpy.random`: `np-frompyfunc` −401,113 with `run`'s environment, −264,907 through `run` itself.

  The `--accept-growth` reason is correct as written.
- **Item 2's cause, and its fix, on Linux (EXECUTED, `order-*.log`, both architectures).**
  - **Before (`23f1c4f`).** The shard's first five files in order: 2 failed, 81 passed, the two named tests refused by the guard. `test_runner_async.py` alone: 2 failed, 13 passed, with or without pytest's faulthandler plugin.
  - **After (`596655c`).** 83 passed; alone, 15 passed with and without the plugin; the shard's 15 files in order, 445 passed on aarch64 and on x86_64 (`order2-*.log`).
- **Item 2 is not a weakening (READ, EXECUTED).**
  - Both tests hand `_drive` stand-ins for wasmtime. The guard, the first statement of `_drive`, finds no wasmtime handler because no engine exists in that process. That is the guard doing its job on an input the product never gives.
  - The guard keeps its own checks: 071's criterion 11, seven orders in subprocesses, and its unit with stand-ins for `sigaction` and `dladdr`.
  - The patch is scoped to the two tests by `monkeypatch`, with a comment. It is a judge change, accepted with `--accept-judge` as rule 4 asks.
- **Patching beats a real engine in a fixture (EXECUTED, `triple-arm64.log`).**
  - A real engine does not keep the guard true for the rest of a session. Once any inline pytest session has run in the same process, the guard refuses even with an engine present (F1).
  - So a fixture engine would make the two `_drive` tests fail in that order. Patching keeps them about their own rule in any order.
- **"The product never reaches the guard without an engine" holds (READ, at `23f1c4f`).**
  - **`run` and `run_async`.** Both go through `_run_checked`, which makes the engine and the module (`runner.py:2375–2376`) before `_call` reaches `_instance` and `_drive` (2657). `run_async`'s first call runs the same function on its worker thread.
  - **Sessions.** `_open_session` makes its engine and module (4601–4602) before its guard (4684). The turn's guard (4394) and the ending's (4210) come later.
  - **Process-wide.** wasmtime installs its handlers once, process-wide, at the first engine (READ in 071's research), so a later run on any thread finds them.

## Findings, most severe first

### F1 (medium; not 080's to fix, but to record). On Linux, after any inline pytest session, the guard refuses 16 real-engine unit tests

- **What happens (EXECUTED, `units-arm64.log`).** The serial unit tier on Linux has 16 `RuntimeError`s from 071's guard: nine in `test_runner_calls.py`, seven in `test_runner_mounts.py`. These tests make real engines.
- **The cause (EXECUTED, `triple-arm64.log`, `culprit2-arm64.log`).**
  - `tests/unit/test_guest.py` makes an engine. Then `test_landing_lane.py` or `test_plugin.py` runs an inline pytest session, whose faulthandler plugin disables and re-enables faulthandler. That leaves faulthandler over `SIG_DFL` with wasmtime's handler gone, the "enabled before, disabled after" order.
  - A two-line probe shows it: faulthandler on, an engine, then guard `None`; one inline `pytest.main(...)`, then guard `SIGSEGV`.
  - `test_guest.py` + either file + `test_runner_calls.py` gives 9 refusals. With the outer session's `-p no:faulthandler`, it gives 0. Main `23f1c4f` gives the same 9.
- **The guard is right.** Several of those tests make the guest trap (`test_a_trap_in_host_alloc_is_the_calls_trap`), which would kill the pytest process.
- **Where it shows.** It is pre-existing since 071, untouched by 080, and the release is unaffected: its Linux job runs v1.1 to v1.4 and three runner unit files, no inline sessions (READ, `release.yml:428–436`). The own-runner shard of 063's dry run did not meet it either. It does meet a developer's serial `uv run pytest` on Linux, and any 063 shard that puts an inline-session file before a runner file.
- **Why it concerns 080's text.** 080's Intent ("whatever runs before them") and its notes read as if Linux order were settled.
- **Asked:**
  - The landing notes say this case is open, and name a follow-up (or 063, whose shard assignment decides it). The simplest fix to weigh there: the inline sessions (`pytester.runpytest`, `pytest.main`) pass `-p no:faulthandler`, or run as subprocesses.
  - The Intent is scoped to "unit tests that never touch wasmtime".

### F2 (low, optional). One recursion-raises check could stay on `run`'s metered engine

- After 080, criterion 2 is the product path's recursion check, and it calls `run` unmetered, the roomier engine.
- Driver and runner engines are held equal by criterion 5, so nothing is lost today. But passing `fuel=10**11` to criterion 2 (it records no fuel, so it stays deterministic) would keep `run`'s thin engine meeting a Python-through-C recursion end to end, as 071's criterion 1 did.

### Notes (no change asked)

- **N1. Not quite "one value" (EXECUTED, `pdmap_shared.txt`, `pdmap_guest.txt`).** Through the driver, pandas' row gives one value in eight fresh workdirs (4,660,036,308). In one shared workdir, as the session-scoped `guest` fixture runs, twelve runs give two values, 34 fuel apart (4,660,036,274 and 4,660,036,308; 7×10⁻⁹). I did not trace it (perhaps host file metadata the guest reads; INFERRED). It is four orders below the ratchet's tolerance, so it is harmless; "identical over five runs" holds in the author's runs and to within 34 fuel in mine.
- **N2. The stated spreads are samples.** `run`'s plain spreads are a random hash secret's, so the notes' "0.09% to 0.45%" is a sample: I saw 0.55% for `heapq`.

## Constitution checks

- §4.9: the change makes fuel counts deterministic; nothing is timed (READ).
- AGENTS rule 4: two checks change how they run, not what they assert; two unit tests set aside a guard they do not test, with a reason. Both are judge changes, accepted with `--accept-judge` (READ, the notes).
- §5.6: I re-ran the fast tier (`-n 3`); the full run is the author's (`judge-080.log`) and the lane's.

## Verdict

**Lands once F1 is answered in writing.** That means a sentence in the landing notes naming the open Linux order case and its follow-up, and the Intent scoped to tests that never touch wasmtime. No code change is asked of 080. F2 is optional. The restated values and the `--accept-growth` reason stand as written.

## One line

080 makes 071's recursion fuel deterministic without losing what 071 tested, and its guard patch is right. Before it lands, its notes should say that on Linux an inline pytest session still turns the guard against 16 real-engine tests, a pre-existing order hazard for a follow-up.
