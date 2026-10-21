# 103 — The engine seam: one module touches wasmtime-py's private API

- **Status:** **built on `d77425d` in worktree `spec/103-the-engine-seam`, 2026-10-20, awaiting
  the build review** (the landing notes below; the base `3626bb6` on branch
  `claude/gallant-ride-9nxxmn`, main `5feb7e9` plus the chain's specifications and reviews).
  Drafted 2026-10-20 on that branch; its pre-build review and confirmation are
  `../reviews/103-the-engine-seam-spec-2026-10-20.md`. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, not build-class (§5.7): it touches no file under `scripts/`,
  `recipes/`, `downloads/` or the release workflow, and no artifact byte. **It changes no line of
  `tests/public_api.txt`.** It is **the first of the stacked chain 103 → 104 → 105 → 106 → 107 →
  108** (the memo, section 8): 104 is built on this specification's reviewed tip, and the chain
  lands as one wave. It is **also a judge change** (two new rules checks, a new unit file, two unit
  rows moved and one re-pointed, the harness driver's engine made through the seam): the lane accepts it with
  `--accept-judge`. Files: `src/wasi_python/_wasmtime_ffi.py` (new), `src/wasi_python/runner.py`,
  `src/wasi_python/mounts.py`, `tests/harness/scan.py`, `tests/harness/guest.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_4_embedding.py` (one check's two private
  reads), `tests/unit/test_wasmtime_ffi.py` (new), `tests/unit/test_runner_calls.py`,
  `tests/unit/test_runner_cancel.py` (its `shared` fixture re-pointed; the pre-build review's
  M1), `tests/unit/test_runner_async.py`, `tests/unit/test_runner_mounts.py`,
  `tests/unit/test_scan.py`, `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md`
  (new) and one row of `context/upstream/README.md` (Design, "The debt is documented"),
  `CHANGELOG.md`, this specification.
- **Depends on:** landed specifications only: 011 (the shared host functions, which never raise
  into wasmtime-py), 015 (the epoch callback and its stop error), 028 (Decision 3: `run` needs
  wasmtime-py, importing the package does not), 032 (the forwarder), 048 (the guard trampoline
  and fuel-neutral forwards), 071 (Decision 9: the trap-handler check reads wasmtime's load base),
  078 (Decision 1: the async stack size, set before any engine), 092 (`sameness.py` and claim
  lists). **104 depends on this specification**: it splits `runner.py` into a package and keeps
  this module where it is (Decision 7).
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`, finding
  H2 ("the engine adapter is not isolated") and section 8 (the chain, the owner's four decisions,
  the baseline set); its own measurements, each labelled, taken on `a9064a2` with the commands
  shown.

## The problem

**wasmtime-py's private API** is every name of wasmtime-py that begins with an underscore or is
not in its documented surface: the module `wasmtime._ffi` (which re-exports the generated
`wasmtime._bindings`), `Func._func`, `Trap._from_ptr`, `WasmtimeError._from_ptr`,
`Caller._context()`, `Store._context()`, and the `ptr()` methods of `Store`, `Config` and
`WasiConfig`. The runner uses it for what the public API cannot do: stop a guest from inside a
host function without raising through wasmtime-py's process-wide exception slot (spec 011),
answer the epoch callback (spec 015), own the output table without wasmtime-py's unlocked one
(spec 011), forward a file call to wasmtime's own WASI fuel-neutrally (specs 032 and 048), set the
async stack size wasmtime-py 49 has no property for (spec 078), and read wasmtime's load base for
the trap-handler check (spec 071).

Today those uses are spread over two modules. Measured on `a9064a2` (EXECUTED,
`uv run python -I build/103/hits.py`, the regex of Decision 3 over every `.py` under `src/` and
`tests/`): **25 lines in `src/`** (`runner.py` 14, `mounts.py` 11) and **6 in `tests/`**
(`tests/harness/guest.py` 2, `tests/unit/test_runner_calls.py` 1,
`tests/unit/test_runner_async.py` 1, `tests/unit/test_runner_mounts.py` 1,
`tests/checks/test_v1_4_embedding.py` 1). They reach thirteen `_ffi` names
(`wasmtime_context_set_epoch_deadline`, `wasmtime_store_epoch_deadline_callback`,
`wasmtime_error_new`, `wasi_config_set_stdout_custom`, `wasi_config_set_stderr_custom`,
`wasmtime_func_call`, `wasmtime_context_get_fuel`, `wasmtime_context_set_fuel`,
`wasmtime_val_t`, `WASMTIME_I32`, `WASMTIME_I64`, `wasm_trap_t`, `dll`; READ, `grep -ohE
'_ffi\.[A-Za-z_]+'`), one optional one (`wasmtime_config_async_stack_size_set`, through
`getattr`), one `_bindings` record (`_wasmtime_store_epoch_deadline_callback.argtypes`), two
tables the judge reads to assert the runner adds nothing to them (`_func.FUNCTIONS`,
`_wasi.CUSTOM_OUTPUTS`; spec 011's `test_calls_add_nothing_to_wasmtime_pys_tables`), the
exception slot `_func.LAST_EXCEPTION` (one unit row), and the six attribute forms above.

The pin `wasmtime>=49,<50` (`pyproject.toml`) is the only guard. When wasmtime-py 50 moves a
name, the first sign is an `AttributeError` inside a call, after a store and an instance exist,
and the fix touches two modules in 25 places with no one place to look. Spec 104 will cut
`runner.py` into nine modules; without this specification first, the 25 places would become 25
places in five modules.

**The seam** is the one module that may touch the private API. The rest of the package drives
the engine through the seam's named operations, so the engine's private surface has one shape in
this project, written down, checked at import and held by a rule.

## Decisions

### 1. The adapter's operations, one per private use today

**The adapter** is `src/wasi_python/_wasmtime_ffi.py`. It imports `wasmtime`, `wasmtime._ffi`,
`wasmtime._bindings` and `wasmtime._func` once, at its top, and exposes these names. Each one is
derived from a use that exists today (The problem); none is speculative. Every parameter and
return is annotated; `Storelike` is a `typing.Protocol` with one method, `_context()`, so a
`Store` and a `Caller` both satisfy it. **The adapter holds no mutable state**: constants,
functions and one class. Nothing in it is reset at fork or released at exit (spec 105 relies on
this).

| name | signature | replaces today |
|---|---|---|
| `PIN` | `"wasmtime>=49,<50"` | the literal in `_wasmtime()`'s message |
| `version()` | `-> str` | `_wasmtime_version()` (removed) |
| `Context` | `ctypes.POINTER(_ffi.wasmtime_context_t)`, a type alias | the raw pointer type in four signatures |
| `context_of(storelike)` | `-> Context` | `caller._context()` (four sites), `storelike._context()` |
| `context_address(storelike)` | `-> int` | `_context_address` (removed; its two callers use this) |
| `set_epoch_deadline(storelike, ticks)` | `-> None`; public `Store.set_epoch_deadline` when the object has it, else the binding on `context_of` (Decision 8) | `_ffi.wasmtime_context_set_epoch_deadline` in `_Call.stop` and `_epoch_now` |
| `get_fuel(storelike)` | `-> int`; raises `WasmtimeError`; public `Store.get_fuel` when the object has it (Decision 8) | `mounts._get_fuel` (removed) |
| `set_fuel(storelike, fuel)` | `-> None`; never raises; public `Store.set_fuel` when the object has it (Decision 8) | `mounts._set_fuel` (removed) |
| `new_error(text)` | `bytes -> int`: the address of an error wasmtime owns, 0 when none was made | `_ffi.wasmtime_error_new` and its cast in `_stop_error` |
| `delete_error(address)` | `int -> None` | `_ffi.wasmtime_error_delete` in a unit row |
| `EPOCH_CALLBACK` | the `CFUNCTYPE` type of the callback | `_bindings._wasmtime_store_epoch_deadline_callback.argtypes[1]` in `_watch` |
| `watch_epochs(store, callback)` | `-> None`; data `None`, a NULL finalizer | `_ffi.wasmtime_store_epoch_deadline_callback(store.ptr(), …)` |
| `OUTPUT_WRITE`, `OUTPUT_FREE` | the two `CFUNCTYPE` types of a custom output's write and free | the two `@ctypes.CFUNCTYPE(…)` declarations on `_output_write` and `_output_free` |
| `set_custom_outputs(wasi, write, free, out_key, err_key)` | `-> None` | `_send_outputs`'s two `_ffi` calls and `wasi.ptr()` |
| `ASYNC_STACK_SETTER` | the binding, or `None` when wasmtime-py lacks it | `getattr(_ffi, "wasmtime_config_async_stack_size_set", None)` |
| `set_async_stack(cfg, size)` | `-> None`; `RuntimeError` naming `version()` when there is neither the property nor the binding | `_set_async_stack` (removed) |
| `engine_symbol_address()` | `-> int` | `ctypes.cast(_ffi.dll.wasm_engine_new, c_void_p).value` in `_wasmtime_base` |
| `raw_func(func)` | `Func -> wasmtime_func_t` | `exports[name]._func`, `stat[name]._func` in `bind` |
| `PreparedCall(func, kinds)` | `kinds` a tuple of `"i32"` and `"i64"`; builds the argument array with its kinds set and a one-slot result array, once; the trap out-pointer is made per call, as `forward` makes it today, since `Trap._from_ptr` takes ownership of what it points to (the pre-build review's L8) | the `slot` tuple `forward` builds and caches |
| `PreparedCall.call(context, args)` | `-> int`, the `i32` result; raises `Trap` or `WasmtimeError` | `_ffi.wasmtime_func_call`, `wasm_trap_t`, `Trap._from_ptr`, `WasmtimeError._from_ptr` |
| `last_exception()` | `-> BaseException \| None` | `_func.LAST_EXCEPTION` in one unit row (no `src/` line reads it; EXECUTED, `grep -n LAST_EXCEPTION src/wasi_python/*.py` is empty) |
| `host_function_count()` | `-> int` | `len(_func.FUNCTIONS.list)` in `test_calls_add_nothing_to_wasmtime_pys_tables` |
| `custom_output_table()` | `-> Any`, wasmtime-py's own table of custom outputs, which the runner never uses (spec 011) | `_wasi.CUSTOM_OUTPUTS` in the same check, which counts its `allocate` calls |
| *the check and the protocol* (the pre-build review's L5) | | |
| `Storelike` | a `Protocol` with one method, `_context()`; a `Store` and a `Caller` satisfy it | the `Any` on today's `caller` and `storelike` parameters |
| `NEEDED`, `OPTIONAL` | tuples of `(holder, name)` pairs (Decision 2) | nothing: the first list of the private names in one place |
| `missing(holders)` | `-> list[str]`, pure (Decision 2) | nothing |
| `check(holders)` | `-> None`; raises the one `ImportError` (Decision 2) | nothing |

The reasons for the shape:

- **A prepared call, not a call function.** The forwarder's cost is in making and filling the
  `wasmtime_val_t` arrays. Today it caches them per call and per name (`_Forwards.slots`). A
  `PreparedCall` owns one pair of arrays for one function, so `mounts.py` caches an object it
  cannot mis-assemble, and the array types never leave the adapter. `call` keeps today's
  precedence exactly: when both a trap and an error come back, the `Trap` is raised and the
  error is wrapped so that it is freed (`WasmtimeError._from_ptr` owns it), as `forward` does
  now. It touches no fuel: the fuel bracket stays in `forward` (Decision 4).
- **The output table stays in the runner.** `_outputs`, its lock, its keys, `_output_write` and
  `_output_free` are the runner's (spec 011): they are state, and the adapter holds none. The
  adapter gives their C types, read from the binding's own `argtypes` (which is what
  `test_the_bindings_the_runner_calls_exist` asserts today's declarations equal, by identity), so
  the declaration is not repeated.
- **The epoch callback stays in the runner.** `_on_epoch`, `_epoch_answer`, `_stop_error` and
  the one `_epoch_callback` object (made once under its lock) are policy and state. The adapter
  gives the callback's type and registers it. `_stop_error` keeps its `try`/`except` and its
  continue-by-one fallback (spec 015's build review, F2): `new_error` is plain, and may raise.
- **`set_fuel` never raises** because today's `_set_fuel` never does: it wraps the error so it
  is freed, and a metered store never refuses. `get_fuel` raises `WasmtimeError` from the error
  pointer, as today.
- **`set_async_stack` keeps spec 078's three branches** in their order: the `Config` property
  when wasmtime-py's class has one (49.0.0 has none: EXECUTED, `isinstance(getattr(wasmtime.Config,
  "async_stack_size", None), property)` is `False`), else `ASYNC_STACK_SETTER`, else
  `RuntimeError` before any engine is made. The binding is read into `ASYNC_STACK_SETTER` at
  import and looked up there at call time, so a test patches the adapter's name, not `_ffi`.
- **`engine_symbol_address`, not `load_base`.** `dladdr` and `_load_base` are the runner's
  platform code (spec 071) and move to `_platform.py` in spec 107. The adapter gives only the
  address of one symbol of wasmtime's library; what library holds it is the platform's work.
- **`last_exception()`, `host_function_count()` and `custom_output_table()` exist for the
  judge** (`test_runner_calls.py:116`, spec 011: the slot is `None` after a call;
  `test_calls_add_nothing_to_wasmtime_pys_tables`: a call defines no host function and takes no
  custom output of wasmtime-py's). No `src/` line reads them; the adapter names them so that the
  rule of Decision 3 covers `tests/` too, with no exemption for a check. They are read-only: the
  check patches `allocate` on the table it is given, as it does today.

### 2. The adapter checks at import that every name it needs exists

At import, after its own imports, the adapter calls `check(holders)` with a table of
**holders**: `{"wasmtime._ffi": _ffi, "wasmtime._bindings": _bindings, "wasmtime._func": _func,
"wasmtime._wasi": _wasi, "wasmtime.Trap": Trap, "wasmtime.WasmtimeError": WasmtimeError,
"wasmtime.Caller": Caller, "wasmtime.Store": Store, "wasmtime.Config": Config,
"wasmtime.WasiConfig": WasiConfig, "wasmtime.Func": Func, "wasmtime._ffi.dll": _ffi.dll}`.
`NEEDED` is a tuple of `(holder, name)` pairs, one per private name of Decision 1's table except
the optional `wasmtime_config_async_stack_size_set`, which is the one entry of a second tuple,
`OPTIONAL`, that `check` does not read (the sheet of Design, "The debt is documented", lists
both): the sixteen `_ffi` names (the thirteen of The problem, `wasmtime_error_delete` and
`wasmtime_error_t` for `delete_error`, and `wasmtime_context_t` for `Context`); `_bindings`'
`_wasmtime_store_epoch_deadline_callback` and `_wasi_config_set_stdout_custom` (each with an
`argtypes` of length 4, since `EPOCH_CALLBACK`, `OUTPUT_WRITE` and `OUTPUT_FREE` are read from
them); `_func.LAST_EXCEPTION`; `_func.FUNCTIONS`; `_wasi.CUSTOM_OUTPUTS`; `Trap._from_ptr`;
`WasmtimeError._from_ptr`; `Caller._context`; `Store._context`; `Store.ptr`; `Config.ptr`;
`WasiConfig.ptr`; `dll.wasm_engine_new`; and `Func._func`, which is an instance attribute, read
as a class annotation (EXECUTED, `wasmtime.Func.__annotations__ == {"_func":
wasmtime._bindings.wasmtime_func}`; a class-level `hasattr` is `False`).

The holder for `dll` is `getattr(_ffi, "dll", None)`, not `_ffi.dll`, since the dictionary
literal evaluates its values while it is built, and `missing` reports every name of a holder that
is `None` (the pre-build review's L6): so a wasmtime-py without `_ffi.dll` still raises the one
`ImportError`, not an `AttributeError` at that line.

`missing(holders) -> list[str]` is pure: it returns the dotted names absent from the table, in
`NEEDED`'s order. `check(holders)` raises **one `ImportError`** when the list is not empty:

```
wasi_python drives wasmtime-py through its private API, and wasmtime-py 50.0.0 lacks:
wasmtime._ffi.wasmtime_error_new, wasmtime.Trap._from_ptr. wasi_python was written against
wasmtime>=49,<50; install a wasmtime-py inside that range, or update wasi_python
```

(the version from `version()`, the names from `missing`, the range from `PIN`). Nothing else is
checked at import: a name that exists with a changed shape is the unit file's work (Decision 5,
U5), and the call that uses it raises as it would today.

**How `_wasmtime()` surfaces it.** `_wasmtime()` (`runner.py:1465`, spec 028, Decision 3) is
the first thing `run`, `run_async` and `Session` call that imports wasmtime-py. It keeps its
`try` block and its one `ImportError` for the three causes it names today (not installed, a
platform wasmtime-py does not support, its library not loading). After that block it does
`from . import _wasmtime_ffi  # noqa: F401`, outside the `try`: the adapter's own `ImportError`
is already one error that names the version and the names, and wrapping it in the "reinstall
it" message would give wrong advice. So a moved symbol is seen at the first `run()`, before any
engine, store or instance exists, with the names in the text. The message keeps its literal
`wasmtime>=49,<50`: when wasmtime-py itself cannot be imported, the adapter cannot be either, so
the message cannot read `PIN`. The range is then written in three places, `pyproject.toml`,
`PIN` and this message, and one unit row (U4) holds the three equal, so a bump that misses one
is red.

**The package still imports without wasmtime-py.** The adapter imports wasmtime-py at its top,
so nothing imports the adapter at package import: `runner.py` and `mounts.py` import it inside
the functions that use it (`from . import _wasmtime_ffi as ffi`), where today's `from wasmtime
import _ffi` lines are. `test_package_imports_without_wasmtime` (spec 028) stays green, and a new
unit row asserts `wasi_python._wasmtime_ffi` is not in `sys.modules` after `import wasi_python`
(Decision 5, U10). A local import of a module already imported is one dictionary lookup, which
is what the forwarder pays today.

### 3. A rules check: only the seam touches the private API

`tests/harness/scan.py` gains `private_engine_hits(root, subdirs, exempt) -> list[str]`, and
`tests/checks/test_rules.py` gains
`test_only_the_engine_seam_touches_wasmtimes_private_api`. The check reads every `.py` file under
`src/` and `tests/` (`scan.files_under`, which skips `__pycache__`), **except exactly two**:
`src/wasi_python/_wasmtime_ffi.py` and `tests/unit/test_wasmtime_ffi.py`. It reads each file's
raw text line by line, comments and docstrings included, and reports `path:line: text` for every
line this regex matches:

```python
PRIVATE_ENGINE = re.compile(
    r"from wasmtime import [^\n]*\b_(?:ffi|bindings|func|wasi)\b"
    r"|\bwasmtime\._(?:ffi|bindings|func|wasi)\b"
    r"|(?<!self)\._context\(\)"
    r"|\._func\b"
    r"|\b_from_ptr\b"
    r"|\.ptr\(\)"
)
```

The reasons:

- **`tests/` is covered too**, beyond the memo's "the only module importing". The harness driver
  (`tests/harness/guest.py:68-73`) sets the async stack size through `_ffi` today, three unit
  rows reach `_ffi`, `_bindings`, `_func` or `.ptr()`, and one check reads `_func` and `_wasi`
  (The problem). A bump that the rule lets tests ignore is not a bump with one place to look.
  Every one of the six lines has a home: the driver calls `_wasmtime_ffi.set_async_stack(cfg,
  WASM_STACK)` (the same three branches `run` gets, which spec 078's
  `test_the_guest_driver_makes_the_runners_engine` holds); three rows move to the adapter's unit
  file (Decision 5); `test_runner_mounts.py:260`'s `call.stopped.ptr()` becomes
  `str(call.stopped)`, a non-empty message, which is what the row checks: a real wasmtime error;
  and `test_calls_add_nothing_to_wasmtime_pys_tables` counts through `host_function_count()`
  and `custom_output_table()`, with every assertion it has today.
- **Raw text, not tokens.** A regex over the tokenized source would let `importlib.import_module
  ("wasmtime._ffi")` through as a string and would need its own parser to test. Raw text is
  simpler and stricter: prose in `src/` outside the adapter must not spell `._context()`,
  `._func`, `_from_ptr`, `.ptr()` or `wasmtime._ffi` either. It says "the seam's `context_of`"
  instead. The adapter's docstrings may say anything.
- **`(?<!self)`** keeps `self._context()` out: `tools.py:1952` calls its own `_context()` method,
  a `contextvars` copy, which is not wasmtime-py's. `self._context()` inside the adapter is never
  written, so nothing hides behind the exemption.
- **`.ptr()`** matches any `ptr()` call. No line of `src/` or `tests/` calls a `ptr()` that is
  not wasmtime-py's (EXECUTED: the 31 hits above are the whole list, and every `.ptr()` among
  them is on a `Store`, `Config`, `WasiConfig` or `WasmtimeError`).
- **`\bwasmtime\._(?:ffi|bindings)\b`** needs the `wasmtime.` prefix, so
  `tests/harness/constructors.py:61`'s string `_GLOBAL__sub_I_highs_bindings.cpp` is not a hit
  (EXECUTED: 0 hits in that file).

**The rule's own files avoid the rule** (the pre-build review's M2). The regex matches its own
source: the raw line `r"|\._func\b"` is a hit (EXECUTED by the reviewer: the `\b` after `func` is
met by the backslash that follows), and U17's stand-in tree needs lines such as `x._func` and
`other._context()` spelled in `tests/unit/test_scan.py`. Neither file is exempt. So, in
`scan.py`, the pattern is assembled from two string literals that do not match on their own
(`"\\._" "func\\b"` for that alternation, and the same split for `_from_ptr` and `.ptr()`), with
a comment saying why; and in `test_scan.py` every fixture line is built by concatenation
(`"x._" + "func"`), with the same comment. U17 asserts that `tests/harness/scan.py` and
`tests/unit/test_scan.py` themselves are not hits, so the dodge cannot lapse silently. The
exemption list stays at exactly two files.

**Seen failing first** (criterion 3): on `a9064a2` the check reports the 31 lines of The problem
(EXECUTED with the same regex: 25 in `src/`, 6 in `tests/`); on the built commit it reports none.
Its unit row (`tests/unit/test_scan.py`, Decision 5, U17) builds a stand-in tree with each of the
six alternations hit once, a `self._context()` and a `highs_bindings.cpp` line that are not, and
an exempt file whose hits are not reported.

### 4. No behaviour changes: the frozen set gives the same verdicts

The change is a move of mechanism, not of policy. Each private call happens in the same order,
on the same thread, under the same lock, with the same fallback:

- **Every forward stays fuel-neutral.** `forward` keeps its bracket exactly: `get_fuel` before,
  `set_fuel(min(before + FUEL_ALLOWANCE, FUEL_MAX))`, the call, `set_fuel(before)` in a
  `finally`, then `stop_fuel = (raised, before)` on a trap or error, then the raise.
  `PreparedCall.call` reads and writes no fuel. `tests/unit/test_runner_mounts.py::
  test_the_rename_rule_forward_is_fuel_neutral` (spec 048, criterion 4) holds this across every
  cap and keeps its verdict.
- **Every errno is the same.** No shadow changes; `forward` still answers `EBADF` before a
  trampoline exists, and still returns `results[0].of.i32` through `PreparedCall.call`.
- **The stop path is the same.** `_Call.stop` and `_epoch_now` set the deadline to 0 through
  `context_of(caller)`; `_epoch_answer` compares `ctypes.addressof(context.contents)` with
  `call.context` as today (plain `ctypes` on a raw pointer is not the private API; the rule does
  not match it).
- **The engine is made the same way**: `_engine` calls `set_async_stack` first, then
  `max_wasm_stack`, under `_lock`, with `_fork["used"]` set before.
- **The trap-handler check reads the same base**: `_wasmtime_base` passes
  `engine_symbol_address()` to `_load_base`.
- **The `.cwasm` cache name is the same string**: `_module_miss` (`runner.py:4739`) reads
  `ffi.version()`, the same `importlib.metadata` string `_wasmtime_version()` gave, so no cache
  file name changes (the pre-build review's L3).

**The acceptance criterion** is the memo's, section 8: `tests/harness/sameness.py` between two
fast-tier records on the **frozen baseline set**, the `v0.1.0a7` release's artifact set verified
against its `SHA256SUMS`, pointed at by `WASI_PYTHON_ARTIFACTS`. **A record** is the
`build/progress/latest.json` the judge writes. The builder runs `uv run pytest -m "not slow" -n 3`
(a slot the lane grants) on the base commit and copies the record to `build/103/baseline.json`,
then on the built commit to `build/103/built.json`, and runs

```
uv run python tests/harness/sameness.py --claims build/103/claims.toml build/103/baseline.json build/103/built.json
```

which must print nothing and exit 0. `build/103/claims.toml` is the claim list of *For the
lane*: the one new check and the unit count. No fuel row moves (host code spends no guest
fuel), no bytes row moves (no artifact changes), no pass is lost. Host-side counts the checks
record as facts (file calls, tool frames) are compared by `sameness.py` too and must not move.

### 5. Unit checks for the adapter: eighteen rows

`tests/unit/test_wasmtime_ffi.py` is new; it is the one test file that may import `wasmtime._ffi`
(Decision 3). Rows U1 to U10 and U18 need no wasm module. Rows U11 to U16 drive wasmtime-py
directly with a WAT module, as `test_runner_calls.py` does today, and need no `python.wasm`:
nothing here needs the frozen set, and the fast tier runs every row. What *does* need the guest,
the end-to-end forward with its errno and fuel, is already held by the checks under
`tests/checks/` and by Decision 4's sameness.

- **U1** `missing()` names each absent name of a stand-in holder table, in `NEEDED`'s order, and
  names nothing when every name is present (a table built from the real wasmtime-py); its second
  assertion lists the adapter's `__all__` against the names of Decision 1's table (the pre-build
  review's L5).
- **U2** `check()` on a table missing two names raises one `ImportError` whose text has
  `version()`, both dotted names and `PIN`.
- **U3** `_wasmtime()` lets the adapter's error through: with `wasmtime_error_new` removed from
  `_ffi` and the adapter dropped from `sys.modules` (both by `monkeypatch`, restored after),
  `runner._wasmtime()` raises `ImportError` matching `wasmtime-py <v> .*wasmtime_error_new`,
  where `<v>` is `re.escape(importlib.metadata.version("wasmtime"))`, never a literal patch
  version (the pre-build review's L7: a 49.1.0 install must not turn the row red); and with
  `sys.modules["wasmtime"] = None`, it raises the "needs wasmtime-py" error with the cause
  chained, as today.
- **U4** `PIN` equals the one dependency of `pyproject.toml` (read with `tomllib`), and the
  range in `_wasmtime()`'s "needs wasmtime-py" message (U3's second half) equals `PIN`, so a bump
  that changes one of the three and not the others is red.
- **U5** the binding shapes: `test_the_bindings_the_runner_calls_exist` moved from
  `test_runner_calls.py`, now asserting `type(runner._output_write) is OUTPUT_WRITE`,
  `type(runner._output_free) is OUTPUT_FREE`, `EPOCH_CALLBACK._restype_ is c_size_t` and its
  four argument types, and the two `argtypes` lists it checks today.
- **U6** `new_error(b"x")` returns a non-zero address and `delete_error` frees it; `_stop_error`'s
  fallback (moved from `test_runner_async.py`), with `_wasmtime_ffi.new_error` patched to raise
  `MemoryError` and then to return 0: the delta is set to 1 and 0 is returned.
- **U7** `set_async_stack`: a stand-in with the property gets the property; a stand-in without
  it, with `ASYNC_STACK_SETTER` patched to a recorder, gets the binding with `cfg.ptr()`; with
  neither, `RuntimeError` matching `wasmtime-py .* cannot set async_stack_size`. And
  `test_the_async_stack_size_property_is_preferred`,
  `test_no_engine_is_made_without_the_async_stack_size` and
  `test_the_guest_driver_makes_the_runners_engine` stay in `test_runner_calls.py`, calling
  `_wasmtime_ffi.set_async_stack` in place of the deleted `runner._set_async_stack` and
  patching `_wasmtime_ffi.ASYNC_STACK_SETTER` in place of `_ffi` (the pre-build review's M1).
- **U8** `engine_symbol_address()` is a non-zero `int`.
- **U9** `last_exception()` is `None` after a clean call (the row at `test_runner_calls.py:116`,
  re-pointed); `host_function_count()` is an `int` that grows by one when a `Linker.define_func`
  is made; `custom_output_table()` has a callable `allocate`.
- **U10** `import wasi_python` in a fresh `-I` interpreter (as `test_package_imports_without_
  wasmtime` runs one) leaves `wasi_python._wasmtime_ffi` out of `sys.modules`; `run` is callable.
- **U11** `PreparedCall` on `(func (param i32 i64) (result i32))` returns the function's answer;
  a second call on the same object returns a second answer (the arrays are reused); on
  `(func (result i32) unreachable)` it raises `Trap`.
- **U12** `get_fuel`/`set_fuel` round-trip on a store of a metered engine; on an unmetered store
  `get_fuel` raises `WasmtimeError` and `set_fuel` raises nothing.
- **U13** `watch_epochs` with an `EPOCH_CALLBACK` that returns `new_error(b"stopped by a unit
  row")`: after the engine's epoch is incremented, a call into a looping guest ends with an
  exception whose text contains that message.
- **U14** `set_epoch_deadline(store, 0)` on a store with no callback: the next call
  into the guest raises `Trap`.
- **U15** inside a host function, `context_address(caller)` equals `context_address(store)`.
- **U16** `set_custom_outputs` on a `WasiConfig`, with `OUTPUT_WRITE` and `OUTPUT_FREE`
  callbacks the row defines: a WAT guest that `fd_write`s to 1 and to 2 reaches the write callback
  with the two keys and the bytes; dropping the store reaches the free callback once per key.
- **U17** `private_engine_hits` (Decision 3's unit row, in `test_scan.py`): the stand-in tree,
  and then the real tree: `tests/harness/scan.py` and `tests/unit/test_scan.py` are not hits
  (the pre-build review's M2); and `private_api_debt_errors` (Design, "The debt is
  documented"): a stand-in adapter and sheet that agree give no error, a name missing from the
  sheet, a row naming no entry and a name absent from the docstring each give one; one row of the
  agreeing stand-in sheet carries an `(optional)` tag after its backticks and is read as its
  backticked text (the confirmation's L10).
- **U18** public first (Decision 8): for every operation whose public form the row's wasmtime-py
  has, the adapter calls it and not the binding. A stand-in store-like object with `get_fuel`,
  `set_fuel` and `set_epoch_deadline` recording their arguments, and `_ffi`'s three bindings
  patched to raise, sees the three public methods used and no binding called; a stand-in
  `Config` class with an `async_stack_size` property sees the property set and
  `ASYNC_STACK_SETTER` not called; a stand-in without any of them sees the bindings called on
  `context_of`. The row reads `wasmtime.Store` for the methods it has, so on a release that adds
  `Caller.get_fuel` the row covers that too without a change.

### 6. A wasmtime-py major bump is done in one place

**A major bump** is a change of the pin's range, `wasmtime>=49,<50` to `>=50,<51`. The
procedure, which the adapter's module docstring carries so the one place to look says what to
do:

1. Change the range in `pyproject.toml` and `PIN`; `uv sync` (U4 holds the two equal).
2. `uv run python -c "import wasi_python._wasmtime_ffi"`. The import check names every name
   that moved (Decision 2). Nothing else in the package fails to import, because nothing else
   names the private API (Decision 3).
3. Fix each named operation inside the adapter. The table of Decision 1 says what each must do;
   rows U5 to U16 say what each must do observably.
4. `uv run pytest tests/unit/test_wasmtime_ffi.py tests/checks/test_rules.py` on the fast tier's
   budget, then the fast tier on the frozen set with `sameness.py` against the last accepted
   record (Decision 4): the same verdicts, or the differences named.
5. The bump is its own specification, since it changes a pinned input of the wheel (constitution
   §4.2); this one gives it its shape. Whether a bump is build-class is that specification's to
   say: `pyproject.toml` is none of the four build-class files, but the released wheel's
   metadata changes.
6. **When a release makes an operation public** (Design, "The debt is documented"), the same
   change, or a minor bump's, does three things: the adapter's preference order is already
   public first (Decision 8), so often nothing changes in the operation; the private name leaves
   `NEEDED` or `OPTIONAL`; and its row is struck from the facts sheet's table (moved to the
   sheet's "Landed" list) in the same change, which the rules check
   `test_the_private_api_debt_is_documented` enforces. If the release is a new major, the pin
   widens as steps 1 to 5 say.

### 7. What the chain honours

- **The path is fixed.** The adapter is `src/wasi_python/_wasmtime_ffi.py`, a sibling of
  `runner.py`. Spec 104 turns `runner.py` into a package of modules and leaves the adapter where
  it is; the rule's exemption names the exact path.
- **The adapter holds no state.** Spec 105's one owner of process state has nothing to take from
  it; the one `_epoch_callback` object and the output table stay in the runner's modules
  (`_engine.py` and `_call.py` after 104).
- **Tests patch the adapter's names**, never `wasmtime._ffi` outside the adapter's unit file
  (U18 patches `_ffi`'s three bindings there): `new_error`, `ASYNC_STACK_SETTER`,
  `watch_epochs`, `context_address` (the `shared` fixture of `tests/unit/test_runner_cancel.py`,
  which patches `runner._context_address` today; the pre-build review's M1). A patch takes
  effect because the runner resolves `ffi.<name>` through the module attribute at call time. The
  rule holds it.
- **Prose in `src/` outside the adapter does not spell the private names** (Decision 3). A
  docstring says "through the seam".
- **`_wasmtime()` keeps the adapter import inside it** wherever 104 moves the function; it is the
  one place a moved symbol is first seen.
- **Spec 106's type checker** finds the adapter fully annotated; `Storelike` is defined here and
  spec 107's call-context protocol may name it.
- **Spec 107's `_platform.py`** takes `engine_symbol_address()` from the adapter and keeps
  `dladdr` to itself.

### 8. Public first, in the seam (the owner, 2026-10-20; added after the pre-build review's draft)

**Public first** means: every adapter operation calls wasmtime-py's public API when the installed
release has it, and falls back to the private binding otherwise, the way `_set_async_stack`
prefers `Config.async_stack_size` today (spec 078, Decision 1). The choice is made inside the
adapter, once at import where the public form is a class attribute (`Config.async_stack_size`,
read into a module constant beside `ASYNC_STACK_SETTER`), or per call by the object given (a
`Store` has the public fuel and deadline methods; a `Caller` does not).

**What 49.0.0 has** (EXECUTED, `uv run python` over `dir()` and `inspect` in the venv):
`Store` has `get_fuel`, `set_fuel`, `set_epoch_deadline` and `set_limits`; `Caller` has `get`
only (and `_context`, `_invalidate`), no fuel and no deadline; `Config` has no
`async_stack_size`; `WasiConfig.stdout_custom` and `stderr_custom` exist only as setter
properties; `Func.__call__(store, *params)` accepts a `Caller`; `Engine` has `increment_epoch`
and no epoch callback; `Store` has no epoch callback; nothing public gives the library's path or a
symbol's address; `Trap(message)` and `WasmtimeError(message)` build Python exceptions, not an
owned C error.

| operation | private binding it calls | public form in 49.0.0 | public name the adapter prefers once a release has it | today |
|---|---|---|---|---|
| `context_of`, `context_address` | `Caller._context`, `Store._context` | none (`Caller` has `get` only) | a public store identity on `Caller` and `Store` (the C API has `wasmtime_caller_context`) | private |
| `set_epoch_deadline(storelike, ticks)` | `wasmtime_context_set_epoch_deadline` | `Store.set_epoch_deadline`; none on `Caller` | `Caller.set_epoch_deadline` | public on a `Store`, private on a `Caller` (below) |
| `get_fuel(storelike)` | `wasmtime_context_get_fuel` | `Store.get_fuel`; none on `Caller` | `Caller.get_fuel` | public on a `Store`, private on a `Caller` (below) |
| `set_fuel(storelike, fuel)` | `wasmtime_context_set_fuel` | `Store.set_fuel`; none on `Caller` | `Caller.set_fuel` | public on a `Store`, private on a `Caller` (below); the public path's `WasmtimeError` is caught and dropped, so `set_fuel` never raises on either path |
| `new_error`, `delete_error` | `wasmtime_error_new`, `wasmtime_error_delete` | none: a C error the epoch callback returns and wasmtime owns | a public epoch callback that takes a Python function returning "stop" or "continue n" | private |
| `EPOCH_CALLBACK`, `watch_epochs` | `_bindings._wasmtime_store_epoch_deadline_callback`, `wasmtime_store_epoch_deadline_callback`, `Store.ptr` | none | `Store.set_epoch_deadline_callback(fn)` | private |
| `OUTPUT_WRITE`, `OUTPUT_FREE`, `set_custom_outputs` | `_bindings._wasi_config_set_stdout_custom`, `wasi_config_set_stdout_custom`, `wasi_config_set_stderr_custom`, `WasiConfig.ptr` | `WasiConfig.stdout_custom = fn`, `stderr_custom = fn` | the same properties, once their table is safe for several threads | private: the properties keep the callable in `_wasi.CUSTOM_OUTPUTS`, a `Slab` with no lock (READ, `_slab.py`; EXECUTED: no module of wasmtime-py imports `threading`), and wasmtime calls the write and free on its own threads, so the runner keeps its own locked table (spec 011) |
| `ASYNC_STACK_SETTER`, `set_async_stack` | `wasmtime_config_async_stack_size_set`, `Config.ptr` | none (no property) | `Config.async_stack_size` (sheet 21) | private; the property first when present |
| `engine_symbol_address` | `_ffi.dll.wasm_engine_new` | none | none wanted: the address of one public C symbol is enough, and only `dladdr` reads it | private |
| `raw_func` | `Func._func` | none | the same as the prepared call's | private |
| `PreparedCall` | `wasmtime_val_t`, `WASMTIME_I32`, `WASMTIME_I64`, `wasm_trap_t`, `wasmtime_func_call`, `Trap._from_ptr`, `WasmtimeError._from_ptr`, `wasmtime_context_t` | `Func.__call__(caller, *params)` | a public call that reuses its argument arrays and gives the trap and error back to the caller | private: `Func.__call__` allocates its arrays on every call, on the hottest path the runner has (one per forwarded file call), and hides the trap and error pointers that the fuel bookkeeping in `forward` reads before it raises |
| `last_exception`, `host_function_count`, `custom_output_table` | `_func.LAST_EXCEPTION`, `_func.FUNCTIONS`, `_wasi.CUSTOM_OUTPUTS` | none | none: the judge reads them to assert the runner adds nothing (sheet 1 for the slot) | private, judge only |
| `version` | none (`importlib.metadata`) | public already | — | public |

**Fuel and the deadline inside a host function stay on the `Caller`.** Every one of the six
sites that reads fuel or sets the deadline inside a host function today holds a `Caller`, the
handle wasmtime gives a host function (`runner.py:3274` and `:3358`, the deadline;
`mounts.py:799`, `:803` and `:809`, the bracket; `:829`, the ABI branch; EXECUTED by the
confirmation's `grep`), and none holds the `Store` object (`_Call` keeps the store's context
address, not the store); every other fuel or deadline call in `src/` is on a `Store` and public
already. 103 does **not** thread the call's `Store` object into those six sites, for three
reasons: the public `Store` methods make the identical C call on the identical context (READ,
`_store.py:61-90` and `:109-115`: `ffi.wasmtime_context_get_fuel(self._context(), …)`), so
nothing would change
but an attribute lookup and a reference on the hottest path; spec 011's guard already compares
the caller's context with the call's, and passing a different object into the forward would
give that guard a second thing to be wrong about; and the judge's stand-in calls (`FakeCall` in
`tests/unit/test_runner_cancel.py`) have no store, so six rows would change for no behaviour.
So on 49.0.0 those six sites take the private path, and the adapter takes the public one the
day a release gives `Caller` the three methods, with no change to the runner. The public
preference is real today wherever a `Store` is given (U18), and `set_async_stack`'s is real the
day `Config.async_stack_size` lands.

## Intent

One module, named, typed, checked at import and held by a rule, is the whole of this project's
dependence on wasmtime-py's private surface. The runner and the mounts drive the engine through
that module's operations and change no behaviour: every forward spends the same fuel, every
errno is the same, every stop lands at the same instruction, and the frozen baseline set gives
the same verdicts. When wasmtime-py's next major release moves a name, the first `run()` says
which names, and the fix is one file.

## Design

### The adapter

```python
"""The engine seam (spec 103): the one module of wasi_python that touches wasmtime-py's private
API. ... [the table of Decision 1, the bump procedure of Decision 6]"""

from __future__ import annotations

import ctypes
from typing import Any, Protocol

import wasmtime
from wasmtime import Caller, Config, Func, Store, Trap, WasiConfig, WasmtimeError
from wasmtime import _bindings, _ffi, _func, _wasi

PIN = "wasmtime>=49,<50"
NEEDED: tuple[tuple[str, str], ...] = (("wasmtime._ffi", "wasmtime_context_set_epoch_deadline"), ...)


def version() -> str: ...
def missing(holders: dict[str, object]) -> list[str]: ...
def check(holders: dict[str, object]) -> None: ...  # raises the one ImportError


check({...})  # at import, after the definitions it needs

Context = ctypes.POINTER(_ffi.wasmtime_context_t)


class Storelike(Protocol):
    def _context(self) -> Any: ...


def context_of(storelike: Storelike) -> Context: ...
def context_address(storelike: Storelike) -> int: ...
def set_epoch_deadline(storelike: Storelike, ticks: int) -> None: ...  # public when it has it
def get_fuel(storelike: Storelike) -> int: ...  # else the binding on context_of(storelike)
def set_fuel(storelike: Storelike, fuel: int) -> None: ...  # (Decision 8; the confirmation's M9)
def new_error(text: bytes) -> int: ...
def delete_error(address: int) -> None: ...

EPOCH_CALLBACK = _bindings._wasmtime_store_epoch_deadline_callback.argtypes[1]
_EPOCH_FINALIZER = _bindings._wasmtime_store_epoch_deadline_callback.argtypes[3]

def watch_epochs(store: Store, callback: Any) -> None: ...

OUTPUT_WRITE = _bindings._wasi_config_set_stdout_custom.argtypes[1]
OUTPUT_FREE = _bindings._wasi_config_set_stdout_custom.argtypes[3]

def set_custom_outputs(wasi: WasiConfig, write: Any, free: Any, out_key: int, err_key: int) -> None: ...

ASYNC_STACK_SETTER = getattr(_ffi, "wasmtime_config_async_stack_size_set", None)

def set_async_stack(cfg: Config, size: int) -> None: ...
def engine_symbol_address() -> int: ...
def raw_func(func: Func) -> Any: ...
def last_exception() -> BaseException | None: ...
def host_function_count() -> int: ...
def custom_output_table() -> Any: ...


class PreparedCall:
    __slots__ = ("func", "kinds", "params", "results")

    def __init__(self, func: Any, kinds: tuple[str, ...]) -> None: ...
    def call(self, context: Context, args: tuple[int, ...]) -> int: ...
```

`check` runs before `Context`, `EPOCH_CALLBACK` and the other module constants are built, since
building them is what fails when a name is missing. The holder table is the real modules and
classes; `missing` reads a `(holder, name)` pair as `hasattr`, except `("wasmtime.Func",
"_func")`, which it reads from `Func.__annotations__`, and the two `_bindings` records, whose
`argtypes` must have length 4.

### The runner's side

Each of the nine `from wasmtime import _ffi` lines in `runner.py` and the three in `mounts.py`
becomes `from . import _wasmtime_ffi as ffi`, in the same function. Then:

- `_Call.__init__`: `self.context = ffi.context_address(store)`. `_shared`'s guard:
  `ffi.context_address(caller) != call.context`. `_context_address` is deleted.
- `_Call.stop` and `_epoch_now`: `ffi.set_epoch_deadline(caller, 0)`; the adapter takes the
  public method when the object has one and calls `context_of(caller)` itself on the private path
  (Decision 8; the confirmation's M9).
- `_stop_error`: `address = ffi.new_error(b"stopped by wasi_python")`; `if address: return
  address`; the rest as today. The adapter import sits inside the `try`, where today's `from
  wasmtime import _ffi` sits, so an import failure in the callback still continues by one tick
  (the pre-build review's semantics note).
- `_module_miss`'s cache name (`runner.py:4739`) reads `ffi.version()`, the same
  `importlib.metadata` string, so no cache file name changes (the pre-build review's L3).
- `_watch`: `_epoch_callback = ffi.EPOCH_CALLBACK(_on_epoch)` under the lock, then
  `ffi.watch_epochs(store, callback)`. The `_bindings` import goes.
- `_output_write` and `_output_free` keep their plain `@ctypes.CFUNCTYPE(...)` declarations.
  A decorator runs at module import, and decorating them with the adapter's types would import
  the adapter, and so wasmtime-py, at package import, which Decision 2 forbids. **U5 holds the
  two declarations equal by identity** to `OUTPUT_WRITE` and `OUTPUT_FREE` (ctypes caches a
  `CFUNCTYPE` by its signature), as the row does today. The adapter's two names exist for that
  row, and for spec 104, which may move the output table into a module that makes the two
  callbacks on first use and then takes the types from the adapter. `_send_outputs` calls
  `ffi.set_custom_outputs(wasi, _output_write, _output_free, keys[0], keys[1])`.
- `_set_async_stack` and `_wasmtime_version` are deleted; `_engine` calls
  `ffi.set_async_stack(cfg, _WASM_STACK)`.
- `_wasmtime_base`: `_handlers["wasmtime"] = _load_base(ffi.engine_symbol_address())`.
- `_wasmtime()`: as Decision 2 says.

### The mounts' side

- `bind`: `_Forwards({name: ffi.raw_func(exports[name]) ...}, {name: ffi.raw_func(stat[name])
  ...}, stat["memory"])`; `_Forwards.slots` holds `PreparedCall` objects.
- `forward`: builds `ffi.PreparedCall(func, SIGNATURES[name])` on a miss; then the bracket of
  Decision 4 with `ffi.get_fuel(caller)` and `ffi.set_fuel(caller, …)` around
  `slot.call(context, args)`, where `context = ffi.context_of(caller)` is kept for `slot.call`
  only (the confirmation's M9).
- `__call__`'s ABI branch: `self.stop_fuel = (e, ffi.get_fuel(caller))`.
- `_get_fuel` and `_set_fuel` are deleted.

### The harness's side

`tests/harness/guest.py`'s `engine()`: `from wasi_python import _wasmtime_ffi` inside the
function, then `_wasmtime_ffi.set_async_stack(cfg, WASM_STACK)` in place of the two `_ffi`
lines. Its docstring keeps its reason.

### The judge's side

`scan.private_engine_hits`, the rules check, the unit file, the five touched unit files and
`test_calls_add_nothing_to_wasmtime_pys_tables` (its two private reads through the adapter), as
Decisions 3 and 5 say. Two of the five reach names this specification deletes (the pre-build
review's M1): the `shared` fixture of `tests/unit/test_runner_cancel.py` (`:49`) patches
`_wasmtime_ffi.context_address` in place of `runner._context_address`, and
`test_the_async_stack_size_property_is_preferred` (`tests/unit/test_runner_calls.py:312`) calls
`_wasmtime_ffi.set_async_stack` and patches `_wasmtime_ffi.ASYNC_STACK_SETTER` in place of
`runner._set_async_stack` and `_ffi`'s binding (U7). The claim list is `build/103/claims.toml`,
copied into *For the lane*.

### The debt is documented (the owner, 2026-10-20; added after the pre-build review's draft)

**The debt** is the set of private bindings the runner still needs: each is a thing wasmtime-py
could make public, and until it does, a thing a release can move. The debt is written down in
one facts sheet, held in step with the code by a rules check, and paid down by the procedure of
Decision 6, step 6.

- **The sheet** is `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md` (34 is
  the next free number; the folder's shape follows
  `21-wasmtime-py-async-stack-size/facts.md`: Project, Against, Status, Title, Files, Why we need
  it, the "facts sheet, not an issue" paragraph, then numbered facts labelled EXECUTED or READ).
  Its heart is one table, "The bindings", with **one row per entry of `NEEDED` and `OPTIONAL`**
  (thirty-one rows: sixteen `_ffi` names, two `_bindings` records, two `_func` names, one
  `_wasi` name, nine class attributes, and the optional async-stack setter): the binding as a dotted name
  in backticks, the C API function it is, what the runner does with it, the public wasmtime-py
  API that would replace it, whether 49.0.0 has it, and the existing sheet it overlaps (21 for
  the async stack size, 1 for the exception slot). Below the table, a "Landed" list holds the
  rows struck when a release made them public. `context/upstream/README.md`'s table gains the
  matching row, appended after row 29.
- **(a) The adapter's module docstring** carries the same list in short form, one line per
  operation, `private binding → public name wanted`, so the one place to look (Decision 6) says
  what is owed without the sheet open.
- **(b) A rules check**, `tests/checks/test_rules.py::test_the_private_api_debt_is_documented`,
  over `scan.private_api_debt_errors(adapter, sheet) -> list[str]`: it reads the adapter's
  source with `ast` (no wasmtime-py import, as every other rules check is static), takes
  `NEEDED` and `OPTIONAL` as tuple literals (`ast.literal_eval`), forms each dotted name as
  `holder + "." + name`, reads every row of the sheet's "The bindings" table (a line starting
  with `` | ` `` under that heading, its first cell's backticked text; the `(optional)` tag of the
  optional row sits outside the backticks and is not compared; the confirmation's L10), and
  reports: every dotted name with no row;
  every row whose first cell is no dotted name of the two tuples; and every dotted name the
  module docstring (`ast.get_docstring`) does not contain. So the sheet cannot drift from the
  code in either direction, and a binding removed from `NEEDED` because a public name landed is
  struck from the table in the same change (moved to "Landed"), or the check is red. Its unit
  row is U17's second half.
- **(c) When a release makes an operation public**, the change is Decision 6, step 6: switch
  the preference order (already public first, so often nothing), drop the private name from
  `NEEDED` or `OPTIONAL`, strike the row, and widen the pin if the release is a new major.

### `ruff`

`from wasmtime import _bindings, _ffi, _func, _wasi` and the `noqa: F401` on `_wasmtime()`'s
import are the only lint-sensitive lines; `ruff check` and `ruff format --check` stay green on
`src/` and `tests/`.

## Scope

In: Decisions 1 to 8, and the facts sheet of Design, "The debt is documented", with its rules
check and its README row. Out:

- **Threading the call's `Store` object into the host functions** so fuel and the deadline take
  the public path on 49.0.0 (Decision 8 says why not); the adapter takes it the day `Caller` has
  the methods.
- **Asking wasmtime-py for anything**: the sheet is a facts sheet, not an issue (question 80;
  the Bytecode Alliance's policy on agents); whether to ask, and the words, are the owner's.

- **Splitting `runner.py`** (spec 104), **the process-state owner** (105), **typed call state and
  the type checker** (106), **`mounts.py` behind a protocol and the platform module** (107).
- **Any change to a public name**, a default, a limit, an errno, a fuel count or an artifact
  byte: none; Decision 4 holds it.
- **Replacing wasmtime-py's exception slot** or any other mechanism with a public one: the
  adapter names what is used, it does not change what is used.
- **A wasmtime-py 50 bump**: Decision 6 says how; it is its own specification when 50 is out.
- **Extending the rule to `scripts/` or `release/`**: nothing there imports wasmtime-py
  (EXECUTED, the same regex over `scripts/` and `release/`: 0 hits).

## Acceptance criteria

Fourteen, each checkable:

1. **The adapter exists** at `src/wasi_python/_wasmtime_ffi.py` and exposes exactly the names of
   Decision 1's table (U1's second assertion lists `__all__` against the table's names), each
   parameter and return annotated.
2. **The import check**: U1, U2 and U3 pass; `uv run python -c "import wasi_python._wasmtime_ffi"`
   prints nothing on wasmtime-py 49.0.0.
3. **The rules check** `tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_
   private_api` is **seen failing first** on `a9064a2` with 31 hits (25 in `src/`, 6 in
   `tests/`; the output kept as `build/103/rule-before.txt`) and passes on the built commit,
   `tests/harness/scan.py` and `tests/unit/test_scan.py` included (Decision 3, the split
   literals; U17 holds it).
4. **No line of `src/` or `tests/`** outside the two exempt files matches the regex of
   Decision 3 (criterion 3's pass is the evidence).
5. **Sameness on the frozen set**: `sameness.py --claims build/103/claims.toml` between the base
   record and the built record prints nothing and exits 0 (Decision 4); both records are kept
   under `build/103/` and their check counts named in the landing notes.
6. **No fuel row moves** and **no bytes row moves**: a consequence of 5, stated so the lane reads
   it; the landing notes say "0 fuel rows, 0 bytes rows".
7. **No pass is lost**: the built record's `suite` passes are the base's plus the new check and
   the unit rows; the landing notes give both counts.
8. **Fuel neutrality held**: `tests/unit/test_runner_mounts.py::test_the_rename_rule_forward_is_
   fuel_neutral` passes on the built commit, unchanged.
9. **The eighteen unit rows** of Decision 5 pass, in `tests/unit/test_wasmtime_ffi.py` (U1 to
   U16, U18) and `tests/unit/test_scan.py` (U17); the three moved rows are gone from their old
   files (`uv run pytest --collect-only -q` names no `test_the_bindings_the_runner_calls_exist`
   outside the new file); the two re-pointed files (`test_runner_cancel.py`,
   `test_runner_calls.py`) keep every row they have.
10. **The package imports without wasmtime-py** (`test_package_imports_without_wasmtime`) and
    without the adapter (U10).
11. **`ruff check` and `ruff format --check`** are green on `src/` and `tests/`; `test_no_module_
    level_name_is_bound_twice` stays green (the adapter binds each name once).
12. **`tests/public_api.txt` is unchanged**: `git diff --stat` of the branch against its base
    names no line of it, and the API snapshot check stays green.
13. **The debt is documented** (Design): the sheet
    `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md` exists with its
    thirty-one rows and its README row; `tests/checks/test_rules.py::test_the_private_api_debt_is_
    documented` is **seen failing first** on `a9064a2` (no adapter file: one error naming it) and
    passes on the built commit; the adapter's docstring names every entry of `NEEDED` and
    `OPTIONAL` (the same check).
14. **Public first** (Decision 8): U18 passes; `set_async_stack` and the three fuel and deadline
    operations take the public path when the object has it, and the six `Caller` sites keep
    their private path on 49.0.0 (criterion 5's sameness is the evidence that nothing moved).

## For the lane

- **Kind:** parallel-safe, a judge change; the first entry of the stacked chain 103 → 108, which
  lands as one wave of six (the owner, 2026-10-20, the memo's section 8). Its branch is
  `spec/103-the-engine-seam`, from main's tip; 104 is built on its reviewed tip. It shares
  `CHANGELOG.md` with every entry (textual merges), `src/wasi_python/runner.py` and `mounts.py`
  with 104 to 107 (stacked, so no conflict: each is built on the one before), and
  `tests/checks/test_rules.py` with any judge change that adds a rule.
- **The dispatch:** one release-workflow run on the chain's final tip stands for the six
  (the owner, the memo's section 8); this entry's own evidence is the fast tier on the frozen set
  and the sameness line of Decision 4.
- **The claim list** (`build/103/claims.toml`, as the build ran it: the two new rules-check
  nodes, the new unit file, and the unit suite's net growth of 17):

  ```toml
  [[claim]]
  spec = "103"
  new = [
    "tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api",
    "tests/checks/test_rules.py::test_the_private_api_debt_is_documented",
    "tests/unit/test_wasmtime_ffi.py",
  ]
  units = 17
  ```

  103: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none.
  **The judge hash changes** in `tests/harness/scan.py`, `tests/harness/guest.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_4_embedding.py`,
  `tests/unit/test_wasmtime_ffi.py`, `tests/unit/test_scan.py`, `tests/unit/test_runner_calls.py`,
  `tests/unit/test_runner_cancel.py`, `tests/unit/test_runner_async.py` and
  `tests/unit/test_runner_mounts.py`.
- **The flags** (paste-safe; no `--accept-growth` is expected, and one would be a finding):

  ```
  --accept "103: one module, src/wasi_python/_wasmtime_ffi.py, touches wasmtime-py's private API, public first where a release has the public form; the runner and the mounts drive the engine through its named operations; a moved symbol is one ImportError at the first run(), naming the wasmtime-py version and the names; the private bindings still needed are listed in context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md; no behaviour change, the frozen set's verdicts the same"
  --accept-judge "103: a rules check that no .py under src/ or tests/ but the seam and its unit file imports wasmtime._ffi, _bindings, _func or _wasi or touches ._context(), ._func, _from_ptr or .ptr(); a rules check that every entry of the adapter's NEEDED and OPTIONAL tuples is a row of the debt sheet's table, every row an entry, and every entry named in the adapter's docstring; the adapter's unit file (seventeen rows) and the scan's two rows; two rows moved to it; two files re-pointed to the adapter's names; one embedding check counts wasmtime-py's tables through the seam; the harness driver sets the async stack size through the seam; no existing expectation edited"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch covers it on three systems.

## One line

Twenty-five lines in two modules reach into wasmtime-py's private API today; after this, one
named, typed, import-checked module does, a rule keeps it so, and a moved symbol is one error at
the first `run()` instead of an `AttributeError` inside a call.

## Landing notes

Built 2026-10-20 in the worktree `/home/user/wt/103`, branch `spec/103-the-engine-seam`, from
the base `3626bb6` (branch `claude/gallant-ride-9nxxmn`: main `5feb7e9`, the memo `a9064a2`, the
chain's specifications and their pre-build reviews). Every number here is EXECUTED on that base
or on the built commit, with its command; the outputs are kept under `build/103/` in the
worktree (git-ignored): `seen-failing.txt`, `rule-before.txt`, `fast.log`, `built.json`,
`claims.toml`, `sameness.txt`.

- **Rebase onto main** (the coordinator, 2026-10-21): the chain was rebased onto main's
  `dda6075` (wave 08 landed), linear, every commit replayed. Two conflicts fell in this entry's
  commits, both append-style, both sides kept: `context/upstream/README.md` at `755e102` and
  `d77425d` (main's rows 30, 32 and 33 beside this entry's row) and `tests/harness/scan.py` at
  `e517a1a` (main's `npy_fenv_*` block of spec 099 and this entry's private-API rule, both
  appended at the end; main's first). Main took sheet number 30 (numpy's floating-point status)
  and spec 100's branch holds 31, so this entry's sheet is
  `context/upstream/34-wasmtime-py-public-api-for-the-runner/` and its README row is 34: the
  folder moved by `git mv` in `755e102`'s replay, its text unchanged, and the path and "row 30"
  in this file (eight lines) and in `tests/checks/test_rules.py` (one line) follow, amended into
  the commits that wrote them (`e319829`'s replay met those lines once more and took its own
  text, renumbered); the memo, the reviews and 107's notes keep the path they read. Hashes:
  `755e102` → `50d61ed`, `e517a1a` → `8a36a1c`, `d77425d` → `a92c0d4`, `c15adf4` → `5bba86b`,
  `e319829` → `287b1f8`; before them the memo `a9064a2` → `e087213`, the drafts `c9515ef` →
  `73d3e85`, `a4f31c8` → `67c5c74`, `5c35061` → `340a495`, `46fa9fc` → `1995a7d`, `e364b99` →
  `e867874`, and the pre-build reviews `3626bb6` → `c3391ca`, `b0ce5e7` → `4fae0bf`, `244975f`
  → `e8cafb5`, `9a3f8e6` → `4db7837`, `05b3329` → `9d7f749`, `2cffdcf` → `3675106`.
- **Commits:** `e517a1a` (the seam `src/wasi_python/_wasmtime_ffi.py`, its checks, the runner
  and the mounts behind it, the harness driver and the five test files), `d77425d` (the debt
  sheet's row for `wasmtime_error_t` and the README row's count), and the commit that carries
  this Status line and these notes.
- **The checks were written first and seen failing on `3626bb6`** (`build/103/seen-failing.txt`,
  EXECUTED): `tests/unit/test_wasmtime_ffi.py` fails at collection (`ImportError: cannot import
  name '_wasmtime_ffi' from 'wasi_python'`);
  `test_only_the_engine_seam_touches_wasmtimes_private_api` reports 31 findings, digest
  `3f64ef046fdb` (`build/103/rule-before.txt`: `runner.py` 14, `mounts.py` 11, `tests/` 6, the
  lines of The problem); `test_the_private_api_debt_is_documented` reports one finding,
  `_wasmtime_ffi.py does not exist`. On the built commit all three pass (criteria 3, 4 and 13).
- **EXECUTED numbers re-measured on `3626bb6`**, each agreeing with the draft: 31 hits of
  Decision 3's regex over `src/` and `tests/` (25 in `src/`: `runner.py` 14, `mounts.py` 11; 6
  in `tests/`); 0 under `scripts/` and `release/`; 0 in `tests/harness/constructors.py`; the
  thirteen `_ffi` names of The problem (`re.findall(r"_ffi\.([A-Za-z_0-9]+)")` over the base
  `runner.py` and `mounts.py`); `git grep LAST_EXCEPTION 3626bb6 -- src/wasi_python` empty;
  `wasmtime.Func.__annotations__ == {"_func": wasmtime._bindings.wasmtime_func}` and
  `hasattr(wasmtime.Func, "_func")` is `False`; `Config.async_stack_size` is not a property
  (wasmtime-py 49.0.0).
- **One difference from the specification, the sheet fixed and not the check:** `NEEDED` holds a
  sixteenth `_ffi` name, `wasmtime_error_t`, so `NEEDED` has 30 entries, `OPTIONAL` 1, and the
  sheet's table 31 rows (`context/upstream/README.md`'s row 34 says thirty-one; the draft's
  Decision 2, Design and criterion 13 said fifteen and thirty, and now say sixteen and
  thirty-one, the build review's finding 2). `delete_error(address)` must cast the address to
  `ctypes.POINTER(_ffi.wasmtime_error_t)`: EXECUTED,
  `_ffi.wasmtime_error_delete(ctypes.c_void_p(address))` raises `ctypes.ArgumentError: argument
  1: TypeError: expected LP_wasmtime_error instance instead of c_void_p`, and no entry of
  `NEEDED` gives that pointer type otherwise. Decision 2's reason for `wasmtime_context_t` ("the
  alias is a private name too") covers it; the sheet's new row says the same.
- **Choices the build made inside the Decisions:** `set_async_stack` reads the property from
  `type(cfg)` at call time, as spec 078's `_set_async_stack` did, not from a module constant at
  import: U7 and U18 give stand-in `Config` classes, which a constant read from
  `wasmtime.Config` could not see; the real `Config` is covered by the same read. The three fuel
  and deadline operations look the public method up per call (`getattr(storelike, name, None)`),
  so a `Store` takes the method and a `Caller` the binding on its context, and a release that
  gives `Caller` the methods is taken with no change here (Decision 8). U3 also removes the
  package attribute `wasi_python._wasmtime_ffi` for its first half: `from . import name` returns
  an existing attribute without importing, so without that the adapter's import check would not
  run again; `monkeypatch.undo()` restores both before the second half. `__all__` has the 28
  names of Decision 1's table (23 operations and constants, `Storelike`, `NEEDED`, `OPTIONAL`,
  `missing`, `check`); U1 lists it. `forward` asserts the caught exception is set before it
  raises it, for spec 106's type checker.
- **U9 and wasmtime-py's slab:** `host_function_count()` is the length of `FUNCTIONS.list`, the
  table's high-water mark; wasmtime-py's `Slab` reuses a freed slot before growing (READ,
  `_slab.py`: `allocate` pops the free chain first). The first parallel run showed it (the row
  was the 84th failure in that worker, after rows that freed host functions), so the row
  defines functions until the count grows by exactly one, bounded by the mark, and asserts it
  never shrinks; the kept run below is after that fix. The embedding check's assertion ("a call
  defines no host function") is unchanged by it: it compares equal counts.
- **Rows moved and re-pointed** (criterion 9; `uv run pytest --collect-only -q`, EXECUTED):
  `test_the_bindings_the_runner_calls_exist` (from `test_runner_calls.py`) and
  `test_the_stop_error_is_real_and_never_leaves_a_zero_delta` (from `test_runner_async.py`)
  are collected once each, in `tests/unit/test_wasmtime_ffi.py` only; the assertion at
  `test_runner_calls.py:116` reads `_wasmtime_ffi.last_exception()` (its row kept);
  `_record_async_stack`, `test_the_async_stack_size_property_is_preferred` and
  `test_no_engine_is_made_without_the_async_stack_size` patch `_wasmtime_ffi.ASYNC_STACK_SETTER`
  and call `_wasmtime_ffi.set_async_stack`; `test_runner_cancel.py`'s `shared` fixture patches
  `_wasmtime_ffi.context_address`; `test_runner_mounts.py:260` reads `str(call.stopped)`;
  `test_calls_add_nothing_to_wasmtime_pys_tables` counts through `host_function_count()` and
  patches `allocate` on `custom_output_table()`, every assertion kept. So the unit file has
  seventeen rows (U1 to U16, U18), `test_scan.py` two (U17's two halves), two rows left their
  files: the unit suite grows by 17.
- **The fast tier** (EXECUTED, `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` on
  `d77425d` with `WASI_PYTHON_ARTIFACTS` the verified `v0.1.0a7` set; `build/103/fast.log`):
  **83 failed, 2363 passed, 52 skipped** in 308 s; the 83 are exactly the baseline's
  (`build/baseline-a7/failing-nodes.txt`, a `diff` of the sorted node ids is empty: 82 checks
  against an artifact set older than the tree and `test_the_walk_judges_links`, which needs a
  non-root user). The baseline record (`build/baseline-a7/baseline.json`, `a9064a2`, the same
  set): 83 failed, 2344 passed, 52 skipped; unit suite 1847 (1833 passed, 13 skipped). The built
  record (`build/103/built.json`): unit suite 1864 (1850 passed, 13 skipped): 17 more, the same
  one failing. No pass lost (criterion 7); `tests/unit/test_runner_mounts.py::
  test_the_rename_rule_forward_is_fuel_neutral` passes unchanged (criterion 8).
- **Sameness** (criterion 5; EXECUTED, `uv run python tests/harness/sameness.py
  /home/user/wasi_python/build/baseline-a7/baseline.json build/103/built.json --claims
  build/103/claims.toml`), the output verbatim, exit 0:

  ```
  note: explained by claims: 103 4
  ```

  **0 fuel rows, 0 bytes rows** (criterion 6); no verdict moved. The first run's one unexplained
  line, `collected_files: tests/unit/test_wasmtime_ffi.py only in the second record`, is the new
  unit file itself: the claim list names it under `new` (the draft's list had the two
  rules-check nodes and the count only).
- **The claim list** (`build/103/claims.toml`, as run):

  ```toml
  [[claim]]
  spec = "103"
  new = [
    "tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api",
    "tests/checks/test_rules.py::test_the_private_api_debt_is_documented",
    "tests/unit/test_wasmtime_ffi.py",
  ]
  units = 17
  ```

- **The flags for the lane** (paste-safe; no `--accept-growth`):

  ```
  --accept "103: one module, src/wasi_python/_wasmtime_ffi.py, touches wasmtime-py's private API, public first where a release has the public form; the runner and the mounts drive the engine through its named operations; a moved symbol is one ImportError at the first run(), naming the wasmtime-py version and the names; the private bindings still needed are listed in context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md; no behaviour change, the frozen set's verdicts the same"
  --accept-judge "103: a rules check that no .py under src/ or tests/ but the seam and its unit file imports wasmtime._ffi, _bindings, _func or _wasi or touches ._context(), ._func, _from_ptr or .ptr(); a rules check that every entry of the adapter's NEEDED and OPTIONAL tuples is a row of the debt sheet's table, every row an entry, and every entry named in the adapter's docstring; the adapter's unit file (seventeen rows) and the scan's two rows; two rows moved to it; two files re-pointed to the adapter's names; one embedding check counts wasmtime-py's tables through the seam; the harness driver sets the async stack size through the seam; no existing expectation edited"
  ```

- **Other criteria:** `uv run python -c "import wasi_python._wasmtime_ffi"` prints nothing,
  exit 0 (criterion 2); `ruff check` and `ruff format --check` are green on `src/` and `tests/`,
  and `test_no_module_level_name_is_bound_twice` passes (criterion 11); `git diff --stat
  3626bb6 -- tests/public_api.txt` is empty (criterion 12); `test_package_imports_without_
  wasmtime` and U10 pass (criterion 10); U18 passes (criterion 14).
- **CI:** none of its own; the chain's one dispatch on the final tip (the memo's section 8).
- **CHANGELOG and roadmap:** not touched by the build. `CHANGELOG.md` is shared by every entry
  of the wave, so the lane's integration commit carries this specification's line under the one
  unreleased section (the build review's finding 1, answered in writing: the branch edits no
  line of it). The line is written here for the integrator to paste.
- **CHANGELOG line (for the integrator)**, one bullet under "0.1.0a8 — unreleased":
  "**One module touches wasmtime-py's private API** (spec 103).
  `src/wasi_python/_wasmtime_ffi.py` is the engine seam: the runner and the mounts drive the
  engine through its named operations, it prefers wasmtime-py's public API wherever the installed
  release has it, and at the first `run()` it raises one `ImportError` naming the wasmtime-py
  version and every private name that moved. A rules check holds that no other `.py` under
  `src/` or `tests/` reaches the private API; a second holds the debt sheet
  `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md` equal to the names the
  seam needs. No behaviour, fuel or errno changes."
- **The build review:** `../reviews/103-the-engine-seam-2026-10-20.md` (lands; two Lows, both
  answered in its Disposition: the CHANGELOG line above, and the body's counts brought to the
  built ones in the Kind line, Decision 2, the Design, criterion 13 and "For the lane").
- **The builder's self-check** (`../reviews/README.md`):
  - rebased onto the named base today, the base commit in the Status line: checked (`3626bb6`,
    the chain's base; 103 is its first link, so nothing to rebase onto).
  - CI run dispatched on this exact commit and read: not checked, by the chain's rule: one
    dispatch on the final tip stands for the six.
  - every number from a measured run on this base, labelled EXECUTED; the growth list this
    build's: checked (no growth).
  - "For the lane": the claim list, the exact flags, each reason beginning with the spec
    number, the wave kind (parallel-safe, a judge change), dry-run needs (none of its own):
    checked, above.
  - every new check seen failing first: checked. A Windows and a Linux branch named or
    excluded: excluded with a reason: the change has no platform branch (the seam reads one
    symbol's address; `dladdr` and the signal reads stay in the runner).
  - every gap names its closer; every reserved follow-up has a roadmap line: checked (no gap
    added, no follow-up reserved).
  - `packages.toml` has its reason line: not applicable (no package). README rows the spec
    changes listed: checked (`context/upstream/README.md`, row 34's count).
  - CHANGELOG under the one unreleased section: not written on this branch, in writing: the
    file is shared by the wave's six entries, so the lane's integration commit carries the line,
    whose exact text is above under "CHANGELOG line (for the integrator)"; questions numbered:
    none asked.
  - `ruff check`, `ruff format --check`, the fast tier: green but the baseline's 83, output in
    `build/103/`: checked.
