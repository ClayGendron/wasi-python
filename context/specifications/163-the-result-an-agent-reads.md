# 163: The result an agent reads

- **Status:** drafted 2026-10-30, to be reviewed before it is built (a change to the public API; **structural**; and the build recipe, since the reactor's bootstrap and the stdlib zip change). The owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3"). Decision 4 needs the owner's amendment of constitution §4.4 first (the last section).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **structural**: a public class, two `Completed` fields, a module `src/wasi_python/_results.py` (at most 400 lines), and the listed lengths of `runner.py:run`, `run_async` and `Session.__init__` raised by two keywords each and claimed (spec 142). Build recipe (constitution §5.6): `recipes/reactor_bootstrap.py`, two new zip files under `recipes/guest/host/`, `scripts/steps/70_zip.sh`; both binaries, the zip, `MANIFEST` and `SHA256SUMS` change. No pin, no patch, no new guest import or export.
- **Depends on:** landed 031 and 036 (the tool protocol and its host), 055 (sessions), 129 (output from a pipe), 142 (the allowance), 150 and 157 (a call from an image). In flight: 164 (the same three entry points and `Completed`; Decision 11), 162 (a checkpoint keeps the session's mode; 162 says so), 167 (plotly's `_repr_mimebundle_` gives an HTML display once it lands).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§1, item 2; §2, item C). The owner's notebook app `test_app/` (untracked; `app/driver.py`, `app/main.py`), READ as the need, nothing copied. `../research/2026-10-22-how-the-market-describes-sandboxed-python.md` §4.

## The problem

An agent that runs `df.describe()` wants the table back, as text and HTML; a cell that draws a chart wants the chart. Today a call returns two byte streams (`src/wasi_python/_call.py:61-91`). A session turn already evaluates its last expression apart (`recipes/reactor_bootstrap.py:291-308`), but only to print its `repr` through `sys.displayhook`. A `run` of `-c` code has no value at all.

The owner's notebook app built the rest by hand (READ): a guest driver that splits off the last expression, calls `_repr_html_` and `_repr_svg_`, defines `display()`, and sends every record over stdout behind a 0x1E marker for the host to parse back. So a program that prints a 0x1E byte and some JSON forges a record, and a record over the output cap is cut mid-JSON. Every hosted interpreter returns a typed result instead (the memo, §1, READ).

## Decisions

### 1. Opt-in: `results=` and `figures=`

`run`, `run_async` and `Session` take `results: bool = False` and `figures: bool = False`. With `results=True` a call or turn returns its value and displays (Decisions 2 and 3). `figures=True` adds matplotlib's figures (Decision 9). Off is the default, because the records are a channel from guest to host and none opens without an explicit argument (constitution §4.15). For a session the mode is the session's: the guest learns it at the first turn (Decision 5).

`figures=True` without `results=True` is a `TypeError`, as `gate=` without `tools=` is (`runner.py:753`). So is `results=True` with `host=`: the raw door is the embedder's, and the runner reads no frame of it (Decision 4).

### 2. The record: `Display`

```python
@dataclass(frozen=True, slots=True)
class Display:
    data: Mapping[str, str | bytes]  # MIME type -> content, read-only
    truncated: tuple[str, ...] = ()  # the MIME types cut or dropped at the bound
    stdout_at: int = 0               # bytes the guest had written to stdout before it
    stderr_at: int = 0
```

The MIME types kept are `text/plain` (always: the `repr`), `text/html`, `text/markdown`, `image/svg+xml`, `application/json` (its JSON text, a `str`) and `image/png` (`bytes`). The guest reads `_repr_mimebundle_` first, then `_repr_html_`, `_repr_markdown_`, `_repr_svg_`, `_repr_json_` and `_repr_png_`, as a notebook does. A method that raises, or returns the wrong type, is skipped. Other MIME types are dropped. Keys are Jupyter's.

### 3. `Completed.value` and `Completed.displays`

`Completed` gains `value: Display | None = None` and `displays: tuple[Display, ...] = ()`, after `image_sha256`.

