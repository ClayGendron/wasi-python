# Review of 162 — A session's state is a snapshot

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/162-a-sessions-state-is-a-snapshot.md`, at `4849fc4e` on `docs/0.1.3-specifications`, with 163's and 164's Decisions beside it
- **Run:** none: a specification review
- **Re-ran:** function lengths by `ast` over `_sessions.py`, `runner.py` and `_snapshot.py`; `grep -n` of every line the specification cites. No guest was run.
- **Time box:** 45 minutes (structural and build-class); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

READ: AGENTS.md; constitution §4.4, §4.6, §4.15, §5.6, §7; `context/reviews/README.md`; the specification; 163 (whole) and 164's Decision 9; the memo of 2026-10-30 §2 A; `recipes/reactor_main.c` (the clock and entropy wrappers at 90–107, the statics at 145–171, `wizer_initialize`, `freeze_for_image`, `run`, `turn`, `shutdown`, `prepare` at 655–711); `recipes/reactor_bootstrap.py` (`_refresh`, `run`, `_setup`, `turn`, `prepare`, `_end`, `_flush_writers`); `src/wasi_python/_snapshot.py` (`SnapshotOrigin`, `SnapshotFailed`, `_read`, `_header_origin`, `_start`, `_same_set`, `_memory_image`, `_restore`); `_sessions.py` (`_Guest`, `_drive_turn`, `_turn_inside`, `_session_turn`, `_open_session`); `runner.py:1121-1132`; `_fs_table.py:75-175`; `_call.py:300-335`; `recipes/guest/host/tools.py:355-365`; `scripts/steps/60_link.sh:169`; `tests/harness/artifacts.py`; `docs/how-to/snapshots.md:110-135`.

Every line the specification cites says what it claims, with one exception (Finding 7). EXECUTED: `_drive_turn` is 66 lines, `_turn_inside` 78, `_open_session` 142 (listed).

## Acceptance criteria against evidence

1. Seen failing first — buildable; the rows of Decision 12 lack three (Findings 1 to 3).
2. The rows on three systems — buildable.
3. The contract — buildable; `SnapshotFailed.completed` widening is a break to name (Finding 11).
4. The structure — buildable if the capture stays out of `_turn_inside` (Finding 10).
5. The artifact set — buildable: `checkpoint` joins `PLAIN_EXPORTS` and `SNAPSHOT_EXPORTS` in `tests/harness/artifacts.py` as `(i32) -> (i32)`.
6. and 7. — buildable.

## Findings, most severe first

1. **Medium: a fork that did not ask for results keeps the checkpoint's results mode, unless `_setup` resets it** (163 Decisions 5, 6 and 9). 163's Depends line says "a checkpoint keeps the session's mode; 162 says so"; 162's Decision 5 says the mode is the start's own. 162 is right. A mode is a channel from guest to host, and constitution §4.15 opens a channel only on the call's own argument; 163 also refuses `results=` beside `host=`, because the raw door is the embedder's. Mechanically, 162's resume reruns `_setup` with the start's argv, so the start's `-Xhost-results` is read; but an `_setup` that only sets the mode when the option is present leaves the session's `builtins.display`, its figures backend and its "value goes to a frame" flag in place. Failure: a session with `results=True, figures=True` checkpoints; `Session(snapshot=cp, host=raw)` runs `df.head()`: nothing is echoed to stdout, and the bootstrap sends a display frame into the embedder's raw door. Fix text, 162 Decision 5's last bullet: "The results mode is the start's: `_setup` reads `-Xhost-results` and sets the mode either way. Without it, it clears the mode, unbinds `builtins.display` when it is the bootstrap's, and puts back the matplotlib backend the bootstrap chose." Decision 12 gains the row: "a checkpoint of a results session, started without `results=`, prints its value and sends no frame; started with it, returns `value`." Whichever of 162 and 163 lands second carries the row. 163's Depends line reads: "162 (each start from a checkpoint reads its own mode; 162, Decision 5)".
2. **Medium: the image carries every byte the session held, and Decision 9 names only the environment.** The image is the whole of linear memory, live and freed (READ, `_memory_image`). That includes files read under the session's grants, mount bytes, tool answers, and environment values the start's `_setup` replaces. A guest can read its whole linear memory without ctypes: numpy builds an array over any address given in `__array_interface__` (INFERRED from numpy's array interface). So a start's grants bound what it reads from the host from then on. They do not bound what the image already holds. Decision 5's "grants … are the start's own" reads the other way. Failure: an embedder checkpoints a session that read `/data/a` and forks it for a second user granted only `/data/b`. That user's code reads the first user's rows from `__main__`, or from freed heap. Fix text, Decision 9, after its first paragraph: "A checkpoint also carries every byte the session's memory holds, live or freed: what it read from its grants, mounts and tools, and its environment's values, whatever a start replaces. Every start from it, and anyone who holds the saved file, can read them. A start's grants bound what it reads from the host from then on, not what the image holds. Start a checkpoint only where whoever runs code there may read everything the session read." `docs/how-to/snapshots.md`'s new section says the same in two sentences.
3. **Medium: "two forks draw differently" holds only for the generators `_refresh` names** (`reactor_bootstrap.py:73-100`). `_refresh` reseeds `random`, `numpy.random`'s legacy state, tempfile's sequence, sympy's and two more by name (READ). A generator held in a name is copied as it is: `np.random.default_rng()`, numpy's recommended API, a `random.Random()`, and any token drawn before the checkpoint. The reseed also replaces a session's own `random.seed(1)`, as the row says. Failure: `rng = np.random.default_rng()` in turn 1, checkpoint, two forks: `rng.random()` gives the same number in both; and a notebook that seeded for a reproducible fork gets a new stream in each. Fix text, Decision 5, a new bullet: "**Randomness.** Each start reseeds the module generators every start from a snapshot reseeds, even after the session's own seed: seed again in the first turn for a reproducible fork. A generator held in a name, and every value drawn before the checkpoint, is the same in every start." Decision 12 gains the row "a `default_rng()` held in a name draws the same in two forks; `random.random()` draws differently". The page says it.
4. **Low: the poll wrapper must not wrap below zero** (Decision 4). A deadline the guest computed before the checkpoint can be below `offset`. Subtracting in unsigned 64-bit then gives a wait of centuries, cut only by `deadline_s`. Fix text: "subtracts it, saturating at 0, so a deadline already past returns at once".
5. **Low: a failed read between the two calls** (Decision 2). `_drive_turn` catches wasmtime's errors only. A `MemoryError` from copying a large memory ends the session, since `_session_turn` marks any error (READ, `_sessions.py:913-924`). That is safe, but it contradicts "the session goes on". Fix text: "The read is in a `try` whose `finally` calls `checkpoint(0)`. A `MemoryError` from the read is raised by `Session.checkpoint` once `checkpoint(0)` has returned 0, and the session goes on. A trap or -1 from either call ends it as Decision 6 says. `Session.checkpoint` arms no deadline and no fuel of its own; the lifetime still bounds it."
6. **Low: the plain reactor would answer `checkpoint(1)`.** After a turn on the plain binary, `initialized && turned` holds, so a host in another language gets an image no instance can restore. `prepare` refuses there only because the plain reactor is not initialized before a turn. Fix text, Decision 2: "`enter == 1` also refuses on the plain reactor: a static set only in `wizer.initialize` says this is the snapshot."
7. **Low: `_same_set` has no `session` parameter today** (`_snapshot.py:447-469`). With `start=None` it returns `checked` unchanged, so a session given `artifacts=` holds no digests. Decision 8 describes the change as present behaviour, and its cost is unstated. Fix text: "`_same_set` gains `session: bool`. For a session on the snapshot binary with a set passed, it digests the binary and the zip at the opening, about 0.1 s for each such session, checkpointed or not. The digests then key the module cache, as a found set's do." (The memo of 2026-10-27 measured SHA-256 of a 203 MiB image at 94 ms; INFERRED, the same order for the binary.)
8. **Low: the new header fields are validated, and the old ones are defined.** Fix text, Decision 7: "The reader refuses a `kind` other than `"prelude"` or `"checkpoint"`, and a `parent_sha256` that is neither null nor 64 lowercase hex digits. A checkpoint's `guest_paths` and `env_names` are the session's opening's." A 0.1.2 reader calls a checkpoint's header damaged (its `home`); the set check would refuse it anyway, so no format bump is needed.
9. **Low: what else carries, said once** (Decision 5). A checkpoint is not reproducible: its heap holds real times, real entropy and freed bytes. Its `image_sha256` names it and does not predict it. Other things carry too. A turn's `os.chdir` carries the working folder into a start whose grants may not hold it. Bytes unflushed in a writer on descriptor 1 or 2 other than `sys.stdout` are flushed by `_end` in every start and by the live session. `atexit` handlers run at every start's end. The session's uncollected cyclic garbage is frozen by the resume's `gc.freeze()` and never collected in a start. Fix text: one bullet per item in Decision 5. `checkpoint(1)` also calls `clear_unused_stack()`, which changes no live state, so the last turn's dead C frames stay out of the file.
10. **Low: the two-call export needs its own branch, and `_turn_inside` has two lines of room.** `_drive_turn` calls `exports[export](store, p, len(data))`, and `checkpoint` takes one argument. `_drive_turn` is 66 lines and `_turn_inside` 78 (EXECUTED). Fix text, Decision 11, R7: "`_drive_turn` takes the checkpoint's branch and sets `state.captured`; `_turn_inside` gains no line." Also: `SESSION_EXPORTS` stays `("turn", "shutdown")`, so a 0.1.2 set still opens a session, and `checkpoint` is looked up in `state.exports` at the call.
11. **Low: `SnapshotFailed` changes for every reader.** Its docstring speaks of the making only, and `completed` becomes `Completed | None`. Code that reads `e.completed.exit_code` breaks on the new reason. Fix text: the docstring names `Session.checkpoint`, and the news file carries an `### Upgrading` line: "`SnapshotFailed.completed` may be `None` when no code ran".

