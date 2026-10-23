# A per-run budget of request bytes, and N8

- **Status:** research, 2026-10-18. It commits the project to nothing. It feeds spec 060 (`../specifications/060-a-per-run-budget-of-request-bytes.md`).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the author of spec 060's draft. It wrote none of the code it reads. Box: 90 minutes.
- **The question,** from the 0.1.0a4 security review's F3 and N8 (the review and its a5 addendum, `build/reviews-evidence/a4-security/` in the main tree, git-ignored) and spec 056, Decision 4: what should a per-run budget of tool request bytes count, what should its default be, how does it fail, and what is its knob? And what closes N8?

## Labels

EXECUTED means run here, on macOS arm64 (darwin), CPython 3.14.2, wasmtime-py 49.0.0, main `5e66995`, against the frozen artifact set `build/sets/s-c4190ca065ada03a` of the main tree (its `SHA256SUMS` is byte for byte the main tree's `build/artifacts/SHA256SUMS`). The scripts and their output sit beside this memo, in `2026-10-18-a-per-run-budget-of-request-bytes/`. READ means read from a file, cited by path. INFERRED means the researcher's reasoning. Times below are benchmark facts of this one machine, never a check's assertion.

## 1. Where request bytes are admitted and parsed today (READ)

- **The door** (`src/wasi_python/runner.py`, `_door`): `host::call(ptr, len, …)` checks the addresses, then, under `tools=`, calls `admit(length)` with the frame's length **before** reading it. If `admit` returns bytes, they are the answer and the frame is never copied out of guest memory. Only if it returns `None` does the door copy the frame (`bytes(memory.read(…))`) and call the frame host with it.
- **The frame host** (`src/wasi_python/tools.py`, `_ToolHost`):
  - `admit(length)` counts the frame (`_frames += 1`). It answers `budget_exceeded` past `max_calls` ("this run allows N tool frames"), and `too_large` over `_TOOL_REQUEST_BYTES` (1 MiB). Otherwise it keeps `(seq, length)` as pending and returns `None`.
  - `__call__(frame)` admits the frame itself when nothing is pending (a raw `host=` that drives a `_ToolHost` directly), so every frame is counted once. Then `_answer` runs on the door's thread, holding the GIL: `_parse` (JSON with duplicate-key, NaN, integer-length, nesting and surrogate rules), the envelope, the tool lookup, and `_Validator.check` (100,000 steps at most). Only then does a call go to the work thread (spec 036).
- **The runner's wiring** (`runner.py`, `_tool_host`): one `_ToolHost` per call, with `max_calls=c["tool_calls"]`, which `_check_tools` takes from `max_tool_calls=` or, unset, from the call's one read of `defaults()` (spec 049, Decision 2).
- **So the cost F3 names is the bytes `admit` lets through.** A frame refused in `admit` costs the host only the call to `admit`; a frame admitted costs a copy, a parse and a validation in proportion to its size.

## 2. Measured costs (EXECUTED)

`bench060.py` (output `bench060.txt`) and `fuel060.py` (output `fuel060.txt`).

**A. Host CPU per admitted frame, the frame host alone** (thread CPU, median of 5):

| shape (about 1 MiB unless named) | CPU | per MiB | answer |
|---|---:|---:|---|
| empty objects, `Any` | 313.8 ms | 0.314 s | `invalid_arguments` (too complex) |
| empty lists, `Any` | 255.0 ms | 0.255 s | `invalid_arguments` |
| integers, `list[int]` | 266.3 ms | 0.266 s | `invalid_arguments` |
| integers, an unknown tool | 109.4 ms | 0.109 s | `unknown_tool` |
| one escaped string, `str` | 30.2 ms | 0.030 s | `ok` |
| a typical call, 61 bytes | 0.02 ms | (0.335 s) | `ok` |

- The worst shape here costs 0.31 s per MiB. The review measured 0.27 to 0.65 s per frame on its Mac (READ, `p4b_cpu_notrace.log`, `p6_flood_profile.log`). This machine is about twice as fast; the shapes rank the same.
- The cost is about linear in bytes for a given shape. A small frame has a fixed cost of about 20 µs; that cost is bounded by `max_tool_calls` (1,000 × 20 µs = 20 ms), not by bytes.

**B. A frame refused from its length** (`admit` alone, 100,000 frames): 2.85 µs per frame. The bytes are never read, so the cost does not depend on the length the guest claims.

**C0. What the guest pays.** Re-sending one prepared 1 MiB frame costs the guest 1,705, 2,124 and 3,001 fuel in three repetitions (101 frames against 1, `fuel060.txt`), against a run's baseline of about 178 million. The review measured about 1,400. Either way the guest's cost is noise; the host pays about 10⁵ times more per frame in CPU.

**C. A guest floods 40 worst-shape 1 MiB frames through `run`**, today and under a prototype budget of 16 MiB (a wrapper around `admit`, in the benchmark only; nothing in `src/` changed):

| | frames read | frame-host CPU | run wall | answers |
|---|---:|---:|---:|---|
| today, no byte budget | 40 | 12.50 s | 12.78 s | 40 `invalid_arguments` |
| prototype, 16 MiB | 16 | 4.94 s | 4.99 s | 16 `invalid_arguments`, 24 `budget_exceeded` |

The same with fuel metering on gave the same split (12.58 s and 4.90 s). Under the prototype the 24 refused frames were never read: they never reached the frame host's `__call__`.

**What this means for the bound** (INFERRED from A and C). Today the only bound on one run's frame CPU is the deadline: at 0.31 s per frame, about 190 worst-shape frames fill the default 60 s here (about 90 on the review's Mac), well under the 1,000 `max_tool_calls` allows. A budget of B bytes bounds it at about B × 0.31 s/MiB here, B × 0.65 s/MiB on the review's Mac, plus `max_tool_calls` × 3 µs for the refused frames.

