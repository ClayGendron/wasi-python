# Review of 102 — The engine seam: one module touches wasmtime-py's private API (pre-build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107); not the author
- **Reviewed:** the specification as drafted
  (`context/specifications/102-the-engine-seam.md` on `claude/gallant-ride-9nxxmn`, read
  untracked over `5c35061` and committed unchanged as `c9515ef` while this review was written:
  612 lines, every cited line at the same number; `src/` and `tests/` read at that commit, which
  carries no code change from `a9064a2`: `git diff --stat main...HEAD` names only files under
  `context/`)
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question" -q
  -p no:cacheprovider` → 3 passed, 41 deselected, exit 0 (EXECUTED: the draft has its header
  fields and sections and none of the three rejected words). The draft's regex of Decision 3,
  run as a scratch script over every `.py` under `src/` and `tests/` → 31 hits: `mounts.py` 11,
  `runner.py` 14, `tests/` 6, the same lines the draft lists; over `scripts/` and `release/` → 0
  (EXECUTED). wasmtime-py's private surface, read in the venv (EXECUTED, wasmtime 49.0.0):
  `Func.__annotations__ == {"_func": wasmtime._bindings.wasmtime_func}` and
  `hasattr(Func, "_func")` is `False`; `Config.async_stack_size` is not a property;
  `_ffi.wasmtime_config_async_stack_size_set` exists; every one of the draft's thirteen `_ffi`
  names, `wasmtime_error_delete`, `_func.LAST_EXCEPTION`, `_func.FUNCTIONS` (a `Slab` with
  `.list`), `_wasi.CUSTOM_OUTPUTS` (a `Slab` with `.allocate`), `Trap._from_ptr`,
  `WasmtimeError._from_ptr`, `Caller._context`, `Store._context`, `Store.ptr`, `Config.ptr`,
  `WasiConfig.ptr` and `_ffi.dll.wasm_engine_new` exist; `_bindings._wasmtime_store_epoch_
  deadline_callback.argtypes` and `_bindings._wasi_config_set_stdout_custom.argtypes` have
  length 4; `argtypes[1]._restype_` of the epoch callback is `c_ulong`, which is `c_size_t` on
  this platform; `ctypes.CFUNCTYPE(None, c_void_p) is argtypes[3]` of the stdout binding
  (the identity U5 relies on); `_ffi.wasmtime_error_new is _bindings.wasmtime_error_new` (the
  re-export). The regex against its own source: the line `r"|\._func\b"` is a hit (EXECUTED;
  the other five alternation lines are not). Time box: 25 minutes, parallel-safe.

## Acceptance criteria against evidence
1. The adapter exists with exactly the table's names — checkable; not yet met (pre-build). The
   row that lists `__all__` is not one of Decision 5's seventeen, and the table lacks four names
   the draft itself defines (L3). READ.
2. The import check, U1 to U3; the import prints nothing on 49.0.0 — checkable; not yet met. Every
   name `NEEDED` would carry exists today (EXECUTED, above), so the import would print nothing;
   `wasmtime_error_delete` is used but not in `NEEDED` (L2); the holder table reads `_ffi.dll`
   before `check` runs (L4). READ.
3. The rules check seen failing first with 31 hits, passing on the built commit — the 31 hits on
   the base are EXECUTED (this review's scratch run agrees line for line); the pass on the built
   commit is not evidenced as drafted: the regex matches its own source in `tests/harness/scan.py`
   and U17's fixture lines in `tests/unit/test_scan.py`, neither exempt (M2). EXECUTED.
4. No line outside the two exempt files matches — follows from 3; the same gap (M2). INFERRED.
5. Sameness on the frozen set, `--claims build/102/claims.toml`, prints nothing — checkable;
   `sameness.py --claims` exists (spec 092 landed in wave 03, `tests/harness/sameness.py:24`).
   Not yet met. READ.
6. 0 fuel rows, 0 bytes rows — checkable from the record; consistent with the design: no host
   code spends guest fuel, no artifact byte changes. INFERRED.
7. No pass is lost — not evidenced as drafted: all six rows of `tests/unit/test_runner_cancel.py`
   patch `runner._context_address`, which the draft deletes, and
   `test_the_async_stack_size_property_is_preferred` calls `runner._set_async_stack`, also
   deleted; neither file's change is in the draft (M1). READ.
8. Fuel neutrality held, the rename rule's row unchanged — checkable; the bracket in the Design
   matches today's `forward` (`mounts.py:798-820`) call for call. READ.
9. Seventeen unit rows; the three moved rows gone from their old files — checkable (a
   `--collect-only` grep). The count is seventeen in U1–U17 but criterion 1 needs one more (L3).
   READ.
10. The package imports without wasmtime-py and without the adapter — checkable;
    `test_package_imports_without_wasmtime` (`tests/checks/test_v1_4_embedding.py:738`) sets
    `sys.modules["wasmtime"] = None`, so an adapter imported at package import would turn it red
    on its own; the draft imports the adapter only inside functions. READ.
11. `ruff` green; `test_no_module_level_name_is_bound_twice` green — checkable; not yet met. READ.
12. `tests/public_api.txt` unchanged — checkable; the snapshot names no `runner` private
    (EXECUTED: `grep` for `_wasmtime_version`, `_set_async_stack`, `_context_address`, `_get_fuel`,
    `_set_fuel`, `wasi_python.runner` finds nothing in its 301 lines), so deleting them cannot move
    it. EXECUTED.

## Findings, most severe first
1. **Two tests reach runner names the draft deletes, and neither file is in the draft** (M)
   (`tests/unit/test_runner_cancel.py:49`, `tests/unit/test_runner_calls.py:312`) — Decision 1's
   table removes `_context_address` and the Design removes `_set_async_stack`, but the `shared`
   fixture does `monkeypatch.setattr(runner, "_context_address", lambda caller: CONTEXT)` and
   `test_the_async_stack_size_property_is_preferred` calls `runner._set_async_stack(cfg,
   STATED)`; `test_runner_cancel.py` is not in the Kind line's file list and the Design names no
   change to that test.
   Failure: on the built commit `monkeypatch.setattr` on a missing attribute raises
   `AttributeError` in the fixture, so all six rows of `test_runner_cancel.py` error and one row of
   `test_runner_calls.py` fails → seven lost passes, red under AGENTS rule 5, and criterion 7
   cannot be met. What closes it: name both files in the Kind line and the Design; re-point the
   fixture to `monkeypatch.setattr(_wasmtime_ffi, "context_address", lambda caller: CONTEXT)`
   (it takes effect because `_shared` resolves `ffi.context_address` at call time through the
   module attribute) and the row to `_wasmtime_ffi.set_async_stack(cfg, STATED)`; add
   `context_address` to Decision 7's list of adapter names tests patch; the judge-hash line and
   the `--accept-judge` text name both files. (That row's `monkeypatch.setattr(_ffi,
   "wasmtime_config_async_stack_size_set", None)` at line 310 also becomes a patch of
   `ASYNC_STACK_SETTER`, as U7 says for its two neighbours.)
2. **The rule's regex matches its own source and its unit row's fixtures** (M)
   (`102-the-engine-seam.md`, Decision 3: "except exactly two"; criterion 3) — the alternation
   `\._func\b` matches the raw line `r"|\._func\b"` that `tests/harness/scan.py` must carry
   (EXECUTED above: the `\b` after `func` is satisfied by the backslash that follows), and U17's
   stand-in tree needs lines such as `x._func`, `other._context()`, `_from_ptr` and `.ptr()`
   spelled in `tests/unit/test_scan.py`; neither file is exempt, and both are under `tests/`.
   Failure: on the built commit the check reports at least `tests/harness/scan.py:<the pattern's
   line>` plus U17's fixture lines, so criterion 3's "passes on the built commit" and criterion 4
   are false as drafted. What closes it: one sentence in Decision 3 saying how the two files
   avoid themselves, either the pattern and the fixtures assembled from pieces that do not match
   (`"\\._" "func\\b"` split across two literals, and the fixture lines built by concatenation,
   with a comment saying why), or the exemption widened to name `tests/harness/scan.py` and
   `tests/unit/test_scan.py` exactly, the count changed from two to four; and U17 asserting that
   the scanner's own file is not a hit, so the dodge cannot silently lapse.
3. **`_wasmtime_version()` has a second caller the Design does not name** (L)
   (`src/wasi_python/runner.py:4739`, in `_module_miss`) — the table says `_wasmtime_version()`
   is removed, replaced by `version()`, and the Design names only `_set_async_stack`'s use; the
   `.cwasm` cache file name `f"{digest[:32]}-wasmtime{_wasmtime_version()}-{flavor}.cwasm"` also
   calls it.
   Failure: a builder that follows the Design literally leaves a `NameError` at the first cache
   miss with a cache directory. Fix text for the Design's runner side: "`_module_miss`'s cache
   name (`runner.py:4739`) reads `ffi.version()`, the same `importlib.metadata` string, so no
   cache file name changes"; Decision 4 gains the line "the `.cwasm` cache name is the same
   string".
4. **`wasmtime_error_delete` is in the table but not in `NEEDED`** (L) (Decision 1's
   `delete_error`; Decision 2's "the thirteen `_ffi` names") — the thirteen are the names
   `src/` reaches; `delete_error` wraps `wasmtime_error_delete`, which only
   `tests/unit/test_runner_async.py:249` calls today, so Decision 2's "one per private name of
   Decision 1's table" is fourteen, not thirteen.
   Failure: a wasmtime-py that moves `wasmtime_error_delete` passes the import check and fails
   inside U6 with an `AttributeError`, the shape the draft exists to prevent. Fix text:
   "fourteen `_ffi` names, `wasmtime_error_delete` the fourteenth; The problem's thirteen are
   the names `src/` reaches today".
5. **Criterion 1's `__all__` row is not one of the seventeen, and the table lacks four names
   the draft defines** (L) (criterion 1; Decision 5; the Design's adapter sketch) — `Storelike`,
   `NEEDED`, `missing` and `check` are module names the draft defines and U1, U2 and spec 106
   read, but Decision 1's table does not list them, so "exposes exactly the names of Decision 1's
   table" cannot hold; and no U-row lists `__all__` against the table, while `claims.toml` says
   `units = 17`.
   Failure: the builder must choose between a wrong criterion and a wrong unit count. Fix text:
   add the four to the table (a "the check and the protocol" group); make the `__all__` row the
   second assertion of U1 (so the count stays seventeen) and say so in criterion 1.
6. **The holder table reads `_ffi.dll` before `check` runs** (L) (Decision 2: `"wasmtime._ffi.
   dll": _ffi.dll`) — the dictionary literal evaluates `_ffi.dll` while being built, so a
   wasmtime-py without `_ffi.dll` fails with `AttributeError` at that line, not with the one
   `ImportError` that names the version and the names.
   Failure: the draft's promise "one `ImportError`" does not hold for that one name. Fix text:
   "`getattr(_ffi, "dll", None)` is the holder, and `missing` reports every name of a `None`
   holder".
