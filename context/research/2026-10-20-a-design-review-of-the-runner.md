# A design review of the runner: `src/wasi_python` against a rubric for sandbox SDKs

- **Status:** executed 2026-10-20 on main `30e9b41` (the counts) and `5feb7e9` (the plan);
  the research specifications 103 to 108 stand on. Every claim is labelled EXECUTED, READ or
  INFERRED.
- **Method:** the whole of `src/` read (11,423 lines), then measured with `grep`, `git` and
  the fast tier's collection (`uv run pytest --collect-only -q -m "not slow"`: 2,616 tests);
  `ruff check` and `ruff format --check` green on `src/` (EXECUTED). The rubric is what a host
  SDK over a native engine that runs untrusted code looks like when it is done well, drawn from
  wasmtime-py, Pyodide's loader, gVisor's and Firecracker's host sides and Jupyter's kernel
  manager (READ: their public designs; nothing copied).
- **What it decides:** nothing by itself. It names eleven findings, ranked, and the six
  specifications that act on them (section 8).

`cli.py` (11,423 lines). Design, not correctness. Every number below is EXECUTED from the
tree at `30e9b41` unless marked READ or INFERRED.

**Verdict in one line.** The contract and the safety design are principal-grade; the internal
structure has not kept pace with the feature velocity, and the next investment before 0.1.0
should be structural, not functional.

---

## 1. The rubric: what "done well" looks like for this kind of project

This is a *host SDK over a native engine that runs untrusted code*. Its nearest relatives are
wasmtime-py itself, Pyodide's loader, gVisor's and Firecracker's host sides, and the Jupyter
kernel manager. When such a thing is done well it has these eight properties.

| # | Property | What it means in practice |
|---|---|---|
| R1 | **A small, explicit contract** | Few public names; invariants stated as sentences and checked by tests; failures promised by type, never by message; a written compatibility policy. |
| R2 | **Safety by construction** | Safe defaults; every channel to the host bounded; all arguments validated before any side effect; time-of-check races closed by identity (device and inode, handles) rather than by path strings. |
| R3 | **Layering with an isolated engine adapter** | Exactly one module touches the engine's private API; policy (what is allowed) is separate from mechanism (how the engine is driven); the dependency graph between modules is acyclic. |
| R4 | **Minimal, enumerable process state** | Module-global mutable state is rare, owned by one object, and reset in one place for fork and exit; lifecycles are explicit state machines, not collections of boolean flags; lock order is written down. |
| R5 | **Portability behind one seam** | OS-specific behaviour lives in one platform module with a small interface, chosen once, not in `if sys.platform` branches scattered through the logic. |
| R6 | **Testability through injection, not patching** | Seams are constructor parameters or protocol objects; tests drive public behaviour; production code carries no test-only hooks or flags. |
| R7 | **Evolvability** | Modules sized so one person can hold one in their head; the code explains *why* without a document archive open beside it; a type checker in CI; an upgrade plan for the engine pin. |
| R8 | **Operability** | Diagnostics (`stats()`), warnings that cannot break the caller, deterministic error text, and a record of what the guest did. |

## 2. The scorecard

