# Review of 006 — Safe by default: the hostile guest, judged (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I was given the constitution, `AGENTS.md`, `context/README.md`, the reviews README, the 005 pre-build review (for its format), the specification under review, the three memos it stands on, and the code it changes. I did not rely on the author's summary.
- **Reviewed:** `context/specifications/006-safe-by-default.md` (draft, 141 lines, untracked), against the working tree at `360b51b` with spec 005's build in it.
- **Ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, wasmtime CLI 49.0.3).** Scripts and outputs are under `…/scratchpad/review-006/` (`probes/`, `proto/`). Nothing under `build/` was written.
  - **Artifacts.** The 0.1.0a1 set (3.14.8) from `…/scratchpad/build-314-a1/artifacts/`, and a read-only copy of `build/artifacts/` (3.15.0, built 2026-10-17 00:09) at `review-006/a315/`.
  - **Prototype reactors.** I built three of them from scratch copies of `recipes/reactor_main.c`. I used the compile and link commands recorded in `build/link/reactor-commands.txt`, run in the 3.15 build directory with `-o` and the map pointed into scratch. Each was snapshotted with step 80's exact flags (`build/out/wizer-command.txt`) into scratch.
    - **A**, the specification as written: `module_search_paths = ["/usr/local/lib/python315.zip"]` and `module_search_paths_set = 1`, then `__wasilibc_reset_preopens()` before `clear_unused_stack()`.
    - **B**: the reset only.
    - **C**, my suggested fix: A, plus `config.stdlib_dir` set to the zip and `config.site_import = 0`. After start-up, `site.setquit()`, `site.setcopyright()` and `site.sethelper()` are called.
    - All three compiled and linked with exit 0, and Wizer exited 0.
  - **Imports and exports.** All three prototypes have the same 43 imports (42 WASI calls plus `host::call`) and the same exports as the 3.15 build: `_initialize`, `host_alloc`, `memory`, `run`, `wizer.initialize`, and on the snapshot `host_alloc`, `memory`, `run`.
  - **Rebuild identity.** A's snapshot, rebuilt with `env -i PATH=/usr/bin:/bin HOME=<scratch> TZ=Asia/Tokyo` and a different root directory, has the same SHA-256 (`36f93653ad4d3a7c…`).
  - **Fuel** from the judge's own driver (`tests/harness/guest.py`, which gives exact fuel):

    | binary | build | `-c pass` | `-c "import pandas"` |
    |---|---|---|---|
    | snapshot | 3.15 as built | 124,178,786 | — |
    | snapshot | A | 124,303,697 (**+124,911, +0.101%**) | — |
    | snapshot | B (reset only) | 124,178,447 (−339) | — |
    | snapshot | C | 124,150,757 (−28,029, −0.023%) | — |
    | plain | 3.15 as built | 246,819,329 | 4,995,344,218 |
    | plain | A | 246,250,760 (−0.23%) | 4,995,041,477 |
    | plain | B | 246,819,329 (±0) | 4,995,344,218 |
    | plain | C | 246,448,542 (−0.15%) | 4,994,994,764 |

  - **Probes through `wasi_python.run`** (`probes/p1`–`p8`), on 3.14, 3.15, A and C. Their results are quoted in the findings.
