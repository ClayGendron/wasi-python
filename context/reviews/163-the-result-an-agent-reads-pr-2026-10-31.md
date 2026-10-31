# Review of 163 — The result an agent reads

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `git diff origin/dev...HEAD` on `spec/163-the-result-an-agent-reads`, first at `0346c6eb` and `54c13c88` on `30566232`; then the fix rounds `2b4c1c1b` and `f192f87b` (rebased with its parents `bc6157c4` and `b3419e42` onto `1c36543d`), read beside the specification, its pre-build review (`163-the-result-an-agent-reads-spec-2026-10-30.md`) and constitution §4.4 as amended on 2026-10-31
- **Run:** 41212674574 on head `f192f87b`, as the orchestrator relayed it (I made no `gh` call and dispatched nothing). The gather is green and the scoreboard shows 0 failures (1,010 of 2,079 pass, 129 gaps, 7 blocked). All 13 Windows legs are green. `ci-status` is red only for the missing review file, which this file supplies. GROWTH lists 43 rows and every one is claimed. 42 are shown with 162's reason and 1 with 165's, because those news files' globs match first in the gather's listing. All 43 also sit inside this news file's `tests/checks/test_v1_*`, so none is unclaimed.
- **Re-ran:** against the worktree's local set (`build/artifacts`, built on d64f8146's pins, before 166's CPython 3.15.2): `uv run pytest -m "not slow" -n 2` → 4426 passed, 10 failed, 17 skipped, exit 1; `tests/checks/test_v1_4_results.py` by file → 11 passed; with `tests/unit/test_results.py` and `tests/checks/test_rules.py` → 180 passed, 1 skipped; `uv run pytest tests/lint` → 14 passed; five probes through `wasi_python.run` (below). On the fix round, with the set the author rebuilt on 166's pins: `tests/checks/test_v1_4_results.py`, `tests/unit/test_results.py`, `tests/checks/test_rules.py` and `tests/lint` → 199 passed, 1 skipped, exit 0.
- **Box:** 45 minutes (structural, build class); overrun by the fast tier's wall time, not by reading.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

The ten local failures are all the stale set read against 166's pins (EXECUTED): `test_v1_1_artifact_set` (the pins, the MANIFEST's patches and a static constructor), `test_v1_5_rebuild_from_pins` (two), and four behaviour rows whose expectations moved with 166 (`hash-tuple`, numpy's linalg, pandas' tz job, both binaries). None touches a file this branch changes. The pull request's run is the first on the new pins, and it is what decides them.

Probes (EXECUTED, local set): `import_path=` with `results=True` returns the value 42 and leaves argv as `['-c']`, so the flag after the `-c` prelude reaches the inner `run`. `tools=` with `results=True` returns the display and the value, and the tool record counts 2 frames. A turn whose value's `repr` raises returns exit 1, no value, and `_` is `None`. A 2 MiB frame under `tools=` and `output_bytes=1000`: see Finding 2. 1,003 display frames, each over the room: the last is answered `kept: false` with its id, which shows it was read and parsed.

## Acceptance criteria against evidence

1. Seen failing first — met (READ). The landing notes give the collection error for the 35 unit rows and the eleven goal rows' failing lines on `dev`; `build/163/goal-on-dev.log` and `unit-on-dev-src.log` hold them. The pull request's self-check is not read: no `gh`.
2. The rows green on three systems under `ci:full` — met: run 41212674574 has the gather green and 0 failures. Locally the 11 goal rows and the 35 unit rows pass (EXECUTED).
3. The contract — met (EXECUTED). `git diff origin/dev -- tests/public_api.txt` adds 13 lines: `Display`'s four fields, `value` and `displays`, and `results` and `figures` on `run`, `run_async` and `Session`. Nothing else changes. The news file claims it and the three rises (`[claim.judge]`).
4. The structure — met (EXECUTED). `test_rules.py` is green. `_results.py` has 269 lines and its longest function is under 80.
5. The artifact set — met. Run 41212674574's 43 GROWTH rows all fit inside `grows`. The claim is `grows = ["tests/checks/test_v1_*"]`. Every call now runs `_take_mode`, `_set_mode`, `_cell_begin` and `_cell_end`, and under `ci:full` the upstream groups' fuel can grow too. `tests/upstream/…` is outside that prefix. Read the gather's GROWTH rows against it; a row outside it is the Medium of criterion 5 (Finding 5).
6. The documentation — met (READ, EXECUTED). `how-to/results.md` is in the nav, the four reference pages and two docstrings follow, and the lint tier is green.
7. The run — met: run 41212674574 is green apart from the review file's absence. The landing notes cite the pre-build review, and they should add this file and the run id at the merge.