| # | Property | Score | One-line reason |
|---|---|---|---|
| R1 | Contract | **Strong** | 22 + 9 public names, snapshotted in `tests/public_api.txt`; "nothing a guest does makes `run` raise"; exceptions promised by type; a written deprecation policy. |
| R2 | Safety | **Strong** | Safe defaults in a frozen `Defaults` read once per call; every channel capped (output, memory, time, fuel, file calls, open files, staging bytes, tool frames, tool bytes, validation steps, nesting, abandoned threads); folders judged by identity; preopens re-verified from inside a wasm module. |
| R3 | Layering | **Weak** | 24 reaches into wasmtime-py's private API (`_ffi`, `_bindings`, `Func._func`, `_from_ptr`, `caller._context()`) spread over two modules; `mounts.py` imports `runner` at construction and calls ten of its private names; `__init__` and `runner` import each other. |
| R4 | Process state | **Weak** | `runner.py` holds 60 mutable module globals and 27 locks; the fork hook resets 19 of them by hand; the session's lifecycle is spread over ten flag fields of a 35-field `_State`; `_Home` encodes its lifecycle in seven fields. |
| R5 | Portability | **Adequate** | Each OS-specific concern is a clean pair or triple of functions (`_walk_posix`/`_walk_windows`, three stack probes, two tree removals, two lock implementations), but the choice is made inside each function, six times over. |
| R6 | Testability | **Adequate, trending Weak** | The best parts (`_Waits`, `_Bounded`, `_ToolLoop`, `_reaper_loop`) inject their clocks and threads. But eight module-global test hooks live in production code, a `_reaper` dict carries `enabled`/`paused` flags for the judge, and 20 test files monkeypatch 20 distinct private names of `runner`. |
| R7 | Evolvability | **Weak** | One 6,241-line module with about 250 top-level definitions covering 22 concerns; 315 references to 60 specification numbers and 38 to review finding IDs in the source; 286 `Any` annotations and no type checker; `ruff` runs only E, F, I, UP, B. |
| R8 | Operability | **Strong** | `stats()`, `FileRecord`, `ToolRecord`, `Completed.trapped` with four promised strings, warnings queued and flushed outside every lock so an embedder's `showwarning` cannot deadlock. |

The pattern: everything the *embedder* sees is designed with unusual care. Everything the
*maintainer* sees has accreted. That is the normal shape of a project that has shipped 89
specifications in four days under a review gate that checks behaviour, not structure.

## 3. What is done well, and should be kept exactly as it is

These are not courtesies. They are the parts I would point other teams at.

1. **The contract is a sentence a test can check.** "Every argument is checked before any
   work", "nothing a guest does makes `run` raise", "a call given no root and no grants has
   nothing writable", "a default is read once, when the call is made". Each is written in
   the docstring, enforced in `_checked`, and pinned by a unit check. `public_api.txt` turns
   the API surface into a regression test.
2. **Judging by identity, never by spelling.** `_walk` opens each path component with
   `O_NOFOLLOW` (or `CreateFileW` without `FILE_SHARE_DELETE`), records `(dev, ino)` for the
   whole chain, and `_judge` compares identities. Then `_check_preopens` instantiates a
   tiny WAT module and asks wasmtime what inode it actually opened, re-implementing
   SipHash-1-3 to compare. This closes the class of rename-between-check-and-use bugs that
   most sandboxes only document.
3. **Every resource has a number.** The staging ceiling for mounts, the 1,024 provider
   numbers starting at 2³⁰ so wasmtime's own never collide, the validator's step budget, the
   64-level nesting bound computed in one pass before `json.loads`, the four abandoned
   tool threads. The project has internalised "unbounded is a bug".
4. **Injected time.** `_Waits`, `_Bounded`, `_ToolLoop` and `_reaper_loop` take their clocks,
   sleeps and thread starters as parameters, so the judge counts ticks instead of sleeping.
   This is the correct design and it is why the fast tier runs 2,616 tests in minutes.
5. **The guard with an expiry.** `GUARDED` shadows two WASI calls to carry wasmtime 49.0.2's
   and 49.0.3's advisory fixes, and a rules check (`test_the_rename_and_readdir_guard_match_the_floor`)
   fails the day the pin admits only patched versions. Temporary code that knows when to leave.
6. **`cli.py`.** 277 lines, mirrors `run()` one option per argument, adds no power, exit codes
   say "is there a result", not "how did the program end". Nothing to change.
7. **`tools.py`'s shape.** Clear sections (tools, vetting, validator, frames, loop, bound,
   host, stubs), a protocol version, a closed set of outcome kinds, and the host-side
   JSON rules fixed "so an answer is the same on every host". The validator's cost model
   (one step per schema node, keys made once at `tool()` time) is the right way to bound a
   schema check against hostile input.

## 4. Findings, ranked

### H1. `runner.py` is the architecture, and it is one file

