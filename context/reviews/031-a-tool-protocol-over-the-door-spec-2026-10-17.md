# Review of 031 — A tool protocol over the door (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4.4, §4.5, §4.9, §4.13, §4.15, §5.2, §5.6, §5.7, §7), the owner's decisions ("12 and 14", 15, 17, "37 … and 13", "38–40", "41–42"), questions 50 to 53 (`questions-for-the-owner.md`, uncommitted), the design memo `research/2026-10-17-a-tool-protocol-over-the-door.md` and its prototype folder, spec 030 and its pre-build review (for format), the drafts of 032 (filesystem provider) and 033 (the zip carries what packages need), and the code the spec changes: `runner.py` (`run`, `run_async`, `_checked`, `Defaults`/`DEFAULTS`, `Completed`, `_run_checked`, `_instance`, `_drive`, `_Call`, `_shared`, `_epoch_answer`, `_door`, `_after_fork_in_child`, `_deferred_ctrl_c`), `__init__.py`, `recipes/hostmodule.c`, `scripts/steps/70_zip.sh`, `80_snapshot.sh`, `scripts/make_stdlib_zip.py` and `scripts/assemble_artifacts.py` (the recipe lines of `MANIFEST`), and `pyproject.toml`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/031-a-tool-protocol-over-the-door.md` as drafted (untracked), against the runner on `dc188a6`.
- **Ran (EXECUTED, darwin-arm64).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the spec was edited; `scripts/build.sh` and the full judge were not run. The artifacts were copied from `build/artifacts/` first. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/031-review/`:
  - `door_copy_probe.py` → `door_copy_probe.txt`: today's runner, a `host=` stand-in for `_ToolHost` with a 1 MiB cap, a guest sending four 256 MiB frames (finding 1);
  - `pool_model.py` → `pool_model.txt`: a model of Decision 9's pool, no guest (finding 2);
  - `json_edges.py` → `json_edges.txt`: `json.loads` edge cases on host CPython 3.11, 3.12, 3.13 and 3.14 (findings 3 and 6);
  - `schema_keywords.py` → `schema_keywords.txt`: the keywords pydantic 2.14.1 and langchain-core 1.6.12 emit, classed by Decision 6 (finding 5);
  - `enum_equality.py` → `enum_equality.txt` (finding 4);
  - `worker_affinity.py` → `worker_affinity.txt` (finding 7).

## What holds

- **The shape is right and matches the owner's decisions.** READ. `@tool` over a plain function, a schema from hints and an `Args:` docstring, MCP's descriptor names, `from host import tools` with real signatures (decision 38), validated first and `subprocess.run`'s error rule with `ToolError` in the guest (39), no adapters in the wheel, recipes in the README (40), an optional gate with tools as capabilities, a default `max_tool_calls` and a per-call record (37), nothing about identity or policy in the runner (17), async refused now and specified later (15).
- **`host=` and `tools=` excluding each other is the right call.** READ, INFERRED. The door is one function. Sharing it would mean telling frames apart by their bytes, which reads the raw door's frames and breaks §4.4's opacity, and would let a guest steer a frame to the side that checks less. Refusing `gate=` without `tools=` is right for the same reason. An embedder that needs both keeps serving its own frames through `host=`, which the published frame format allows.
- **No change to the binary or its imports (§4.4).** READ. The guest half is pure Python over `_host.call`; `hostmodule.c` already gives `ConnectionRefusedError` for no host and `OSError` for a fault, which Decision 12 maps.
- **Errors cross only by intent.** READ. Only `ToolError`/`ToolDenied` text, truncated, reaches the guest; anything else is "(internal error)" with the exception kept on the host. That closes the memo's finding 2 leak (Monty, Cloudflare).
- **Daemon threads, not `ThreadPoolExecutor`.** READ. `concurrent.futures.thread` joins its workers at exit, so a hung tool on such a worker would hang interpreter exit. The reason is sound.
- **Fuel stays exact given the same answers.** READ, INFERRED. Fuel counts guest instructions only. A door call's guest-side cost depends on the answer's bytes (`host_alloc`, the copy, the decode), and the answer depends only on the tool's value, the guest's own `id` and the host's fixed messages. The epoch callback under `cancel=` does not consume fuel. So criterion 19 tests a true property, provided the discovery order is fixed (finding 11).
- **`tools=` is the explicit argument §4.15 asks for.** Without it nothing of this spec runs and the door behaves as today (Decision 1, criterion 21).
- **The schema strictness is workable for ordinary tools.** EXECUTED (`schema_keywords.txt`): a typical pydantic argument model (`str`, an `int` with `ge`/`le`, an optional `datetime`) and a LangChain `@tool`'s `tool_call_schema` use only checked or ignored keywords. Finding 5 covers the common cases that are refused.

## Acceptance criteria against evidence

Nothing is built, so this checks each criterion's design.

- 1–3, 5, 6, 8, 9: sound, and each fails today because the names are missing. 3 should add finding 4's cases.
- 4: "nesting 100,000 deep" passes today only because the probe frame is a list, not an object. On host 3.14 `json.loads` parses 100,000 levels on a non-main thread (EXECUTED, `json_edges.txt`), so the same depth inside `args` reaches the validator. See finding 3.
- 7: sound. Add `max_tool_calls=` without `tools=` (finding 12).
- 10–14, 17, 18, 20–22: sound.
- 15: does not catch a stale result. The event is set only after the run, so the late result never arrives during the second call. Set it before the second call (finding 9).
- 16: `deadline_s=0.3` must cover interpreter start, discovery and the first call on the plain binary on the slowest CI runner. If it does not, the run ends `"deadline"` before any tool call and the check fails. It must not assert `trapped` either: after `ToolTimeout` the guest may exit 0 within the last two ticks. See finding 9.
- 19: sound once the discovery order is fixed (finding 11).
- 23: the commands should pin versions (finding 12).
- 24: names the zip's byte growth but not the fuel growth it causes (finding 10).
- Missing: Ctrl-C during a tool call; one call's stranded workers not starving another call; the fork hook; the request cap applied before the copy; a cap on record and message size; the JSON parse rules (finding 9).

## Findings, most severe first

1. **The request cap and the call budget do not bound the host's work: the frame is copied before either is checked.** High. Decision 8 says the 1 MiB cap "bounds that work and its memory", and that `max_tool_calls` "bounds the host's work". Neither holds as designed.
   - READ: `_ToolHost` is passed as the `_Call`'s host (Design; Decision 4), so it runs inside `_door`'s `frame`. `frame` calls `host(bytes(memory.read(caller, ptr, ptr + length)))` (`runner.py`, `_door`). `memory.read` returns a `bytearray` copy (`wasmtime/_memory.py:81-101`) and `bytes()` copies it again. So the whole frame, up to the guest's memory (1 GiB by default), is copied twice before steps 1 and 2 run.
   - EXECUTED (`door_copy_probe.txt`): with today's runner, a host that refuses anything over 1 MiB was handed four frames of 268,435,456 bytes each, 1,073,741,824 bytes in all, and the run exited 0.
   - Past the budget, Decision 8 lets the guest go on. Each over-budget frame is still copied in full and answered, until the deadline. With `deadline_s=None` there is no end. Only the record is bounded, not the work.
   - Fix: let the tool host refuse by length before the copy. For example, `_door` reads a request cap from its host (`_door(host, max_request=TOOL_REQUEST_BYTES)` when the host is a `_ToolHost`). It answers `too_large`, and `budget_exceeded` past the limit, from `length` alone, without `memory.read`. The raw `host=` path stays as it is. Then an over-budget frame costs O(1) host work, and a guest that loops on them only spends its own fuel and time. Add a unit check: a frame whose `length` is over the cap never reaches `memory.read` (count the reads with a fake memory). Add an end-to-end check with a 256 MiB frame. Then state Decision 8's claim as true.
   - Question 52 (run on, against decision 42's stop) remains the owner's. This fix makes "run on" safe either way. Without it, "run on" lets a guest make unbounded host work.

2. **One guest can strand the whole process-wide worker pool and starve every other call's tools.** High. The pool is shared by all calls in the process. A timed-out sync tool keeps its worker. A full pool makes the next call wait.
   - INFERRED from Decision 9, then shown on a model (EXECUTED, `pool_model.txt`, four workers): guest A calls a tool that hangs, with `timeout_s` set, four times. Each call times out, and A runs on. Guest B, another run in the same process, then calls an instant tool. B's call times out.
   - It is guest-driven. A guest needs only a tool whose time depends on its arguments, such as a fetch of a slow URL or a query on a large range. Each `ToolTimeout` returns control to the guest, which calls again. Within one run it strands up to `tool_workers` (32) threads. The owner's direction is a runtime for many agents' code in one host. This is a cross-tenant denial of service that §4.15's "every limit has a default" does not cover.
   - The stranded tool also keeps running with its authority after the guest was told `timeout`. A guest that retries can then make a destructive tool act twice. The record says `timeout`, and nothing says the tool may still finish.
   - Fix (any one, stated in the spec, with a check):
     - (a) A per-call quota on stranded workers. Once a call holds `k` workers whose tools timed out and are still running (for example `k = 1`, or 4), its next call is answered `timeout` without running gate or tool. Or the run stops, named, as 032 does at its limit. The pool is then shared fairly. 32 workers serve at least `32 / k` calls.
     - (b) No shared pool: one daemon thread per tool call, with the per-call quota of (a).
   - Either way, `ToolRecord` should say when a worker was left running (for example `outcome="timeout"` with `abandoned=True`), so an auditing embedder knows a side effect may still land.
   - Check: two concurrent calls. Call A strands its quota; call B's instant tool still answers `ok`. Count outcomes only.

3. **The JSON parse rules leave guest-controlled holes and depend on the host's Python and process settings.** Medium. Decision 6 relies on `json.loads` with `parse_constant`, and on CPython's own limits. EXECUTED (`json_edges.txt`, the same on 3.11 to 3.14 unless noted):
   - `1e400` and `-1e400` parse to `inf` and `-inf`. `parse_constant` sees only the literal tokens `NaN` and `Infinity`, so a non-finite float reaches the validator and the tool.
   - `json.loads(bytes)` detects the encoding, so UTF-16 and UTF-32 frames parse. The format says UTF-8.
   - Duplicate keys parse, and the last one wins. The gate is also given `request_bytes`. If that is the raw frame, a gate that reads it with another parser can see other values.
   - A lone surrogate (`"\ud800"`) parses. Encoding an answer that echoes it with `ensure_ascii=False` and `.encode("utf-8")` raises `UnicodeEncodeError`. The `unknown_tool` and `invalid_arguments` messages echo guest text, so `_ToolHost` would raise. `_door` then gives `HOST_FAULT`, and the frame may be missing from the record.
   - The digit limit is process-wide. After `sys.set_int_max_str_digits(0)` (an embedder's choice, or `PYTHONINTMAXSTRDIGITS=0`), a 5,000-digit integer parses. A 1 MiB integer then costs super-linear time on the door thread.
   - Nesting depth depends on the Python version. On a non-main thread, 5,000 levels raise `RecursionError` on 3.11, parse on 3.12 and 3.13, and 100,000 levels parse on 3.14. Once parsed, a recursive Python validator, the `$bytes` decoder, or a recursive `$ref` schema meets `RecursionError` at Python's limit of 1,000. That happens outside the parse step that Decision 6 maps to `protocol`.
   - Fix: write the parse rules into Decision 6 as rules of the protocol, not of the host's CPython:
     - decode strict UTF-8 first;
     - a `parse_float` that refuses non-finite results;
     - a `parse_int` that refuses literals longer than a fixed bound (for example 20 digits, or 4,300 whatever the process sets);
     - an `object_pairs_hook` that refuses duplicate keys;
     - an explicit depth limit (for example 64), checked by an iterative walk after the parse and before validation, which is a `protocol` answer;
     - answers encoded with `ensure_ascii=True` and `allow_nan=False`.
   - Make `ToolCall.request_bytes` the size, as `ToolRecord`'s is (finding 12). Criterion 4 gains these frames, with the deep one inside `args`.

4. **The validator's equality and type rules are underspecified, and Python's defaults are wrong for JSON.** Medium.
   - `enum` and `const`, compared with `in` or `==`, admit `true` for `1`, `false` for `0`, `1.0` for `1`, `[true]` for `[1]` and `{"a": true}` for `{"a": 1}`. EXECUTED, `enum_equality.txt`. That is the coercion Decision 6 forbids, and a gate or tool expecting an `int` gets a `bool`.
   - Fix: define JSON equality, type-strict and recursive, with `bool` never equal to a number. Decide whether `5.0` is an `integer`: JSON Schema says yes, but "no coercion" suggests no. Write the rule down and put both in criterion 3.
   - Also state these:
     - `additionalProperties` may be a schema, not only a boolean. The spec's own `dict[str, T]` needs it, and pydantic emits it.
     - `$defs` and `definitions` are allowed containers, and `$ref` is local only, with recursion bounded by finding 3's depth.
     - An `items` that is an array (the draft-04 tuple form) is refused.
   - `Tool` is a frozen dataclass holding a mutable `input_schema` dict. EXECUTED (`json_edges.txt`): the dict can be changed after `tool()` vetted it. Adding `pattern` afterwards gives a half-checked schema without `validates_input=True`, which Decision 6 says cannot happen. The generated `__hash__` also makes a `Tool` unhashable (a `TypeError` in a set).
   - Fix: deep-copy the schema in `tool()`. Re-vet it in `_checked`, or keep the vetted copy private. Set `eq=False` (identity) or define the hash.

5. **Common pydantic constructs and non-identifier property names break the schema path.** Medium.
   - EXECUTED (`schema_keywords.txt`): a pydantic model with a `set`, a `tuple`, a `multiple_of`, a discriminated union and a `pattern` emits `uniqueItems`, `prefixItems`, `multipleOf`, `discriminator` and `pattern`. `tool()` refuses each one unless `validates_input=True`. The common cases all pass: a plain model, a LangChain `@tool`, `$defs`/`$ref`, `anyOf` with `null`, `format`, `title`, `default`.
   - Fix, cheap and exact: add `uniqueItems` (with finding 4's JSON equality), `multipleOf` (integers exactly; for floats say how), `prefixItems` (with `items` for the rest), `minProperties` and `maxProperties` to the checked list. Add `discriminator` (OpenAPI's, not JSON Schema's; `oneOf` is still checked) and `contentMediaType` to the ignored list. Keep `pattern` refused, and say why: an embedder's regex on up to 1 MiB of guest text is a ReDoS (catastrophic regex backtracking) risk on the door thread. With that, "refused unless `validates_input=True`" (question 50) is workable for real tools.
   - Worse, **one bad property name breaks every tool.** The guest builds an `inspect.Signature` from each input schema. A property named `from`, `class` or `max-results`, all common in MCP and REST schemas, makes `inspect.Parameter` raise `ValueError` (EXECUTED, `json_edges.txt`). As specified, `host/tools.py` builds every function at import, so `from host import tools` fails for all tools.
   - Fix: `tool()` refuses a root property name that is not a Python identifier, or is a keyword, naming it. The README recipes rename such properties. Or the guest gives that tool a `**kwargs` signature. Either way, check it in criterion 2 or 8. `required` names missing from `properties` should also be refused in `tool()`.

6. **The record and the messages are unbounded in two ways.** Medium.
   - With `max_tool_calls=None`, the record holds one `ToolRecord` per frame, without limit. Host memory grows with the guest's frame count, and `memory_bytes` does not cover it.
   - The messages that echo guest data (an unknown key, a tool name, a wrong value) have no length rule. Only `ToolError` text is truncated. A guest that sends 1,000 frames, each naming a 1 MiB unknown key, could leave about 1 GB of messages in the record (INFERRED from the 1 MiB cap and the 1,000 default).
   - Fix: bound every message at 4,096 characters, with each echoed guest value cut to 64. Cap the record at its first 1,000 entries plus a count of the rest, whatever `max_tool_calls` is. Spec 032 does this with its first 1,000 faults. Add both to criterion 4.

7. **Tools run on a thread that is not the caller's, and the spec does not say what that breaks.** Medium-low.
   - The README's first example makes tools that close over the caller's authority. Resources bound to a thread fail on a tool worker. EXECUTED (`worker_affinity.txt`): a `sqlite3` connection made on the caller's thread raises `ProgrammingError` on the worker, so every call is "(internal error)". Thread-locals do not cross either; Decision 9 copies only `contextvars`.
   - Spec 032 runs its provider on the guest's own thread, and says a provider must bound its own time. vfs, the main consumer, will meet both models.
   - Fix: say in Decision 9 and the README that tools and gates run on another thread, that thread-affine objects (`sqlite3` with `check_same_thread`, thread-locals) do not work there, and why this differs from 032. Bounding the time needs another thread.

8. **The guest should send only the arguments its caller gave.** Medium-low.
   - Decision 12 builds each guest signature with the schema's defaults, but does not say whether a call sends them.
   - If it does, a pydantic or LangChain tool written `x: int = None` has `"default": null` on a `"type": "integer"` property. A guest call that leaves `x` out then sends `null` and gets `invalid_arguments`. The schema's default is description text from the host. The tool's own default should apply.
   - Fix: the guest binds without `apply_defaults` and sends only the bound arguments. Criterion 8 checks that an omitted optional argument is absent from the frame.
   - Also decide what `tool()` does with a derived `x: int = None`: refuse it, or map it to `Optional[int]`.

9. **Missing and fragile checks.** Medium-low (§4.9, AGENTS rule 3).
   - Missing checks:
     - Ctrl-C during a blocked tool. Decision 9 promises `cancelled`, then `KeyboardInterrupt`. Model it on spec 030's criterion 3: the main thread, a self-sent SIGINT, the record's last entry `cancelled`. The tool host must only read spec 011's flag, never clear it; `_shared` clears it.
     - Stranded workers do not starve another call (finding 2).
     - The fork hook drops the pool and makes its lock and queue anew. A lock held by a worker at the fork must not carry over. `tools.py` registers its own `at_fork` hook, or `runner._after_fork_in_child` resets it only when `wasi_python.tools` is in `sys.modules`.
     - The cap is checked before the copy (finding 1). Messages and the record are bounded (finding 6).
   - Criterion 15 should set the event before the guest's second call, so that the late result arrives while that call is in flight. Assert that the second call's answer is its own. That is the stale-result bug a sliced wait invites.
   - Criterion 16: use a deadline that comfortably covers start-up on the plain binary under load, such as 3 s. The tool blocks on an event, so only the outcome depends on it. Assert only the record's last entry (`timeout`) and that `run` returned, never `trapped`.
   - Criterion 4: put the deep nesting inside `args` (finding 3).

10. **Build-class consequences the spec does not state, and its size.** Medium-low.
    - It is build-class (§5.7): it adds `recipes/guest/` and changes `70_zip.sh`. So the zip, `MANIFEST`'s recipe lines and the snapshot all change. The snapshot "runs only beside this exact zip" (`80_snapshot.sh:3-5`).
    - **Fuel grows on every plain-binary start:** about 77,912 instructions per zip member (`research/2026-10-17-what-else-the-default-profile-carries.md`, finding 5, EXECUTED there). Two members are about +156,000 fuel on each plain start, about +0.06% on `pass`. Criterion 24 should predict this and accept it with `--accept-growth`, with that reason. A snapshot start does not pay it (same memo).
    - Spec 033 (drafted) also changes `70_zip.sh`, so the two cannot be in flight together. Decision 44 orders the zip's per-member fix first. Say which lands first.
    - **Size.** One builder can build this, but it is the largest runner change since 015: a hint mapper, a docstring parser, a validator, the frame host, a worker pool with four bounds, a guest package, stubs, 22 checks and two recipe runs. The build-class part is small. Recommended split:
      - **031:** `wasi_python.tools` (`tool()`, the validator, `_ToolHost` without the bounds, `stubs()`), the guest package in the zip, and criteria 1–6, 8, 9 and 22. Build-class, short in the lane.
      - **031b:** the runner (`tools=`/`gate=`/`max_tool_calls=`, the workers and bounds, `Completed.tool_calls`, the fork hook) and criteria 7 and 10–21. It touches no `scripts/` or `recipes/`, so it can be built in parallel.
      - If the author keeps one spec, the builder should develop end to end with the guest package on a read-only grant and `PYTHONPATH`, and add the zip lines last.
    - `pyproject.toml` excludes `recipes` from ruff (`extend-exclude`), so Decision 12 needs an explicit include. Criteria 8 and 9 load the guest files on the host's Python (3.11 and up), so the guest package must stay 3.11-compatible.

11. **The discovery order and the result encoding are unstated.** Low.
    - Fuel exactness (criterion 19), stubs and the guest's module all depend on the order of the `list` answer. Say it is the order `tools=` gave.
    - Step 10's "has a JSON form" needs rules that mirror the guest's encoding (Decision 12):
      - non-`str` dict keys refused, not stringified (`json.dumps({1: "a"})` gives `{"1": "a"}`);
      - `allow_nan=False`;
      - `tuple` as an array;
      - `numbers.Integral` and `numbers.Real` accepted (a tool returning numpy's `int64` is common).
    - Encode on the worker, inside the bound, so a result that is slow to encode counts as a timeout.

12. **Smaller points.** Low.
    - `max_tool_calls=` without `tools=` is "checked and has no effect". That is the same trap Decision 3 refuses for `gate=`: it looks like a limit on the raw door. Refuse it too.
    - Naming against 032: `Defaults.max_tool_calls` against 032's `Defaults.file_calls`, both behind run arguments named `max_…`. And `tool_calls: tuple[ToolRecord, ...] = ()` against `files: FileRecord | None = None`. Align the field names now, while both are drafts.
    - `ToolCall.request_bytes` should be stated as an `int`. A gate may mutate `arguments` in place, despite "may not change the arguments". Give the gate a deep copy, or the tool a fresh one.
    - `timeout_s`: refuse NaN and infinity, as `_deadline_limit` does. The frame `id`: an `int` that is not a `bool`, in a stated range, else `null`.
    - `ToolCancelled` never reaches guest code in practice: the guest stops at its next function entry (spec 015 and 030). Say so, so that a model does not rely on `except ToolCancelled` for clean-up.
    - Criterion 17's tool host returns within a tick of the cancel, which is inside `CANCEL_TICKS`, so it does not exercise 030's overdue path (INFERRED). The dependency on 030 is still right, as a safety net. Do not count criterion 17 as a check of 030.
    - `host/tools.py` must import its modules under private names (`import json as _json`), or a tool named `json` collides with them, despite "no reserved names". Add such a name to criterion 8.
    - An artifact set from before this spec (through `artifacts=` or `WASI_PYTHON_ARTIFACTS`) has no `host` package. A run with `tools=` then gives the guest only `ModuleNotFoundError`. Either `run(tools=…)` refuses a `MANIFEST` without the `recipes/guest/host/tools.py` line, or the README says this.
    - Criterion 23 should pin its versions (`--with langchain-core==1.6.12 --with mcp==…`), as the memo recorded them (§7: nothing fetched unpinned).
    - "Four of these decisions (6, 8 and 9)" should read "four choices in Decisions 6, 8 and 9".
    - `tool()` on an object with no `__name__` (a `functools.partial`) needs `name=`; say so.

## Constitution checks

- **§4.4 (the wall):** holds. No third import. The raw door stays opaque, since `host=` and `tools=` are exclusive and the runner never sniffs a raw frame. The gate is optional, per decision 37.
- **§4.5 (embedder-neutral):** holds. No identity, user or embedder name in the protocol. The README examples must not name vfs.
- **§4.9 (counts, not time):** holds in intent. Criterion 16's short deadline is a flake risk, and criterion 4's depth case depends on the Python version (finding 9).
- **§4.13 (tooling):** holds. No new dependency. Ruff's coverage of `recipes/guest/` needs a `pyproject.toml` change (finding 10).
- **§4.15 (safe by default):** holds for the channel: `tools=` is explicit. It does not yet hold for the host's own resources: the copy before the cap (finding 1), the shared pool (finding 2), and the record with no limit (finding 6). Question 53 (no per-call default timeout) is consistent with §4.15, since the run's 60 s deadline is the default time limit.
- **§5.2 (no open questions):** holds. Questions 50 to 53 are decided in the spec and only recorded for the owner. Fix the wording (finding 12).
- **§5.6:** this is the pre-build review the artifact-set change requires.
- **§5.7 (one lane, build-class):** right to call it build-class. It must not overlap 033. The split in finding 10 shortens its time in the lane.
- **§7:** nothing copied; the prototype is the project's own. Criterion 23 should pin what it fetches.
- **Spec 032 and decision 42:** the limits differ. 031 runs on at its limit (question 52), while 032 stops the run. The execution models differ too (finding 7), and so do the record shapes (finding 12). Each difference should be stated or aligned before either is built.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author adopted the split of finding 10: spec 031 is now the protocol, its host module and the guest package in the zip (build-class); **spec 036** (`036-tools-in-the-runner.md`, not build-class) is the runner. Each finding is fixed in one or both.

| finding | disposition | where |
|---|---|---|
| 1 | **Fixed.** The frame host has `admit(length)`, which counts the frame and answers `budget_exceeded` or `too_large` from the length alone. `_door(host, admit=None)` calls it before `memory.read`; the runner learns the cap from the frame host it built (`_instance` passes `admit=tool_host.admit`), so no number is threaded through, and the raw `host=` path is unchanged. A unit check counts reads on a fake memory (0 for a refused frame); an end-to-end check sends four 256 MiB frames. Question 52 now says why "run on" is safe. | 031 D5; 036 D2, criteria 2 and 5 |
| 2 | **Fixed, option (b).** No shared pool: each tool call runs on its own daemon thread. A call may hold at most 4 abandoned threads (`MAX_ABANDONED`); its next call is then answered `timeout` at once, with no gate or tool run. `ToolOutcome.abandoned` says a tool was still running when the guest was answered. The README warns that a retried call may act twice. Checks: the per-call quota, and two concurrent calls where A's stalled tools do not starve B (stand-in: the review's shared pool of four). | 031 Design (`ToolOutcome`); 036 D3, D5, criteria 11 and 12; question 53 |
| 3 | **Fixed.** The parse rules are the protocol's: 1 MiB, strict UTF-8 before parsing, a nesting scan (64 levels) before `json.loads`, `parse_constant`, `parse_float` (no non-finite), `parse_int` (64 characters, whatever the process sets), `object_pairs_hook` (no duplicate keys), no lone surrogate, an object at the top. Answers use `ensure_ascii=True` and `allow_nan=False`. `ToolCall.request_bytes` is the frame's length, an `int`. Criterion 5 carries every case, the deep one inside `args`. | 031 D4, D5, criterion 5 |
| 4 | **Fixed.** Equality is type-strict and recursive (`true` never equals `1`, `1.0` never equals `1`); `integer` excludes `5.0`, stated as a departure from JSON Schema. `additionalProperties` may be a schema; `$defs` and `definitions` are the containers; `$ref` is local; a `$ref` cycle that does not descend into the value is refused; array `items` is refused. `tool()` vets a deep copy and keeps it private; `Tool` hands out copies and compares by identity (`eq=False`). Criteria 3 and 4. | 031 D2, D3, criteria 3 and 4 |
| 5 | **Fixed.** Checked: `uniqueItems`, `multipleOf` (positive integer only, the rule stated), `prefixItems`, `minProperties`, `maxProperties`. Ignored: `discriminator`, `contentMediaType`. `pattern` stays refused, with the ReDoS reason. `tool()` refuses a root property name that is not an identifier or is a keyword, and a `required` name missing from `properties`; the guest gives a descriptor it cannot make a signature from `(**kwargs)` rather than breaking the import. Criteria 2 and 9. | 031 D2, D3, D8, criteria 2 and 9; question 50 |
| 6 | **Fixed.** Every message is at most 4,096 characters, each echoed guest value cut to 64 first. The record lists the first 1,000 frames whatever `max_tool_calls` is, with `frames` and `unlisted` counts, as 032 keeps its first 1,000 faults. A fault is a string (type and first line, 200 characters), as 032's `FileFault`, so no exception or its frames is kept. Criterion 8. | 031 D6, Design, criterion 8 |
| 7 | **Fixed.** 036 Decision 3 says why tools run on another thread (the deadline, `cancel` and Ctrl-C must be answered while a tool blocks, and host code cannot be interrupted) and why 032's provider does not (many short synchronous file calls; a provider bounds its own time). It names what breaks (`sqlite3` with `check_same_thread`, thread-locals) and what crosses (`contextvars`); the README says so. Criterion 16. | 036 D3, D9, criterion 16 |
| 8 | **Fixed.** The guest binds without applying defaults and sends only the arguments its caller gave; the schema's `default` is description only. A derived `x: int = None` is refused ("write `int \| None = None`"). Criteria 2 and 9. | 031 D2, D8 |
| 9 | **Fixed.** Added: Ctrl-C during a tool call (036 criterion 14; the bound reads spec 011's flag and never clears it, unit criterion 3); stalled tools do not starve another call (036, 12); the cap before the copy (036, 2 and 5); bounded messages and record (031, 7 and 8); the JSON rules (031, 5). Criterion 15 (now 036's 9) has tool B set the event, so A's late result arrives while B's call is in flight, and asserts B's answer. Criterion 16 (now 036's 10) uses `deadline_s=3` and asserts only that `run` returned and the last outcome. The fork check: with no pool, lock or queue there is nothing to reset, and a child has none of its parent's tool threads; answered in 036 Decision 8 rather than checked. | 031 criteria 5, 7, 8; 036 criteria 2, 3, 5, 9, 10, 12, 14; 036 D8 |
| 10 | **Fixed; split adopted.** 031 (build-class) is short in the lane; 036 is not build-class and can be built beside a build-class spec once 031 has landed. 031 states that the zip, `MANIFEST`'s recipe lines, `SHA256SUMS` and the snapshot change; predicts the fuel growth (about +156,000 per plain start, +0.06% on `pass`; none on a snapshot start) and accepts it with that reason; states its lane order against 033, 035 and 023 (none in flight with it; it does not wait on 035); and asks the builder to develop against today's artifacts with the package on a read-only grant and `PYTHONPATH`, adding the zip lines last. `pyproject.toml` includes `recipes/guest/` in ruff explicitly; the package stays 3.11-compatible. | 031 header, D8, D9, criterion 14 |
| 11 | **Fixed.** The `list` answer is in the order the embedder gave the tools. The result's JSON form mirrors the guest's encoding (non-`str` keys refused, `allow_nan=False`, tuples as arrays, `numbers.Integral`/`Real` accepted). Encoding is part of the work, so in 036 it runs inside the bound. | 031 D5, D6, D7, criteria 1 and 7 |
| 12 | **Fixed, point by point.** `max_tool_calls=` without `tools=` is refused. Names aligned with 032: `Defaults.tool_calls` behind `max_tool_calls` (032: `Defaults.file_calls` behind `max_file_calls`), and `Completed.tools: ToolRecord \| None = None` (032: `files: FileRecord \| None = None`). `request_bytes` is an `int`; the gate gets a deep copy of the arguments and the tool its own. `timeout_s` refuses NaN and infinity as `_deadline_limit` does. The frame id is an `int`, not a `bool`, from 0 to 2**53 - 1, else `null`. `ToolCancelled` is documented as rarely reaching guest code. Criterion 17 (now 036's 13) is not counted as a check of 030. The guest package imports under private names, and a tool named `json` is in criterion 9. An artifact set without the guest package is refused by `run(tools=)` with `ArtifactsMissing` (its `MANIFEST` recipe line). The recipe commands pin their versions. The wording is fixed: three decisions, four questions (50 to 52 in 031, 53 in 036). `tool()` on a `partial` needs `name=`. | 031 D2, D5, D7, D8; 036 D1, D9, criteria 1, 13, 19 |

## Verdict

**Revise before build.** The design is right in shape, and it matches the owner's decisions 12, 14, 15, 17 and 37 to 40. Two findings change the design and must be settled first:
- the request cap and the call budget must apply before the frame is copied (1);
- one call's stranded tool workers must not starve another call (2).

Findings 3 to 6 are rules the validator and frame host must state, or the builder will improvise them on a security boundary. Findings 7 to 12 are documentation, checks and alignment with 032 and 033. A short re-review of the revised Decisions 4, 6, 8 and 9 is enough. The rest can be confirmed against the diff at build review.

## One line

The protocol has the right shape, but before it is built its caps must act before the copy, its worker pool must be fair across calls, and its JSON and schema rules must be the protocol's own rather than whatever CPython does.

## Confirmation (2026-10-17)

- **Re-reviewed:** the revised `031-a-tool-protocol-over-the-door.md`, the new `036-tools-in-the-runner.md` (reviewed as a new specification), the Disposition above, and questions 49 to 53. Nothing in the specs, `src/`, `tests/`, `scripts/` or `recipes/` was edited, and nothing was committed. New probes and their outputs are in the same scratch folder:
  - `admit_prototype.diff` (a scratch copy of the runner, `admit_pkg/`) with `admit_probe.py` → `admit_probe.txt`;
  - `frame_rules.py` → `frame_rules.txt` (031 Decision 4 as written, host 3.11 to 3.14);
  - `thread_model.py` → `thread_model.txt` (036 Decisions 3 to 5);
  - `validator_cost.py` → `validator_cost.txt`, and `recursive_union.py` → `recursive_union.txt` (pydantic 2.14.1).

### Each disposition against its finding

1. **Confirmed.** EXECUTED (`admit_probe.txt`): with `admit(length)` called before `memory.read`, four 256 MiB frames over a 1 MiB cap were answered `too_large`. Each was counted, none was read from guest memory, and 0 bytes reached the host. With a budget of 3, the guest then sent 200 frames of 256 MiB. Those 200 were counted and answered `budget_exceeded`, only the 3 small frames were read (6 bytes in all), and the run exited 0. The raw `host=` path is unchanged. 036's criteria 2 and 5 check this.
2. **Confirmed for the finding as raised.** EXECUTED (`thread_model.txt`), with one thread per call and 4 abandoned per call: guest A's six calls gave four abandoned timeouts, then two immediate ones, and started 4 threads. Guest B's instant tool answered `ok`. The quota holds only per call, though: see 036 finding C2.
3. **Confirmed.** EXECUTED (`frame_rules.txt`). Decision 4's rules, written as stated, give the same outcome on 3.11, 3.12, 3.13 and 3.14, on a non-main thread:
   - UTF-16, UTF-32 and other non-UTF-8 frames, `NaN`, `1e400`, a 65-character integer (also with the process digit limit off), duplicate keys (also one spelled with an escape), a lone surrogate in a value or a key, nesting of 65 and of 100,000 levels, and a top-level array are all `protocol` answers;
   - a valid surrogate pair, a 64-character integer and brackets inside a string are accepted;
   - an answer that echoes `\ud800` encodes.

   The version dependence is gone. See C3 for one wording point.
4. **Confirmed**, apart from the validator's cost, which this finding did not raise (C1).
5. **Confirmed.** The `(**kwargs)` fallback in the guest is a better answer than the one I proposed.
6. **Confirmed.** Criterion 8 needs one fix (C4).
7. **Confirmed.** 036 Decision 3 states the reason, says what breaks, and has criterion 16.
8. **Confirmed.**
9. **Confirmed.** The answer on the fork hook stands, with C6's caveat.
10. **Confirmed.** The split, the lane order, the fuel prediction and the order of building are all stated.
11. **Confirmed.**
12. **Confirmed**, point by point.

### New findings

**C1. The validator can be made to run for an astronomically long time, on the door thread, where no deadline, cancel or Ctrl-C can stop it.** High. It is a condition for 031.
- 031 Decision 3 allows a `$ref` cycle that descends into the value, as recursive schemas must. pydantic emits such cycles under `anyOf` with branches that overlap: for `Union[list[Node], list[Union[int, Node]]]`, both branches are arrays whose items lead back to `Node` (EXECUTED, `recursive_union.txt`).
- A naive recursive validator tries every branch. Against a guest value that fails only at its deepest leaf, its work doubles with each level. EXECUTED (`validator_cost.txt`): 10,234 schema visits at depth 10, 327,674 at 15, 10,485,754 at 20. The frame allows about 62 levels inside `args`, so the work is about 2^62 visits (INFERRED from the doubling).
- Validation runs in the frame host's `__call__` on the door thread, before `invoke` (031 Decision 5). So 036's bound does not cover it.
  - The store's epoch interrupt cannot fire inside host code.
  - A deadline or cancel is only noticed after the call returns.
  - A Ctrl-C is only deferred.

  The run never ends.
- `uniqueItems` compared pairwise is the same kind of problem, at polynomial cost: a 1 MiB frame carries 524,288 items, which is 137,438,691,328 comparisons (`validator_cost.txt`).
- Fix, in 031 Decisions 3 and 5, with checks in criteria 4 and 5:
  - a deterministic validation budget per frame, for example 100,000 schema-node visits, counted and not timed; past it, the answer is `invalid_arguments` ("the arguments are too complex to check");
  - `uniqueItems` checked in linear time, by a type-tagged canonical key per item (the same strict equality, made hashable).

  Check: the `Node` schema above with a 62-deep failing value is answered within the budget, and an array of 524,288 equal items is refused in one pass. Use a counting stand-in, not a timing.

**C2. Abandoned tool threads are bounded per call, not per process.** Medium-low. A condition for 036.
- `MAX_ABANDONED` caps a running call. When the run returns, its abandoned threads stay alive until their tools end, and the next run starts again from zero.
- EXECUTED (`thread_model.txt`): ten runs in sequence, each meeting a hanging tool, left 40 abandoned threads alive.
- An agent loop that runs many short guests against a tool that can hang therefore grows the process's threads without limit. At the operating system's limit, thread creation fails.
- 036 Decision 5's "a process holds at most five tool threads per running call" reads as a process-wide bound. It is not one.
- Fix:
  - say so in Decision 5 and the README (a tool that can hang must bound itself; each run can leave up to five threads behind);
  - make the number visible, for example `runner.stats()["tool_threads_running"]`, which the judge can read;
  - make a failed thread start a fault answer (`tool_error`, internal), never an exception out of the frame host.

  A process-wide ceiling would bring back the starvation of finding 2, so I do not recommend one. Add a unit check that a thread start which raises gives a fault outcome.

**C3. Say what the nesting limit counts.** Low (031).
- My model counts the whole frame, its envelope included. Then 64 levels in total pass and 65 fail, which is 62 levels inside the `args` value (`frame_rules.txt`). Criterion 5's "65 levels deep inside `args`" fails under either reading, so it does not pin the rule down.
- Write "the frame's nesting, envelope included, at most 64" in Decision 4. Test the boundary: 64 in total passes, 65 fails.
- Also say that a lone surrogate is refused in keys too (the model does so).

**C4. 031 criterion 8 cannot show the message bound.** Low.
- A frame naming a 1 MiB key exceeds the 1 MiB cap, so it is answered `too_large` and never reaches the `invalid_arguments` message it means to bound.
- Use a key that fits, for example 1,000,000 characters. Smaller keys suffice for the check's speed.

**C5. The `admit` and `__call__` handshake is unstated.** Low (031 Decision 5).
- "Unless the door already did" needs a mechanism. For example, `admit` returning `None` leaves an admitted length, and `__call__` consumes it and checks that it equals `len(frame)`. Then a frame is counted exactly once on both paths: the door's, and a raw `host=` in 031's checks.
- 031's unit criterion 5 should count frames on both paths.

**C6. Small points.** Low.
- 036 Decision 7 should say that `Completed.tools` is returned on every ending: exit, trap, `"deadline"`, `"cancelled"`. Criterion 13 already reads it after a cancel.
- If 036's `MANIFEST` cache is guarded by a lock, `_after_fork_in_child` must make it anew, as it does `_zip_lock`. Otherwise Decision 8's "nothing to reset" holds.
- Question 49's "Meanwhile" line names 030, 031 and 032, but not 036.

### Verdict

- **031: confirmed for build, on one condition.** C1's validation budget and linear `uniqueItems` must be written into Decisions 3 and 5 and criteria 4 and 5 before the build starts. This is a security boundary, and it should not be improvised in the build. C3 to C5 are wording and check fixes that the author can fold in at the same time. Those edits need no further pre-build review; the build review checks them against the diff.
- **036: confirmed for build, after 031 lands, on conditions.** C2's statement, the visible count and the fault on a failed thread start, plus C6's first two points, go into the spec before the build or are made by the builder and checked at build review. Its security design holds:
  - refusal by length before the copy (EXECUTED);
  - one thread per call with a per-call quota (EXECUTED in the model);
  - the bound's four ends, with Ctrl-C read and never cleared;
  - one result slot per call;
  - `host=` and `tools=` exclusive.

### One line

The revision fixes every finding. The probes confirm admission before the copy, the version-free frame rules and the per-call thread quota. What remains before 031 builds is a budget on the validator itself.

### Author's note: where each condition was written in (2026-10-17)

- **C1** (031): Decision 3 gains `uniqueItems` in one pass (a type-tagged, hashable canonical key per item, equal exactly when the strict equality is) and a validation budget of 100,000 counted steps per frame (`TOOL_VALIDATION_STEPS`; schema nodes visited and item keys made), past which the call is `invalid_arguments`, "the arguments are too complex to check". Decision 5's validation step names the budget. Criterion 4 checks pydantic's recursive union (its schema written into the check) against a 62-deep value failing at its leaf, 50,001 items with one repeat refused in one pass, and 100,001 distinct items answered "too complex"; each is seen failing first against a naive validator given the same counter. One correction to the reviewer's example: 524,288 *equal* items are refused at the second item by a set, so the check uses distinct items to reach the budget.
- **C2** (036): Decision 5 says the bound is per call, not per process (each run can leave up to five threads behind; no process-wide ceiling, since it would bring back finding 2), adds `runner.stats()["tool_threads_running"]`, and makes a failed thread start a `tool_error` fault. Decision 9's README section says the same. Criterion 3 checks the failed start; criterion 11 reads the count.
- **C3** (031): Decision 4 step 3 counts the frame's nesting with its envelope, at most 64 (62 inside `args`); step 5 refuses a lone surrogate in keys and values. Criterion 5 tests 64 (passes) and 65 (refused), and a surrogate in a key.
- **C4** (031): criterion 8 uses 10,000-character keys and one 1,000,000-character key that fits the cap, so the message bound is reached.
- **C5** (031): Decision 5 states the handshake (`admit` leaves a pending length; `__call__` consumes it and checks it, or calls `admit` itself on the raw path; a mismatch is `protocol`). Criterion 5 counts each frame once on both paths.
- **C6** (036): Decision 7 returns `Completed.tools` on every ending; Decision 8 makes any lock (the `MANIFEST` cache's, the thread count's) anew in `_after_fork_in_child`; criterion 4 adds a run that traps out of fuel after a tool call. Question 49's "Meanwhile" line names 036.
- Status lines: 031 "confirmed for build with conditions, written in"; 036 the same, "builds after 031 lands".

