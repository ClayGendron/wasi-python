# 162: A session's state is a snapshot

- **Status:** **built 2026-10-30** on `spec/162-a-sessions-state-is-a-snapshot`, rebased onto `a1acec5c` (159's merge), before its pull request and review; its rows pass on a local build of the set (both binaries export `checkpoint`), and Decision 12's results-mode row waits on 163. Before: drafted 2026-10-30 and reviewed before it was built (structural; the public API; the guest's exports and the build recipe). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3"). Amended the same day against its pre-build review, `../reviews/162-a-sessions-state-is-a-snapshot-spec-2026-10-30.md`, every finding taken; its Disposition says where.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **structural** (a public method, a session step, the file's header) and **build-class** (a new export; constitution §5.6). `src/`: `runner.py`, `_sessions.py`, `_snapshot.py`, `_snapshot_make.py`. Recipe: `reactor_main.c`, `reactor_bootstrap.py`, `60_link.sh`; both binaries change, the zip does not. Judge: `tests/public_api.txt`, `tests/harness/artifacts.py`, `tests/harness/guest.py`, a new `tests/checks/test_v1_4_checkpoint.py` and its cap in `tests/lint/budget.toml`.
- **Depends on:** landed 055, 073, 150 and 157. Siblings: 163 and 164 edit `reactor_bootstrap.py`'s `turn` and `_setup`, and 164 edits `_drive_turn` and the export lists; whichever lands second rebases and carries Decision 5's results-mode row. 168 lands first; only the copy-on-write restore needs it (Decision 10).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§2, item A). `../research/2026-10-27-a-starting-image-measured.md` (§1.1, §1.5, §2.1, §2.2). `../research/2026-10-27-a-snapshot-the-embedder-chooses.md` (§3).

Labels: READ means read from a file, cited; INFERRED means reasoned.

## The problem

Both public comparisons of WASI Python say "no snapshotting" (the memo, §1). 0.1.2's `prepare` refuses an instance that ran a turn (`recipes/reactor_main.c:663`), so the owner's notebook replays every cell to fork. A memory read after a turn is not yet an image (READ): its C flags say a turn ran (`reactor_main.c:150-153`), so a restore skips `_setup` (`reactor_bootstrap.py:261-288`); its preopen table, monotonic times, import path and open numbers are the old store's (the spike, §2.1, §2.2).

## Decisions

### 1. The shape: `Session.checkpoint() -> Snapshot`

```python
with Session() as s:
    s.run("import pandas as pd; df = pd.DataFrame({'x': [1, 2, 3]})")
    cp = s.checkpoint()
with Session(snapshot=cp) as a, Session(snapshot=cp) as b:
    a.run("df['y'] = df.x * 2")     # b never sees it
done = run(["-c", "print(df)"], snapshot=cp)
```

`snapshot=` already takes any `Snapshot` (READ: `_snapshot.py:423-439`; `runner.py:860`): restore and fork need no new argument.

### 2. One export, called twice

The reactor gains `int checkpoint(int32_t enter)`, C only. `enter == 1` records the monotonic floor (Decision 4), calls `clear_unused_stack()`, sets a new static `checkpointing` and returns 0; the host reads linear memory; `enter == 0` clears it. `enter == 1` refuses (-1) unless `turned` and a static set only by `wizer.initialize` (the snapshot binary) hold, and while `in_turn`, `shut`, `preparing`, `run_called` or `checkpointing` is set; `enter == 0` refuses unless `checkpointing`, and `shutdown` and `prepare` refuse while it is. The image holds `checkpointing == 1`; the live instance, 0 and otherwise unchanged.

`Session.checkpoint` claims the session and calls `_session_turn(..., export="checkpoint")`, as `Session._prepare` does (`runner.py:1121-1132`). `_drive_turn` (`_sessions.py:746`) takes its own branch: both calls, the read in a `try` whose `finally` calls `checkpoint(0)`, then `state.captured`. A `MemoryError` from the read is raised once `checkpoint(0)` returned 0, and the session goes on; a trap or -1 ends it. The lifetime bounds it. `SESSION_EXPORTS` stays `("turn", "shutdown")`; `checkpoint` is looked up in `state.exports`. No new phase or event.

### 3. The resume, in the restored instance

`run` and `turn` begin with `resume_if_restored()`: `checkpointing` set means a restore. It:

