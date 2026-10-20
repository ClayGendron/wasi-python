# 102 — The engine seam: one module touches wasmtime-py's private API

- **Status:** **drafted 2026-10-20** on branch `claude/gallant-ride-9nxxmn` from main `5feb7e9`
  (the memo's commit `a9064a2` on top), awaiting its pre-build review: it changes the runner's
  code, so AGENTS rule 8 asks for one. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, not build-class (§5.7): it touches no file under `scripts/`,
  `recipes/`, `downloads/` or the release workflow, and no artifact byte. **It changes no line of
  `tests/public_api.txt`.** It is **the first of the stacked chain 102 → 103 → 104 → 105 → 106 →
  107** (the memo, section 8): 103 is built on this specification's reviewed tip, and the chain
  lands as one wave. It is **also a judge change** (a new rules check, a new unit file, three unit
  rows moved, the harness driver's engine made through the seam): the lane accepts it with
  `--accept-judge`. Files: `src/wasi_python/_wasmtime_ffi.py` (new), `src/wasi_python/runner.py`,
  `src/wasi_python/mounts.py`, `tests/harness/scan.py`, `tests/harness/guest.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_4_embedding.py` (one check's two private
  reads), `tests/unit/test_wasmtime_ffi.py` (new), `tests/unit/test_runner_calls.py`,
  `tests/unit/test_runner_async.py`, `tests/unit/test_runner_mounts.py`,
  `tests/unit/test_scan.py`, `CHANGELOG.md`, this specification.
- **Depends on:** landed specifications only: 011 (the shared host functions, which never raise
  into wasmtime-py), 015 (the epoch callback and its stop error), 028 (Decision 3: `run` needs
  wasmtime-py, importing the package does not), 032 (the forwarder), 048 (the guard trampoline
  and fuel-neutral forwards), 071 (Decision 9: the trap-handler check reads wasmtime's load base),
  078 (Decision 1: the async stack size, set before any engine), 092 (`sameness.py` and claim
  lists). **103 depends on this specification**: it splits `runner.py` into a package and keeps
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
`uv run python -I build/102/hits.py`, the regex of Decision 3 over every `.py` under `src/` and
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
and the fix touches two modules in 25 places with no one place to look. Spec 103 will cut
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
functions and one class. Nothing in it is reset at fork or released at exit (spec 104 relies on
this).

| name | signature | replaces today |
|---|---|---|
| `PIN` | `"wasmtime>=49,<50"` | the literal in `_wasmtime()`'s message |
| `version()` | `-> str` | `_wasmtime_version()` (removed) |
| `Context` | `ctypes.POINTER(_ffi.wasmtime_context_t)`, a type alias | the raw pointer type in four signatures |
| `context_of(storelike)` | `-> Context` | `caller._context()` (four sites), `storelike._context()` |
| `context_address(storelike)` | `-> int` | `_context_address` (removed; its two callers use this) |
| `set_epoch_deadline(context, ticks)` | `-> None` | `_ffi.wasmtime_context_set_epoch_deadline` in `_Call.stop` and `_epoch_now` |
| `get_fuel(context)` | `-> int`; raises `WasmtimeError` | `mounts._get_fuel` (removed) |
| `set_fuel(context, fuel)` | `-> None`; never raises | `mounts._set_fuel` (removed) |
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
| `PreparedCall(func, kinds)` | `kinds` a tuple of `"i32"` and `"i64"`; builds the argument array with its kinds set and a one-slot result array, once | the `slot` tuple `forward` builds and caches |
| `PreparedCall.call(context, args)` | `-> int`, the `i32` result; raises `Trap` or `WasmtimeError` | `_ffi.wasmtime_func_call`, `wasm_trap_t`, `Trap._from_ptr`, `WasmtimeError._from_ptr` |
| `last_exception()` | `-> BaseException \| None` | `_func.LAST_EXCEPTION` in one unit row (no `src/` line reads it; EXECUTED, `grep -n LAST_EXCEPTION src/wasi_python/*.py` is empty) |
| `host_function_count()` | `-> int` | `len(_func.FUNCTIONS.list)` in `test_calls_add_nothing_to_wasmtime_pys_tables` |
| `custom_output_table()` | `-> Any`, wasmtime-py's own table of custom outputs, which the runner never uses (spec 011) | `_wasi.CUSTOM_OUTPUTS` in the same check, which counts its `allocate` calls |

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
  platform code (spec 071) and move to `_platform.py` in spec 106. The adapter gives only the
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
the optional `wasmtime_config_async_stack_size_set`: the thirteen `_ffi` names; `_bindings`'
`_wasmtime_store_epoch_deadline_callback` and `_wasi_config_set_stdout_custom` (each with an
`argtypes` of length 4, since `EPOCH_CALLBACK`, `OUTPUT_WRITE` and `OUTPUT_FREE` are read from
them); `_func.LAST_EXCEPTION`; `_func.FUNCTIONS`; `_wasi.CUSTOM_OUTPUTS`; `Trap._from_ptr`;
`WasmtimeError._from_ptr`; `Caller._context`; `Store._context`; `Store.ptr`; `Config.ptr`;
`WasiConfig.ptr`; `dll.wasm_engine_new`; and `Func._func`, which is an instance attribute, read
as a class annotation (EXECUTED, `wasmtime.Func.__annotations__ == {"_func":
wasmtime._bindings.wasmtime_func}`; a class-level `hasattr` is `False`).

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

**The acceptance criterion** is the memo's, section 8: `tests/harness/sameness.py` between two
fast-tier records on the **frozen baseline set**, the `v0.1.0a7` release's artifact set verified
against its `SHA256SUMS`, pointed at by `WASI_PYTHON_ARTIFACTS`. **A record** is the
`build/progress/latest.json` the judge writes. The builder runs `uv run pytest -m "not slow" -n 3`
(a slot the lane grants) on the base commit and copies the record to `build/102/baseline.json`,
then on the built commit to `build/102/built.json`, and runs

```
uv run python tests/harness/sameness.py --claims build/102/claims.toml build/102/baseline.json build/102/built.json
```

which must print nothing and exit 0. `build/102/claims.toml` is the claim list of *For the
lane*: the one new check and the unit count. No fuel row moves (host code spends no guest
fuel), no bytes row moves (no artifact changes), no pass is lost. Host-side counts the checks
record as facts (file calls, tool frames) are compared by `sameness.py` too and must not move.

### 5. Unit checks for the adapter: seventeen rows

`tests/unit/test_wasmtime_ffi.py` is new; it is the one test file that may import `wasmtime._ffi`
(Decision 3). Rows U1 to U10 need no wasm module. Rows U11 to U16 drive wasmtime-py directly with
a WAT module, as `test_runner_calls.py` does today, and need no `python.wasm`: nothing here needs
the frozen set, and the fast tier runs every row. What *does* need the guest, the end-to-end
forward with its errno and fuel, is already held by the checks under `tests/checks/` and by
Decision 4's sameness.

- **U1** `missing()` names each absent name of a stand-in holder table, in `NEEDED`'s order, and
  names nothing when every name is present (a table built from the real wasmtime-py).
- **U2** `check()` on a table missing two names raises one `ImportError` whose text has
  `version()`, both dotted names and `PIN`.
- **U3** `_wasmtime()` lets the adapter's error through: with `wasmtime_error_new` removed from
  `_ffi` and the adapter dropped from `sys.modules` (both by `monkeypatch`, restored after),
  `runner._wasmtime()` raises `ImportError` matching `wasmtime-py 49\.0\.0 .*wasmtime_error_new`;
  and with `sys.modules["wasmtime"] = None`, it raises the "needs wasmtime-py" error with the
  cause chained, as today.
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
  `test_no_engine_is_made_without_the_async_stack_size` and
  `test_the_guest_driver_makes_the_runners_engine` stay in `test_runner_calls.py`, patching
  `_wasmtime_ffi.ASYNC_STACK_SETTER` in place of `_ffi`.
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
- **U14** `set_epoch_deadline(context_of(store), 0)` on a store with no callback: the next call
  into the guest raises `Trap`.
- **U15** inside a host function, `context_address(caller)` equals `context_address(store)`.
- **U16** `set_custom_outputs` on a `WasiConfig`, with `OUTPUT_WRITE` and `OUTPUT_FREE`
  callbacks the row defines: a WAT guest that `fd_write`s to 1 and to 2 reaches the write callback
  with the two keys and the bytes; dropping the store reaches the free callback once per key.
- **U17** `private_engine_hits` (Decision 3's unit row, in `test_scan.py`).

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

### 7. What the chain honours

- **The path is fixed.** The adapter is `src/wasi_python/_wasmtime_ffi.py`, a sibling of
  `runner.py`. Spec 103 turns `runner.py` into a package of modules and leaves the adapter where
  it is; the rule's exemption names the exact path.
- **The adapter holds no state.** Spec 104's one owner of process state has nothing to take from
  it; the one `_epoch_callback` object and the output table stay in the runner's modules
  (`_engine.py` and `_call.py` after 103).
- **Tests patch the adapter's names**, never `wasmtime._ffi`: `new_error`, `ASYNC_STACK_SETTER`,
  `watch_epochs`. The rule holds it.
- **Prose in `src/` outside the adapter does not spell the private names** (Decision 3). A
  docstring says "through the seam".
- **`_wasmtime()` keeps the adapter import inside it** wherever 103 moves the function; it is the
  one place a moved symbol is first seen.
- **Spec 105's type checker** finds the adapter fully annotated; `Storelike` is defined here and
  spec 106's call-context protocol may name it.
- **Spec 106's `_platform.py`** takes `engine_symbol_address()` from the adapter and keeps
  `dladdr` to itself.

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
"""The engine seam (spec 102): the one module of wasi_python that touches wasmtime-py's private
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
def set_epoch_deadline(context: Context, ticks: int) -> None: ...
def get_fuel(context: Context) -> int: ...
def set_fuel(context: Context, fuel: int) -> None: ...
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
- `_Call.stop` and `_epoch_now`: `ffi.set_epoch_deadline(ffi.context_of(caller), 0)`.
- `_stop_error`: `address = ffi.new_error(b"stopped by wasi_python")`; `if address: return
  address`; the rest as today.
- `_watch`: `_epoch_callback = ffi.EPOCH_CALLBACK(_on_epoch)` under the lock, then
  `ffi.watch_epochs(store, callback)`. The `_bindings` import goes.
- `_output_write` and `_output_free` keep their plain `@ctypes.CFUNCTYPE(...)` declarations.
  A decorator runs at module import, and decorating them with the adapter's types would import
  the adapter, and so wasmtime-py, at package import, which Decision 2 forbids. **U5 holds the
  two declarations equal by identity** to `OUTPUT_WRITE` and `OUTPUT_FREE` (ctypes caches a
  `CFUNCTYPE` by its signature), as the row does today. The adapter's two names exist for that
  row, and for spec 103, which may move the output table into a module that makes the two
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
  Decision 4 around `slot.call(context, args)`, with `context = ffi.context_of(caller)`.
- `__call__`'s ABI branch: `self.stop_fuel = (e, ffi.get_fuel(ffi.context_of(caller)))`.
- `_get_fuel` and `_set_fuel` are deleted.

### The harness's side

`tests/harness/guest.py`'s `engine()`: `from wasi_python import _wasmtime_ffi` inside the
function, then `_wasmtime_ffi.set_async_stack(cfg, WASM_STACK)` in place of the two `_ffi`
lines. Its docstring keeps its reason.

### The judge's side

`scan.private_engine_hits`, the rules check, the unit file, the four touched unit files and
`test_calls_add_nothing_to_wasmtime_pys_tables` (its two private reads through the adapter), as
Decisions 3 and 5 say. The claim list is `build/102/claims.toml`, copied into *For the lane*.

### `ruff`

`from wasmtime import _bindings, _ffi, _func` and the `noqa: F401` on `_wasmtime()`'s import are
the only lint-sensitive lines; `ruff check` and `ruff format --check` stay green on `src/` and
`tests/`.

## Scope

In: Decisions 1 to 7. Out:

- **Splitting `runner.py`** (spec 103), **the process-state owner** (104), **typed call state and
  the type checker** (105), **`mounts.py` behind a protocol and the platform module** (106).
- **Any change to a public name**, a default, a limit, an errno, a fuel count or an artifact
  byte: none; Decision 4 holds it.
- **Replacing wasmtime-py's exception slot** or any other mechanism with a public one: the
  adapter names what is used, it does not change what is used.
- **A wasmtime-py 50 bump**: Decision 6 says how; it is its own specification when 50 is out.
- **Extending the rule to `scripts/` or `release/`**: nothing there imports wasmtime-py
  (EXECUTED, the same regex over `scripts/` and `release/`: 0 hits).

## Acceptance criteria

Twelve, each checkable:

1. **The adapter exists** at `src/wasi_python/_wasmtime_ffi.py` and exposes exactly the names of
   Decision 1's table (a unit row lists `__all__` against the table's names), each parameter and
   return annotated.
2. **The import check**: U1, U2 and U3 pass; `uv run python -c "import wasi_python._wasmtime_ffi"`
   prints nothing on wasmtime-py 49.0.0.
3. **The rules check** `tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_
   private_api` is **seen failing first** on `a9064a2` with 31 hits (25 in `src/`, 6 in
   `tests/`; the output kept as `build/102/rule-before.txt`) and passes on the built commit.
4. **No line of `src/` or `tests/`** outside the two exempt files matches the regex of
   Decision 3 (criterion 3's pass is the evidence).
5. **Sameness on the frozen set**: `sameness.py --claims build/102/claims.toml` between the base
   record and the built record prints nothing and exits 0 (Decision 4); both records are kept
   under `build/102/` and their check counts named in the landing notes.
6. **No fuel row moves** and **no bytes row moves**: a consequence of 5, stated so the lane reads
   it; the landing notes say "0 fuel rows, 0 bytes rows".
7. **No pass is lost**: the built record's `suite` passes are the base's plus the new check and
   the unit rows; the landing notes give both counts.
8. **Fuel neutrality held**: `tests/unit/test_runner_mounts.py::test_the_rename_rule_forward_is_
   fuel_neutral` passes on the built commit, unchanged.
9. **The seventeen unit rows** of Decision 5 pass, in `tests/unit/test_wasmtime_ffi.py` (U1 to
   U16) and `tests/unit/test_scan.py` (U17); the three moved rows are gone from their old files
   (`uv run pytest --collect-only -q` names no `test_the_bindings_the_runner_calls_exist` outside
   the new file).
10. **The package imports without wasmtime-py** (`test_package_imports_without_wasmtime`) and
    without the adapter (U10).
11. **`ruff check` and `ruff format --check`** are green on `src/` and `tests/`; `test_no_module_
    level_name_is_bound_twice` stays green (the adapter binds each name once).
12. **`tests/public_api.txt` is unchanged**: `git diff --stat` of the branch against its base
    names no line of it, and the API snapshot check stays green.

## For the lane

- **Kind:** parallel-safe, a judge change; the first entry of the stacked chain 102 → 107, which
  lands as one wave of six (the owner, 2026-10-20, the memo's section 8). Its branch is
  `spec/102-the-engine-seam`, from main's tip; 103 is built on its reviewed tip. It shares
  `CHANGELOG.md` with every entry (textual merges), `src/wasi_python/runner.py` and `mounts.py`
  with 103 to 106 (stacked, so no conflict: each is built on the one before), and
  `tests/checks/test_rules.py` with any judge change that adds a rule.
- **The dispatch:** one release-workflow run on the chain's final tip stands for the six
  (the owner, the memo's section 8); this entry's own evidence is the fast tier on the frozen set
  and the sameness line of Decision 4.
- **The claim list** (`build/102/claims.toml`; the node count filled in by the builder from the
  built record):

  ```toml
  [[claim]]
  spec = "102"
  new = ["tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api"]
  units = 17
  ```

  102: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none.
  **The judge hash changes** in `tests/harness/scan.py`, `tests/harness/guest.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_4_embedding.py`,
  `tests/unit/test_wasmtime_ffi.py`, `tests/unit/test_scan.py`, `tests/unit/test_runner_calls.py`,
  `tests/unit/test_runner_async.py` and `tests/unit/test_runner_mounts.py`.
- **The flags** (paste-safe; no `--accept-growth` is expected, and one would be a finding):

  ```
  --accept "102: one module, src/wasi_python/_wasmtime_ffi.py, touches wasmtime-py's private API; the runner and the mounts drive the engine through its named operations; a moved symbol is one ImportError at the first run(), naming the wasmtime-py version and the names; no behaviour change, the frozen set's verdicts the same"
  --accept-judge "102: a rules check that no .py under src/ or tests/ but the seam and its unit file imports wasmtime._ffi, _bindings, _func or _wasi or touches ._context(), ._func, _from_ptr or .ptr(); the adapter's unit file (sixteen rows) and the scan's row; three rows moved to it; one embedding check counts wasmtime-py's tables through the seam; the harness driver sets the async stack size through the seam; no existing expectation edited"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch covers it on three systems.

## One line

Twenty-five lines in two modules reach into wasmtime-py's private API today; after this, one
named, typed, import-checked module does, a rule keeps it so, and a moved symbol is one error at
the first `run()` instead of an `AttributeError` inside a call.

## Landing notes

Filled in when it lands.
