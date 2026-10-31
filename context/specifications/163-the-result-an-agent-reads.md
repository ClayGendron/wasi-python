# 163: The result an agent reads

- **Status:** **built 2026-10-31** on `spec/163-the-result-an-agent-reads`, rebased onto `30566232` (166's merge, after #72's §4.4 amendment, `548affd8`), before its pull request and review (Landing notes). Before: drafted 2026-10-30 and reviewed before it was built (public API, structural, and the build recipe); the owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3"); revised the same day against its pre-build review, `../reviews/163-the-result-an-agent-reads-spec-2026-10-30.md` ("Fit to build after amendments"), every finding taken (its Disposition); Decision 4 built on the owner's amendment of constitution §4.4 of 2026-10-31.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **structural**: a public class, two `Completed` fields, `src/wasi_python/_results.py` (at most 400 lines), and the listed lengths of `runner.py:run`, `run_async` and `Session.__init__` raised and claimed (spec 142). Build recipe (constitution §5.6): the bootstrap and two zip files change both binaries, the zip and `MANIFEST`. No pin, patch, or guest import or export.
- **Depends on:** 164, stacked: built on its reviewed tip or after it lands, reusing its `_Stream.written`, its tail marker and its one helper that builds a call's and a turn's `Completed` (Decision 11). Landed: 031 and 036 (the tool protocol), 055 (sessions), 129 (the pipe), 142 (the allowance), 150 and 157 (images). In flight: 162 (a fork's first turn runs `_setup`, which sets the fork's own mode, Decision 5), 167 (plotly's `_repr_mimebundle_`).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§1, item 2; §2, item C). The owner's notebook app `test_app/` (untracked; `app/driver.py`), READ as the need, nothing copied.

## The problem

An agent that runs `df.describe()` wants the table back, as text and HTML; a cell that draws a chart wants the chart. A call returns two byte streams (`src/wasi_python/_call.py:61-91`). A session turn evaluates its last expression apart (`recipes/reactor_bootstrap.py:291-308`) only to print its `repr`; a `-c` program has no value.

The owner's notebook app built the rest by hand (READ): a guest driver sends the last value and `display()` records over stdout behind a 0x1E marker. Printed 0x1E and JSON forges a record; the cap cuts one mid-JSON. Hosted interpreters return typed results (the memo, §1).

## Decisions

### 1. Opt-in: `results=` and `figures=`

`run`, `run_async` and `Session` take `results: bool = False` and `figures: bool = False`. `figures` adds matplotlib's figures (Decision 9). Off is the default: no channel to the host opens unasked (constitution §4.15). A session's mode is set at its first turn (Decision 5).

`figures` without `results`, or `results` with `host=` (the raw door is the embedder's), is a `TypeError`, as `gate=` without `tools=` is (`runner.py:753`).

### 2. The record: `Display`

```python
@dataclass(frozen=True, slots=True)
class Display:
    data: Mapping[str, str | bytes]  # MIME type -> content, read-only
    truncated: tuple[str, ...] = ()  # the MIME types cut or dropped at the bound
    stdout_at: int = 0               # bytes the guest had written to stdout before it
    stderr_at: int = 0
```

Six MIME types: `text/plain` (always, the `repr`), `text/html`, `text/markdown`, `image/svg+xml`, `application/json` (its text) and `image/png` (`bytes`), read from `_repr_mimebundle_`, then the `_repr_*_` methods, as a notebook does. A method that raises an `Exception` or returns the wrong type is skipped; another `BaseException` propagates. A `repr` that raises is reported as `sys.displayhook` reports it, with no record.

### 3. `Completed.value` and `Completed.displays`

`Completed` gains `value: Display | None = None` and `displays: tuple[Display, ...] = ()`, after `image_sha256`.

`value` is a turn's or a `-c` program's last expression, when not `None`; in results mode it is not printed, and `builtins._` is still bound. A program that replaced `sys.displayhook` gets its hook called, as the interactive interpreter does, and no value is sent. A script, `-m` or stdin program has no value; its displays still arrive. Without `results=True`, stdout is today's to the byte.

### 4. Over the door, as one more operation of the tool protocol

`display()` sends one frame, `{"v": 1, "id": n, "op": "display", "value": false, "data": {...}, "truncated": [...]}`, PNG bytes as the protocol's `{"$bytes": "<base64>"}`. The bootstrap sends the value with `"value": true`.

`_results._ResultHost` answers `display` and hands `list` and `call` to the call's `_ToolHost.__call__`; with no tools it answers them `protocol`, "this run has no tools", so `from host import tools` still raises `ImportError`. A helper beside `_call._tool_host` makes it, wired where the tool host is (`_call.py:455-458`, `_sessions.py:694-697`).

The host validates every display frame, whoever sent it, with the tool protocol's own parser (`_tool_host._parse`): only the six MIME types; each value a `str`, but `image/png`, which must be `$bytes`; `truncated` naming only the six; `value` a JSON boolean. Anything else is answered `protocol` and kept nowhere.

The protocol stays version 1; against a host that refuses `display`, the text is printed (Decision 6). Constitution §4.4's "used only when the embedder passes its tools, and gated by the embedder on every call" does not admit an ungated display frame; the amendment (the last section) does.

### 5. How the guest learns the mode: `-Xhost-results`

The runner puts `-Xhost-results` or `-Xhost-results=figures` first in the caller's argv, after any import prelude (`_call.py:386`). It is read as one argument and removed at the first export of every instance, before the program sees `sys.argv` or `sys.orig_argv`: in `run` and in a session's `_setup`. `_setup` sets the mode in both directions: it binds or unbinds `display` and sets or restores the backend. A fork from 162's checkpoint runs `_setup` at its first turn, so it takes its own start's mode, never the checkpointed session's (constitution §4.15): a fork started without `results=` sends no display frame. A host that passes none gets today's behaviour. Either string in an embedder's argv before the program's target (`-c`, `-m`, a script or `-`) is a `ValueError` naming `results=`; after it, it is the program's own argument.

### 6. `display()` lives in the zip

`host/display.py` holds `display(*objs)`. In results mode it is bound into `builtins`, as IPython binds it; out of it, it prints each object's text, as IPython does in a terminal. It flushes `sys.stdout` and `sys.stderr` before its frame.

### 7. Bounds

A call's or turn's displays, value included, share `output_bytes` decoded bytes and 1,000 records (the tool record's number).

`_ResultHost.admit(length)` never calls `_ToolHost.admit`. It refuses unread a frame longer than the larger of 6 × the room left (the JSON escape's worst case) and, under `tools=`, the tool frame cap, answering `too_large` with `"room": <bytes>`; the refusal counts as a record. With `output_bytes=None` only the guest's memory bounds a frame. After the read, `list` and `call` go to `_ToolHost.__call__`, which admits them by length then, as it does for a raw host: a tool frame spends tool calls and bytes exactly as today, and a display frame spends neither.

Read, a frame is judged by its decoded bytes. Over the room, the guest sends it once more as `text/plain` alone, cut at a character boundary, the other types named in `truncated`. A display past the 1,000th record, or with no room left, is answered `ok` with `"kept": false`; the guest then sends and prints nothing more in that cell. In every such case `Completed.truncated` names `"displays"`.

### 8. Order beside the streams

`stdout_at` and `stderr_at` are the bytes the guest had written to each stream, kept or not, read after the host settles the capture (`_PipeCapture.settle`). Under the head, `stdout[:d.stdout_at]` is what printed before `d`. Under 164's tail, with `N` bytes cut, its place is `stdout_at - N` plus the marker line's length when that is past the marker; before it, the display came in the cut part. `written` is 164's.

### 9. Figures

`host/figures.py` is a matplotlib backend module over Agg's canvas. Its `show()` sends each open figure as a display, `image/png` plus its `repr`, then closes them, as Jupyter's inline backend does. In figures mode the bootstrap sets `MPLBACKEND` to `module://host.figures` unless the embedder's environment sets it, so a program's `matplotlib.use()` still wins; under an image that imported `pyplot`, it switches the backend at the first cell.

At the end of each cell, after an exception too, the figures still open are sent the same way, stopping at the first `"kept": false` and closing the rest unrendered, only if `matplotlib.pyplot` is in `sys.modules`, so a cell that never drew imports nothing. A trap sends none. The PNGs cost the call's fuel.

### 10. Trust

A display is guest output: its HTML and SVG are untrusted, and the documentation says to render them in a sandboxed frame. A program may send any frame through `display()` or `_host.call`; printed bytes can never read as a record. Of several value frames, the host keeps the cell's last.

### 11. Stacked on 164

The two meet in `Completed`, to which 164 adds no field. 164 makes the one `_call.py` helper that builds a call's and a turn's `Completed`; this extends it with `value` and `displays`, so `_instance` and `_turn_inside` grow by no line. 164's `OutputChunk` never carries displays.

### 12. The rows first

Unit rows, `tests/unit/test_results.py`, one per rule of Decisions 4, 5 and 7. Goal checks, `tests/checks/test_v1_4_results.py`: `df.head()` as a turn's value, text and HTML, nothing on stdout; a `-c` value; a display between two prints; a printed forged record; a PNG over the room; `plt.plot` and `plt.show()`; stdout unchanged without `results=`; a call from an image; a fork of a checkpoint in either mode; both binaries alike.

### 13. The documentation

`docs/how-to/results.md`, new, in `mkdocs.yml`'s nav. `docs/reference/results-and-errors.md` gains the two fields and `Display`; `tool-protocol.md` the `display` operation, `room`, `kept` and `-Xhost-results`; `defaults-and-limits.md` says displays take one more `output_bytes`. `how-to/sessions.md:25`, `matplotlib.md` and two docstrings (`Completed.truncated`, `Session.run`) follow.

## Intent

A harness passes `results=True` and reads a cell's value and displays as typed fields no print can forge.

## Design

The guest: `recipes/reactor_bootstrap.py`, `recipes/guest/host/display.py` and `figures.py`, `scripts/steps/70_zip.sh`. The host: `_results.py` (`Display`, `_ResultHost`, the budget, `_check_results` for the keywords), `_call.py` (the fields in 164's helper, `_CheckedCall.results`, the result host's maker, the argv), `_sessions.py` (`_arm`), `runner.py` (the keywords; the pull request states its length; `_checked` stays at or under 80), `__init__.py`. Also `tests/public_api.txt`, `LONG_FUNCTIONS`, the two test files, Decision 13's documents and the news file.

## Scope

Out: displays streamed while the guest runs; an `IPython.display` stand-in (a module named after a package the zip does not carry); `image/jpeg` (no JPEG in Pillow yet; the 0.1.3 spike); a per-turn change of mode; the command line's `--results`; display ids and `update_display`.

## Acceptance criteria

1. **Seen failing first.** Each row of Decision 12, named in the pull request with its failing line. READ.
2. **The rows** of Decision 12 are green on Linux, macOS and Windows in the pull request's run, labelled `ci:full`. EXECUTED.
3. **The contract.** `git diff dev -- tests/public_api.txt` shows `Display`, the two fields, and `results` and `figures` on `run`, `run_async` and `Session`, nothing else. The news file claims it and the three entry points' rises, and no other length. READ.
4. **The structure.** `tests/checks/test_rules.py` is green, with `_results.py` within its bound. EXECUTED.
5. **The artifact set.** `MANIFEST` carries the new hashes. The news file's `grows` names every GROWTH row, by prefix where a family moves together, with one reason: the bootstrap reads the option on every call, and both binaries and the zip grow, their bytes claimed as measured. READ.
6. **The documentation** pages of Decision 13 exist and `uv run pytest tests/lint` is green. EXECUTED.
7. **The run.** The fast tier and `ci-status` are green, and no accepted pass is lost. The landing notes cite the pre-build review and the pull request's review. READ.

## Landing notes

Built 2026-10-31, before its pull request and review; the run, the review and the merge are added at the landing.

**What was built.** `src/wasi_python/_results.py` (`Display`, `_ResultHost`, `_check_results`, `_flag`, `_door_hosts`; 269 lines), the fields in 164's `_call._completed`, `_CheckedCall.results`, the door's hosts made by `_results._door_hosts` in `_call._instance` and `_sessions._arm`, and the keywords in `runner.py` (1,476 lines). The guest: `recipes/reactor_bootstrap.py` (`_take_mode`, `_set_mode`, `_show`, `_cell_begin`, `_cell_end`), `recipes/guest/host/display.py` and `figures.py`, both added to the zip by `scripts/steps/70_zip.sh`. Lengths: `run` 173→182, `run_async` 208→217, `Session.__init__` 178→187 (claimed); `_instance` 147→146; `_checked` 79→80, with the cancel check moved to `_limits._check_cancel` (which `Session._turn_args` now shares); `_turn_inside` 73→74 (the result host read back from the turn's call), against Decision 11's "grow by no line"; both within 80.

**Seen failing first.** Unit rows (`tests/unit/test_results.py`, 35): on `dev`'s `src/` (d64f8146), collection fails, `TypeError: _CheckedCall.__init__() got an unexpected keyword argument 'results'`. Goal rows (`tests/checks/test_v1_4_results.py`, 11) on `dev`'s code and set: seven `TypeError: run() got an unexpected keyword argument 'results'`, three the same for `Session.__init__`, and `test_without_results_stdout_is_todays` `AttributeError: 'Completed' object has no attribute 'value'`. Logs under the worktree's `build/163/`.

**The local set.** First on d64f8146's pins plus this change: python.wasm 99,442,041 bytes (+4,736 against `dev`'s), python-snapshot.wasm 104,566,690 (+8,726), python-stdlib.zip 53,922,068 (+6,794); on it the eleven goal rows passed at their first run, and with them `test_v1_4_checkpoint`, `_prepare`, `_starting_image`, `_sessions`, `_public_api` and `test_v1_1_artifact_set`. Then, for the review's round, on 166's pins: python.wasm 99,497,353, python-snapshot.wasm 104,598,221, python-stdlib.zip 53,836,201, against a build of steps 60 to 90 with `dev`'s bootstrap and zip step (its python.wasm is the accepted `a1137950`): +4,800, +7,095 and +7,004 bytes. The 163 goal rows, `test_v1_4_checkpoint`, `_public_api` and `_sessions` pass on it (73), and of 80 fuel and bytes rows sampled on both sets (`test_v1_4_embedding`, `_prepare`, `_starting_image`, `test_v1_2_portable_and_sealed`, `test_v1_1_artifact_set`), 75 grew by 0.002 to 2.7 percent and three fell by at most 0.012: every call's start runs the mode's read.

**The pre-build review's last Low.** A `run` from a checkpoint sets the mode both ways, as `_setup` does: `_reactor.run` calls `_set_mode` at every start, so a call without `results=` from a results session's checkpoint prints, has no `display` and has Agg back (`test_a_fork_of_a_checkpoint_takes_its_own_starts_mode`).

**The builder's readings, for the review.**
1. The pre-read bound is 6 × the room left plus 1 KiB for a frame's keys and its list of cut types (`ENVELOPE`). Decision 7 says 6 × the room; without the kibibyte a small room refuses even a display whose text fits, since the envelope alone is near 100 bytes. Once the 1,000 records are spent the bound is the kibibyte alone (the tool frame's cap under tools), and a longer frame is answered `"kept": false` unread (the pull request's review, Low 1). Under tools, a frame past both caps is refused `too_large` as a frame, and `truncated` does not name `"displays"` for it (Low 2): it is counted in neither record, which `tool-protocol.md` says.
2. Every frame the result host answers itself counts as a record: a kept display, a `too_large`, a `protocol` refusal. So a loop of forged frames ends at 1,000 records as a loop of displays does. Tool frames go to the tool host and count only there.
3. `text/plain` is always `repr(obj)`; a bundle's own `text/plain` is ignored, as Decision 2's "(always, the repr)" reads.
4. `display(fig)` of a matplotlib `Figure` adds its PNG, as Jupyter's formatter does; the backend's `show()` and the end of a cell use the same rendering.
5. The guest prints a display's text against no host, a door fault, an answer not in protocol 1, or a refusal other than `too_large`; it stops silently after `"kept": false`, a `too_large` with no room, or a second `too_large`.
6. A set without `host/display.py` is not refused: its bootstrap skips `-Xhost-results` as any `-X` option, so `results=True` there prints the value and returns none. An `ArtifactsMissing` like `tools=`'s would need a second manifest line; not built.
7. The figures flushed at a cell's end in figures mode are flushed whatever backend the program chose, as Decision 9 reads; `show()` sends them only under `host.figures`.
8. The result host reaches the tool protocol's frame rules through one late import in its constructor (`tests/unit/test_runner_package.py`'s `LATE` lists it), so `import wasi_python` still loads no tool module.
9. 162's results-mode row (a fork of a checkpoint in either mode) is carried here, as 162's pull request said the second to land would.
10. A value's `repr` is taken in the bootstrap's `_show` and handed to `host.display._value`, so a `repr` that raises shows the user's frames only, as the hook shows them (the review's Low 3; `test_a_repr_that_raises_is_reported_as_the_hook_reports_it`). `Display` sets `__hash__ = None` and says why (Low 6).

## For the owner to decide

1. **Amend constitution §4.4** (recommended): "On top of the door the project may ship one tool protocol, through which a guest calls the host's tools, APIs and MCP servers and hands the host its displays: optional, used only when the embedder passes its tools or asks for results, every tool call gated by the embedder; a display calls nothing of the host's." A reserved file descriptor needs none, but is a second channel with its own parser and bound.
2. **The budget**: displays take one `output_bytes` beside each stream (recommended), or a `display_bytes` default.