1. clears `checkpointing`, sets the clock's offset (Decision 4) and calls `__wasilibc_reset_preopens()`;
2. sets `turned` and `session_set_up` to 0, so `run` runs and a first turn runs `_setup` with the start's argv and environment, reseeding (157, Decision 6);
3. sets `prepared`, taking `end_function` if unset, so the call ends through `_end` (157, Decision 5, A);
4. calls `_reactor._resume()`, new: `sys.path` back to `_BASE_PATH` (kept at the bootstrap's import), the other `path_importer_cache` keys dropped; `_image_main`, `_MAIN_NAMES` and `_image_underscore` from the checkpoint's `__main__`; `_prepared = True`; `gc.freeze()`.

It runs under the start's fuel and deadline. If `_resume` raises, `run` returns 70 and `turn` -1.

### 4. The monotonic clock never runs backwards

`enter == 1` records `floor = monotonic + offset`. The resume sets `offset = floor - monotonic` when positive, else 0. The clock wrapper (`reactor_main.c:90`) adds `offset` to each unpinned monotonic read. A new wrapper of `__wasi_poll_oneoff` subtracts it from each absolute monotonic subscription, on a copy, saturating at 0, so a deadline already past returns at once (`time.sleep` waits for an absolute deadline: INFERRED). With `offset == 0` each costs one comparison.

### 5. What an image carries, and what it cannot

- **An open file or folder** (`_Files.open_now()`, `_fs_table.py:136`) is refused before the export; the session goes on. The host cannot close it, since the guest's object names the number (`sqlite3`, `logging.FileHandler`).
- **Mount staging** stays the host's (`_fs_table.py:174`). **A tool call in flight** cannot exist: the checkpoint claims the session. A guest that imported `host.tools` keeps the old list (`recipes/guest/host/tools.py:361`); the start's host judges each call by its own tools, so a missing name answers `unknown_tool`.
- **Files on disk** are not memory. HOME keeps the session's guest path, with a fresh private folder there.
- **Grants, environment, import path and tools** are the start's own, read at its first export (but see Decision 9).
- **The results mode** (163) is the start's: `_setup` reads `-Xhost-results` and sets the mode either way. Without it, it clears the mode, unbinds `builtins.display` when it is the bootstrap's, and puts back the matplotlib backend the bootstrap chose.
- **Randomness.** Each start reseeds the generators `_refresh` names, even after the session's own seed: seed again in the first turn for a reproducible fork. A generator held in a name (`np.random.default_rng()`, a `random.Random()`) and every value drawn before the checkpoint are the same in every start.
- **Also carried:** a turn's `os.chdir`; `atexit` handlers, run at every start's end; unflushed bytes in another writer on descriptor 1 or 2, flushed by every start; cyclic garbage, frozen by the resume. A checkpoint is not reproducible, so `image_sha256` names it and does not predict it.

### 6. Refusals

In order: a forked process, `RuntimeError`; the plain binary, `ValueError`; a set without the export, `ArtifactsMissing`; an ended session, `SessionEnded`; a running turn, `RuntimeError`; no turn returned yet (`_Guest.SOUND`), `RuntimeError`; a file open, `SnapshotFailed("open file")`; a trap, `SnapshotFailed("trapped")`, and a -1, the lost-track `RuntimeError` (`_sessions.py:848`), both ending the session.

`SnapshotFailed.completed` becomes `Completed | None`, `None` when no export ran. Its docstring names `Session.checkpoint`, and the news file's `### Upgrading` says "`SnapshotFailed.completed` may be `None` when no code ran".

### 7. The origin, and fuel

`SnapshotOrigin` gains `kind: str = "prelude"` (or `"checkpoint"`) and `parent_sha256: str | None = None` (the image the session started from). The reader refuses any other `kind`, and a `parent_sha256` that is neither null nor 64 lowercase hex digits. A checkpoint's `prelude` is `""` and `prelude_fuel` `None` (each turn's `Completed` reported its fuel); `guest_paths` and `env_names` are the session's; `home` is its HOME path, and the reader accepts `IMAGE_HOME` or `/tmp/.home-` and 32 hex digits (`_call.py:312`), nothing else. Missing fields take their defaults, so the file stays format 1; the set check refuses it in 0.1.2 anyway. `repr` reads `<Snapshot checkpoint, 210.3 MiB, made …>`. `snapshots_made` counts checkpoints. The two calls cost a few hundred C instructions, reported nowhere; a start's `fuel_used` is its own, the resume included.

### 8. The set