## Structure

| row | moves | reason |
|---|---|---|
| R1 Contract | holds | One method, two defaulted fields at the end of `SnapshotOrigin`, a widened attribute, each in `tests/public_api.txt`; failures by type (Decision 6). Finding 11 names the break. |
| R2 Safety | holds once Finding 2 is written | Every refusal precedes the export. The copy is bounded by the session's `memory_bytes`. The header is validated (Finding 8). The data a fork can read is not yet stated (Finding 2). |
| R3 Layering | holds | `Memory.data_ptr` and `data_len` only, as 150. No new import edge: `runner → _sessions → _snapshot` exists. |
| R4 Process state | holds | No module-level mutable or lock; the claim and `_Guest.SOUND` decide, with no new phase or event. The reactor gains a tenth C flag, `checkpointing`, beside nine. It is recipe code, outside the rubric's `src/`. |
| R5 Portability | holds | No platform branch; the copy-on-write restore is deferred to its own review. |
| R6 Testability | holds | No seam; the rows drive `Session.checkpoint` and the guest driver. |
| R7 Evolvability | holds if Finding 10 holds | `runner.py` 1,318 + ~35 of 1,500; `_sessions.py` 1,147 + ~15; `_snapshot.py` 517 + ~30 (INFERRED). |
| R8 Operability | holds | `origin.kind`, `parent_sha256` and the `repr` say what a start came from; `snapshots_made` counts checkpoints. |

