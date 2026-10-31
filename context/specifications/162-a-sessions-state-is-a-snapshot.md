# 162: A session's state is a snapshot

- **Status:** drafted 2026-10-30, to be reviewed before it is built (structural; the public API; the guest's exports and the build recipe). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **structural** (a public method, a step in a session's life, the file's header) and **build-class** (a new export; constitution §5.6). `src/`: `runner.py`, `_sessions.py`, `_snapshot.py`, `_snapshot_make.py`. Recipe: `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `scripts/steps/60_link.sh`. Both binaries, `MANIFEST` and `SHA256SUMS` change; the zip does not. Judge: `tests/public_api.txt`, `tests/harness/artifacts.py`, `tests/harness/guest.py`, a new `tests/checks/test_v1_4_checkpoint.py` and its cap in `tests/lint/budget.toml`.
- **Depends on:** landed 055 (sessions), 073 (an open file keeps its bytes), 150 and 157 (the image, `prepare`, `_end`, the restore). Siblings: 163 and 164 edit `reactor_bootstrap.py`'s `turn` and `_setup`, and 164 edits `_drive_turn` and the export lists; whichever lands second rebases. 168 is needed only by the copy-on-write restore (Decision 10).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§1, item 1; §2, item A). `../research/2026-10-27-a-starting-image-measured.md` (§1.1, memory is the whole state; §1.5, the copy and copy-on-write; §2.1, a descriptor left open; §2.2, the preopen table). `../research/2026-10-27-a-snapshot-the-embedder-chooses.md` (§3).

Labels: READ means read from a file, cited; INFERRED means reasoned.

## The problem

Both public comparisons of WASI Python say "no snapshotting" (the memo, §1). 0.1.2's image is made before any program runs: `prepare` refuses an instance that ran a turn (`recipes/reactor_main.c:663`), and `docs/how-to/snapshots.md:126` says a snapshot of a guest's run is not offered. The owner's notebook replays every cell to fork.

A session's memory read after a turn is not yet an image (READ). The C side records that a turn ran (`turned`, `session_set_up`, `reactor_main.c:150-153`), so a restored `run` refuses and a restored session skips `_setup` (`reactor_bootstrap.py:261-288`). The preopen table is the old store's (the spike, §2.2). Stored monotonic times lie in a new store's future. The old import path stays on `sys.path`. A file left open names a number the fork's next open reuses (§2.1).

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

Restore and fork need no new argument: `snapshot=` already takes any `Snapshot` on all three entry points (READ: `_snapshot._start`, `src/wasi_python/_snapshot.py:423-439`; `runner.py:860`). A checkpoint saves, loads and checks as any snapshot.

### 2. One export, called twice

The reactor gains `int checkpoint(int32_t enter)`, C only, running no Python. `enter == 1` records the monotonic floor (Decision 4), sets a new static `checkpointing` and returns 0; the host reads linear memory; `enter == 0` clears it. `enter == 1` refuses (-1) unless `initialized && turned`, and when any of `in_turn`, `shut`, `preparing`, `run_called` or `checkpointing` is set; `enter == 0` refuses unless `checkpointing`. While it is set, `shutdown` and `prepare` refuse.

So the image holds `checkpointing == 1` and the live instance 0, and nothing else of the live instance changes.

`Session.checkpoint` claims the session and calls `_sessions._session_turn(..., export="checkpoint")`, as `Session._prepare` does (`runner.py:1121-1132`). `_drive_turn` (`_sessions.py:746`) makes both calls, the read between them, and sets `state.captured`. A trap ends the session as a turn's does; a -1 ends it as an error (`_sessions.py:848`). No new phase or event.

### 3. The resume, in the restored instance

`run` and `turn` begin with `resume_if_restored()`. `checkpointing` set means a restore, since the live instance clears it before any other export. The resume:

1. clears `checkpointing`, sets the clock's offset (Decision 4) and calls `__wasilibc_reset_preopens()`, so the start's grants work in any order and number;
2. sets `turned` and `session_set_up` to 0, so `run` runs and a session's first turn runs `_setup` with the start's argv and environment, reseeding as every start from a snapshot does (157, Decision 6);
3. sets `prepared`, taking `end_function` if unset, so the call ends through `_end` (157, Decision 5, choice A);
4. calls `_reactor._resume()`, new: `sys.path` back to `_BASE_PATH` (kept at the bootstrap's import) with the other `path_importer_cache` keys dropped, as `prepare` does; `_image_main`, `_MAIN_NAMES` and `_image_underscore` from the checkpoint's `__main__`; `_prepared = True`; `gc.freeze()`.

So a start from a checkpoint is a start from an image whose code was the turns. The resume runs inside its first export, under its fuel and deadline. If `_resume` raises, `run` returns 70 and `turn` -1.

### 4. The monotonic clock never runs backwards

`enter == 1` records `floor = monotonic + offset`. The resume sets `offset = floor - monotonic` when that is positive, else 0. The clock wrapper (`reactor_main.c:90`) adds `offset` to each unpinned monotonic read. A new wrapper of `__wasi_poll_oneoff` subtracts it from each absolute monotonic subscription, on a copy, since `time.sleep` waits for an absolute deadline (INFERRED). With `offset == 0` each costs one comparison.

### 5. What an image cannot carry

- **An open file or folder** (`_Files.open_now()`, `_fs_table.py:136`, wasmtime's numbers and mount files alike) is refused before the export, and the session goes on. The host cannot close it, since the guest's object still names the number. The page names the common cases: an `sqlite3` connection, a `logging.FileHandler`.
- **Mount staging and owed write-backs** stay the host's, written at each turn's end (`_fs_table.py:174`).
- **A tool call in flight** cannot exist: the checkpoint claims the session. A guest that imported `host.tools` keeps the old list (`recipes/guest/host/tools.py:361`); the start's host judges each call by its own tools, so a missing name answers `unknown_tool`.
- **Files on disk** are not memory. HOME keeps the session's guest path, with a fresh private folder there.
- **Grants, environment, import path, tools and 163's results mode** are the start's own, read at its first export.

### 6. Refusals

| condition | raised |
|---|---|
| a forked process | `RuntimeError` (`_platform._refuse_forked`) |
| a session on the plain binary | `ValueError` |
| a set without the `checkpoint` export | `ArtifactsMissing` |
| the session has ended | `SessionEnded`, by the claim |
| a turn is running | `RuntimeError`, by the claim |
| no turn has returned (`state.guest` is not `_Guest.SOUND`) | `RuntimeError`, the claim released |
| a file open | `SnapshotFailed("open file")`, the claim released |
| the export trapped | `SnapshotFailed("trapped")`; the session has ended |

`SnapshotFailed.completed` becomes `Completed | None`, `None` when no export ran.

### 7. The origin, and fuel

`SnapshotOrigin` gains `kind: str = "prelude"` (or `"checkpoint"`) and `parent_sha256: str | None = None` (the image the session started from). A checkpoint's `prelude` is `""` and `prelude_fuel` `None`: its code is its turns, whose fuel each `Completed` reported. Its `home` is the session's HOME path; the header's reader accepts `IMAGE_HOME` or `/tmp/.home-` and 32 hex digits, the shape `_guest_home` makes (`_call.py:312`), and nothing else. Missing fields take their defaults, so the file stays format 1. `repr` reads `<Snapshot checkpoint, 210.3 MiB, made … by wasi-python 0.1.3>`. `snapshots_made` counts checkpoints.

The two calls are a few hundred C instructions, reported nowhere. A start's `fuel_used` is its own work, the resume included; the copy spends none.

### 8. The set

The origin names `state.set_digests`. `_snapshot._same_set` (`_snapshot.py:447`) takes `session=True` from `_open_session` and so digests a passed set for every session on the snapshot binary: the module and the zip's copy are held to the digests a checkpoint names. A start on another set raises `SnapshotMismatch` before any folder is walked (150, Decision 9). Metered or not does not matter.

### 9. Trust

A checkpoint carries the trust of every turn before it, and of its parent image. A turn can hook `builtins`, an import or an `atexit` handler, and every start runs the hook with its own grants, tools and environment. Both pages say: start a checkpoint only where you would run all its turns' code. A saved checkpoint holds the session's environment values. Only the embedder calls `checkpoint()`.

### 10. The copy-on-write restore is its own specification

The spike mapped an image over an instance's memory in 0.76 ms against 21 ms (§1.5, macOS only). It replaces pages wasmtime owns and needs the image as a file. It becomes a platform method after 168, with a Linux measurement and its own pre-build review. 162 keeps the copy in `_snapshot._restore`, the one place it changes. A 21 ms fork is already far below a replay.

### 11. Structure, row by row

R1: one method, two fields and a widened attribute, each in `tests/public_api.txt` and a row. R2: every refusal precedes the export. R3: no private wasmtime API (`Memory.data_ptr` and `data_len`, as 150). R4: no module-level mutable, lock or host flag; the claim and `_Guest.SOUND` decide. R5: no platform branch. R6: no seam. R7: no function past 80 lines; `_drive_turn` grows about four. R8: `origin.kind` and `parent_sha256` say what a start came from.

### 12. The rows first

Guest rows, `tests/checks/test_v1_4_prepare.py`, by the judge's driver: `checkpoint(1)` refuses before a turn, after `run` and twice; `checkpoint(0)` refuses unless entered; `shutdown` refuses while entered; a restore's `run` and `turn` run.

Goal rows, `tests/checks/test_v1_4_checkpoint.py`, each recording `fuel_used`:

- names, a frame and a fitted model return through `Session(snapshot=cp)` and `run(snapshot=cp)`; two forks and the live session never see each other;
- after `random.seed(1)` and `os.environ['K'] = '1'`, the live session's next draw and `K` are unchanged by a checkpoint; two forks draw differently;
- an open file is refused with `completed is None`, and after `close()` the session checkpoints;
- a fork granted writing at the session's `import_path` cannot import a planted module;
- after a turn that slept 2 s, a fork's `time.monotonic()` is not below the turn's, and its `time.sleep(0.01)` ends under `deadline_s=1`;
- a checkpoint of a fork holds both turns, its `parent_sha256` the first's; saved and loaded, it restores;
- a turn's hook on `builtins.print` runs in every fork; a tool the fork lacks answers `unknown_tool`;
- Decision 6's refusals.

Unit rows, `tests/unit/test_snapshot.py`: a header without the new fields loads as a prelude; a session-shaped `home` loads and `/` is refused; the checkpoint `repr`.

### 13. The documentation

`docs/how-to/snapshots.md`: "Checkpoint a session, and fork it" (the example, what carries, open files, trust), replacing line 126. `docs/how-to/sessions.md`: a sentence under "Keep trust levels apart". In `docs/reference/`: `results-and-errors.md`, `defaults-and-limits.md` (a checkpoint's copy of memory), `glossary.md`, and `python-api.md` regenerated.

## Intent

An embedder runs a few turns, calls `checkpoint()`, and starts any number of sessions or calls from that state, each sealed, with its own grants and randomness. The session goes on as if nothing happened.

## Design

In order: the rows, seen failing; the recipe (`reactor_main.c`: the export, the resume, the offset, the poll wrapper; `reactor_bootstrap.py`: `_BASE_PATH`, `_resume`; `60_link.sh`: `--wrap=__wasi_poll_oneoff`); the host (`_drive_turn`, `Session.checkpoint`, the origin, `_same_set`, the guest paths shared with `_snapshot_make._made_in`); the judge's lists; the documentation; the news file.

## Scope

In: the decisions above. Out: the copy-on-write restore (Decision 10); `checkpoint_async` (`asyncio.to_thread` serves); a checkpoint of a `run`.

## Acceptance criteria

1. **Seen failing first.** Every row of Decision 12 fails before its code, named in the pull request. READ.
2. **The rows** are green on Linux, macOS and Windows, labelled `ci:full`. EXECUTED.
3. **The contract.** `git diff dev -- tests/public_api.txt` shows `Session.checkpoint` and the two fields, claimed. READ.
4. **The structure.** `tests/checks/test_rules.py` is green; no `LONG_FUNCTIONS` entry rises. EXECUTED.
5. **The artifact set.** Both binaries export `checkpoint` as `(i32) -> (i32)`; the moved fuel and bytes are claimed. READ.
6. **The documentation** of Decision 13 is in place; `uv run pytest tests/lint` is green. EXECUTED.
7. **The run.** `ci-status` is green; no accepted pass is lost; the landing notes cite both reviews and the fuel facts. READ.

## Landing notes

To be written at the landing.

## For the owner to decide

1. **The copy-on-write restore**: its own specification after 168, in 0.1.3 if both land in time (recommended); or inside 162, which then waits on 168 and a Linux measurement.
2. **An open file at a checkpoint**: refused (recommended); or closed with a warning, which leaves the guest's object naming a number a later open reuses.
