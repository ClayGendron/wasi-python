# 006 — Safe by default: the hostile guest, judged

- **Status:** draft, 2026-10-17; revised the same day to answer its review
  (`../reviews/006-safe-by-default-spec-2026-10-17.md`). It changes the guest (`recipes/`), the
  runner (`src/`) and the judge, so it is reviewed again before it is built.
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the reactor (`recipes/reactor_main.c`),
  judge additions in `tests/` (checks, `tests/harness/guest.py`, `tests/harness/wat.py`),
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 005 (the 3.15 line; this builds on it).
- **Research it stands on:** `../research/2026-10-16-a-principal-engineers-direction.md`
  (the threat model, section 2, and directions 1 and 2),
  `../research/2026-10-16-what-data-folders-the-packages-need.md` (the planted module, the
  planted zone file, temp files in the root), `../research/2026-10-16-where-package-data-lives.md`
  (finding 2: the snapshot's frozen preopen table, and the reset that fixes it), and the
  review's prototypes A, B and C (EXECUTED, its scratch folder `review-006/`).
- **The owner's direction** (2026-10-16): the main users run AI-generated code; the runtime
  must have "no way (unless explicitly provided) to access the host file system or network".
  The new hard constraint "safe by default" is the owner's to add to the constitution
  (`../questions-for-the-owner.md`, question 3). This specification does not need it: it
  makes the runner's defaults safe under the constitution as it stands.

## The policy, in three sentences

Code planted in a root never runs in a later call, on either binary. Data planted in a root
that a caller reuses is read by later calls (dateutil's zones, `mimetypes`' tables, any user
file); only a fresh root closes that, and a call without `root` gets a fresh one. A call that
names no limit still has one for memory, time and output.

## Decisions

1. **The hostile guest is judged under v1.2** ("sealed"), in a new file,
   `tests/checks/test_v1_2_hostile_guest.py`, so no goal is added to the constitution. Each
   row of the principal engineer's threat model that the runtime can enforce gets a check.
   Checks that guard a change are written first and seen failing; checks that guard
   behaviour that already holds are named as such and pass on their first run. Paths that
   name the version (`python3.X`, `python3XY.zip`) come from `MANIFEST`'s `python` line. The
   checks:
   1. `test_a_link_out_of_the_root_is_refused` (both binaries, through the runner; a guard of
      existing behaviour): a symbolic link with an absolute host target, and a relative one
      that climbs out, are refused at creation or on open; nothing outside the root is read or
      written.
   2. `test_planted_code_never_runs` (both binaries; a guard of a change on the plain reactor,
      of existing behaviour on the snapshot): run 1 plants every route the review found:
      a module in `usr/local/lib/python3.X/`, one in its `lib-dynload/`, one in its
      `site-packages/`, a `site-packages/zz.pth` whose line would write a marker file, and a
      `usr/local/bin/pyvenv.cfg` with its own `lib/python3.X/site-packages/` holding a module
      and a `.pth`. Run 2 on the same root asserts: no planted module imports, the marker file
      is absent, stderr is empty, and `sys.path == [<the zip>]`. It does not assert
      `sys.prefix`: a planted `pyvenv.cfg` still moves the plain reactor's `sys.prefix` to
      `/usr/local/bin` (Decision 4), which is data, not code.
   3. `test_a_planted_zone_file_leaves_zoneinfo_alone` (the runner's defaults; a guard of a
      change): a file planted at `/usr/share/zoneinfo/America/New_York` in the root does not
      change `zoneinfo.ZoneInfo("America/New_York")`'s offset.
   4. `test_temporary_files_go_to_tmp` (the runner's defaults; a guard of a change):
      `tempfile.gettempdir()` is `/tmp`, and `mkstemp` writes there, not at `/`.
   5. `test_a_call_without_a_root_shares_nothing` (a guard of a change): with
      `tempfile.tempdir` pointed at a scratch directory by `monkeypatch`, two calls with no
      `root` see different roots holding only the runtime's own files, a file the first writes
      is absent in the second, and the scratch directory is empty after each call.
   6. `test_memory_has_a_default_cap` (a guard of a change): with no `memory_bytes`, the check
      lowers `DEFAULTS.memory_bytes` to 128 MiB (above the snapshot's initial 56.4 MiB and the
      plain reactor's 40 MiB) and allocating 200 MiB raises `MemoryError` in the guest.
   7. `test_a_run_has_a_default_deadline` (a guard of a change): with no `deadline_s`, the check
      lowers `DEFAULTS.deadline_s` to 0.2 s and a `while True: pass` ends with
      `trapped == "deadline"`. It asserts only that outcome, never a time.
   8. `test_output_has_a_default_cap` (a guard of a change): with no `output_bytes`, the check
      lowers `DEFAULTS.output_bytes` to 4 KiB; a guest writing 1 MiB to stdout and then
      printing to stderr gets exactly 4 KiB of stdout back, its stderr in full, exit code 0,
      and `Completed.truncated == ("stdout",)`.
   9. `test_the_door_bounds_every_frame` (the runner, with a small WAT guest from
      `tests/unit/wat.py` that imports `host::call`; a guard of a change): a request whose
      pointer and length run past guest memory is answered −2 and the host function is never
      called; a host response of 2 GiB or more is answered −2; a host that raises is answered
      −2; in each case `run()` returns a `Completed` and the next call works. The check lowers
      `runner.MAX_RESPONSE` with `monkeypatch` rather than make a 2 GiB response. It runs the
      WAT guest through `run(artifacts=…)`, an `Artifacts` whose snapshot is the WAT module
      (exporting `memory`, `host_alloc` and `run`) beside the real zip and `MANIFEST`. The WAT
      helper moves from `tests/unit/wat.py` to `tests/harness/wat.py`, so checks and unit tests
      import it alike.
   10. `test_a_large_response_is_a_host_fault` (both binaries, through the runner under a
       `memory_bytes` cap; a guard of existing behaviour): a host response larger than the
       guest's free memory makes `_host.call` raise `OSError` (−2), and the program goes on.
   11. `test_extra_preopens_work_on_the_snapshot` (the judge's driver, given a new `preopens=`
       argument; a guard of a change): the snapshot is given a second, read-only preopen at
       `/data`, in both orders; it reads the real data and the root's own file, and a write to
       `/data` is refused, as on the plain reactor. It also calls `gc.unfreeze()`, scans
       `gc.get_objects()` for file objects, asserts that it found the three stdio objects (so an
       empty scan cannot pass), and that none is on a descriptor of 3 or above, so a later
       pre-import that leaves a file open is caught.

2. **The runner's defaults.** `run()` keeps its names, and these change:
   - `root` becomes optional. Without it, the runner makes a fresh private directory (mode
     `0700`, under `tempfile.gettempdir()`), places the stdlib zip in it (a full copy, 11.1 MB
     on 3.15, as today: the runner copies and never links), runs the program, and removes the
     directory in a `finally`, after the `Store` that holds its preopen is released. Such a
     private root is never recorded in the runner's placement caches (`_placed`, `_placing`),
     so a long-running process does not grow them. A caller who passes `root` grants that
     directory, as today.
   - `memory_bytes` defaults to 1 GiB; `None` passed explicitly means no cap beyond wasm32's
     4 GiB. A one-million-row pandas groupby runs under 256 MiB (the review, EXECUTED).
   - `deadline_s` defaults to 60 s; `None` passed explicitly means no deadline. An epoch
     deadline costs nothing per instruction, unlike fuel, so fuel stays opt-in for exact
     counting. This changes existing callers: a job longer than 60 s now ends with
     `trapped == "deadline"` unless it passes `deadline_s=None` or a larger value.
   - a new `output_bytes`, default 16 MiB per stream; `None` means no cap. Bytes past the cap
     are dropped, never buffered; the output callback still returns `len(data)` for them, so the
     guest's `write` succeeds and does not retry (wasmtime-py takes the return value as the
     count written). The stream's name is added to `Completed.truncated`, a new last field
     with a default of `()`, so positional construction keeps working.
   - the environment: the runner creates `/tmp` in the root and starts from
     `{"TMPDIR": "/tmp", "HOME": "/tmp", "PYTHONTZPATH": ""}`; the caller's `env` is laid over
     it. The three can be overridden but not removed; the README and the CHANGELOG say so, since
     `os.environ` no longer holds exactly what `env=` gave.

   The three numbers live in `wasi_python.runner.DEFAULTS`, a frozen dataclass that `run()`
   reads at call time (so `monkeypatch` reaches it). "Not given" is a private sentinel, so
   `None` keeps meaning "no limit" for a caller who opts out on purpose.

3. **The door bounds every frame.** The runner's door checks `ptr + length` against the
   memory's `data_len` before reading, requires the response to be at most `MAX_RESPONSE`
   (a module constant, `0x7FFFFFFF`) bytes, checked before the response is copied, and to fit
   what `host_alloc` returned, and answers −2 otherwise. Its body is wrapped so that no Python
   exception from the frame or the host leaves it; wasmtime's own `Trap` and `WasmtimeError`
   (a deadline or fuel running out inside `host_alloc`) are re-raised, so they end the run as
   they do anywhere else. `run()` returns a `Completed` and never raises for anything a guest
   frame or a host function does. The judge's own door in `guest.py` gets the
   same bounds, so the judge does not differ from the runner here.

4. **Only the zip is on the guest's import path, and `site` does not run.** In
   `init_interpreter` (`recipes/reactor_main.c`), for both binaries:
   - `module_search_paths` is the one stdlib zip and `module_search_paths_set = 1`;
   - `stdlib_dir` is the same zip, so frozen modules keep `__file__`
     (`os.__file__ == "/usr/local/lib/python315.zip/os.py"`, as every zipped module's reads);
   - `site_import = 0`, and then `site.setquit()`, `site.setcopyright()` and
     `site.sethelper()` are called, so `exit`, `quit`, `help`, `copyright`, `credits` and
     `license` exist as in native Python. `sys.flags.no_site` becomes 1; the README's platform
     notes say so;
   - `home` is not set: it does not stop a planted `pyvenv.cfg` from moving the plain
     reactor's `sys.prefix` to `/usr/local/bin` (the review's prototype D, EXECUTED; getpath
     lets a venv's prefix override a configured one, and `Py_SetPath`, the one way around it, is
     gone in 3.15). No code runs from it, because `site` does not run and the import path is
     fixed; the moved `sys.prefix` is listed as reused-root data in Decision 6.

   The zip's path is built in C from `PY_MAJOR_VERSION` and `PY_MINOR_VERSION`, so it cannot
   disagree with the interpreter it is compiled into, and step 60 does not change. The review's
   prototype C, which is this decision, gave `sys.path ==
   ['/usr/local/lib/python315.zip']` on both binaries and ran none of the planted routes
   (EXECUTED).

5. **The snapshot honours the runtime's preopens.** `wizer.initialize` calls
   `__wasilibc_reset_preopens()` after `pinned = 0` and before `clear_unused_stack()`, so the
   reset's own stack residue is cleared. wasi-libc documents it for this use; wasi-sdk 33's
   `wasi/libc.h` declares it (READ). The table is rebuilt from the runtime's preopens by name,
   in any order, on first use (the review, EXECUTED on the 3.15 reactor). No new import:
   `fd_prestat_get` and `fd_prestat_dir_name` are already among the 42 and are not among the
   four wrapped calls. If wasi-vfs (option C3 of the package-data memo) is ever adopted, this
   decision is revisited: wasi-vfs registers its packed directories as preopens at start-up,
   and a reset would drop them.

6. **The README says what is protected, and what is not.** A section "Safety" states the policy
   above, lists what the wall enforces (the threat model's EXECUTED rows), the defaults of
   Decision 2, and what is not protected: disk use in a granted root; data planted in a reused
   root (dateutil's zones, `mimetypes`, any user file, and the plain reactor's `sys.prefix` after
   a planted `pyvenv.cfg`); a program damaging its own stdlib zip
   during its own run; timing; the real clock and entropy; the one-byte exit status. A disk
   quota is out of scope here; it gets no check until a research memo names how one could be
   enforced.

7. **Measured, not promised.** The review measured prototype C's `-c pass` at −0.023% on the
   snapshot and −0.15% on the plain reactor against the 3.15 build. The landing notes record
   the built figures; any growth past the 0.01% tolerance gets its cause there.

## Intent

A framework author who calls `run(["-c", code])` with nothing else gets a sandbox that cannot
reach the host's files, cannot run forever, cannot exhaust the host's memory through the guest
or its output, cannot crash the host through the door, and shares nothing with the next call.
A caller who passes `root` knows that data, never code, carries over between calls on it. Every
one of those claims is a check.

## Design

```
src/wasi_python/runner.py              DEFAULTS, optional root, output cap, Completed.truncated,
                                       base env, a bounded door, private roots kept out of caches
recipes/reactor_main.c                 search path, stdlib_dir, site_import, and the three site
                                       helpers in init_interpreter; __wasilibc_reset_preopens()
tests/checks/test_v1_2_hostile_guest.py   the eleven checks
tests/harness/guest.py                 preopens=; the door's bounds
tests/harness/wat.py                   moved from tests/unit/; a door-probing guest
README.md, CHANGELOG.md                "Safety"; the behaviour changes for existing callers
```

## Scope

In: the above. Out: typed grants (read-only and writable mounts, `files=` in and outputs out),
a disk quota, deterministic replay, and anything that changes the constitution; they wait on
the owner (`../questions-for-the-owner.md`) or on their own specifications.

## Acceptance criteria

1. The checks of Decision 1 that guard a change were seen failing before their fix; the guards
   of existing behaviour (1.1, 1.2 on the snapshot, 1.10) passed on their first run. The
   landing notes list the first run's results, check by check.
2. Steps 60 to 90 rebuild from the 005 build; run twice they give the same reactor, snapshot
   and zip.
3. `uv run pytest` is green; the run that records the state uses `--accept-judge` (the checks
   and the driver changed), the ratchet loses no pass, and any grown metric has its cause in
   the landing notes.
4. The README's "Safety" section states the policy, each default, and each unprotected channel;
   the CHANGELOG states the changes for existing callers (the deadline, the environment, the
   optional root, `Completed.truncated`, `sys.flags.no_site`).

## Landing notes

(Filled in on landing.)