## Findings, most severe first

1. **Low: past the thousandth record, frames are still read and parsed** (`src/wasi_python/_results.py:138-150`, R2). On the bound: 6 × room + 1 KiB is right per frame. `\u00XX` is the worst escape, at six bytes per decoded byte, and base64 is 4/3. The envelope is about 150 bytes: the keys, a 16-digit id and five type names. But neither the records nor a `too_large` shrinks the bound. A program can call `_host.call` again and again with one prepared frame of up to 96 MiB (the default room is 16 MiB). The host then copies and JSON-parses every one, uncounted by fuel, until the deadline ends the call. The tool host bounds its total with `tool_request_bytes`. Stdout already lets a guest push unbounded bytes at a low fuel cost, and the deadline holds, so this is Low. Failure: `deadline_s=None, fuel=N`; a loop of 96 MiB display frames past record 1,000 → each is read and parsed, and nothing ends the loop but fuel spent at a few instructions per frame. Fix text, in `admit`: "Once `self._records >= RECORDS`, the display bound is `ENVELOPE`: without tools a longer frame is answered `ok`, `kept: false` unread; under tools the bound is the tool frame cap." Add one unit row.
2. **Low: under `tools=`, a frame past both bounds is refused as a display and leaves the tool record** (`_results.py:143-150`, R8). EXECUTED: a 2 MiB frame with `tools=[lookup], output_bytes=1000, results=True` is answered "the frame is 2097154 bytes; a display has room for 1000". The record is `ToolRecord(frames=0)` and `Completed.truncated == ("displays",)`. Without `results=` the same frame is tool frame 1, outcome `too_large`. This is Decision 7's letter, but `Completed.tools` no longer counts every frame, and `"displays"` is named when no display was cut. Fix text: under tools, an unread refusal leaves `cut` alone, and its message reads "the frame is N bytes; at most M" without naming a display. Alternatively, say in `tool-protocol.md` that under `results=` a frame past both caps is counted in neither record.
3. **Low: a `repr` that raises shows the guest helper's frames** (`recipes/reactor_bootstrap.py:_show`; Decision 2: "reported as `sys.displayhook` reports it"). EXECUTED: the traceback holds two frames, `host/display.py`'s `_value` and `_bundle`, above the user's `__repr__`, where the plain hook (C) shows none. Fix text: `_show` calls `repr(value)` itself before `_shown._value` (the `<reactor>` frames are stripped), and `_bundle` takes the text it is given. Alternatively, `_report` also strips frames whose file ends in `host/display.py`.
4. **Low: the landing notes' lengths** (`context/specifications/163-the-result-an-agent-reads.md`, "What was built"). EXECUTED on `origin/dev`: `_turn_inside` is 73 and is now 74 (the notes, and Decision 11, say "grew by no line"). `_checked` is 79 and is now 80 (the notes say "stays at 80"). Both are within the limit. Fix text: "`_turn_inside` 73→74 (the result host read back); `_checked` 79→80."
5. **Low, pending the run: the `grows` prefix** (news file). It is broad and does not cover `tests/upstream/`. Fix text, once the gather is read: widen it to every GROWTH family listed, for example `"tests/upstream/*"`, with the same reason, or narrow it to the families that moved.
6. **Low: `Display` is a frozen dataclass that cannot be hashed** (`_results.py:45-69`, R1). EXECUTED: `hash(Display({...}))` raises `TypeError`, and so does a `Completed` that carries one. Fix text: say so in `Display`'s docstring ("compared by value, not hashable: `data` is a mapping"), or set `__hash__ = None` explicitly.

## Structure (the eight rows, EXECUTED measurements)

`runner.py` 1,476 lines (up 27; 24 left under 1,500), `_call.py` 1,402, `_sessions.py` 1,244, `_results.py` 269. Long functions: the list's seven at their claimed lengths, with `_instance` at 146. No module-level mutable or lock is added in `src/`. No private-API use, no platform branch outside `_platform*`, and no test seam in `src/`. No code file names a specification (`src/`, `tests/`). The commit trailers name Claude Opus 5.5.