6,241 lines; about 250 top-level definitions; 22 distinct concerns in sequence
(limits, `run`, `run_async` and its pool, private temp folders and their lock protocol, a
bespoke tree remover, fork handling, argument checking, POSIX and Windows path walking,
identity judging, the stdlib zip copy and matplotlib's data extraction, SipHash and the
preopen check, the call pipeline, the drive loop and shared host functions, the epoch
callback, linkers and trampolines, output capture, Ctrl-C, `poll_oneoff` emulation, the
door, hashing and caching, the guest-thread hand-off, stack probing and signal-handler
verification, module compilation and the `.cwasm` cache, the epoch ticker, and sessions).

Process state is the glue between them: 60 mutable module globals and 27 locks. The cost
shows in three places:

- `_after_fork_in_child` must list every lock and every cache by name (19 globals today)
  and re-create them. A new global that is forgotten is a silent fork hazard. I found no
  check that enumerates the module's locks and asserts each is reset.
- `_release` at exit clears eight caches by name, for the same reason.
- Tests reach for the globals directly: `runner._held`, `runner._sweep_state`,
  `runner._ctrl_c`, `runner._fork`, `runner._calls`, `runner._engines`, `runner._zips`.

**Recommendation.** Turn `runner.py` into a package of modules, one per concern, with the
boundaries the file's own section comments already draw (they are good section comments).
A first cut that changes no public name:

| module | lines today (INFERRED from ranges) | contents |
|---|---|---|
| `_limits.py` | ~300 | `Defaults`, the `_*_limit` checks, `_check_inputs` |
| `_places.py` | ~900 | `Grant`, `_walk*`, `_judge`, `_check_import_path`, `_check_mounts`, `_runtime_folders` |
| `_private_dirs.py` | ~700 | `_Private`, the lock protocol, `_sweep_*`, `_remove_tree` and its two walks |
| `_zip.py` | ~300 | the private zip copy and matplotlib's data |
| `_engine.py` | ~500 | engines, modules, the `.cwasm` cache, linkers, trampolines, the epoch ticker |
| `_call.py` | ~900 | `_run_checked` to `_instance`, `_drive`, `_Call`, `_shared`, the door, `poll_oneoff`, streams |
| `_home.py` | ~350 | `_Home`, `_Box`, `_start_guest`, `_join_guest` |
| `_platform.py` | ~450 | stack probes, `_tell_interpreter`, trap-handler verification, kernel identity, locks |
| `_sessions.py` | ~1,350 | `_State`, the reaper, endings, turns, `Session` |
| `_process.py` | new | one object owning every piece of process state, with `reset_after_fork()` and `release_at_exit()` |

The `_process.py` object is the important one. With the state in one place, the fork reset
becomes `dataclasses.replace`-shaped rather than a hand-maintained list, and a unit check
can assert "no module in the package defines a `threading.Lock` at module level outside
`_process.py`".

### H2. The engine adapter is not isolated

The runner depends on wasmtime-py's private surface in 24 places across two modules:
`_ffi.wasmtime_context_set_epoch_deadline`, `_ffi.wasmtime_store_epoch_deadline_callback`,
`_ffi.wasmtime_error_new`, `_ffi.wasi_config_set_std{out,err}_custom`, `_ffi.dll`,
`_ffi.wasmtime_func_call`, `_ffi.wasmtime_context_{get,set}_fuel`, `_ffi.wasmtime_val_t`,
`_bindings._wasmtime_store_epoch_deadline_callback.argtypes`, `Func._func`,
`Trap._from_ptr`, `WasmtimeError._from_ptr`, `caller._context()`, `store.ptr()`.

Each use is justified in a comment (the process-wide exception slot, the per-call output
table without a lock, fuel-neutral forwarding). The pin `wasmtime>=49,<50` is the only
guard. When wasmtime-py 50 arrives, the migration touches two modules in 24 places with
no single place to look, and the first sign of a moved symbol is an `AttributeError`
deep inside a call.