- **Read (READ):**
  - our code: `src/wasi_python/runner.py`, `src/wasi_python/__init__.py`, `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `recipes/hostmodule.c`, `scripts/steps/60_link.sh`, `scripts/line.conf`;
  - the judge: `tests/harness/guest.py`, `tests/harness/scoreboard.py:31` (`FUEL_TOLERANCE = 1e-4`), `tests/checks/test_v1_2_portable_and_sealed.py`, `test_v1_3_data_stack.py`, `test_v1_4_embedding.py`, `tests/known_gaps.toml`;
  - CPython 3.15.0: `Modules/getpath.py:225-236, 340-420, 545-760, 800-840`, `Lib/site.py:805-830, 1060-1095`, `Lib/importlib/_bootstrap.py:1080-1105`;
  - wasi-libc: `preopens.c` at prior-art commit `165235b`. SDK 33's own commit, `161b3195`, is not in the clone. SDK 33's `wasi/libc.h:22-27` declares the reset with the documented wording;
  - wasmtime-py 49.0.0: `_memory.py:81-133`, `_wasi.py:197-208`, `_func.py:189-250`, `_value.py:36-43, 106-130`.

## Acceptance criteria against evidence

1. *Every check exists and was seen failing before its fix.* **Not reachable as written.** Some checks guard behaviour that already holds, so they cannot fail first (finding 7).
2. *Steps 60 to 90 rebuild and give the same bytes twice.* Checkable, and the right proof. A's snapshot reproduced across two Wizer runs that used different environments and roots.
3. *`uv run pytest` green; no pass lost; growth has its cause.*
   - Checkable, but Decision 6 predicts the wrong growth (finding 2).
   - The new checks change the judge. That needs `--accept-judge`, which the criterion does not name (finding 8).
4. *The README's "Safety" section names each default and each unprotected channel.* Checkable. The list in Decision 5 is short of what the probes show (finding 5).

## Findings, most severe first

1. **Decision 3 does not close code execution across runs. The plain reactor still runs a planted `.pth` file and imports from a planted `site-packages`, and check 1.2 as written would pass anyway** (`006:29-32`, `006:82-89`). High.
   - **Today (EXECUTED, 3.14 and 3.15 plain reactor, `probes/p2_pth*.py`).**
     - Run 1 writes `/usr/local/lib/python3.15/site-packages/zz.pth` (one `import` line) and a module there.
     - Run 2, on the same root, adds that directory to `sys.path` and prints `PTH RAN at startup`. That is the planted code, running before the program.
     - The cause: the isolated config keeps `site_import = 1`. `site.main()` adds `sys.prefix/lib/python3.15/site-packages` and executes its `.pth` lines (READ, `site.py:1060-1095`).
   - **With prototype A, the specification as written (EXECUTED).** `evil.py` in `python3.15/` and in `lib-dynload/` are no longer imported, which is what check 1.2 tests. But `sys.path` is `['/usr/local/lib/python315.zip', '/usr/local/lib/python3.15/site-packages']`, the planted site-packages module imports, and the `.pth` still runs.
   - **A second route (EXECUTED, `probes/p3_venv_315.py`, 3.15 and A).** Run 1 plants `/usr/local/bin/pyvenv.cfg` and a module in `/usr/local/bin/lib/python3.15/site-packages/`. In run 2, getpath reads the planted file: `sys.prefix` becomes `/usr/local/bin`, two `RuntimeWarning`s go to stderr, the planted `.pth` runs, and the planted module imports. getpath reads `pyvenv.cfg` whenever `Py_SetPath` was not called, whatever `module_search_paths_set` says (READ, `getpath.py:348`).
   - **The snapshot is not affected (EXECUTED).** `site` and getpath ran at build time.
   - So Decision 3's "after this it escapes by construction" is false for the plain reactor. Check 1.2 as specified would go green over a live hole.
   - **Fix, verified as prototype C (EXECUTED).**
     - In `init_interpreter`, set `config.site_import = 0` as well.
     - Then call `site.setquit()`, `site.setcopyright()` and `site.sethelper()`. With `no_site` set, `import site` does not run `main()`.
     - On both binaries, C gives `sys.path == ['/usr/local/lib/python315.zip']`. It ignores the planted `.pth`, `site-packages` and venv module. `exit(3)` returns 3, and `help` and `license` exist.
     - The one visible difference: `sys.flags.no_site == 1`. No check reads `sys.flags` (`grep`). Say so in the README's platform notes.
     - A planted `pyvenv.cfg` still moves the plain reactor's `sys.prefix` to `/usr/local/bin`, with no warning and no import. Record that as a known, harmless residue, or have check 1.2 assert `sys.prefix == "/usr/local"` and fix it with `config.home`. I have not tested whether `config.home` stops it.
   - **Fix for check 1.2.**
     - Plant all five routes: `python3.X/`, `lib-dynload/`, `site-packages/` with a module, `site-packages/*.pth`, and `pyvenv.cfg` with its site-packages.
     - Assert that no planted code runs (a marker file the `.pth` would write is absent).
     - Assert `sys.path == [<the zip>]` on both binaries.

2. **Decision 3 alone sets `sys._stdlib_dir` to `None`. Every frozen stdlib module loses `__file__`, and the snapshot's fuel grows past the tolerance that Decision 6 promises** (`006:82-89`, `006:104-106`). Medium.
   - **What A does (EXECUTED).** On both binaries, `sys._stdlib_dir` is `None` and `getattr(os, "__file__", "MISSING")` is `MISSING`.
     - getpath computes `stdlib_dir` only when it computes the path itself (READ, `getpath.py:736-741`, `:837`).
     - FrozenImporter sets `__file__` only from `sys._stdlib_dir` (READ, `_bootstrap.py:1082-1102`).
     - Native Python has `os.__file__`. `os.path.dirname(os.__file__)` is a common way to find the stdlib, and AI-written code uses it.
   - **What else A changes (EXECUTED).** The snapshot's `-c pass` grows by 124,911 instructions (+0.101%). The ratchet allows 0.01%. The reset alone (B) costs −339, so the growth comes from the path change. I infer, but did not prove, that the cause is the missing `stdlib_dir`: C differs from A only in setting it and in `site`, and C shrinks by 0.023%.
   - **Fix.**
     - Set `config.stdlib_dir` to the zip's guest path as well. With C, `sys._stdlib_dir` is `/usr/local/lib/python315.zip` and `os.__file__` is `/usr/local/lib/python315.zip/os.py`, which matches how every zipped module's `__file__` reads. `numpy`, `pandas`, a CSV round trip, a groupby, `ZoneInfo` through `tzdata`, `importlib.resources` and `-V` all work on A and C (EXECUTED, `probes/p5_proto.py`).
     - Decision 6 should state the measured effect: on the snapshot, roughly −0.02%; on the plain reactor, −0.15%. It should not promise "no growth".

3. **Check 1.9 cannot be built as written, and the defects it should find are elsewhere** (`006:47-50`). Medium.
   - **The bad request cannot be made on the shipped binaries (READ, `hostmodule.c:42-45`).** From Python, `_host.call` always passes a valid buffer's pointer and length. Neither binary has `ctypes`. So "a request whose pointer or length runs past guest memory" cannot be produced "on both binaries".
   - **The runner's door is still wrong for such a frame (READ, wasmtime-py `_memory.py:93-101`).** `Memory.read` clamps like a slice. A frame that runs past memory reaches the host truncated, or empty, and the door answers 0. The judge's own door in `guest.py` does the same.
   - **A response of 2 GiB or more escapes `run()` (READ, `_value.py:42`, `_func.py:212-250`).**
     - The length passed to `host_alloc` wraps silently to i32.
     - `memory.write` then raises `IndexError` inside the callback.
     - wasmtime-py stores that in a process-global `LAST_EXCEPTION` and raises it again from `exports["run"]`. The runner catches only `wt.Trap`, `wt.ExitTrap` and `wt.WasmtimeError`, so `run()` raises `IndexError` instead of returning `Completed`.
     - Because the global is shared by the process, concurrent calls could see each other's exception.
   - **A response that is merely larger than free guest memory** already gets −2: `malloc` fails and `host_alloc` returns 0. That case passes today.
   - **Fix.**
     - Drive the bad-pointer case with a small WAT guest that imports `host::call` (`tests/unit/wat.py` exists for this), against the runner's `_door`. Call it what it is, a runner check, not "both binaries".
     - Specify the runner fix. Bound `ptr + length` by `memory.data_len`, and require `len(response) <= 0x7FFFFFFF`; otherwise answer −2. Wrap the door body so that no Python exception leaves it. State that `run()` returns a `Completed` and never raises for anything a guest or host frame does.
     - Keep the both-binaries part to what Python can reach: a response larger than the guest's free memory, under a `memory_bytes` cap.
     - Give `guest.py`'s door the same bounds check, or say why the judge may differ.

4. **A call without `root` costs more than Decision 6 says, and the runner grows two caches with every such call** (`006:61-63`, `006:104-106`). Medium.
   - **The cost.** Every rootless call copies the whole stdlib zip into the fresh directory: 11,140,659 bytes for 3.15 (EXECUTED, `ls -l`). Then it removes the tree. `_place_stdlib` copies and never links, and it must keep doing so (READ). Decision 6 names only "a directory's creation and removal".
   - **The leak (READ, `runner.py`).** `_placed[str(dest)]` and `_placing.setdefault(str(dest), Lock())` are keyed by path and never pruned. Every rootless call has a new path, so a long-running framework process grows both dicts without bound.
   - **The removal order (INFERRED).** The removal must come after the `Store` (and the WASI context holding the preopened directory) is released, and it must sit in a `finally`. Otherwise it fails on Windows, where an open handle blocks deletion, and it leaks the directory when `run()` raises (finding 3).
   - **Fix.**
     - State the per-call copy as a cost and leave its time to the memo.
     - Do not record private roots in `_placed` and `_placing`, or drop their entries when the call ends.
     - Specify the removal: `del store`, then `shutil.rmtree` in a `finally`.
     - Check 1.5 should point `tempfile.tempdir` at a scratch directory with `monkeypatch`, and assert that the directory is empty after both calls.

5. **The base environment closes one of the three planted-data channels, but the specification reads as if it closes all of them** (`006:33-35`, `006:73-76`, `006:99-102`, `006:108-112`). Medium.
   - **The probe (EXECUTED, `probes/p8_env.py`, 3.15 plain and snapshot).** With the base environment, a root `/tmp`, and a planted `America/New_York` (Tokyo's data) and `/etc/mime.types`:
     - `zoneinfo` gives the correct −04:00;
     - `dateutil.tz.gettz("America/New_York")` gives `0:00:00` from the planted file. dateutil is in the zip and is pre-imported in the snapshot;
     - `mimetypes.guess_type("a.zzz")` gives `('application/x-planted', None)`;
     - `tempfile.gettempdir()` is `/tmp`, and `mkstemp` writes there.
   - The Intent says the program "cannot leave anything for the next call". That holds only for a call without `root`.
   - **Fix.** State the policy in one sentence, in the decisions and in the README:
     - code planted in any root never runs in a later call (finding 1 makes this true);
     - data planted in a root the caller reuses is read by later calls. That covers dateutil's zones, `mimetypes`, `license()`'s search, and any user file. Only a fresh root closes it.
     - `PYTHONTZPATH=""` closes zoneinfo's half as a courtesy.
     - Rename check 1.3 to say it covers `zoneinfo`, and add the dateutil and `mimetypes` results to Decision 5's "not protected" list.

6. **Check 1.11 sets up a known gap for something out of scope, with a closer that does not exist** (`006:55-58`, `006:118-121`). Medium-low.
   - The Scope puts "a disk quota" out of scope. Yet 1.11 sets up a known-gap entry that "closes with the typed-grants specification".
   - That document does not exist.
   - Direction 5 (typed grants) promises read-only and writable mounts, not quotas.
   - `known_gaps.toml` says "a gap is an allowance, not a backlog", and its one entry names an existing memo.
   - **Fix.** Drop 1.11, and keep disk use in the README's "not protected" list (Decision 5 already has it). If a check is wanted, first write a placeholder research memo that names the experiment for a quota (§5.2), and make that memo the gap's closer.

7. **Acceptance criterion 1 cannot hold for the regression guards** (`006:131-134`). Low.
   - These pass today:
     - check 1.1, links (the threat model's EXECUTED row);
     - check 1.2 on the snapshot (EXECUTED, `probes/p2_pth_315.py`);
     - the "response larger than free memory" part of check 1.9 (finding 3).
   - These fail today, as intended:
     - 1.2 on the plain reactor;
     - 1.4 (`/` without `TMPDIR`; data-folders memo);
     - 1.10 (EXECUTED, finding 12);
     - 1.6 to 1.8, which have no defaults today.
   - **Fix.** Split the criterion: the checks that guard a change were seen failing; the guards of existing behaviour, named one by one, passed on the first run.

8. **Judge changes the Design does not list** (`006:51-54`, `006:113-120`). Low.
   - **The driver.** Check 1.10 needs the judge's driver to take extra preopens, in a chosen order, and read-only. `guest.py` takes one root today. That is a judge change, and the Design table omits `tests/harness/guest.py`.
   - **The judge hash.** The new checks change the judge's hash, so the landing run needs `--accept-judge "<reason>"` (AGENTS.md rule 6). Criterion 3 should say so.
   - **Wording.** The phrase "a runner-level probe (the judge's driver, not the public API)" contradicts itself. Say "the judge's driver, given a `preopens=` argument".

9. **Small check-level gaps** (`006:29-46`). Low.
   - **Reading `DEFAULTS`.** `run()` must read `DEFAULTS` at call time, not bind it as a default argument, or `monkeypatch` has no effect.
   - **A lowered memory default (EXECUTED).** If a check lowers it, it must stay above the snapshot's initial memory of 56.375 MiB (the plain reactor's is 40 MiB). Below that, instantiation fails with a `WasmtimeError`, not a `MemoryError`. The 1 GiB default itself is ample: a one-million-row pandas groupby runs under a 256 MiB cap on both binaries.
   - **Check 1.8.** It should also lower `output_bytes` rather than write 16 MiB. The cap depends on the callback still returning `len(data)` for dropped bytes. wasmtime-py takes the callback's integer as the bytes written (READ, `_wasi.py:202-205`), and a short count would make the guest's `write` retry. State that the callback returns `len(data)` for dropped bytes too.
   - **Check 1.2's paths.** They should derive `python3.X` from `MANIFEST`, as `_zip()` in v1.4 does, not hard-code 3.15.
   - **Check 1.4's name.** It says files "stay out of the root", but `/tmp` is in the root. It means "out of `/`".

10. **Decision 3's build flag is not needed; the reset's place should be exact** (`006:82-97`). Low.
    - **The flag.** `-DSTDLIB_ZIP` would have to pass through step 60's `sed` and `eval` as a quoted narrow string, and then be widened for `PyWideStringList_Append`. `reactor_main.c` can build the same path from `PY_MAJOR_VERSION` and `PY_MINOR_VERSION`. Then it cannot disagree with the interpreter it is compiled into, and step 60 does not change.
    - **The reset's place.** "As its last step" should read "after `pinned = 0`, before `clear_unused_stack()`", so the reset's own stack residue is cleared. That is the order I built and reproduced.

11. **Text** (`006:61-80`, `006:108-112`). Low.
    - **The Intent.** It says `run(code)`, but `run` takes an argv list. A string would be split into characters. Write `run(["-c", code])`.
    - **The base environment.** It changes the documented "`os.environ` holds exactly what `env=` gave" (threat-model row). Its three keys can be overridden but not removed. The README and CHANGELOG must say both.
    - **`Completed.truncated`.** It goes last, with a default of `()`, so positional construction keeps working.
    - **The CHANGELOG.** It must state the behaviour change for existing callers. A job longer than 60 s now ends with `trapped == "deadline"` unless it passes `deadline_s=None`.
    - **Decision 5's "not protected" list** should add: a program can damage its own stdlib zip during its own run (the principal engineer's memo, INFERRED there), and the clock and entropy are real.
    - **A forward constraint (INFERRED from the wasi-vfs memo, lines 106-109).** wasi-vfs registers its packed directories with `__wasilibc_register_preopened_fd` at start-up. A reset at the end of `wizer.initialize` would drop them. If C3 is chosen later, this decision must be revisited. Say so in one line.

12. **Confirmations; no change needed.**
    - **Decision 4 works on the real 3.15 reactor (EXECUTED, `probes/p6_preopens.py`).** The runs gave the root at `/` and a read-only data directory at `/data`, in both orders:
      - **The 3.15 snapshot as built, root first.** `/data/x.txt` reads the copy planted in the root, and `open("/data/new", "w")` succeeds, writing into the root.
      - **The same snapshot, data first.** `/mark.txt` and `/data/x.txt` both give errno 44. Pre-imported modules still work.
      - **A's snapshot, either order.** It reads the real data and the root's mark, and writes to `/data` are refused with errno 63. That is the plain reactor's behaviour.
      - So check 1.10 will fail first and pass after the fix.
    - **No descriptor survives the snapshot (EXECUTED, `probes/p4_fds.py`, 3.14 and 3.15, after `gc.unfreeze()`).**
      - The only live file objects are stdio, on descriptors 0 to 2.
      - Descriptors 3 and up are what the runtime gave.
      - `zipimporter` holds only `archive` and `prefix`.
      - On wasip1, `preopen_state_close` does nothing (READ), so the reset closes nothing.
      - It is safe today. Add an assertion to check 1.10 that the snapshot holds no file object on descriptor 3 or above, so a later pre-import that leaves a file open is caught.
    - **The four `--wrap`ped calls are unaffected (READ).** The repopulation uses `fd_prestat_get` and `fd_prestat_dir_name`, which are not wrapped, and it runs after `pinned` is cleared.
    - **Imports and exports are unchanged in A and C (EXECUTED).** §4.4 holds.
    - **The snapshot's pre-imports are unaffected.** `zoneinfo`'s reset in `_refresh` honours `PYTHONTZPATH=""` on the snapshot (EXECUTED, finding 5). `tempfile` is not pre-imported, so `TMPDIR` is read per call (EXECUTED, `probes/p1_state.py`).

## Constitution checks

- **§4.1 zero patches:** holds. Every change is in `recipes/` or `src/`.
- **§4.3 one target:** holds.
- **§4.4 two channels:** holds. The import list is identical (EXECUTED).
- **§4.5 embedder-neutral:** holds. The defaults name no embedder.
- **§4.6 artifact set:** unchanged.
- **§4.9 tests count:** check 1.7 waits on the wall clock but asserts only the stop reason, not a time. That is acceptable, and the specification says so. No check may assert a duration.
- **§4.10 evidence:** Decision 3's "escapes by construction" is a claim that the probes disprove (finding 1). Decision 6's no-growth claim is also disproved (finding 2).
- **§5.2 no open questions:**
  - check 1.11's closer is a document that does not exist (finding 6);
  - the rest is decided.
- **§2.2 and §2.4, one preopen:** check 1.10 uses a second preopen only through the judge's driver, as a robustness check. The public API and README must not advertise it until the owner answers question 1. The specification respects that; keep it explicit.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.** Decision 4 sets `site_import = 0` and calls `site.setquit/setcopyright/sethelper`, as prototype C; it also sets `home` to `/usr/local` against the planted `pyvenv.cfg`'s `sys.prefix`, with a stated fallback if that does not hold. Check 1.2 plants all five routes and asserts no planted code runs, no marker, empty stderr and `sys.path == [<the zip>]`.
2. **Fixed.** Decision 4 sets `stdlib_dir` to the zip; Decision 7 states the review's measured −0.023% / −0.15% and promises nothing.
3. **Fixed.** Decision 3 specifies the door's bounds (`data_len`, `0x7FFFFFFF`, a wrapped body, `run()` never raises); check 1.9 uses a WAT guest against the runner; check 1.10 keeps the both-binaries case Python can reach; `guest.py`'s door gets the same bounds.
4. **Fixed.** Decision 2 states the per-call zip copy, keeps private roots out of `_placed` and `_placing`, and removes the directory in a `finally` after the `Store` is released; check 1.5 uses a monkeypatched `tempfile.tempdir` and asserts it is empty.
5. **Fixed.** "The policy, in three sentences" opens the specification; check 1.3 is renamed to name `zoneinfo`; Decision 6 lists dateutil and `mimetypes` as not protected.
6. **Fixed.** Check 1.11 (the disk gap) is dropped; disk use stays in the README's "not protected" list until a research memo names a way to enforce a quota.
7. **Fixed.** Criterion 1 is split: guards of a change seen failing; guards of existing behaviour (1.1, 1.2 on the snapshot, 1.10) named and passing on their first run.
8. **Fixed.** The Design lists `guest.py` and `wat.py`; check 1.11 says "the judge's driver, given a new `preopens=` argument"; criterion 3 names `--accept-judge`.
9. **Fixed.** `DEFAULTS` is read at call time; checks 1.6 to 1.8 lower the defaults (memory to 128 MiB, above both initial memories); the output callback returns `len(data)` for dropped bytes; paths come from `MANIFEST`; check 1.4 is renamed `test_temporary_files_go_to_tmp`.
10. **Fixed.** The zip path is built from `PY_MAJOR_VERSION`/`PY_MINOR_VERSION`; step 60 does not change; the reset sits after `pinned = 0`, before `clear_unused_stack()`.
11. **Fixed.** The Intent says `run(["-c", code])`; Decision 2 and criterion 4 state the environment change and the deadline's effect on existing callers; `Completed.truncated` goes last with a default; Decision 6's list gains the zip-damage and real-clock rows; Decision 5 names the wasi-vfs constraint.
12. Noted; the descriptor assertion is part of check 1.11 (the extra-preopens check).

## Verdict

**Not ready to build.** Decision 4 and the runner defaults are sound, and Decision 4 is now proven on the real reactor. But Decision 3, the specification's main safety claim, leaves code execution across runs open on the plain reactor through `site`, and the check meant to catch it would pass. Findings 1 and 2 are a five-line change to `init_interpreter`, which I built and ran as prototype C. Findings 3 to 6 need the decisions rewritten. After one revision, the specification should be ready.

One line: the reset works; the import-path fix is half a fix. Turn off `site`'s path work, set `stdlib_dir` to the zip, test all five planting routes, and fix the door and the rootless call's cleanup in the specification before building.

## Confirmation by the reviewer, 2026-10-17

- **Reviewed:** the revised `context/specifications/006-safe-by-default.md` (working tree, uncommitted) and the author's dispositions above. I read the whole revision, not only the changed lines.
- **Ran (EXECUTED).**
  - **Prototype D.** D is prototype C plus `PyConfig_SetString(&config, &config.home, L"/usr/local")`, which is Decision 4 exactly as revised. I built it the same way as A to C (scratch compile and link with the recorded step-60 commands, step 80's Wizer flags). Compile, link and Wizer exited 0. Nothing under `build/` was written.
  - **Probes on D.** `probes/p3_venv_315.py`, `p2_pth_315.py` and `p5_proto.py` through `wasi_python.run`, and `p7_fuel.py` through the judge's driver.
- **Read (READ).** CPython 3.15.0 `Modules/getpath.py:346-417` and `:651-656`. `Include/`: `Py_SetPath` is no longer declared in 3.15, and `getpath.c:944` takes `py_setpath` only from the global module search path that it set. `tests/unit/wat.py`, and `pyproject.toml:54-55` (`pythonpath = ["tests"]`).

### Each finding

1. **Confirmed fixed, except the `home` line, which is new finding N1.** The five routes, the marker, the empty stderr and `sys.path == [<the zip>]` are all in check 1.2. D runs none of the planted routes on either binary, and on both its `sys.path` is `['/usr/local/lib/python315.zip']` with stderr empty (EXECUTED).
2. **Confirmed fixed.** D gives `sys._stdlib_dir == '/usr/local/lib/python315.zip'` and `os.__file__ == '/usr/local/lib/python315.zip/os.py'`. numpy, pandas, a groupby, `tzdata`, `importlib.resources` and `-V` all work (EXECUTED). Decision 7 promises nothing, which is right.
3. **Confirmed fixed in design.** Two details are new findings N2 and N3.
4. **Confirmed fixed.**
5. **Confirmed fixed.** The policy sentence is clear and true for D. A small wording point: "code planted in a root never runs" holds for code the caller does not itself name. A caller that runs `run(["script.py"], root=reused)` runs whatever an earlier call left in `script.py`. Adding "unless the caller names that file to run" makes the sentence exact.
6. **Confirmed fixed.**
7. **Confirmed fixed.** The renumbering is consistent:
   - criterion 1's guards (1.1, 1.2 on the snapshot, 1.10) match the checks;
   - checks 1.9 (WAT guest, the runner) and 1.10 (both binaries, large response) are what finding 3 asked for;
   - check 1.11 is the extra-preopens check;
   - the Design's "eleven checks" counts right.
8. **Confirmed fixed.**
9. **Confirmed fixed.** Check 1.6's 128 MiB cap with a 200 MiB allocation, check 1.7's 0.2 s, and check 1.8's 4 KiB with 1 MiB written are all sound. Each lowers its default, and each asserts an outcome, never a time.
10. **Confirmed fixed.** Building the path from `PY_MAJOR_VERSION` and `PY_MINOR_VERSION` works in C11: a wide literal concatenated with narrow `Py_STRINGIFY` literals is wide.
11. **Confirmed fixed.**
12. **Confirmed, with new finding N4.**

None is reopened.

### New findings from the revision, most severe first

N1. **`home = /usr/local` does not stop a planted `pyvenv.cfg` from moving `sys.prefix`. That leaves Decision 4 holding a decision to be made at build time** (`006:146-149`). Medium.
    - **On D (EXECUTED, `probes/p3_venv_315.py`).** After a run that plants `/usr/local/bin/pyvenv.cfg`, the plain reactor's next run still has `sys.prefix == '/usr/local/bin'` (`sys.base_prefix` stays `/usr/local`). It imports nothing, runs no `.pth`, and writes nothing to stderr. The snapshot keeps `/usr/local`.
    - **Why (READ).** `home` only makes getpath skip the `home =` key inside `pyvenv.cfg` (`getpath.py:370-371`). `venv_prefix` is still set whenever the file exists (`:348-360`), and `prefix = exec_prefix = venv_prefix` overrides any configured prefix (`:651-656`). The only switch that skips venv detection is `py_setpath`, which in 3.15 comes only from `Py_SetPath`, and that is gone from the headers.
    - **What this leaves.** The fallback the revision wrote ("if `home` does not hold it, the build records the residue … and the assertion is dropped") is now decided by evidence. Leaving it conditional would be a decision deferred to the build (§5.2).
    - **Fix.**
      - Drop `home` from Decision 4. It does nothing, and the smallest thing wins (§6.4).
      - Drop the `sys.prefix` assertion from check 1.2.
      - State the residue as a fact: on the plain reactor, a `pyvenv.cfg` planted in a reused root sets `sys.prefix` and `sys.exec_prefix` to `/usr/local/bin`. No code runs from it, and imports are unaffected.
      - Add it to Decision 6's "data planted in a reused root" list.
      - Check 1.2 can assert the stronger, true things that D shows: the marker is absent, stderr is empty, and `sys.path == [<the zip>]`.
    - **Fuel, for Decision 7.** D's `-c pass` is 124,131,393 on the snapshot (−0.038% against the 3.15 build) and 246,243,110 on the plain reactor (−0.23%). So `home` changes the figures slightly, and without it C's figures stand.

N2. **Check 1.9's "a host response of 2 GiB or more" would make the judge allocate at least 2 GiB, and the runner would then copy it** (`006:69-71`, `006:129-133`). Low-medium.
    - The runner does `bytes(response)` before anything else (READ, `runner.py`, `_door`). So a 2 GiB response costs 2 to 4 GiB of the judge's own memory, which is a real risk on a CI runner with 7 GB.
    - **Fix.**
      - Put the bound in a module constant (`runner.MAX_RESPONSE = 0x7FFFFFFF`). Have the door check `len(response)` before copying.
      - The check lowers the constant with `monkeypatch`, as it does `DEFAULTS`, and returns a response one byte over.
      - A unit test can cover the arithmetic at the true bound with a fake length. A `memoryview` over an `mmap` of a sparse file also works on POSIX, but it is not portable.

N3. **The "wrapped body" must not swallow wasmtime's own traps** (`006:131-133`). Low.
    - `alloc(caller, n)` re-enters the guest. A deadline or out-of-fuel during `host_alloc` raises `wt.Trap` inside the door.
    - If the wrapper catches it and answers −2, the guest goes on, and the call ends later with a less clear stop reason. INFERRED: an expired epoch or empty fuel traps again at the next check.
    - **Fix.** The wrapper catches `Exception` but re-raises `wasmtime.Trap` and `wasmtime.WasmtimeError`. Then wasmtime-py's trampoline carries the original trap out (READ, `_func.py:212-250`), and `run()` reports `"deadline"` or `"out of fuel"` as usual.

N4. **Check 1.11's descriptor assertion is vacuous on the snapshot as worded** (`006:76-80`). Low-medium.
    - `wizer.initialize` ends with `gc.freeze()`, and `gc.get_objects()` does not list frozen objects.
    - On the snapshot, a plain scan found no file objects at all, not even stdio. After `gc.unfreeze()`, it found the nine stdio objects on descriptors 0 to 2 (EXECUTED, `probes/p4_fds.py`, 3.14 and 3.15).
    - **Fix.** The check calls `gc.unfreeze()` before scanning. It also asserts that it found the stdio objects, so an empty scan can never pass.

N5. **One choice is still open in the Design** (`006:179`). Low.
    - The Design says "`recipes/reactor_bootstrap.py` … (or in `init_interpreter`)".
    - **Fix.** Pick one. `init_interpreter` is what prototypes C and D ran (EXECUTED). It keeps the `site` calls next to `site_import = 0`, and it leaves the frozen bootstrap unchanged.

N6. **Say how check 1.9 runs a WAT guest through `run()`** (`006:69-71`). Low.
    - `run()` takes its binary from `artifacts=`, and it places the zip named by `MANIFEST`'s `python` line.
    - So the check passes `Artifacts(snapshot=<the WAT module>, plain=…, stdlib_zip=<the real zip>, manifest=<the real MANIFEST>)`. The WAT module exports `memory`, `host_alloc` and `run`.
    - `wat.py` sits in `tests/unit/`, and `pyproject.toml` puts only `tests/` on the path. A check imports it as `from unit import wat`, or the helper moves to `tests/harness/`. Name which.

### Constitution, after the revision

- §4.1, §4.3, §4.4, §4.5 and §4.6 hold. D's imports and exports are the same as A's and C's, and the 43 imports are unchanged.
- §4.9 holds. Checks 1.6 to 1.8 assert outcomes, never durations.
- §4.10 holds for the specification's numbers, which all cite this review's executed runs.
- §5.2 holds once N1 replaces the `home` conditional with the measured fact and N5 picks one place.
- §7: nothing tripped.

### Verdict after the revision

**Ready to build once N1 and N4 are corrected in the text.** Every original finding is fixed or answered, and none is reopened.
- **N1.** The one line of design that does nothing (`home`) goes, and its conditional becomes a stated fact. I measured it on prototype D.
- **N4.** Without `gc.unfreeze()`, a check assertion would always pass.
- **N2, N3, N5 and N6.** One-line text changes that can go in at the same time.

None of these changes the design.

One line: the revision answers all twelve findings. Drop `home`, which does not hold `sys.prefix`, and unfreeze the collector before the descriptor scan, and the specification can be built.

## The author's answers to the confirmation

- **N1:** fixed. Decision 4 does not set `home`, says why (prototype D), and lists the moved `sys.prefix` as reused-root data in Decision 6; check 1.2 does not assert `sys.prefix`.
- **N2:** fixed. `MAX_RESPONSE` is a module constant checked before the copy; check 1.9 lowers it.
- **N3:** fixed. Decision 3 re-raises wasmtime's `Trap` and `WasmtimeError`.
- **N4:** fixed. Check 1.11 calls `gc.unfreeze()` and asserts the stdio objects were found.
- **N5:** fixed. The helpers are called in `init_interpreter`.
- **N6:** fixed. Check 1.9 runs the WAT guest through `run(artifacts=…)`; `wat.py` moves to `tests/harness/`.