7. **U3 hardcodes a patch version inside the pin's range** (L) (Decision 5, U3: `match=
   r"wasmtime-py 49\.0\.0 .*wasmtime_error_new"`) — the pin is `>=49,<50`; a 49.1.0 install
   turns the row red with no defect.
   Failure: a red fast tier after `uv sync` on a newer 49.x. Fix text: match
   `re.escape(importlib.metadata.version("wasmtime"))` (the adapter cannot be imported inside
   U3, so not `_wasmtime_ffi.version()`).
8. **`PreparedCall` says nothing of the trap out-pointer** (L) (Decision 1: "builds the
   argument array with its kinds set and a one-slot result array, once"; the sketch's
   `__slots__`) — today's `forward` makes `ctypes.POINTER(_ffi.wasm_trap_t)()` fresh per call
   (`mounts.py:800`) and `Trap._from_ptr` takes ownership of what it points to; a pointer kept on
   the object and not zeroed would read as a trap on the call after a trap.
   Failure: a second call on the same `PreparedCall` after a trap raises a stale `Trap` or
   frees twice. Fix text: "the trap out-pointer is made per call, as `forward` makes it today;
   only the two value arrays are kept".

## Constitution checks
- §4.2 (every input pinned): no input changes; the pin `wasmtime>=49,<50` stays, and U4 holds
  `pyproject.toml`, `PIN` and `_wasmtime()`'s message equal (READ: `pyproject.toml:18` has that one
  dependency). Holds.
- §4.5 (embedder-neutral): no embedder name in the draft or the new module's names. Holds.
- §4.9 (tests count, never time): the seventeen rows count names, addresses, calls and keys; no
  clock. Holds.
- §4.10 (claims carry their evidence): the draft's EXECUTED lines (31 hits by file, the
  `Func.__annotations__` fact, the property's absence, 0 hits under `scripts/` and `release/`,
  the empty `LAST_EXCEPTION` grep) were each re-run here and agree. Holds. The memo's "24 places"
  against the draft's 25 is the draft's count that is right (`runner.py` 14 and `mounts.py` 11
  under the draft's regex).
- §4.13 (uv, ruff, pytest): named; the `noqa: F401` on `_wasmtime()`'s import is the one lint
  exception and is justified. Holds.
- §4.14 (git): the branch `spec/102-the-engine-seam` from main's tip, 103 stacked on its reviewed
  tip; no other branch or worktree. Holds.
- §4.15 (safe by default): no default, limit or channel changes; Decision 4 says so and the
  acceptance is `sameness.py` on the frozen `v0.1.0a7` set. Holds, subject to M1 (lost passes
  would show in the record, so the gate is real).
- §5.2 (no undecided choice): the shape checks pass (EXECUTED); M2 leaves one decision the draft
  must make (how the scanner's own files avoid the rule). Otherwise holds.
- §5.6 (pre-build review where the runner's code changes): this review. Holds.
- Kind: parallel-safe and a judge change is right. The draft touches none of `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or the release workflow; it edits `tests/harness/` and
  `tests/checks/` and adds a unit file, so `--accept-judge` is due. The judge-hash line must
  gain the two files of M1.