**Recommendation.** One module, `_wasmtime_ffi.py`, that imports `_ffi` and `_bindings`
once, exposes the twelve operations by name (`set_epoch_deadline(context, n)`,
`call_func(context, func, params, results)`, `get_fuel`, `set_fuel`, `new_error(text)`,
`set_custom_outputs(wasi, write, free, keys)`, `epoch_callback_type()`, `raw_func(func)`,
`context_of(caller)`, `trap_from_ptr`, `error_from_ptr`, `load_base()`), and checks at
import that every symbol exists, raising one `ImportError` that names the wasmtime-py
version and the missing names. A rules check asserts that `_wasmtime_ffi.py` is the only
module importing `wasmtime._ffi` or `wasmtime._bindings`.

### H3. The call's state is an untyped dict; the session's lifecycle is ten flags

`_checked` returns `dict[str, Any]` with about 21 keys. It is read with `c["fuel"]` in some
places and `c.get("tools")` in others, and the comments say why: "a hand-built `c` without
it: no limit", "the judge's stand-ins". Production code is shaped by the test fixtures'
omissions.

`_State` has 35 attributes. Its lifecycle is encoded across `ended`, `outcome`, `busy`,
`closing`, `done`, `turn_thread`, `ending_thread`, `called`, `sound`, `needs_initialize`
and `counted`. Which combinations are legal is implicit in `_claim`, `_mark`,
`_claim_ending`, `_end_session`, `_session_turn`, `_abandon_turn` and `close`. `_Home`
likewise: `state` (a string), `done`, `serving`, `abandoned`, `raised`, `ended`, `thread`.

The code is careful and the comments cite the review findings that each flag closed. But a
state machine expressed as flags cannot be checked for completeness, and every new path
(spec 078's forced-out home, spec 055's closer threads) adds a flag and a comment.

**Recommendation.**
- Replace `c` with a frozen `@dataclass class _CheckedCall` with every field typed and
  required; the test stand-ins construct it with explicit values. `_State` loses `c`, `wt`,
  `engine` as loose attributes.
- Give the session one `phase: _Phase` enum (`OPEN`, `TURN`, `ENDING`, `ENDED`) and one
  `transition(state, event) -> _Phase` function with a table; keep `ended: str | None` and
  `outcome` as the recorded reasons. Do the same for `_Home` (`IDLE`, `STARTING`, `RUNNING`,
  `CANCELLED`, `DONE`). A table-driven machine is also what the judge can exhaustively test.

### H4. `mounts.py` and `runner.py` depend on each other

`_Files.__init__` does `from . import runner` and stores the module; it then calls
`runner._siphash13`, `_epoch_now`, `_epoch_ticker.count`, `_hook["exiting"]`,
`_ctrl_c_watched`, `_ctrl_c["pending"]`, `_trampoline_module`, `_stat_trampoline_module`,
and reads `runner.__dict__`. `runner.py` in turn imports `_Files`, `SIGNATURES`,
`GUARDED`, `COUNTED` and the WAT builders from `mounts`.

`mounts.py` is the wasi-libc emulation layer: a self-contained, testable thing (and its
1,908-line unit file shows it is tested that way). It should not know that the runner has
an epoch ticker or a Ctrl-C flag.

**Recommendation.** Pass a small protocol object into `_Files` (`_CallContext` with
`stop_now(caller)`, `deadline_passed()`, `exiting()`, `ctrl_c_pending()`, `ino_of(path)`,
`trampolines(engine)`). `runner` implements it; the tests implement a fake. The circular
import disappears, and `mounts.py` can be read alone.

### H5. Test seams are module globals in production code