## 3. What a budget counts

Three choices (INFERRED, with EXECUTED evidence where named):

- **Every frame's length, refused ones included.** It counts bytes the host never reads: a frame refused from its length costs 2.85 µs whatever its length (B). The judge already sends one frame claiming 1 GiB (`tally060.txt`, the 1,073,741,824 row); counting it would refuse the rest of that run for a cost it never caused. It measures the guest's claims, not the host's work.
- **Admitted bytes**: the lengths `admit` lets through, which the door then copies and the frame host parses. This is exactly the cost of F3 (§1, §2 A). It is known in `admit` from the length alone, before a byte is read, as spec 056, Decision 4 asks.
- **Both, as two knobs.** The first adds nothing the second does not bound, and §4.15 asks a default for each knob. One knob is enough.

**Counting admitted bytes, checked before the frame is read**: a frame is refused when the bytes already admitted plus its length would pass the budget. So the bytes a run's frame host reads never pass it, a frame that fits is read whatever came before, and a refused frame spends nothing. Bytes are counted whatever the answer: a frame that fails to parse cost its parse.

## 4. Its default

**What legitimate workloads send** (EXECUTED, `tally060.py`, `tally060.txt`). A hook counted, for every frame host made while the tool checks and units ran (the four files that drive tools; 369 passed, and the one failure is the hook's own import showing in a child process):

- 159 frame hosts saw a frame. The median run admitted 77 bytes.
- Every run that admitted more than 64 KiB is a unit test that drives `_ToolHost` directly (READ: `tests/unit/test_tools.py`, the 800,000-quote frame, the at-the-cap frame, and `test_the_record_is_bounded`, 1,501 frames and 16,103,569 bytes). The runner's budget does not reach those: a `_ToolHost` made by a test has no budget unless it asks for one.
- Every other run admitted at most 63,300 bytes (900 small frames).
- The README's recipes (*Tools*, the LangChain and MCP adapters, async tools) send frames of tens of bytes: a region code, a currency (READ, `README.md`, *Tools*). They are not run by the judge.

**The default: 16 MiB (16,777,216 bytes)** (INFERRED):

- It is 16 frames at the 1 MiB cap. The worst shape then costs about 5 s of host CPU here and about 10 s on the review's Mac (§2), against the 60 s it may cost today: a sixth of the default deadline at worst, where today it is all of it.
- It is about 265 times the largest per-run total any check sends through `run` (63,300 bytes), and 1,000 frames averaging 16 KiB fit it; at the default `max_tool_calls`, a guest whose frames average under 16 KiB meets the frame limit first.
- It is the number embedders already know: the default output cap per stream, and the answer cap per frame, are both 16 MiB.
- Rejected: 4 MiB (2.6 s worst on the review's Mac, but only three full frames for a guest that sends a file through a tool); 64 MiB (about 42 s worst on the review's Mac, too close to the deadline to be a bound). A guest that sends bulk data should write to a writable mount (spec 034), whose provider receives it without a JSON parse; the README can say so.
- **It is a tighter default, so it needs no owner's decision** (§4.15: only a looser default does). Spec 049, Decision 8 lets an alpha change anything; after 0.1.0 the same change would still be allowed in a minor release by its two exceptions (a tighter default; security).

## 5. How it fails (READ, INFERRED)

The existing limits fail two ways (READ, `runner.py`'s `run` docstring; `tools.py`, `admit`):

- `max_file_calls` ends the run: `trapped == "out of file calls"`, one of the four promised strings. A file call cannot be answered "no" without breaking the guest's libc.
- `max_tool_calls` answers each further frame `budget_exceeded`; the guest gets `ToolBudgetExceeded` and runs on. The record lists the refusal with `op=None` (not read).

A byte budget is a tool-protocol limit and belongs with the second:

- **The kind is `budget_exceeded`**, an existing kind (snapshot line "outcome kinds"). The guest package maps it to `ToolBudgetExceeded` already (READ, `recipes/guest/host/tools.py`, `_CLASS_OF_KIND`), so the guest and the artifact set do not change, and no new kind enters protocol 1. The message names the byte budget, so a guest and an embedder can tell it from the frame budget ("this run allows 16777216 bytes of tool requests; …"). Messages are not promised (spec 049, Decision 8).
- **The order in `admit`**: past `max_calls` first (as today), then `too_large` (a frame over 1 MiB stays `too_large` and spends nothing), then the byte budget.
- **No new trap string and no new record field.** `ToolOutcome.request_bytes` already lists each frame's length; at the default `max_tool_calls` every frame is listed, so the admitted total is the sum over outcomes not refused in `admit`. A total field would be one more public name to freeze for a number the record already gives.
- The guest's `ToolBudgetExceeded` docstring says "all the tool calls it may make". It lives in `recipes/guest/host/__init__.py`, which is build-class; the next change to the guest package can widen it. The message the guest reads is the host's and names bytes.

## 6. The knob (READ)

The tool limits are exposed one way (`runner.py`; `tests/public_api.txt`):

- a keyword-only argument of `run` and `run_async`, `max_tool_calls: int | None = <default>`, that needs `tools=` (without it, `TypeError`: "the raw door has no limit");
- a `Defaults` field, `tool_calls: int | None = 1000`, checked by `_integer_limit` (an integer from 0 to 2**63 − 1, or `None` for no limit; `True` is a `TypeError`);
- the snapshot's `default tool_calls = 1000` line.

**The names: `max_tool_request_bytes=` and `Defaults.tool_request_bytes`** (INFERRED). `tool` groups it with `max_tool_calls` and says it needs `tools=`; `request_bytes` is the name the record already uses (`ToolCall.request_bytes`, `ToolOutcome.request_bytes`) and tells it from the answer's cap, which this budget does not touch. `max_tool_bytes` was shorter and ambiguous.

**What spec 049 says** (READ, `049-the-public-api-is-frozen.md`, Decisions 8 and 13):

- Before 0.1.0, alphas may change anything. After it, a minor release may add keyword-only arguments and dataclass fields placed last with a default; a tighter default is its first exception, and a security fix its second.
- A specification that changes the snapshot says so in its Kind line, lists every snapshot line it adds and the rule that allows each, meets Decision 10's docstring rules (an `Args:` entry in `run` and `run_async`, an `Attributes:` entry in `Defaults`), regenerates `tests/public_api.txt` and the README's reference with `tests/harness/api.py --write`, adds a CHANGELOG line, and lands with `--accept-judge`.
- The four snapshot lines it adds: `field tool_request_bytes: int | None = 16777216` (after `tool_calls`, last); `param max_tool_request_bytes: int | None = <default>  keyword-only` in `run` and in `run_async` (after `max_tool_calls`, last); `default tool_request_bytes = 16777216`.
- The defaults are read once per call (spec 049, criterion 10, `test_set_defaults_changes_what_run_reads`): the new field must come from the same `limits` object `_check_tools` already receives, so the count of reads stays one.

**The command line** (READ, `src/wasi_python/cli.py`): it has `--deadline-s`, `--memory-bytes`, `--output-bytes` and `--fuel`, and no tools, mounts, `--max-tool-calls` or `--max-file-calls`. The command cannot offer a Python function as a tool, so it gets no flag.

## 7. Sessions (READ, spec 055; not landed)

Spec 055 (bounded sessions, build-class, confirmed for build, late in the queue) makes one frame host per turn, so `max_tool_calls` bounds each turn, "set once on the session" (its Decision table "What is per session and what is per turn"). Its rule for arguments `run` gains covers the new one: a session takes every argument of `run` but `argv`, `stdin` and `cancel`. So `max_tool_request_bytes` is per turn, set once on the session, like `max_tool_calls`; a session's total is then bounded by its turns and its `lifetime_s` (INFERRED). Whichever of 055 and 060 lands second carries the keyword into `Session` and its table.

## 8. N8 (EXECUTED, READ)

**What the review says** (READ, the review's Confirmation, item 2, "N8"): one construction still publishes a partial's bound values. `class Outer: __call__ = inner`, where `inner`'s own class has `__call__ = partial(...)`, and someone has hand-copied `__annotations__` onto `inner` so the hints read. `_bound_keywords` follows `__call__` once; `inspect.signature` follows it to any depth; `_type_hints` also follows one hop, which is why the same construction without hand-copied annotations is refused. The review rates it a note: "a two-level callable object with grafted annotations. No embedder writes it by accident." Its suggestion: follow `__call__` again on each hop, bounded by `_WRAPPER_DEPTH`, and add the case as a check.

**Reproduced on main** (`n8_060.py`; `n8_060.txt` on CPython 3.14.2, `n8_060_py311.txt` on 3.11.14, the same lines but for 3.11's wording of the depth-1 refusal): at chain depth 2 and 3, `tool()` publishes `api_key`, `limit` and `user_id`, and the secret is in the descriptor. At depth 1 it is refused (the hints do not read), as the review said. Each hop's `__call__` in the probe is an object, and the last is a `staticmethod` of the partial, so 3.11 to 3.14 call it the same way (3.14 makes a bare `partial` a method descriptor).

**The prototype walk** (in the probe only): on each hop that is not a function, a builtin or a class, follow `type(target).__call__`, as `inspect.signature` does, and stop where it stops: at a C slot (`types.WrapperDescriptorType`, `MethodWrapperType`, `MethodDescriptorType`, `BuiltinFunctionType`, `ClassMethodDescriptorType`), which carries no partial. Results:

- depth 2 and 3 publish only `limit`, and the secret is in no descriptor;
- a function, a callable object, a bound method and a plain partial describe as before;
- `operator.itemgetter(0)`, a C callable, ends the walk at once (no loop to the depth limit);
- a `__call__` cycle (an object whose class's `__call__` is the object) ends at 64 links with the walk's `TypeError`, "its wrappers nest deeper than 64", as a `__wrapped__` cycle does (`n8_cycle_060.py`, `n8_cycle_060.txt`).

The same results on 3.11.14 and 3.14.2.

Without the stop at C slots, following `__call__` on every hop would loop on an object whose class's `__call__` is a slot wrapper (each slot's type has its own `__call__` slot) until the 64-link limit, and refuse a tool that works today (INFERRED, from CPython's `inspect._signature_get_user_defined_method`, which skips the same types). `_type_hints` needs no change: it reads the hints wherever the review's case put them, and the fix only adds the bound names to `Tool._fixed`, so they are left out of the schema and refused in a frame.

## What the specification should decide

A budget of admitted request bytes per call, checked in `admit` from the length before the bytes are read; default 16 MiB; `max_tool_request_bytes=` and `Defaults.tool_request_bytes`; `budget_exceeded` with a message naming bytes; no command-line flag; per turn in a session. N8 closed by following `__call__` on every hop, stopping at C slots.

## Addendum after the pre-build review (2026-10-18)

Spec 060's pre-build review (`build/reviews-evidence/060-spec/` in the main tree) found two things this memo missed. Neither changes a measurement above.

- **`list` frames** (its F1, READ there, P4). Each 26-byte `list` frame makes the frame host encode the whole tool list again (`_answer`, `_encode(body)` per frame). No byte budget sees that cost. Encoding the descriptors array once and splicing the `id` in gives the same bytes at a fortieth of the cost (EXECUTED, `list_splice_060.py`, `list_splice_060.txt`; host-only, thread CPU, median of 20, one copy of the answer included as the door makes it, the write into guest memory not measured):

  | tools | list | encoded per frame | encoded once, spliced |
  |---:|---:|---:|---:|
  | 5 | 12,891 B | 0.039 ms | 0.002 ms |
  | 100 | 447,891 B | 1.068 ms | 0.017 ms |
  | 300 | 1,943,891 B | 4.228 ms | 0.082 ms |
  | 1,000 | 10,479,891 B | 21.886 ms | 0.528 ms |

  The probe asserts that the two answers are equal byte for byte, for an integer `id` and for `null`. What is left per `list` frame (the splice, the door's copies) is per frame, so `max_tool_calls` bounds it.
- **A metaclass's `__call__`** (its F2, EXECUTED there, P2 and P5). §8's walk stops at every class; `inspect.signature` reads a user-defined metaclass `__call__` first. Treating a class as any other hop (following `type(cls).__call__` unless it is a C slot) closes that case and changes none of the review's 27 other callables.
- **A `__call__` cycle on main** (its F6, EXECUTED there): on 3.14 `tool()` raises `RecursionError` from `inspect.signature`; on 3.11, a `TypeError` from `_type_hints`. The walk makes both its own `TypeError` (§8, `n8_cycle_060.txt`).