`value` is the last expression of a session turn, or of a `-c` program, when it is not `None`. In results mode it is no longer printed: it goes to `value` alone, and `builtins._` is still bound, as `sys.displayhook` binds it. A script or `-m` program has no value; its displays still arrive. Without `results=True`, both fields keep their defaults and every byte of stdout is as today.

### 4. Over the door, as one more operation of the tool protocol

`display()` sends one frame, `{"v": 1, "id": n, "op": "display", "value": false, "data": {...}, "truncated": [...]}`, PNG bytes as the protocol's `{"$bytes": "<base64>"}`. The bootstrap sends the value with `"value": true`.

`_results._ResultHost` answers `display` and hands `list` and `call` to the call's `_ToolHost`; with no tools it answers them `protocol`, "this run has no tools", so `from host import tools` still raises `ImportError`. Display frames are not in `Completed.tools` and spend no tool call and no tool request byte. It is wired where the tool host is: `_call.py:455-458` and `_sessions.py:694-697`.

The protocol stays version 1: `display` is an operation a host may not serve, and against one that refuses it the text is printed (Decision 6). Constitution §4.4 says the protocol is "used only when the embedder passes its tools"; this widens it to "or asks for results", still one protocol over one door.

### 5. How the guest learns the mode: `-Xhost-results`

The runner puts `-Xhost-results`, or `-Xhost-results=figures`, first in the caller's argv, after any import prelude (`_call._import_prelude`, `_call.py:386`). The bootstrap's `run` and the session's `_setup` read it and remove it before the program sees `sys.argv` or `sys.orig_argv`. `-X` is CPython's channel for implementation options and leaves the embedder's environment alone; a host that passes none gets today's behaviour. An embedder's argv that holds it is a `ValueError` naming `results=`.

### 6. `display()` lives in the zip

`host/display.py` holds `display(*objs)`. In results mode the bootstrap binds it into `builtins` as `display`, as IPython does, so agent code calls it without an import. Out of results mode it prints each object's text to stdout, as IPython's `display` does in a terminal, so one program runs either way. `display()` flushes `sys.stdout` and `sys.stderr` before its frame.

### 7. Bounds