| row | moves | reason |
|---|---|---|
| R1 Contract | holds | One class, two defaulted fields after `image_sha256`, and two keywords on three entry points, all snapshotted. Failures are typed (`TypeError` for the keywords and `host=`, `ValueError` for the flag before the target). Finding 6 is a write-in. |
| R2 Safety | holds, Finding 1 | Off by default; `results=` with `host=` is refused. Every display frame is judged host-side with `_tool_host._parse`: six types, `str` or `$bytes` by type, `truncated` within the six, `value` a boolean, and `text/plain` required. Printed bytes never reach the door. `admit` never calls `_ToolHost.admit` (a unit row asserts `frames == 0`). |
| R3 Layering | holds | `_results` sits before `_call` in the written order, and its `_tool_host` and `tools` imports are late (`LATE` lists them). The graph stays acyclic. |
| R4 Process state | holds | `_ResultHost` is per call or per turn. The mode is set both ways at every `run` and every `_setup`, so a fork takes its own start's mode (goal row). |
| R5 Portability | holds | No branch. `settle()` serves both captures. |
| R6 Testability | holds | The goal rows drive `run` and `Session`. The unit rows build `_ResultHost` directly and load the guest package with a fake `_host`, with no seam in `src/`. |
| R7 Evolvability | holds | `_door_hosts` keeps `_instance` and `_arm` flat. `runner.py`'s headroom is now 24 lines, which the next keyword specification should know. |
| R8 Operability | holds, Finding 2 | Displays stay out of `Completed.tools`, and `truncated` names `"displays"`. |

The structure holds.

Judge edits, each with a reason (READ): `LONG_FUNCTIONS` (three rises and one fall, claimed); `public_api.txt`, `test_v1_4_public_api.py`, `release_shards.toml`, `budget.toml`, `harness/calls.py` and `test_runner_package.py` (claimed); `harness/api.py` adds the new module to the file lists; `test_lifecycles.py` 23→24 fields; `test_runner_tools.py` now holds `tools` followed by `image_sha256` rather than both being last, which keeps its point. None loosens a verdict. No `.github/` or `release/` file changes.

## Constitution checks

- §4.4 as amended: a display calls nothing of the host's and needs no gate, and tool frames are still gated by the tool host (probe 2). Holds.
- §4.15: off by default, and a fork without `results=` sends no frame (goal row). Holds.
- §4.6 and §5.6: both binaries and the zip change, with two new members in `70_zip.sh`. `MANIFEST` is the build's, and the run on the new pins judges it.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Answered by the author in one fix commit, `2b4c1c1b`; I read that commit and confirm each answer below.

1. Fixed. `admit` treats the records as spent at 1,000. Without tools, a frame longer than `ENVELOPE` then gets `kept: false` unread; under tools, frames up to the tool cap are still read. A unit row covers it (`test_past_the_last_record_a_frame_longer_than_its_keys_is_not_read`). Confirmed.
2. Fixed. Under tools, a frame past both caps is answered `too_large` "at most M". It does not set `cut`, and `tool-protocol.md` says it is counted in neither record. A unit row covers it. Confirmed. A write-in remains (Finding 7).
3. Fixed. `_show` takes `repr(value)` in the bootstrap and passes it to `_value`. The goal row `test_a_repr_that_raises_is_reported_as_the_hook_reports_it` requires stderr to be the same with and without results. My traceback above is its failing run. Confirmed.
4. Fixed in the landing notes. Confirmed.
5. Answered with a measurement. The author rebuilt on 0.1.3's pins with and without the change: 75 of the 80 sampled rows grew, by 0.002 to 2.7 percent. Only rows under `tests/checks/` carry fuel or bytes in the acceptance, so `tests/upstream/` has nothing to claim. Confirmed; the run's GROWTH rows remain the test.
6. Fixed. `Display.__hash__ = None`, the docstring says why, and a unit row covers it. Confirmed.
7. **Low, new in the fix round: the "at most M" message can understate the bound** (`_results.py:admit`). Without spent records, a frame is read up to the larger of 6 × room + 1 KiB and the tool cap. With the default room that is about 96 MiB, yet the message names the tool cap, 1 MiB. Such a refusal also counts toward the 1,000 records, which still bounds a loop of them. Fix text: name `max(bound, cap)` in the message. Fixed in `f192f87b`: the message now names `max(bound, cap)`, and the both-caps unit row checks it at a 1 MiB room. The author saw the row fail before the fix with "at most 1048576". On `f192f87b`, `tests/unit/test_results.py` and `tests/checks/test_rules.py` gave 173 passed, 1 skipped (EXECUTED). Confirmed.

## Verdict

Lands on `f192f87b`: run 41212674574 is green and every GROWTH row is claimed, the code holds, no High or Medium stands, and Findings 1 to 7 are fixed and confirmed.
