# 060 — A per-run budget of request bytes

- **Status:** drafted 2026-10-18; awaiting its pre-build review. It changes neither the guest's
  imports nor its exports, the artifact set nor the build recipe, so §5.6 does not require a
  review before build; one is asked because it adds a limit and a public knob, and answers a
  security review's finding. Drafted on `spec/060-a-per-run-budget-of-request-bytes` from main
  `5e66995`.
- **Owner:** Clay Gendron
- **Kind:** runner and docs; **parallel-safe**: `src/` and `tests/` only, with `README.md`,
  `CHANGELOG.md` and this specification. No build-class file: it touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or workflow, and not the guest package
  (`recipes/guest/host/`). **It changes the public API** (spec 049, Decision 13): Decision 9
  lists the four snapshot lines it adds and the rule that allows each. A judge change: new
  checks, and `tests/public_api.txt` regenerated. The code: `src/wasi_python/tools.py`
  (`_ToolHost.__init__` and `admit`; `_bound_keywords`), `src/wasi_python/runner.py`
  (`Defaults`, `run`, `run_async`, `_checked`, `_check_tools`, `_tool_host`).
- **Depends on:** 056 (the a4 security review's findings: its Decision 4 names this
  specification; its `_bound_keywords` is what N8's fix changes), 049 (the public API frozen:
  the snapshot, the docstring rules, `defaults()` read once per call), 053 (async tools: the
  frame host's present signature), 036 and 031 (the frame host, `admit`, `max_tool_calls`), all
  landed. 055 (bounded sessions) is not landed; Decision 7 says how the two meet.
- **Research it stands on:**
  - `../research/2026-10-18-a-per-run-budget-of-request-bytes.md` (EXECUTED: the host's CPU per
    admitted frame by shape, a refused frame's cost, the guest's fuel to re-send, a flooding
    guest through `run` with and without a prototype budget, the bytes every tool check and unit
    sends per run, and N8 reproduced with a prototype fix; scripts and output beside it);
  - the 0.1.0a4 security review, `build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md`
    in the main tree (git-ignored): F3, and its Confirmation's item 2, N8; and its a5 addendum,
    `0.1.0a5-addendum-2026-10-18.md` beside it: "F3 and N8 follow the release, before 0.1.0
    final";
  - `056-the-a4-security-reviews-findings.md`, Decision 4: "a per-run budget of request bytes,
    its default, and its knob, checked in `admit` from the frame's length before the bytes are
    read".

## The problem

**F3 (medium-low).** Each tool frame the door admits, up to 1 MiB, is copied out of guest memory
and parsed and validated in Python on the door's thread, holding the GIL. One worst-shape 1 MiB
frame costs the host 0.31 s of CPU on the research's Mac and 0.27 to 0.65 s on the review's;
re-sending it costs the guest about 1,400 to 3,000 fuel, noise against a run's 178 million (the
research, §2). Nothing bounds the bytes of one run's frames. `max_tool_calls` (1,000) allows far
more frames than the default deadline can hold, so the deadline is the only bound: a guest can
keep one host thread busy for its whole 60 s (about 190 worst-shape frames on the research's
Mac). Under `run_async` with several workers, several such guests contend with the event loop.
The README states this today, in *Tools* ("The host's cost per frame") and *Not protected*.

**N8 (a note).** `tool()` still publishes a `functools.partial`'s bound values for one
construction: a callable object whose class's `__call__` is another callable object, whose
class's `__call__` is the partial, with `__annotations__` hand-copied onto the middle object so
the hints read. `_bound_keywords` follows `type(obj).__call__` once; `inspect.signature` follows
it to any depth. Reproduced on main at depth 2 and 3 (the research, §8). The review: "No
embedder writes it by accident", and "it can follow the release".

## Decisions