Eight hooks: `_after_walk`, `_on_entry`, `_on_arm`, `_on_export`, `_after_export`,
`_on_call`, `_session_clock`, `_start_ending`; plus `_reaper["enabled"]` and
`_reaper["paused"]` ("the judge may open sessions without the thread; it may drive `_reap`
alone"); plus `_drive_folder`, "a seam the tests replace". And 20 unit files monkeypatch 20
distinct private names (`_ctrl_c_watched` eight times, `_remove_tree` five).

Each hook is small and each is explained. Together they mean the production code has
branches that only the judge takes, and the judge is coupled to the implementation's
private names, so the refactors in H1 to H4 will break tests that test nothing about
behaviour.

**Recommendation.** Fold the hooks into the `_process.py` object from H1 (or into the
`_CallContext` from H4) as optional observer callbacks set through one constructor; the
judge builds a `_Process` with its observers and injects it. `_Waits`, `_Bounded` and
`_ToolLoop` already show the pattern. Then write down the rule: a unit check may patch
nothing in `wasi_python` that starts with an underscore except through that one object.

### M1. No static type checking

286 `Any` annotations; 9 `type: ignore`; `ruff` selects only `E, F, I, UP, B`. For a
codebase whose correctness argument is "every value is judged by its real type" and whose
hardest bugs are in the hand-off between threads, a type checker is cheap insurance, and
it would have forced H3's dict to become a dataclass on its own. Add `mypy --strict` (or
pyright strict) over `src/` to `test_rules.py`, with a per-module allowlist that shrinks.

### M2. The source cites the archive instead of explaining itself

315 references to 60 specification numbers and 38 to review findings ("the build review's
F3", "the a4 security review's F2", "the re-review's N3") in `src/`. The *why* is usually
also written in the sentence, which is good; the IDs add noise and go stale (the reviews
directory already holds 187 files). Keep one `# spec NNN` per concern at its module
docstring, keep the prose reasons, and drop the finding IDs from the code (they belong in
the landing notes, which already have them).

### M3. Platform selection is repeated six times

`_walk` chooses POSIX or Windows; `_guest_stack` chooses among three; `_try_lock`,
`_unlock_close`, `_kernel_identity`, `_remove_tree`, `_real_dir_at`/`_real_dir` and
`_identity_of` each choose again. Each pair is clean. The design cost is that "what does
Windows do differently" has no one answer. A `_platform.py` module with one interface
(`open_dir_handle`, `identity`, `lock`, `unlock_close`, `stack_bounds`, `kernel_identity`,
`remove_tree`) and two implementations chosen at import would make the Windows story
reviewable in one file, and is where M1's type checker pays off most.

### M4. Two notions of "the file changed" guard the same integrity check

`_stamp` is `(dev, ino, size, mtime_ns, ctime_ns)` and guards the zip copy. `_digest`,
which backs the SHA256SUMS check of spec 087, caches by `(resolved path, size, mtime_ns)`
only. `_versions` caches by path forever. `_guest_packages` caches by the full stamp. A
cache in front of an integrity check should key on at least the full stamp, or hold the
descriptor it hashed and `fstat` it. The artifact folder is trusted by the threat model, so
this is defence in depth, not a hole; but the inconsistency will confuse the next reader.

### M5. The private-folder protocol deserves to be its own thing

Lock files beside folders, a kernel identity written into the lock, a sweep that removes
dead processes' folders, a budgeted tree remover that holds at most two descriptors and
checks each parent's identity on the way up. About 700 lines, well reasoned (spec 016,
spec 084), and interleaved with the call pipeline. This is exactly the kind of component
that should have its own module, its own invariants paragraph, and property-based tests
(concurrent creators and sweepers on one temp dir), rather than sharing a file with the
door and `poll_oneoff`.

### L1. The package's own import cycle

`__init__.py` defines `Artifacts` and `ArtifactsMissing`, then imports `runner` at the
bottom with a "Last:" comment, because `runner` imports them back. Move the two into
`_artifacts.py`; both import from it; the comment goes.

### L2. Friend-class coupling in `tools.py`

`_Work` reads `host._gate`, `host._size`, `host._loop`; `_Ops` reads `bound._lock` and
calls `bound._begin`. Inside one module this is fine; it is noted because `tools.py` is
otherwise the model the other modules should follow.

## 5. What the process is missing (against the rubric's "done well")

The project's process is unusually strong on *decisions* (89 specifications, a decisions
log, a constitution) and on *behavioural* review (187 reviews, a judge that refuses to lose
a pass). It has no equivalent for *structure*:

- No module size or complexity ceiling in the rules (`test_rules.py` checks many things;
  not that).
- No type checker (M1).
- No engine-upgrade plan: the pin is `<50` and nothing says what a bump costs or where to
  look (H2).