## Constitution checks

- §4.4: no new import; the export is the host's to call, and nothing in the guest reaches it.
- §4.6: both binaries, `MANIFEST` and `SHA256SUMS` change; the zip does not. Criterion 5 holds the export's type.
- §4.15: nothing opens without the embedder's call; Finding 1 keeps a fork's channels its own.
- §4.9: the rows count fuel and exit codes; the sleep row bounds a hang by `deadline_s`, it does not time anything.
- §5.6: this is the pre-build review for the export, the recipe and the structure.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. to 3. Mediums: amend the text as given, and 163's Depends line for Finding 1.
4. to 11. Lows with fix text; they need no round.

The author's answers, 2026-10-30 (the specification's author, a sub-agent of the orchestrating session); every finding taken:

1. Taken. Decision 5's results-mode bullet resets the mode both ways; Decision 12 gains the row, carried by whichever of 162 and 163 lands second (the Depends on line). 163's Depends line is 163's author's to correct. Confirmed: Decision 5's bullet and the row in Decision 12 (once 163 has landed) are as the fix text; 163's Depends line and its Decision 5 now say a fork takes its own start's mode, in both directions (READ).
2. Taken. Decision 9's second paragraph, as the fix text, condensed; Decision 5's grants bullet points to it; Decision 13's snapshots section says it. Confirmed: Decision 9's second paragraph, Decision 5's pointer and Decision 13 (READ).
3. Taken, decided as the fix text: the module generators are reseeded even after the session's own seed, and held generators repeat. Decision 5's "Randomness" bullet and a Decision 12 row (`default_rng()` the same in two forks, `random.random()` not). Confirmed: the Randomness bullet and the row with both draws (READ).
4. Taken. Decision 4: the subtraction saturates at 0. Confirmed (READ, Decision 4).
5. Taken. Decision 2: the read in a `try` whose `finally` calls `checkpoint(0)`; a `MemoryError` is raised and the session goes on; the lifetime bounds the call. Confirmed (READ, Decision 2).
6. Taken. Decision 2: `enter == 1` also needs a static set only by `wizer.initialize`; Decision 12's guest row refuses it on the plain reactor. Confirmed: Decision 2's static and the guest row on the plain reactor (READ).
7. Taken. Decision 8 names `_same_set`'s new `session` parameter and its cost of about 0.1 s per such opening. Confirmed (READ, Decision 8).
8. Taken. Decision 7: `kind` and `parent_sha256` are validated; `guest_paths` and `env_names` are the session's; a unit row refuses a bad one. Confirmed: Decision 7 and the unit row (READ).
9. Taken. Decision 5's "Also carried" bullet; `checkpoint(1)` calls `clear_unused_stack()` (Decision 2). Confirmed: Decision 5's "Also carried" and `clear_unused_stack()` in Decision 2 (READ).
10. Taken. Decision 2 and R7: `_drive_turn` takes the branch, `_turn_inside` gains no line, `SESSION_EXPORTS` is unchanged. Confirmed: Decisions 2 and 11 (READ).
11. Taken. Decision 6: the docstring names `Session.checkpoint` and the news file carries the `### Upgrading` line. Confirmed (READ, Decision 6).

## Verdict

Fit to build: Mediums 1 to 3 and Lows 4 to 11 are answered in the amended specification, read again whole on 2026-10-30, and 163's line on the results mode now agrees with Decision 5.