1. **The budget counts admitted bytes, checked in `admit` before the frame is read.**
   - **Admitted** means the lengths `admit` lets through: the frames the door then copies and the
     frame host parses. That is exactly F3's cost. A frame refused in `admit` (past
     `max_tool_calls`, over 1 MiB, or past this budget) is never read and costs 2.85 µs whatever
     its length (the research, §2 B), so it spends nothing.
   - **The rule:** a frame is refused when the bytes already admitted plus its length would pass
     the budget. So the bytes one call's frame host reads never pass it; a frame that fits is
     admitted whatever was refused before it; and a frame that exactly reaches the budget is
     admitted.
   - **Whatever the answer.** An admitted frame spends its length whether it is answered `ok`,
     `protocol`, `unknown_tool` or `invalid_arguments`: the parse is the cost.
   - **Why not every frame's length.** It would count bytes never read, so it would measure the
     guest's claims, not the host's work. The judge already sends one frame that claims 1 GiB
     (the research, §3).
   - **Why one knob, not two.** Counting raw lengths too adds no bound the admitted count lacks,
     and §4.15 asks a default for every knob.
   - This is spec 056, Decision 4's design, unchanged.

2. **The default is 16 MiB (16,777,216 bytes).**
   - **The bound it gives.** 16 frames at the 1 MiB cap. The worst shape then costs about 5 s of
     host CPU on the research's Mac and about 10 s on the review's, a sixth of the default
     deadline at worst. Today the worst is the whole deadline. The research's prototype cut a
     40-frame flood from 12.50 s of frame-host CPU to 4.94 s, with the 24 frames past the budget
     never read.
   - **No legitimate workload meets it.** Every tool check and unit was tallied: through `run`,
     no call admitted more than 63,300 bytes, and the median call 77 (the research, §4). The
     README's recipes send tens of bytes per frame. 1,000 frames averaging 16 KiB fit, so at the
     default `max_tool_calls` a guest whose frames average under 16 KiB meets the frame limit
     first.
   - **A number embedders know.** The default output cap per stream and the answer cap per frame
     are 16 MiB too.
   - **Rejected:** 4 MiB (three full frames is tight for a guest that sends a file through a
     tool); 64 MiB (about 42 s worst on the review's Mac: no real bound). Bulk data belongs on a
     writable mount (spec 034), whose provider gets it without a JSON parse; the README says so.
   - **It needs no owner's decision.** It is a new, tighter limit, and §4.15 asks the owner only
     for a looser default. Spec 049, Decision 8 lets an alpha change anything; after 0.1.0 it
     would still be allowed in a minor release, by both of that decision's exceptions (a tighter
     default, and security).

3. **It fails as the frame limit fails: `budget_exceeded`, and the guest runs on.**
   - The frame host answers `budget_exceeded`, an existing kind, so the guest gets
     `ToolBudgetExceeded`, as for `max_tool_calls`. The guest package already maps the kind
     (`recipes/guest/host/tools.py`), so neither the guest nor the artifact set changes, and
     protocol 1 gains no kind. `PROTOCOL` stays 1.
   - The record lists the refusal as `admit` lists its other refusals: `op=None`, `tool=None`,
     the frame's `request_bytes`, the answer's `response_bytes`.
   - **The message names bytes**, so a guest and an embedder can tell it from the frame limit:
     "this run allows 16777216 bytes of tool requests; 16000000 are used, and this frame is
     800000". Messages are not promised (spec 049, Decision 8).
   - **The order in `admit`:** past `max_tool_calls` first, as today; then `too_large` (a frame
     over 1 MiB stays `too_large` and spends nothing); then this budget.
   - **Not a trap.** `max_file_calls` ends a run ("out of file calls") because a file call
     cannot be refused without breaking the guest's libc. A tool call can be refused cleanly,
     so the run goes on; each further frame costs only `admit`, and `max_tool_calls` and the
     deadline still bound them.
   - **No new record field.** `ToolOutcome.request_bytes` already gives each frame's length. At
     the default `max_tool_calls` every frame is listed, so the admitted total is the sum over
     the outcomes `admit` did not refuse. A total field would be one more public name to
     freeze for a number the record already gives.