A call's or turn's displays, its value included, share one budget: `output_bytes` decoded bytes (text as UTF-8, PNG as bytes), and at most 1,000 records (the tool record's number).

A frame is admitted by its length before it is read, against a fixed multiple of the room left (the JSON escape's worst case), then judged by its decoded bytes. Over the room, the host answers `too_large` with `"room": <bytes>`, and the guest sends it once more as `text/plain` alone, cut at a character boundary, the other types named in `truncated`. A record past the 1,000th, or with no room left, is dropped. In every such case `Completed.truncated` names `"displays"`, as it names a stream today.

### 8. Order beside the streams

A display carries `stdout_at` and `stderr_at`: the bytes the guest had written to each stream when it was called, kept or not. The host settles the capture (`_outputs._PipeCapture.settle`) before it reads them. With the cap keeping the head, `stdout[:d.stdout_at]` is what printed before `d`. Counting what was written, not what was kept, keeps the number true under 164's keep-the-tail option. `_outputs._Stream` gains `written` for it.

### 9. Figures

`host/figures.py` is a matplotlib backend module. Its canvas is Agg's. Its `show()` sends each open figure as a display, `image/png` plus the figure's `repr`, then closes them, as Jupyter's inline backend does. In figures mode the bootstrap sets `MPLBACKEND` to `module://host.figures` when the embedder's environment does not set it. matplotlib reads it at its first import, so a program's own `matplotlib.use()` still wins. Under an image that already imported `pyplot`, the bootstrap switches the backend once, at the first cell.

At the end of each cell, after an exception too, the figures still open are sent the same way, only if `matplotlib.pyplot` is in `sys.modules`, so a cell that never drew imports nothing. A trap runs no Python and sends none. The PNGs cost the call's fuel.

### 10. Trust

A display is the guest's output, as stdout is: its HTML and SVG are untrusted, and the documentation says to render them in a sandboxed frame. A program may call `display()` or `_host.call` with any frame it likes. What it cannot do is make printed bytes read as a record, since records never pass through a stream. If the program sends a value frame itself, the host keeps the last one of the cell.

### 11. Where this meets 164

The one place they meet is `Completed`: `value` and `displays` are appended after `image_sha256`, with defaults, and any field 164 adds goes after them; `truncated` may name `"displays"` beside 164's streams. `_Stream.written` is added by whichever lands first. 164's callback carries stream bytes only, never displays. Both raise the same listed lengths; the second to land rebases and lists what it measures.

### 12. The rows first

Unit rows, `tests/unit/test_results.py`: the frame's parse; the budget, room and `too_large`; the 1,000th record; `list` with no tools; and the `TypeError`s and `ValueError` of Decisions 1 and 5. Goal checks, `tests/checks/test_v1_4_results.py`: a turn's `df.head()` gives `text/plain` and `text/html` in `value` and nothing on stdout; a `-c` program's value; a display between two prints, ordered by `stdout_at`; a printed forged record leaves `displays` empty; a PNG over the room arrives as marked text; `plt.plot` gives one PNG display, and `plt.show()` before a print orders it; without `results=`, stdout is today's byte for byte; a call from an image; both binaries give the same records.

### 13. The documentation

`docs/how-to/results.md` is a new page. `docs/reference/results-and-errors.md` gains the two fields and `Display`. `docs/reference/tool-protocol.md` gains the `display` operation, `room` and `-Xhost-results`, for a host in another language. `docs/how-to/sessions.md:25` and `docs/how-to/matplotlib.md` follow.

## Intent

An agent's harness passes `results=True` and reads a cell's value and displays (text, HTML, PNG) as typed fields that no printed output can forge and no bound cuts mid-record.

## Design

The guest: `recipes/reactor_bootstrap.py` (the option read and removed, the value sent, `display` bound, figures flushed), `recipes/guest/host/display.py`, `recipes/guest/host/figures.py`, `scripts/steps/70_zip.sh`. The host: `_results.py` (`Display`, `_ResultHost`, the budget), `_call.py` (the two fields, `_CheckedCall.results`, the wiring, the argv), `_sessions.py` (`_arm`, `_turn_inside`), `_outputs.py` (`_Stream.written`), `runner.py` (the keywords), `__init__.py`. The judge and the record: `tests/public_api.txt`, `LONG_FUNCTIONS`, the two test files, the documents of Decision 13, the news file.

## Scope

In: the decisions above. Out: Displays streamed while the guest runs (164's callback carries streams); an `IPython.display` stand-in (a module named after a package the zip does not carry); `image/jpeg` (no JPEG in Pillow yet; the 0.1.3 spike); a per-turn change of mode; the command line's `--results`; display ids and `update_display`.

## Acceptance criteria

1. **Seen failing first.** Every row of Decision 12 fails before its code; the pull request names each with its failing line. READ.
2. **The rows** of Decision 12 are green on Linux, macOS and Windows in the pull request's run, labelled `ci:full`. EXECUTED.
3. **The contract.** `git diff dev -- tests/public_api.txt` shows `Display`, the two fields and the four keywords, nothing else. The news file claims it and the three raised lengths. READ.
4. **The structure.** `tests/checks/test_rules.py` is green, with `_results.py` within its bound. EXECUTED.
5. **The artifact set.** `MANIFEST` carries the new zip's hash and the bootstrap's. The fuel the goal rows move is claimed in the news file. READ.
6. **The documentation** pages of Decision 13 exist and `uv run pytest tests/lint` is green. EXECUTED.
7. **The run.** The fast tier and `ci-status` are green, and no accepted pass is lost. The landing notes cite the pre-build review and the pull request's review. READ.

## Landing notes

To be written at the landing.

## For the owner to decide

1. **Amend constitution §4.4** so the one tool protocol is "used only when the embedder passes its tools or asks for results" (recommended). The alternative carries records over a third channel, a reserved file descriptor. That needs no amendment, but it is a second channel the constitution does not name.
2. **The budget**: displays share one `output_bytes` beside each stream (recommended). The alternative is a separate `display_bytes` default in `Defaults`.