- The pre-build review (constitution §5.6) is required for changes to the guest's
  imports, the artifact set and the build recipe. A change that adds a sixth concern to
  `runner.py` gets no design review, only a behaviour review, which is how the file got
  here.

**Recommendation.** One rules check: no module in `src/` over 1,500 lines, no function over
80, enforced from the day the split in H1 lands. And extend §5.6's pre-build review to any
specification that adds a module-level mutable or a new `_ffi` use.

## 6. Order of work (as first proposed; section 8 is the order adopted)

None of this changes a public name, so all of it is parallel-safe under the judge.

1. **H2, the FFI adapter** (half a day). Smallest, most mechanical, and it de-risks the
   wasmtime 50 bump that is otherwise a surprise.
2. **H1 + H5 together, the split and the `_Process` object** (two to three days). The
   split is mostly moving text along the existing section comments; the `_Process` object
   is where the design work is. Do the fork-reset test first.
3. **H3, typed call state and the session phase enum** (one day), followed at once by
   **M1, the type checker**, which will then pass.
4. **H4, `mounts.py` behind a protocol** (one day).
5. **M3, `_platform.py`** (one day), then **M2, M4, M5, L1** as the files are touched.

## 7. One line

The embedder's side of this package is designed as well as any sandbox SDK I know; the
maintainer's side is one 6,000-line module held together by sixty globals, and the fix is
a structural pass that touches no public name.

## 8. The chain of specifications this memo stands under (the owner, 2026-10-20)

Six parallel-safe specifications, stacked, each built on the one before (constitution §4.14),
changing no line of `tests/public_api.txt` and no artifact byte. The owner approved the plan
on 2026-10-20 with four decisions: the numbers 103 to 108; **all six land as one wave, past
§5.7's five** (the owner, 2026-10-20: "land all 6 specs at once, we can go past the 5
limit"); one dispatch of the release workflow on the chain's final tip in place of one per
specification (the owner's rule for rebase-only entries, extended to the chain); and the
baseline set is the `v0.1.0a7` release's, verified against its `SHA256SUMS`, with
`tests/harness/sameness.py` as the judge of "no verdict moved" after each build.

Two later decisions of the same day. **Public first, and the debt written down** (the owner,
2026-10-20): every adapter operation of spec 103 calls wasmtime-py's public API where the
installed release has it, and the private bindings the runner still needs are listed in
`context/upstream/30-wasmtime-py-public-api-for-the-runner/facts.md`, held in step with the
adapter by a rules check. **Code speaks for itself** (the owner, 2026-10-20): no code file names
a specification, a memo, a review, a finding ID or a `context/` path; the reason stays in words,
and a `context/` document may cite and link the code. Spec 107 clears `src/` (331 `spec NNN`
uses on e319829, EXECUTED) and holds it with a check; spec 109, reserved, clears `tests/`
(1,143), `scripts/` (213) and `release/` (4) the same way, as the chain's last entry.

**Renumbered** (the coordinator, 2026-10-20): the chain was drafted as 102 to 108 on main
`5feb7e9`; the lane reserved 102 for the release tier the same afternoon (main `e56b387`), so the
chain moved up by one, 103 to 109, in one commit on the PR branch once the fourth entry had landed
(built as 102 to 105; the two still to build and the reserved last entry took their new numbers
before building). The commit renames the files and rewrites every citation, read line by line
from a script's plan; no behaviour or verdict changes, though the comments in `src/` and `tests/`
that still cite the old numbers (cleared by 107 and 109) move with it, so the judge's hash moves;
each specification's landing notes keep the hashes the builders wrote.

| spec | title | findings |
|---|---|---|
| 103 | The engine seam: one module touches wasmtime-py's private API | H2 |
| 104 | The runner becomes a package: one module per concern | H1, M5, L1 |
| 105 | One owner for the process's state, and the test seams move off module globals | H1, H5 |
| 106 | Typed call state, explicit lifecycles, and a type checker in the judge | H3, M1 |
| 107 | `mounts.py` behind a call-context protocol, one platform module, one stamp | H4, M3, M4, M2 |
| 108 | A structural review is a stage | section 5 |