- AGENTS rule 4 (never weaken the judge): `test_runner_mounts.py:260`'s `call.stopped.ptr()` →
  `str(call.stopped)` does not weaken the row: `WasmtimeError.__init__` itself calls
  `wasmtime_error_new` (EXECUTED: `inspect.getsource`), so `ptr()` distinguishes only a closed
  error from an open one, which `str()` non-empty equally holds for an open one; and
  `test_calls_add_nothing_to_wasmtime_pys_tables` keeps every assertion, counting through
  `host_function_count()` and patching `allocate` on `custom_output_table()`. Clean.
- Semantics the author asked to be checked: the prepared call's precedence (an error is wrapped so
  it is freed, then a trap replaces it and is raised) matches `mounts.py:810-813`; the fuel
  bracket stays in `forward` and `PreparedCall.call` touches no fuel, matching `mounts.py:798-820`;
  `set_fuel` never raising and `get_fuel` raising `WasmtimeError` match `mounts.py:2208-2223`;
  `_stop_error`'s `try`/`except` and continue-by-one fallback match `runner.py:3412-3424` (the
  adapter import belongs inside that `try`, where today's `from wasmtime import _ffi` sits, so an
  import failure in the callback still continues by one tick: a half-sentence for the Design);
  `set_async_stack`'s three branches in order match `runner.py:4085-4101`, with the one change
  (the binding read at import into `ASYNC_STACK_SETTER`) stated and its test consequence (patch
  the adapter's name) stated; the `(?<!self)` exemption covers `tools.py:1952` and nothing else
  in the 31 hits is a false positive (every `.ptr()` and `._func` hit is wasmtime's). The
  `_epoch_answer` comparison on a raw pointer stays outside the rule, as the draft says.
- §7 never-do list: nothing tripped. No patch, no fetch, no copying, no commit, no branch; the
  draft leaves no question list.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. Two tests reach runner names the draft deletes, and neither file is in the draft — fixed: the Kind line names `tests/unit/test_runner_cancel.py`; the Design's judge side re-points the `shared` fixture to `_wasmtime_ffi.context_address` and `test_the_async_stack_size_property_is_preferred` to `_wasmtime_ffi.set_async_stack` with `ASYNC_STACK_SETTER` patched (U7 names the row too); Decision 7's list of names tests patch gains `context_address`, with the sentence on why a patch takes effect; the judge-hash list and the `--accept-judge` text name the file; criterion 9 says both re-pointed files keep every row (Kind; Decision 5, U7; Decision 7; Design, "The judge's side"; criterion 9; For the lane).
2. The rule's regex matches its own source and its unit row's fixtures — fixed: Decision 3 gains "The rule's own files avoid the rule": the pattern is assembled from split literals in `scan.py` and every fixture line is concatenated in `test_scan.py`, each with a comment saying why; U17 asserts both files are not hits; the exemption stays at exactly two; criterion 3 says the pass includes both files (Decision 3; Decision 5, U17; criterion 3).
3. `_wasmtime_version()` has a second caller the Design does not name — fixed: the Design's runner side names `_module_miss` (`runner.py:4739`) reading `ffi.version()`, and Decision 4 gains "the `.cwasm` cache name is the same string" (Design, "The runner's side"; Decision 4).
4. `wasmtime_error_delete` is in the table but not in `NEEDED` — fixed: Decision 2 counts fifteen `_ffi` names, the thirteen of The problem plus `wasmtime_error_delete` for `delete_error` and `wasmtime_context_t` for `Context` (the alias is a private name too, so it is in `NEEDED` as well); the sheet's table has a row for each (Decision 2; Design, "The debt is documented").
5. Criterion 1's `__all__` row is not one of the seventeen, and the table lacks four names the draft defines — fixed: Decision 1's table gains the group "the check and the protocol" (`Storelike`, `NEEDED` and `OPTIONAL`, `missing`, `check`); the `__all__` listing is U1's second assertion; criterion 1 says so. The count is eighteen, not seventeen, because the owner's addition (U18, public first) is a row of its own (Decision 1; Decision 5, U1; criterion 1).
6. The holder table reads `_ffi.dll` before `check` runs — fixed: `getattr(_ffi, "dll", None)` is the holder and `missing` reports every name of a `None` holder (Decision 2).
7. U3 hardcodes a patch version inside the pin's range — fixed: U3 matches `re.escape(importlib.metadata.version("wasmtime"))`, never a literal (Decision 5, U3).
8. `PreparedCall` says nothing of the trap out-pointer — fixed: the table's `PreparedCall` row says the trap out-pointer is made per call, as `forward` makes it today, and only the two value arrays are kept (Decision 1).
9. *Semantics note* (the adapter import inside `_stop_error`'s `try`) — fixed: the Design's runner side says the import sits inside the `try`, so an import failure in the callback still continues by one tick (Design, "The runner's side").
10. *Additions made after the draft this review read* (the owner, 2026-10-20), for the reviewer to read: **Decision 8, "Public first, in the seam"**: every adapter operation calls wasmtime-py's public API when the installed release has it and falls back to the binding otherwise; a table per operation (the binding, the public form in 49.0.0 as EXECUTED, the public name preferred once a release has it, and the reason where the private one is kept); the decision that fuel and the deadline inside a host function stay on the `Caller` (the seven sites hold a `Caller`, not the `Store`; the public `Store` methods make the identical C call; the judge's stand-ins have no store) with the adapter taking the public path the day `Caller` has the methods; U18 holds the preference. **Design, "The debt is documented"**: the facts sheet `context/upstream/30-wasmtime-py-public-api-for-the-runner/facts.md` (thirty rows, one per entry of `NEEDED` and `OPTIONAL`), its row in `context/upstream/README.md`, the adapter's docstring list "private binding → public name wanted", the rules check `test_the_private_api_debt_is_documented` (static, by `ast`; both directions plus the docstring), and Decision 6's step 6 for the day a release makes an operation public. Criteria 13 and 14, the Scope, the claim list (two new rules-check nodes, eighteen unit rows) and the flags carry them.

## Verdict
Ready to build once M1 (the two tests outside the draft that reach deleted names) and M2 (how
`scan.py` and `test_scan.py` avoid the rule they carry) are written into the draft; the six Lows
are write-ins with their fix text above.