4. **The knob: `max_tool_request_bytes=` on `run` and `run_async`, and
   `Defaults.tool_request_bytes`.**
   - **The names.** `tool` groups it with `max_tool_calls` and says it needs `tools=`.
     `request_bytes` is the record's own word (`ToolCall.request_bytes`,
     `ToolOutcome.request_bytes`), and tells it from the answer's 16 MiB cap, which this budget
     does not touch. `max_tool_bytes` was shorter but ambiguous.
   - **Its values**, by `_integer_limit`'s rules, as `max_tool_calls`: an integer from 0 to
     2**63 − 1, or `None` for no limit. `True` is a `TypeError`; a negative number or 2**63 is a
     `ValueError` naming `max_tool_request_bytes` (in `Defaults`, `tool_request_bytes`). 0
     refuses every frame, the guest's discovery included, as `max_tool_calls=0` does.
   - **It needs `tools=`.** Given without it, `run` raises `TypeError` before any work: "the raw
     door has no limit; pass tools=", as for `max_tool_calls`. The raw `host=` is the embedder's
     own code, which parses its own frames.
   - **Unset, it takes `defaults().tool_request_bytes`** from the call's one read of the
     defaults: `_check_tools` already receives that read (`limits`), so the count of reads per
     call stays one (spec 049, criterion 10).
   - **Placed last.** The keyword goes after `max_tool_calls`, the last keyword of `run` and of
     `run_async`; the field after `tool_calls`, the last field of `Defaults`, with its default.
     Both are what spec 049, Decision 8 lets a minor release add.
   - **Documented** by spec 049, Decision 10's rules: an `Args:` entry in `run` and in
     `run_async`, an `Attributes:` entry in `Defaults`.