The origin names `state.set_digests`. `_snapshot._same_set` (`_snapshot.py:447`), which today leaves a passed set undigested, gains `session: bool`: a session on the snapshot binary with a set passed digests its binary and zip at the opening, about 0.1 s each time (INFERRED from the spike's 94 ms for 203 MiB), and the digests key the module cache. A start on another set raises `SnapshotMismatch` (150, Decision 9).

### 9. Trust

A checkpoint carries the trust of every turn before it, and of its parent image. A turn can hook `builtins`, an import or an `atexit` handler, and every start runs the hook with its own grants, tools and environment.

A checkpoint also carries every byte the session's memory holds, live or freed: what it read from its grants, mounts and tools, and its environment's values, whatever a start replaces. Every start, and whoever holds the saved file, can read them (numpy reads any address through `__array_interface__`: INFERRED). A start's grants bound what it reads from then on, not what the image holds. Start a checkpoint only where its code may read everything the session read. Both pages say so.

### 10. The copy-on-write restore is its own specification

The spike's mapping (0.76 ms against 21 ms, §1.5, macOS only) replaces pages wasmtime owns. It becomes a platform method after 168, with a Linux measurement and its own review. 162 keeps the copy in `_snapshot._restore`.

### 11. Structure, row by row

R1: one method, two fields, a widened attribute, in `tests/public_api.txt`. R2: refusals precede the export; Decision 9 states what a fork reads. R3: public `Memory` API only. R4: no module-level mutable, lock or host flag. R5: no platform branch. R6: no seam. R7: no function past 80 lines; `_turn_inside` gains no line. R8: `origin.kind` and `parent_sha256`.

### 12. The rows first

Guest rows, `tests/checks/test_v1_4_prepare.py`, by the judge's driver: `checkpoint(1)` refuses before a turn, after `run`, on the plain reactor and twice; `checkpoint(0)` refuses unless entered; `shutdown` refuses while entered; a restore's `run` and `turn` run.

Goal rows, `tests/checks/test_v1_4_checkpoint.py`, each recording `fuel_used`:

- names, a frame and a fitted model return through `Session(snapshot=cp)` and `run(snapshot=cp)`; two forks and the live session never see each other;
- after `random.seed(1)` and `os.environ['K'] = '1'`, the live session's next draw and `K` are unchanged by a checkpoint; two forks' `random.random()` differ, and a `default_rng()` held in a name draws the same in both;
- an open file is refused with `completed is None`, and after `close()` the session checkpoints;
- a fork granted writing at the session's `import_path` cannot import a planted module;
- after a turn that slept 2 s, a fork's `time.monotonic()` is not below it, and `time.sleep(0.01)` ends under `deadline_s=1`;
- a checkpoint of a fork holds both turns, its `parent_sha256` the first's; saved and loaded, it restores;
- a turn's hook on `builtins.print` runs in every fork; a tool the fork lacks answers `unknown_tool`;
- once 163 has landed: a results session's checkpoint, started without `results=`, prints its value and sends no frame; started with it, returns `value`;
- Decision 6's refusals.

Unit rows, `tests/unit/test_snapshot.py`: a header without the new fields loads as a prelude; a session-shaped `home` loads and `/` is refused; a bad `kind` or `parent_sha256` is refused; the checkpoint `repr`.

### 13. The documentation

`docs/how-to/snapshots.md` gains "Checkpoint a session, and fork it" (what carries, open files, randomness, and that a fork reads everything the session read), replacing line 126; `docs/how-to/sessions.md`, a sentence under "Keep trust levels apart"; `docs/reference/`'s errors, limits, glossary and API pages.

## Intent

An embedder calls `checkpoint()` after a few turns and starts any number of sealed sessions or calls from that state; the session goes on unchanged.

## Design

In order: the rows, seen failing; the recipe; the host, with the guest paths shared with `_snapshot_make._made_in`; the judge's lists; the documentation; the news file.

## Scope

In: the decisions above. Out: the copy-on-write restore (Decision 10); `checkpoint_async` (`asyncio.to_thread` serves); a checkpoint of a `run`.

## Acceptance criteria

1. **Seen failing first**: each row of Decision 12, named in the pull request. READ.
2. **The rows** are green on three systems, labelled `ci:full`. EXECUTED.
3. **The contract**: `tests/public_api.txt` gains the method and two fields, claimed. READ.
4. **The structure**: `tests/checks/test_rules.py` is green; no `LONG_FUNCTIONS` entry rises. EXECUTED.
5. **The artifact set**: both binaries export `checkpoint` as `(i32) -> (i32)`; moved fuel and bytes are claimed. READ.
6. **The documentation** is in place; `uv run pytest tests/lint` is green. EXECUTED.
7. **The run**: `ci-status` green, no pass lost, both reviews cited. READ.

## Landing notes

To be written at the landing.

## For the owner to decide

1. **The copy-on-write restore**: its own specification after 168, in 0.1.3 if time allows (recommended); or inside 162, waiting on a Linux measurement.
2. **An open file at a checkpoint**: refused (recommended); or closed with a warning, which leaves the guest's object naming a number a later open reuses.