5. **The private frame host takes `max_bytes`, default `None`.** `_ToolHost(…, max_bytes=None)`
   keeps the count; the runner's `_tool_host` passes `c["tool_request_bytes"]`. The default is
   `None`, not 16 MiB, so the one source of the default is `defaults()`, and the units that drive
   a `_ToolHost` directly to test something else (the record's bound sends 16.1 MB) are not
   changed. A raw `host=` that serves a `_ToolHost` (a private use) admits each frame in
   `__call__`, which counts the bytes the same way.

6. **No command-line flag.** `wasi-python run` has `--deadline-s`, `--memory-bytes`,
   `--output-bytes` and `--fuel`, and neither `--max-tool-calls` nor `--max-file-calls`: the
   command cannot offer a Python function as a tool (READ, `src/wasi_python/cli.py`). Its
   options are frozen by spec 049, Decision 7, and this adds none.

7. **Sessions (spec 055, not landed): per turn, set once on the session.** 055 gives each turn a
   new frame host, so `max_tool_calls` bounds each turn, "set once on the session". Its rule for
   arguments `run` gains (a session takes every argument of `run` but `argv`, `stdin` and
   `cancel`) covers this one: `max_tool_request_bytes` bounds each turn, set once on the
   session. A session's total is then bounded by its turns and its `lifetime_s`. Whichever of
   055 and 060 lands second adds the keyword to `Session`, to 055's table of what is per
   session and per turn, and to its snapshot lines; 060 most likely lands first, since 055 is
   late in the build-class queue.

8. **N8: `_bound_keywords` follows `__call__` on every hop, and stops where `inspect` stops.**
   - On each hop that is not a partial, a bound method, a `__wrapped__` link, a function, a
     builtin or a class, the walk follows `type(target).__call__`, as `inspect.signature` does,
     and no longer only once.
   - It stops when that `__call__` is missing or is one of C's slot types
     (`types.WrapperDescriptorType`, `types.MethodWrapperType`, `types.MethodDescriptorType`,
     `types.BuiltinFunctionType`, `types.ClassMethodDescriptorType`). Those carry no partial,
     and `inspect` skips the same types (`_signature_get_user_defined_method`). Without this
     stop, a C callable such as `operator.itemgetter(0)` would walk its slots' own `__call__`
     to the 64-link limit and be refused, where today it is not.
   - The walk stays bounded by `_WRAPPER_DEPTH` (64): a `__call__` cycle is refused with the
     walk's `TypeError`, as a `__wrapped__` cycle is.
   - `_type_hints` is unchanged. The fix only adds the bound names to `Tool._fixed`; spec 056's
     rules then leave them out of the schema, the descriptor and `stubs()`, and refuse a frame
     that names them.
   - The research's prototype of exactly this walk hid the bound keywords at depth 2 and 3,
     described a function, a callable object, a bound method and a partial as before, and
     ended at once on `operator.itemgetter(0)`.

9. **The snapshot's lines** (spec 049, Decision 13). It adds four lines to
   `tests/public_api.txt` and removes or changes none:

   | line | where | allowed by (049, Decision 8) |
   |---|---|---|
   | `  field tool_request_bytes: int \| None = 16777216` | `dataclass Defaults`, after `tool_calls` | before 0.1.0, any change; after it, a field placed last with a default, and a tighter default |
   | `  param max_tool_request_bytes: int \| None = <default>  keyword-only` | `def run`, after `max_tool_calls` | a keyword-only argument; its default is a tighter limit (exception 1) and closes F3 (exception 2) |
   | the same line | `async def run_async`, after `max_tool_calls` | the same |
   | `default tool_request_bytes = 16777216` | after `default tool_calls = 1000` | a tighter default (exception 1) |

   The README's generated reference changes in the entries for `Defaults`, `run` and
   `run_async`, by `tests/harness/api.py --write`. The CHANGELOG gains a Security line
   (Decision 11). The landing uses `--accept-judge`.

10. **Checks first, by counts.** Each new check is seen failing on main `5e66995` before the
    code changes, and against its named stand-ins after. No check measures time: the units
    count `_parse` calls, frames and answers; the guest check counts outcomes and tool runs.

11. **The README and the CHANGELOG.**
    - *Tools*, **Limits**: a third limit, "at most `max_tool_request_bytes` bytes of admitted
      requests per call (default `defaults().tool_request_bytes`, 16 MiB; `None` means no
      limit), counted from each frame's length before it is read; past it the guest gets
      `ToolBudgetExceeded` and runs on". Bulk data belongs on a writable mount.
    - *Tools*, **The host's cost per frame**: rewritten. The per-frame cost stays; "No limit
      bounds the bytes of one run's frames yet" becomes the budget's bound (about 5 to 10 s of
      host CPU at the default on an arm64 Mac, for the worst shape), with the advice to lower it,
      with `max_tool_calls` and the deadline, where many untrusted guests run at once.
    - *Tools*, **What `run` refuses**: `max_tool_request_bytes=` without `tools=` joins `gate=`
      and `max_tool_calls=`.
    - *The tool protocol*, the kinds table: `budget_exceeded` reads "the run's frames are used
      up (1,000 by default), or its request bytes (16 MiB by default)".
    - *Safety*, **Not protected**: the entry "host CPU spent parsing and checking tool frames, up
      to the call's deadline" becomes "up to the call's request-byte budget (16 MiB by default;
      `None` lifts it, and then the deadline bounds it)".
    - The API reference: regenerated (Decision 9).
    - `CHANGELOG.md`, the 0.1.0a6 section: one **Security** bullet: "A per-run budget of tool
      request bytes (spec 060; the 0.1.0a4 security review's F3): `max_tool_request_bytes=` on
      `run` and `run_async`, and `Defaults.tool_request_bytes`, default 16 MiB, counted from
      each frame's length before it is read; past it the guest gets `ToolBudgetExceeded`. A
      tighter default: a program that sends more than 16 MiB of tool requests in one call
      passes a larger value or `None`." And one more in the same bullet or the next: "`tool()`
      finds a partial's bound keywords through a `__call__` chain of any depth (the review's
      N8)."

## Intent

One call's tool frames cost the host a bounded amount of parsing, whatever the guest sends:
16 MiB of admitted requests by default, counted before a byte is read, with a knob the embedder
sets like every other limit. And a partial's bound value stays hidden however deep the callable
objects around it nest.

## Design

```
src/wasi_python/tools.py      _ToolHost(max_bytes=None): a count of admitted bytes; admit refuses
                              a frame whose length would pass it (after the frame limit and the
                              1 MiB cap), answering budget_exceeded with op=None;
                              _bound_keywords follows type(obj).__call__ on every hop, stopping
                              at C slot types (N8)
src/wasi_python/runner.py     Defaults.tool_request_bytes = 16 << 20 (checked in __post_init__);
                              run and run_async: max_tool_request_bytes=_UNSET, passed to
                              _checked; _check_tools: the keyword refused without tools=, read
                              from the same limits, checked by _integer_limit, returned as
                              "tool_request_bytes"; _tool_host passes max_bytes=
tests/unit/test_tools.py              criterion 1 (the count in admit)
tests/unit/test_runner_tools.py       criterion 2 (the knob and its default)
tests/checks/test_v1_4_embedding.py   criteria 3 and 4 (v1.4: the budget through run; N8)
tests/public_api.txt          four lines added (Decision 9), by tests/harness/api.py --write
README.md                     Tools (Limits, the host's cost per frame, what run refuses); the
                              protocol's kinds table; Not protected; the API reference
CHANGELOG.md                  0.1.0a6: one Security entry
```

In `admit`, as a sketch (the builder writes the code):

```
seq = self._frames = self._frames + 1
if max_calls is not None and seq > max_calls:     -> budget_exceeded, "tool frames"
elif length > _TOOL_REQUEST_BYTES:                -> too_large
elif max_bytes is not None and self._admitted + length > max_bytes:
                                                  -> budget_exceeded, "bytes of tool requests"
else: self._admitted += length; pending = (seq, length); return None
```

## Scope

In: Decisions 1 to 11.

Out, each with its reason:
- **Answer bytes.** An answer is made by the embedder's own tool, capped at 16 MiB per frame,
  and encoded on the work thread; the guest does not choose its cost.
- **The raw `host=` door.** It is the embedder's own function (Decision 4).
- **A per-process budget** across calls: the runner keeps no state between calls, and one
  call's budget must not starve another's (the reason spec 036 gave for abandoned threads).
- **The per-frame fixed cost** (about 20 µs for a small frame): `max_tool_calls` bounds it
  (1,000 × 20 µs).
- **A lower default `max_tool_calls`**, which the review offered as an alternative: the byte
  budget bounds the cost without cutting chatty, legitimate guests' calls.
- **A total in `ToolRecord`** (Decision 3).
- **The guest's `ToolBudgetExceeded` docstring** ("all the tool calls it may make"): it is in
  `recipes/guest/host/__init__.py`, build-class; the next change to the guest package widens it
  to "its tool calls or its request bytes". The message the guest reads already names bytes.
- **`Session`'s keyword:** 055's, or this one's if 055 lands first (Decision 7).
- **F4** (the release ties what it signs to what it built): spec 057.

## Acceptance criteria

Each check is written before the code and seen failing on main `5e66995`; each named stand-in
(a mutant of the built code) is applied, its checks run and seen failing, and the file restored.
The landing notes list each with its failing line.

1. **`test_the_request_byte_budget_counts_admitted_bytes`** (unit, `tests/unit/test_tools.py`,
   no artifacts). `_parse` is wrapped to count its calls. A `_ToolHost` with `max_bytes=1000`:
   - a frame of 600 bytes is admitted and answered (1 parse);
   - `admit(401)` returns a `budget_exceeded` answer whose message names "bytes", nothing is
     pending, and the outcome has `op=None` and `request_bytes=401` (still 1 parse);
   - `admit(400)`, exactly reaching 1000, is admitted (2 parses after its frame);
   - `admit(1)` is refused (2 parses);
   - `admit(_TOOL_REQUEST_BYTES + 1)` on a fresh host with `max_bytes=_TOOL_REQUEST_BYTES` is
     `too_large`, and a frame of `_TOOL_REQUEST_BYTES` bytes is then still admitted;
   - the raw path, `host(frame)` with no `admit` before it, counts the same way;
   - with `max_calls=1, max_bytes=0`, frame 1 is refused with the bytes message and frame 2
     with the frames message;
   - `max_bytes=None` (the private default) admits 2,000 frames of 1,000 bytes (2,000 parses).

   Seen failing on main: `_ToolHost` takes no `max_bytes`. Stand-ins:
   - (a) every frame's length counted, refused ones included: the 400-byte frame after the
     refused 401 is refused;
   - (b) `>=` for `>`: the frame that exactly reaches the budget is refused;
   - (c) the check made in `__call__`, once the door has read the frame: `admit(401)` returns
     `None`;
   - (d) the budget checked before the 1 MiB cap: the over-cap frame is `budget_exceeded`.
2. **`test_the_request_byte_budget_is_a_limit_with_a_default`** (unit,
   `tests/unit/test_runner_tools.py`, no artifacts; artifact lookups counted, as 053's criterion
   1 counts them):
   - `Defaults(1 << 30, 60.0, 16 << 20).tool_request_bytes == 16 << 20`, and
     `wasi_python.defaults().tool_request_bytes == 16 << 20`;
   - `Defaults(…, tool_request_bytes=None)` is accepted; `-1` and `2**63` raise `ValueError`,
     `True` raises `TypeError`, each naming `tool_request_bytes`;
   - `_checked` with `tools=[noop]`: unset gives 16 MiB; `5` gives 5; `None` gives `None`;
     `True`, `-1` and `"1"` raise, naming `max_tool_request_bytes`;
   - `run(["-c", "pass"], max_tool_request_bytes=5)` without `tools=` raises `TypeError` with 0
     lookups, and so does `run_async`'s, with 0 submits;
   - after `set_defaults(replace(defaults(), tool_request_bytes=7))`, `_checked` gives 7; the
     old defaults are restored in a `finally`;
   - `_tool_host` of a checked call builds a frame host whose byte budget is the call's value.

   Seen failing on main: `Defaults` has no such field. Stand-ins: (e) the field's default
   `None`; (f) `_tool_host` passes no `max_bytes`; (g) `_check_tools` reads `tool_request_bytes`
   with a second `_current_defaults()` call, which spec 049's
   `test_set_defaults_changes_what_run_reads` must fail ("run reads the defaults once").
3. **`test_the_request_byte_budget_holds`** (v1.4, `tests/checks/test_v1_4_embedding.py`,
   through `run`). A counting tool `store(data: bytes) -> int` returns `len(data)`. The guest
   calls `tools.store(b"x" * 300_000)` three times, then `tools.store(b"ab")`, catching
   `ToolBudgetExceeded`, and prints what it saw. With `max_tool_request_bytes=1_000_000`:
   - the guest prints `[300000, 300000, 'budget', 2]` and exits 0;
   - the outcomes are `ok` (discovery), `ok`, `ok`, `budget_exceeded`, `ok`; the refused one has
     `op is None` and a message naming "bytes";
   - the tool ran 3 times;
   - the request bytes of the outcomes not refused sum to at most 1,000,000.

   The same program with no keyword (the default) prints `[300000, 300000, 300000, 2]`: the
   default does not meet a 1.2 MB call. Seen failing on main (the keyword is a `TypeError`).
   Stand-ins: (h) no budget passed to the frame host (four results); (c) as above (the refused
   outcome's `op` is `"call"`).
4. **`test_a_call_chain_of_any_depth_hides_bound_keywords`** (v1.4, no artifacts). N8's
   construction at depth 2 and 3, each hop a class whose `__call__` is the next object, the last
   class's `__call__` a `staticmethod(functools.partial(orders, user_id=42, api_key=SECRET))`
   (a `staticmethod`, so Python 3.11 to 3.14 call it the same way), and `orders`'
   `__annotations__` copied onto every object:
   - the schema's properties are `{"limit": …}` only; `SECRET` is in no descriptor and no stub;
   - through a `_ToolHost`, a frame naming `user_id` is `invalid_arguments` with the
     unknown-argument message, and the tool does not run; a frame with `limit=3` runs it once,
     with `(42, SECRET, 3)`;
   - `_bound_keywords("t", operator.itemgetter(0))` is empty, and a plain callable object still
     describes its own parameters;
   - an object whose class's `__call__` is the object itself is refused with `TypeError`
     ("nest deeper").

   Seen failing on main (depth 2 publishes `api_key` and `user_id` with their values). Stand-ins:
   (i) the walk follows `__call__` once (main's walk); (j) the walk follows `__call__` on every
   hop without the stop at C slot types (`itemgetter` raises `TypeError`).
5. **Nothing else moves.** The fast tier while building, then the full judge once, in the
   worktree, without `--accept`, against the frozen set `s-c4190ca065ada03a` (or the lane's
   current one): v1.4 gains exactly the two new checks; the unit suite gains the two units; no
   pass is lost and nothing grows; no existing check meets the new default (no `budget_exceeded`
   where there was none). `test_the_public_api_matches_its_snapshot` passes after
   `tests/harness/api.py --write`, and the snapshot's diff is exactly Decision 9's four lines;
   `test_every_public_name_is_documented`, `test_the_readme_reference_matches_the_api` and
   `test_set_defaults_changes_what_run_reads` pass. `ruff check` and `ruff format --check` are
   green on `src/` and `tests/`.
6. **The research's flood, re-run on the built tree** (a benchmark fact, recorded in the landing
   notes, not a check): `bench060.py`'s part C with the prototype removed and the real default in
   force reads 16 of 40 frames and answers 24 `budget_exceeded`.
7. **The README and the CHANGELOG** carry Decision 11's text.

## Landing notes

Not built yet.
