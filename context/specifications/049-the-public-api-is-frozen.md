# 049 — The public API is frozen and documented

- **Status:** built 2026-10-18 in the worktree `wasi_python-049` on `spec/049-the-public-api-is-frozen`, from main `1c0123c` (034 landed), commits `6f7a2fe` to `e700ce8` and these notes; awaiting its build review. Before that: confirmed for build 2026-10-18 with two conditions (the review's Confirmation), written here: **C1**, the README check blanks code fences first, indented fences included, searches inside them for the same internal names, and pairs backticks only outside them, with a stand-in in criterion 6 that pairs naively (0 of 6) and one that blanks only line-start fences (3 of 6); **C2**, the Decision 13 sentence for `context/README.md` is written by the builder on its branch, not by the lane at landing (§5.7). 034 lands first (landed 2026-10-18). Decision 8 revised 2026-10-18 for the owner's answer to question 88: a deprecated thing survives at least two final minor releases. drafted 2026-10-18; reviewed before build the same day
  (`../reviews/049-the-public-api-is-frozen-spec-2026-10-18.md`; verdict: ready to build once
  F1 to F7 are written in) and revised against all thirteen findings (the review's
  Disposition says where each went); awaiting the reviewer's confirmation. It changes neither
  the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no
  review before build; one was asked for because Decision 8 binds every later specification
  that touches the package. **It lands after spec 034** (Decision 13).
- **Owner:** Clay Gendron
- **Kind:** the package's two public modules (`src/wasi_python/__init__.py`: `__all__`, three
  renamed constants, `defaults()`, `set_defaults()`, `stats` re-exported, the module
  docstring; `src/wasi_python/tools.py`: `__all__`, seventeen renamed constants, `tool`'s two
  overloads), the docstrings of every public name where it is defined (`runner.py`,
  `mounts.py`, `tools.py`), seven annotations (Decision 5's changes 1, 2 and 4), one read of the
  defaults per call (`runner._checked`, Decision 2), `src/wasi_python/py.typed` (new, empty),
  judge additions (`tests/harness/api.py`, `tests/public_api.txt`,
  `tests/checks/test_v1_4_public_api.py`) and a judge change (the renamed constants where tests
  and the harness name them, Decision 4; the wheel rule), `README.md`, `CHANGELOG.md`. **Not
  build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release
  workflow.
- **Depends on:** 001 (the runner, `artifacts()`), 013 and 014 (arguments checked first), 015
  (`run_async`, `Defaults.async_workers`), 017 (`Grant`), 019 and 022 (the command line), 028
  (wasmtime a plain dependency, the lazy import), 031 and 036 (`wasi_python.tools`, `tools=`),
  032 (`Mount`, `FileRecord`), 048 (the guard linker): all landed. **034 (writable mounts),
  which lands first.** 034 adds public names and rewrites the same docstrings and README
  sections this specification does, so this one starts its source and README work from main
  after 034 has landed (Decision 13).
- **Research it stands on:** the roadmap's milestone 6, "the public API frozen and documented"
  (`../roadmap.md`); this specification's survey of main at `77bd08e` (EXECUTED, quoted in "The
  problem" and Decision 10: `survey.py`, `probe_annotations.py`, `probe_internal_names.py` and,
  for the revision, `probe_readme_constants.py` at `44faa43`, each run with `uv run python` on
  Python 3.14.2; the lines that matter are quoted here); the pre-build review's own probes
  (EXECUTED there: the signature render is the same on Python 3.11 to 3.14, raw `__doc__` is not
  and `inspect.cleandoc` is; an undocumented dataclass gets a generated `__doc__`; `Defaults`
  accepts `None` for five limits); the package's source and `README.md` as they stand (READ);
  the constitution's §4.13 (no dependency without a written reason), §4.15 (a looser default
  needs the owner) and §5.5 (a security fix is a reason to release). The conventions of PEP 8
  ("Public and internal interfaces": `__all__`, and a leading underscore for what is internal),
  PEP 561 (`py.typed`) and PEP 387 (CPython's own deprecation rule) are used as published; they
  were not re-read for this draft (INFERRED from their known text).

## The problem

wasi_python is about to make its first release to rely on. An embedder will write code against
`run`, `Completed`, `Grant`, `Mount` and `tool`. Today nothing says which of the package's names
they may rely on, nothing notices when one changes, and the documentation is spread through a
long README.

What the survey found (EXECUTED, `survey.py` on main `77bd08e`):

- `wasi_python.__all__` has 14 names: `Artifacts`, `ArtifactsMissing`, `Completed`, `Errno`,
  `FileFault`, `FileProvider`, `FileRecord`, `Grant`, `Mount`, `Stat`, `artifact_dir`,
  `artifacts`, `run`, `run_async`. Three more module-level names carry no underscore and are not
  in it: `ARTIFACT_DIR`, `ARTIFACTS_ENV`, `CHECKOUT_ARTIFACT_DIR`.
- `wasi_python.tools` has no `__all__`. It has 26 module-level names without an underscore: the
  eight the README teaches (`Tool`, `ToolCall`, `ToolOutcome`, `ToolRecord`, `ToolError`,
  `ToolDenied`, `tool`, `stubs`) and eighteen constants (`PROTOCOL`, `PROTOCOLS`,
  `TOOL_REQUEST_BYTES`, `TOOL_RESPONSE_BYTES`, `TOOL_VALIDATION_STEPS`, `TOOL_NESTING`,
  `VALUE_NESTING`, `INT_CHARS`, `MESSAGE_CHARS`, `ECHO_CHARS`, `FAULT_CHARS`, `RECORD_OUTCOMES`,
  `MAX_ID`, `KINDS`, `TOO_COMPLEX`, `SAME_VALUE_CHAIN`, `MAX_ABANDONED`,
  `DEADLINE_MARGIN_TICKS`).
- The README names the internal binding `DEFAULTS` in six backticked spans: three times as
  `wasi_python.runner.DEFAULTS` or `dataclasses.replace(DEFAULTS, …)` (one of them the way to
  size `run_async`'s pool, by assigning it), and three times bare (`DEFAULTS.file_calls`,
  `DEFAULTS.async_workers`, `DEFAULTS.tool_calls`); and `wasi_python.runner.stats()` once
  (EXECUTED, `probe_readme_constants.py` at `44faa43`: six spans, lines 534, 690, 697, 818,
  850 and 1079). `run`'s docstring names `BASE_ENV` and `CANCEL_TICKS`, constants of that
  module.
- Every public name has a docstring, but `FileProvider`'s three methods do not. No docstring
  has an `Args:` section; dataclass fields are explained by `#` comments, which neither
  `help()` nor a generated reference can read.
- 106 annotations on public signatures and fields evaluate in a namespace of public and
  standard names; 2 do not: `run`'s and `run_async`'s `host: Host | None`, where `Host` is an
  alias inside `runner.py` (EXECUTED, `probe_annotations.py`: "annotations evaluated: 106
  failed: 2"). Some that evaluate are narrower than what the code accepts: `Defaults`'
  `memory_bytes`, `deadline_s`, `output_bytes` and `file_calls` take `None` but say `int` or
  `float` (the review, F2).
- There is no `py.typed`, so a type checker treats the package as untyped.
- `tool()` returns `Any`, so a function decorated with `@tool` loses its type in a checker.

## Decisions

1. **The public surface is two modules, one command and two environment variables.** The
   modules are `wasi_python` and `wasi_python.tools`. The command is `wasi-python` (also `python
   -m wasi_python`). The environment variables are `WASI_PYTHON_ARTIFACTS` and
   `WASI_PYTHON_CACHE`. Everything else is internal: the modules `runner`, `mounts`, `cli` and
   `__main__`, and every name not in a public module's `__all__`. Internal means it may change
   in any release without notice.
   - The internal modules keep their names. Renaming them `_runner` and so on would rewrite most
     of the judge (it imports `wasi_python.runner` in nearly every file) and every
     specification in flight, for nothing a user sees. They are internal by declaration: the
     package docstring and the README's reference say so, and Decision 10's check keeps every
     public document from pointing into them.
   - `wasi_python.tools` stays a module of its own, not re-exported at the top level, so `import
     wasi_python` still never imports the protocol (spec 031).

2. **`wasi_python.__all__` is exactly these 18 names**, sorted (034 adds two more, Decision
   13):

   | name | what it is | defined in |
   |---|---|---|
   | `Artifacts` | the artifact set's four paths (made by `artifacts()`, or by the user) | `__init__.py` |
   | `ArtifactsMissing` | exception, a `RuntimeError` | `__init__.py` |
   | `Completed` | how one program ended (result) | `runner.py` |
   | `Defaults` | the limits a call has when it names none | `runner.py` |
   | `Errno` | a provider's error answers, an `IntEnum` | `mounts.py` |
   | `FileFault` | one provider fault (result) | `mounts.py` |
   | `FileProvider` | a mount provider's protocol (for type checkers) | `mounts.py` |
   | `FileRecord` | a call's provider calls (result) | `mounts.py` |
   | `Grant` | a host folder the guest sees (made by the user) | `runner.py` |
   | `Mount` | a provider the guest sees (made by the user) | `mounts.py` |
   | `Stat` | what `stat` answers (made by the user's provider) | `mounts.py` |
   | `artifact_dir` | the folder holding the artifact set | `__init__.py` |
   | `artifacts` | the artifact set's paths, or `ArtifactsMissing` | `__init__.py` |
   | `defaults` | the `Defaults` calls read now | `__init__.py` |
   | `run` | run one program | `runner.py` |
   | `run_async` | `run` from async code | `runner.py` |
   | `set_defaults` | replace the `Defaults`, returning the old | `__init__.py` |
   | `stats` | counts kept by this process | `runner.py` |

   `__version__` is public too, outside `__all__`, as is usual.

   **`defaults()` and `set_defaults(new: Defaults) -> Defaults` replace assigning
   `wasi_python.runner.DEFAULTS`.** Today the README tells a user to assign an attribute of an
   internal module. Re-exporting `DEFAULTS` would be worse: `wasi_python.DEFAULTS = x` would
   bind a second name that `run` never reads, and do nothing, silently. A function cannot be
   shadowed that way. The binding `run` reads stays `runner.DEFAULTS`, internal; so the judge's
   existing `monkeypatch.setattr(runner, "DEFAULTS", …)` keeps working unchanged, and code that
   still assigns it from 0.1.0a4's README keeps working until the internal name changes. The
   README's idiom becomes `set_defaults(dataclasses.replace(defaults(), async_workers=4))`.

   **What `set_defaults` does, under threads** (the review, F7):
   - It raises `TypeError` for anything but a `Defaults` (whose own checks have already run).
   - It swaps the new value in and reads the old one **under one lock**, and returns the old
     one, so two threads that race each get a distinct previous value and neither loses a
     restore.
   - **A call reads the defaults once, when it is made.** Today one call reads `DEFAULTS` three
     times (`_checked`, `_check_tools`, `_check_places`), so a `set_defaults` on another thread
     could give it a mix. The runner reads the binding through one internal helper,
     `_current_defaults()`, called once in `_checked`, which passes the value to
     `_check_tools` and `_check_places`; `run_async` makes that read on the caller's thread,
     when it is called, as it checks its arguments today, and gives the same value's
     `async_workers` to `_submit` for the pool's size. A call already made keeps what it
     read. This is a small runner change and is in the Scope.
   - **The pool.** A new `async_workers` applies to `run_async` calls made afterwards: the
     next such call without an `executor` makes a pool of the new size. Calls already running or queued on the old
     pool still run there, so for a while both pools' workers may run guests (after 8 → 4, up
     to 12 at once). `set_defaults`'s docstring says so, and the README's bound ("8 workers
     bound one process at about 8.3 GiB") gains that sentence.

   **`stats()` becomes public**, because the README already sends embedders to it to watch
   abandoned tool threads (spec 036). Promised: that it returns a dict of counts with at least
   the keys `compiled`, `loaded`, `written` and `tool_threads_running`, and what
   `tool_threads_running` counts. What the first three count belongs to the `.cwasm` cache,
   which Decision 8 leaves unpromised; their meaning may change with it. A minor release may
   add keys.

3. **`wasi_python.tools.__all__` is exactly 9 names:** `PROTOCOL`, `Tool`, `ToolCall`,
   `ToolDenied`, `ToolError`, `ToolOutcome`, `ToolRecord`, `stubs`, `tool`.
   - **`PROTOCOL` stays public** (the review, F11): it is the protocol number this host speaks,
     the guest package exports its own `PROTOCOL` (`recipes/guest/host/__init__.py`), and
     Decision 8 says the protocol is versioned by that number. An embedder needs a supported
     way to read it. Its value, 1, is in the snapshot.
   - A `Tool`'s public attributes are `name`, `description`, `fn`, `validates_input`,
     `timeout_s`, `read_only`, `destructive`, `idempotent`, `open_world`, the properties
     `input_schema` and `output_schema`, the method `descriptor()`, and calling it (`__call__`,
     rendered explicitly; its `*args, **kwargs` need no `Args:` entry). Only `tool()` makes one
     (spec 031), so its field order is not promised.
   - The other seventeen constants become private (Decision 4). Most are protocol 1's bounds,
     documented in the README's "The tool protocol" and fixed by the protocol's number; the
     rest (`MAX_ABANDONED`, `DEADLINE_MARGIN_TICKS`) are the runner's own policy, documented in
     "Tools" (spec 036). An embedder reads the numbers there.

4. **Private means a leading underscore, in a public module.** Every module-level name that
   `__init__.py` or `tools.py` binds (by a `def`, a `class`, an assignment, or an import from
   inside the package, such as `from . import runner as _runner`) and that is not in its
   `__all__` starts with `_`. Imports from outside the package (`os`, `dataclass`) and dunders
   are exempt.
   - **The renames.** `ARTIFACT_DIR`, `ARTIFACTS_ENV` and `CHECKOUT_ARTIFACT_DIR` become
     `_ARTIFACT_DIR`, `_ARTIFACTS_ENV` and `_CHECKOUT_ARTIFACT_DIR`; each of `tools.py`'s
     seventeen private constants gains a `_` (`TOOL_REQUEST_BYTES` becomes
     `_TOOL_REQUEST_BYTES`, and so on). Inside `tools.py` and `__init__.py` every use follows.
   - **The judge change is 27 lines in 5 files** (EXECUTED, a `grep` for module-qualified
     references at `44faa43`; the review's F10): `tests/test_api.py` 8 (`ARTIFACTS_ENV` 4, and
     the strings `"ARTIFACT_DIR"` and `"CHECKOUT_ARTIFACT_DIR"` in `monkeypatch.setattr` 4);
     `tests/harness/paths.py` 2 (lines 5 and 99); `tests/unit/test_runner_tools.py` 3
     (`T.TOOL_REQUEST_BYTES`, `T.MAX_ABANDONED`, `T.RECORD_OUTCOMES`);
     `tests/unit/test_guest_tools.py` 3 (`T.KINDS`; `T.PROTOCOL` stays); and
     `tests/unit/test_tools.py` 11 (`T.TOOL_VALIDATION_STEPS`, `T.TOOL_REQUEST_BYTES`,
     `T.SAME_VALUE_CHAIN`). No file in `scripts/`, `.github/` or `src/` outside the two public
     modules names them.
   - **Rename by qualified reference, never with a word-boundary replace.** The harness has
     its own `KINDS` (`tests/harness/wasm.py`, a wasm section table) and its own
     `ARTIFACTS_ENV` (`tests/harness/paths.py:37`, `tests/unit/test_checks_wiring.py`), and the
     guest package has its own `PROTOCOL`; none of these change.
   - **Nothing private is re-exported.** A name in a public `__all__` is public where it is
     defined too: `from .runner import _run as run` is refused, so a public name is never an
     alias for an internal object whose name says it may change.
   - **When in doubt, private.** A private name can be made public in any minor release at no
     cost. A public name can be removed only through a deprecation (Decision 8). So the
     surface starts small.

5. **The signatures and fields, frozen as they stand, with four changes.** The snapshot
   (Decision 9) records them all; this list says what each shape promises. None of the four
   changes any behaviour; each makes an annotation say what the code already does, so that it
   is not frozen narrower than the code (the review, F1 and F2).
   - `run(argv, *, …)` and `run_async(argv, *, …)`: every argument after `argv` is
     keyword-only, so a new one can be added without breaking a call. A default shown as
     `<default>` means "read from `defaults()` when the call is made". `run_async` takes `run`'s
     arguments except `cancel`, plus `executor`.
   - **Change 1:** `host`'s annotation becomes `Callable[[bytes], bytes | bytearray |
     memoryview] | None`, written out, in both, because the door takes any of the three from a
     host (`runner.py`, `_door`). `Host` stays an internal alias. A public signature names only
     public and standard names (Decision 12).
   - **Change 2:** `Mount.provider` is annotated `FileProvider` instead of `Any`. Nothing at run
     time changes: `run` checks a provider by its methods, as today. 034's
     `WritableFileProvider` is a sub-protocol, so it fits.
   - **Change 3:** `tool` gains two `typing.overload` declarations; the implementation is
     unchanged:
     - `tool(fn: Callable[..., Any], /, *, name: str | None = None, description: …, …) -> Tool`,
       for `@tool` and for `tool(f, name=…, …)` (the README's MCP and LangChain adapters, and
       `tests/unit/test_tools.py`, call it that way);
     - `tool(fn: None = None, /, *, name: str | None = None, …) -> Callable[[Callable[...,
       Any]], Tool]`, for `@tool(...)`.

     Both keyword lists are the implementation's, with the same defaults. **`fn=` by keyword is
     not promised**: the overloads take `fn` positionally only (`/`). The implementation keeps
     accepting `tool(fn=f)` at run time, unpromised, so no caller breaks today.
   - **Change 4:** `Defaults.memory_bytes`, `output_bytes` and `file_calls` are annotated
     `int | None`, and `deadline_s` `float | None`, as `tool_calls` already is: each accepts
     `None` for "no limit" (the README says so). `async_workers` stays `int`.
   - **Two kinds of dataclass.** Users make `Artifacts` (for `run(artifacts=…)`; the judge
     builds one by position), `Grant`, `Mount`, `Stat` and `Defaults` (through
     `dataclasses.replace`). For these the order of the existing fields is promised, since a
     user may pass them by position. The runner makes the rest (`Completed`, `FileFault`,
     `FileRecord`, `ToolCall`, `ToolOutcome`, `ToolRecord`); a user reads them. For these the
     field names and types are promised, not construction by position. Every public dataclass
     is frozen, and stays frozen.
   - **`Completed.trapped`** is `None`, or one of four fixed strings, `"out of fuel"`,
     `"deadline"`, `"cancelled"`, `"out of file calls"`, or a trap's plain name or an error's
     first line as wasmtime gives it. The four are promised; wasmtime's words are not.
   - **`ToolOutcome.outcome`** is `"ok"` or one of the protocol's kinds, listed in the README.
     The kinds belong to protocol 1 and change only with `PROTOCOL`.
   - **`Errno`**'s members and numbers are promised. The set is closed today (spec 032); adding
     a member is an addition.
   - The values of `defaults()` when the package is imported are recorded too: 1 GiB of memory,
     a 60 s deadline, 16 MiB of output, 10,000 file calls, 1,000 tool calls, and
     `async_workers` from the machine's CPU count (recorded as `<factory>`, because it depends
     on the machine).

6. **Exceptions are promised by type, never by message.** The public classes are
   `ArtifactsMissing` (a `RuntimeError`), `ToolError` and `ToolDenied` (a `ToolError`). The list
   below is what `run` and `run_async` raise today, written down without changing any of it
   (the review, F4: the first draft's list was short).
   - **Before any work:** `TypeError` or `ValueError` for a bad argument; `ArtifactsMissing`
     when there is no usable artifact set; `ImportError` when wasmtime-py cannot load (its own
     error chained, spec 028).
   - **While the call is prepared or runs:**
     - `OSError` (and its subclasses, such as `FileExistsError` and `NotADirectoryError`) for a
       host filesystem failure while the root, the private folders, the zip copy or the cache
       is prepared;
     - `RuntimeError` in a process forked after a guest ran; for `run_async`, after interpreter
       shutdown; and for a folder or the zip copy that changed between the runner's check and
       its use (README, *Grants*);
     - an error from wasmtime-py (today `wasmtime.WasmtimeError`, for a folder removed between
       the runner's check and wasmtime's own open). The type is **not promised**: it is
       wasmtime-py's, not this package's;
     - `KeyboardInterrupt` for Ctrl-C (`run`); `asyncio.CancelledError` when the awaiting task
       is cancelled (`run_async`);
     - any `BaseException` that is not an `Exception`, raised by the embedder's own `host`,
       provider, tool or gate, propagates (README, *Mounts* and *Safety*).
   - **What never makes them raise:** nothing a guest does, and no `Exception` that a provider,
     a tool or a gate raises (specs 006, 032, 036); those are recorded in the result.
   - **A new failure** is raised as one of the promised types above, or as a new subclass of
     one, so an existing `except` still catches it. Messages may change in any release.
   - The `Raises:` sections of `run` and `run_async` (Decision 10) name exactly these types.
     The command's JSON `kind` on exit 1 is the exception's class name, so it names one of
     them.

7. **The command line is frozen like the Python API.** `wasi-python run [OPTIONS] [--]
   ARG...` with the options `--env`, `--stdin`, `--deadline-s`, `--memory-bytes`,
   `--output-bytes`, `--fuel`, `--no-snapshot`, `--grant`, `--grant-writable`, `--root`,
   `--private-root` and `--no-root`; the exit codes 0 (a result), 1 (`run` raised), 2 (a usage
   error) and 130 (Ctrl-C); one line of JSON with the keys `exit_code`, `trapped`, `fuel_used`,
   `truncated`, `stdout` or `stdout_base64`, `stderr` or `stderr_base64`, or, on exit 1, `error`
   and `kind`. Each option stays one of `run`'s arguments (spec 019). The help text's wording is
   not promised.

8. **The promise for 0.x.** Versions follow PEP 440 as `0.MINOR.PATCH`. The promise starts at
   0.1.0, the first final release; until then, alphas may still change anything, as this
   specification does.
   - **A patch release** (0.1.1) changes no public name, signature, field, default value or
     command option. Its snapshot is identical. It fixes behaviour.
   - **A minor release** (0.2.0) may add: names, keyword-only arguments whose default keeps
     today's behaviour, dataclass fields placed last with a default (or keyword-only),
     `Errno` members, `stats()` keys, command options and JSON keys. It may remove or change
     incompatibly only what was deprecated at least two final minor releases before it, apart
     from the two exceptions below.
   - **A deprecation** is announced in three places at once: a `DeprecationWarning` where the
     deprecated thing is used (with `stacklevel` pointing at the caller's line); the docstring's
     first line, "Deprecated since 0.N: use X instead.", which the README's reference then
     shows; and a "Deprecated" line in the CHANGELOG. The thing keeps working for at least two
     final minor releases, as CPython's PEP 387 does (the owner, question 88): deprecated in
     0.N, it still works in 0.N and 0.N+1, and 0.N+2 is the first release that may remove it.
     Its removal is a "Removed" line in the CHANGELOG.
   - **Two exceptions, and only two** (the review, F8):
     1. **A tighter default** (a smaller limit in `defaults()`) may come in a minor release,
        without a deprecation, as a "Changed" line in the CHANGELOG. It can break a program
        that needed the old limit; the program's fix is one argument. A looser default needs
        the owner's decision (§4.15), in any release.
     2. **Security.** A change that closes a hole may break the surface in any release, without
        a deprecation, named under "Security" in the CHANGELOG (§5.5 makes a security fix a
        reason to release).

     Either is a visible snapshot change, as every change is.
   - **Not promised:** exception messages; `repr`s; help text; internal modules and names;
     wasmtime's trap names and error types; what `stats()`'s cache counts count; timings; fuel
     counts, which follow the guest's code; the `.cwasm` cache's layout; and the guest's
     contents (package versions are release policy, spec 004). The door's ABI and the tool
     protocol carry their own contracts: the door is the constitution's (§4.4), and the
     protocol is versioned by `PROTOCOL`.
   - **Where the promise lives:** in the README's reference (Decision 11) and in this
     specification (the owner, question 88: "the rest as spec 049 writes it").
   - **At 1.0** the same rules hold with "major" in place of "minor". When 1.0 comes is the
     owner's decision, not this specification's.

9. **A machine-checked snapshot of the surface: `tests/public_api.txt`.** It is a judge file
   (under `tests/`), so any change to the public API changes the judge's hash and shows in
   review as a judge change. It is written by `tests/harness/api.py` (`uv run python
   tests/harness/api.py --write`), which renders the live surface as plain text, one fact per
   line, so a change is a small diff. **`--check` compares both outputs**, the snapshot file
   and the README block (Decision 11), and exits 1 if either differs. The render holds:
   - per public module, in `__all__` order: each name's kind (`def`, `async def`, `class`,
     `dataclass`, `protocol`, `enum`, `exception`, `constant`);
   - a function: one line per parameter with its kind (positional-only, positional,
     keyword-only), its annotation as written, and its default's `repr`; then the return
     annotation; for `tool`, each overload's parameters and return too
     (`typing.get_overloads`);
   - a dataclass: `frozen`, then one line per public field (no leading `_`) with its annotation,
     its default (`required`, a `repr`, or `<factory>`) and `kw_only`;
   - a class: its public bases; each public method and property defined on it, with its
     parameters, and `Tool`'s `__call__`; an enum's members and values; an exception's base;
   - a constant (`PROTOCOL`): its value;
   - `defaults()`'s values on import; `stats()`'s keys; the protocol's outcome kinds; the two
     environment variables' names;
   - the command: its entry point from `pyproject.toml`, each option of the parser with its
     action and metavar, and the JSON keys of a result and of an error, read by running the
     command's `main` with a stand-in `run` (as `tests/unit/test_cli.py` does). Actions are
     rendered through a fixed map (`store`, `append`, `store_true`, `once`), never by class
     name: argparse's classes are private, and `--root` uses the package's own `_Once`.

   **How the render reads the code, so it is the same everywhere** (the review, F5):
   - **Signatures and fields** come from `inspect.Parameter`, `dataclasses.fields` and `ast`,
     never from `str(inspect.Signature)`, whose quoting differs between Python versions.
     **Annotations** are read as the stored strings, which `from __future__ import
     annotations` guarantees; the render asserts that import in every module that defines a
     public name (`__init__.py`, `runner.py`, `mounts.py`, `tools.py`), since without it
     Python 3.14 would evaluate them and the names `runner.py` imports only for type checking
     (`Tool`, `ToolCall`, `ToolRecord`) would raise `NameError`.
   - **Docstrings** are read as `inspect.cleandoc(vars(obj).get("__doc__") or "")` (for a
     property or method, from the function's own `__doc__`): only the object's own docstring,
     with the indentation removed the same way on every version. Raw `__doc__` differs between
     3.12 and 3.13, and `inspect.getdoc` inherits a base class's text.
   - **An undocumented name counts as undocumented.** A docstring that is empty, inherited, or
     the one `dataclasses` generates (it starts with `f"{cls.__name__}("`) is none.
   - The render runs in a child interpreter, so nothing a test changed in the judge's process
     (a patched `runner.DEFAULTS`) reaches it. `api.py` takes the package's path
     (`--package PATH`, default `src/wasi_python`), so criteria 1 and 4's stand-ins can point
     the child at a scratch copy.
   - Both files are written with `newline="\n"`: the judge runs on Windows too, and
     `.gitattributes` says LF.

   On a difference the check prints the unified diff and the `--write` command. The result is
   the same on every Python the package supports (3.11 and up) and every system (criterion 11).

10. **Every public name is documented, and the check says what is missing.** In Google style.
    The harness has its own small parser for `Args:`, `Attributes:` and `Raises:`; it does not
    reuse or extend `tools._HEADINGS`, which decides how a *tool's* description is cut for the
    guest, so changing it would change behaviour.
    - every name in both `__all__`s, and every public method and property defined on a public
      class (`FileProvider.stat`, `list`, `read`, none documented today; `Tool.descriptor`,
      `input_schema`, `output_schema`), has a docstring of its own (Decision 9's reading);
    - every parameter of a public function or method is described in its `Args:` section,
      except `self` and `Tool.__call__`'s `*args, **kwargs`;
    - every public field of a public dataclass is described in its class docstring's
      `Attributes:` section; the `#` comments that describe fields today move there;
    - `run`, `run_async`, `artifacts`, `artifact_dir`, `set_defaults` and `tool` have a
      `Raises:` section; `run`'s and `run_async`'s name exactly Decision 6's types, and
      `set_defaults`' names `TypeError`;
    - an argument `run` and `run_async` share is described by the same text in both, so the
      two cannot drift;
    - **no public docstring names a specification**, in any paragraph (the review, F12: 14
      such references outside the summaries today, EXECUTED there). A public docstring is the
      docstring of a public name, of a public method or property, or of one of the two public
      modules. Citations move to `#` comments beside the code, where maintainers read them;
    - **no public document names an internal name.**
      - In a public docstring: a backticked token whose root is a module-level name of an
        internal module, and not a public name. On main that is 7 hits (EXECUTED,
        `probe_internal_names.py`): `run`'s `DEFAULTS` (three times), `BASE_ENV` and
        `CANCEL_TICKS`; `run_async`'s and `Defaults`' `DEFAULTS`.
      - In the README (the review, F3): a backticked span, which may wrap a line, that holds
        `wasi_python.runner`, `wasi_python.mounts` or `wasi_python.cli`, or an upper-case
        constant assigned at module level in an internal module (46 names on main, `Errno`'s
        member names left out, since they are public through `Errno`). Ordinary words such as
        `main` are not caught, because only upper-case constants are. On main that is 6 spans
        (EXECUTED, `probe_readme_constants.py` at `44faa43`: lines 534, 690, 697, 818, 850 and
        1079). The builder re-counts after 034 lands.

      Each `DEFAULTS` becomes `defaults()` (`defaults().file_calls`, and so on), `stats()` is
      named from the top level, and the two constants in `run`'s docstring become the values
      they hold.

11. **The README's reference is generated from the same render.** A new `## API reference`
    section, before `## Safety`, opens with a short hand-written paragraph: what is public,
    that everything else is internal, and Decision 8's promise in a few sentences. Below it, a
    block between `<!-- api reference: begin (generated by tests/harness/api.py) -->` and
    `<!-- api reference: end -->` holds, for each public name: a fenced signature (or a
    dataclass's fields), its summary, and its `Args:`, `Attributes:` and `Raises:` as lists;
    then the command's options and exit codes.
    - **`run_async` is shown short** (the review, F12): "`run`'s arguments except `cancel`,
      plus:" and its `executor` entry only. Its docstring stays complete, for `help()` and an
      editor's hover; the render alone shortens it.
    - `--write` rewrites the block; `--check` and criterion 9 compare it with the render. The
      README's prose elsewhere keeps teaching; apart from Decision 10's six spans and the pool
      sentence of Decision 2, it is not changed here.

12. **Type hints: `py.typed` ships, and no type checker is added.**
    - `src/wasi_python/py.typed`, empty (PEP 561), is in the wheel; hatchling takes it as a
      package file, and the wheel rule (`tests/harness/artifacts.py`, `wheel_errors`) requires
      it.
    - Every public parameter, return value and dataclass field is annotated, and every
      annotation, each of `tool`'s overloads' included, evaluates in a namespace holding only
      the builtins, `typing`'s and `collections.abc`'s names, `os`, `threading`,
      `concurrent.futures`, `pathlib.Path`, and the public names of both modules. That catches a
      missing annotation, a misspelt one and an internal name (`Host` today), with no new tool.
      It cannot see an annotation narrower than the code; Decision 5's change 4 fixes the ones
      the review found, and a review of each later change reads the snapshot's types.
    - **No mypy or pyright in the dev group.** §4.13 asks a written reason for any dependency,
      and the reason is missing: a consumer's type checker reads only the package's public
      signatures, which the check above covers. Checking the internals strictly (6,000 lines,
      much of it ctypes and wasmtime-py values typed `Any`) would be a project of its own that
      changes nothing a consumer sees. If a consumer ever meets a typing defect the check
      missed, that defect becomes a check (AGENTS.md, rule 3), and a checker is added then, with
      its reason.

13. **Order with 034, and how later specifications change the API.**
    - **034 lands first** (the review, F6). It has passed its build review; asking it to grow
      by about sixteen documented items, a README block and a snapshot after that review would
      send it back. This specification's builder may write the render and the checks
      (Decisions 9 and 11; criteria 1 to 4 and 7 to 9) before 034 lands, since they touch only
      `tests/`. The renames, the docstring pass, the annotations and the README start from main
      after 034 has landed, and cover 034's names like any others: its docstrings lose their
      spec numbers and gain `Attributes:` and `Args:` here.
    - **The reviewer's checklist for 034's part of the snapshot**, which must appear exactly:
      `RefusedWrite` (a frozen dataclass: `mount`, `method`, `paths`, `errno`, `at`, `cause`)
      and `WritableFileProvider` (a protocol, a `FileProvider` with `write`, `mkdir`, `remove`,
      `rmdir`, `rename`) in `wasi_python.__all__` (20 names); `Mount.writable: bool = False`,
      keyword-only; `FileRecord.refused: tuple[RefusedWrite, ...] = ()` and
      `FileRecord.refused_total: int = 0`, last. Any other difference from 034's landed code
      is a finding.
    - **The rule for every later specification.** One that adds, removes or changes anything
      the snapshot records:
      - says so in its **Kind** line ("changes the public API") and lists, in a Decision, the
        snapshot lines it adds, removes or changes, and which of Decision 8's rules allows each;
      - meets Decision 10 for what it adds, regenerates `tests/public_api.txt` and the README
        block with `--write` in its own branch, and adds a CHANGELOG line under Added, Changed,
        Deprecated, Removed or Security;
      - is reviewed with the snapshot's diff in view; the reviewer checks that the diff is
        exactly the listed lines;
      - lands with `--accept-judge`, as any judge change does.

      A change the snapshot shows but no specification lists is a finding.
    - **Where drafters will see the rule** (the review, F8). A rule written only here binds
      only those who read this specification. The lane applies one sentence to
      `context/README.md`, at the end of the `specifications/` bullet, when this specification
      lands:

      > A specification that changes anything `tests/public_api.txt` records says so in its
      > Kind line ("changes the public API"), lists the snapshot lines it changes and the rule
      > of spec 049, Decision 8, that allows each, and regenerates the snapshot and the
      > README's reference with `tests/harness/api.py --write`.

      `context/README.md` is where the specification stage's rules live and what every drafter
      reads first (AGENTS.md sends them there); it is not a judge file, so the sentence does not
      change the judge.

14. **No version bump here.** The snapshot carries no version number. The CHANGELOG's
    unreleased section gains: Added, `defaults()`, `set_defaults()`, `stats()` at the top level,
    `PROTOCOL` in `wasi_python.tools.__all__`, `py.typed`, and the API reference; Changed, the
    seventeen other `wasi_python.tools` constants and three `wasi_python` constants are
    private, four `Defaults` fields and `host` are annotated as the values they take, a call
    reads the defaults once, and the README no longer names `wasi_python.runner` or
    `DEFAULTS`; and a line stating Decision 8's promise and that it starts at 0.1.0.

## Intent

An embedder can tell from one page which names they may rely on. Any change to those names, or
to their signatures, fields or defaults, fails the judge until a specification lists it and a
review sees it.

## Design

```
src/wasi_python/__init__.py      __all__ (18, 20 with 034's); _ARTIFACT_DIR, _ARTIFACTS_ENV,
                                 _CHECKOUT_ARTIFACT_DIR; defaults(), set_defaults() and its
                                 lock; stats re-exported; the module docstring names the
                                 public surface and says the rest is internal
src/wasi_python/tools.py         __all__ (9); seventeen constants gain "_"; tool's overloads;
                                 docstrings with Args/Attributes, no spec numbers
src/wasi_python/runner.py        docstrings of Completed, Defaults, Grant, run, run_async,
                                 stats (Args, Attributes, Raises; no internal names, no spec
                                 numbers); host's annotation; Defaults' four annotations;
                                 _current_defaults(), read once in _checked and passed on
src/wasi_python/mounts.py        docstrings of Errno, Stat, FileProvider and its methods, Mount,
                                 FileFault, FileRecord and 034's names; Mount.provider:
                                 FileProvider
src/wasi_python/py.typed         new, empty
tests/harness/api.py             the render, --write, --check and --package (Decisions 9, 11)
tests/public_api.txt             the snapshot
tests/checks/test_v1_4_public_api.py   the checks below (goal v1.4; no artifacts needed)
tests/harness/artifacts.py       wheel_errors requires wasi_python/py.typed
tests/test_api.py, tests/harness/paths.py, tests/unit/test_runner_tools.py,
tests/unit/test_guest_tools.py, tests/unit/test_tools.py    the 27 renamed lines
README.md                        ## API reference; six spans naming DEFAULTS or runner
                                 replaced; the pool sentence
CHANGELOG.md                     the unreleased section
context/README.md                one sentence (Decision 13), applied by the lane at landing
```

A few lines of the snapshot, to fix its shape (the builder's render decides the rest, and the
review reads the whole file):

```
module wasi_python
dataclass Grant: frozen
  field host: str | os.PathLike[str] = required
  field guest: str = required
  field writable: bool = False  kw_only
def run -> Completed
  param argv: Iterable[str]  positional
  param root: str | os.PathLike[str] | bool | None = False  keyword-only
  param deadline_s: float | None = <default>  keyword-only
default deadline_s = 60.0
stats keys: compiled loaded tool_threads_running written
module wasi_python.tools
constant PROTOCOL = 1
command wasi-python = wasi_python.cli:main
  option --grant GUEST=HOST  append
```

The builder works in this order: the render and its checks first, each seen failing against
main (this part may start before 034 lands); then, from main after 034, the renames, the
one read of the defaults and `set_defaults`; then the docstrings, name by name, until the
documentation check's counts are 0; then `py.typed`, the annotations and the overloads; then
the README block and `--write`.

## Scope

In: the above, including one runner change of behaviour under threads: a call reads the
defaults once (Decision 2). Out: renaming the internal modules; a documentation site or Sphinx;
the guest side's API (`from host import tools`, the stdlib inside the guest), which the tool
protocol's number and the README govern; a strict type check of the internals; deciding when
1.0 comes; any other change to what `run` does or raises (Decision 6 writes down today's
exceptions; it changes none). The README's prose sections stay as they are apart from the six
spans and the pool sentence Decisions 2 and 10 name.

## Acceptance criteria

Every check is in `tests/checks/test_v1_4_public_api.py` (goal v1.4), needs no artifact set,
and is seen failing first against main as it stands at build time. Nothing measures time; each
check counts names, lines, reads or items, and its failure message gives the counts and the
first items.

1. **`test_the_public_api_matches_its_snapshot`**: the render, made in one child interpreter,
   equals `tests/public_api.txt`. Seen failing first: with no snapshot file ("no snapshot:
   run … --write"). Stand-in: `--package` pointed at a scratch copy where `Stat.size`'s default
   is 1; the check fails, and its diff is exactly one removed and one added line, both naming
   `size`.
2. **`test_public_modules_export_exactly_their_all`**: each `__all__` is sorted, has no
   duplicate, names no `_` name, and every name in it resolves; `from wasi_python import *`
   binds exactly the 20 names (18 and 034's two) and `from wasi_python.tools import *` exactly
   the 9. Seen failing first: `wasi_python.tools` has no `__all__`, and `wasi_python` lacks
   `defaults`, `set_defaults` and `stats`.
3. **`test_private_names_carry_an_underscore`**: by `ast`, every name `__init__.py` or
   `tools.py` binds and does not export starts with `_`. Seen failing first: it lists 20 names
   (3 and 17).
4. **`test_nothing_private_is_re_exported`**: by `ast`, no import in a public module binds a
   name in its `__all__` from a name that starts with `_`. A guard: it passes on main.
   Stand-in: `--package` pointed at a scratch copy of `__init__.py` with `from .runner import
   _UNSET as UNSET` and `UNSET` in `__all__`; it fails with that one name.
5. **`test_every_public_name_is_documented`**: Decision 10's rules, each a count of what is
   missing (docstrings, own docstrings of public methods, `Args:` entries, `Attributes:`
   entries, `Raises:` sections and their types, shared arguments whose text differs, spec
   references in public docstrings). Every count is 0. Seen failing first: on main, 3 methods
   (`FileProvider.stat`, `list`, `read`) have no docstring; `run` alone has 19 undocumented
   arguments; 57 public fields have no `Attributes:` entry; 14 spec references. Stand-in for
   the reading rule: a scratch dataclass with no docstring and an exception subclass with
   none are each counted as undocumented, not passed by their generated or inherited text.
6. **`test_public_docs_name_nothing_internal`**: Decision 10's last rule; the count of hits in
   public docstrings and the count of README spans are both 0. Seen failing first: 7 and 6 on
   main, as listed there (the builder records the counts at build time, after 034).
7. **`test_public_annotations_resolve`**: every public annotation, each overload's included,
   evaluates in Decision 12's namespace; the count evaluated is reported, and the count that
   fails is 0; `tool` has exactly two overloads, the first taking a positional `fn` and
   returning `Tool`, the second taking `fn: None` and returning a callable. Seen failing
   first: 2 of 106 fail (`Host`), and `tool` has none.
8. **`test_the_package_is_typed`**: `src/wasi_python/py.typed` exists and is tracked. Seen
   failing first. The v1.1 check `test_wheel_carries_the_artifact_set` now also fails a wheel
   without `wasi_python/py.typed`; stand-in: a synthetic wheel without it (as
   `tests/unit/test_checks_wiring.py` builds them) fails with that one line.
9. **`test_the_readme_reference_matches_the_api`**: the README has exactly one block between
   the two markers, and it equals the render. Seen failing first: no block.
10. **`test_set_defaults_changes_what_run_reads`** (unit, no artifacts):
    - `set_defaults` with a `Defaults` whose `memory_bytes` differs returns the previous one;
      `defaults()` returns the new one; `runner._checked`, given no limits, carries the new
      value; `set_defaults(None)` and `set_defaults({})` raise `TypeError`; the previous value
      is restored. Zero artifact lookups, counted as spec 036's criterion 1 counts them.
    - **One read per call:** with `runner._current_defaults` (Decision 2) replaced by a
      counting wrapper, a call to `run` that stops after its checks (as spec 036's criterion 1
      stops it) and one to `run_async` each call it exactly once. Seen failing first: on main
      there is no single read; the stand-in that keeps the three reads counts 3.
    - **The lock:** with `set_defaults`' lock replaced by a counting wrapper, each call
      acquires it exactly once, and reads the old value and writes the new one inside it.
    - Seen failing first: the names do not exist.
11. **The render is the same on every supported Python.** The builder runs `uv run --python 3.11
    python tests/harness/api.py --check` and the same with the dev environment's Python (3.14
    today); both exit 0, and `--check` covers the snapshot and the README block. The commands
    and outputs go in the landing notes (§4.10). Not a check: the judge does not fetch
    interpreters. The release workflow's judge runs on Linux, Windows and macOS, so criteria 1
    and 9 meet all three systems there.
12. **The update path works once, end to end.** In a scratch copy, the builder adds a throwaway
    keyword argument to `run`; criterion 1 fails with a diff of one added line; `--write` makes
    it pass and changes the README block by one entry. Recorded in the landing notes, not kept.
13. Every existing check passes with the renamed constants; `ruff check` and `ruff format
    --check` are clean; `uv run pytest` is green with `--accept-judge`; lost 0; grew 0 (the
    artifact set does not change).

## The owner's choices

Nothing waits on the owner. Decision 8's promise was question 88, answered on 2026-10-18
(`../decisions.md`): the stricter promise, a deprecated thing survives at least two final minor
releases, as CPython's PEP 387, and the rest as this specification writes it. Decision 8 says
so, and the README paragraph the build writes states the same terms.

## Landing notes

Built 2026-10-18 by the implementer, a fresh agent (Claude Opus 5.5). It worked in the worktree
`wasi_python-049` on `spec/049-the-public-api-is-frozen`, from main `1c0123c`, after 034 landed.
The judge ran against the main tree's frozen artifact set `build/sets/s-f94dec535086b06c`. That
set's `SHA256SUMS` equals `build/artifacts/SHA256SUMS`, the set 051's acceptance judged. The set
was never rebuilt. Each claim is EXECUTED unless it says otherwise. The worktree's `build/` logs
named here are not kept; their lines are quoted.

**Commits on the branch, one per build step:**
- `6f7a2fe` step 1: the render and its checks, seen failing on main;
- `259fc0a` step 2: the renames, `set_defaults`, and one read of the defaults per call;
- `85547a4` step 3: the docstrings;
- `48a9f88` step 4: `py.typed`, the annotations, `tool`'s overloads;
- `e700ce8` step 5: the README's reference, the snapshot, the CHANGELOG, `context/README.md`;
- the commit after `e700ce8`: these notes and the status line.

**What changed.**
- `src/wasi_python/__init__.py`:
  - `__all__` is the 20 names.
  - `_ARTIFACT_DIR`, `_ARTIFACTS_ENV` and `_CHECKOUT_ARTIFACT_DIR` are renamed.
  - `from . import runner as _runner` is added.
  - `defaults()` returns `_runner._current_defaults()`.
  - `set_defaults(new)` checks `isinstance(new, Defaults)` (else `TypeError`). Then, under
    `_defaults_lock`, it reads `_runner.DEFAULTS` and assigns the new value. It returns the old
    value.
  - `Defaults` and `stats` are re-exported from `runner`.
  - The module docstring names the public surface and says the rest is internal.
- `src/wasi_python/tools.py`:
  - `__all__` holds 9 names.
  - Seventeen constants gain `_`, with every use in the module.
  - `tool` gains two `typing.overload` declarations. The implementation is unchanged.
  - The docstrings are rewritten.
- `src/wasi_python/runner.py`:
  - `_current_defaults()` is new. `_checked` calls it once.
  - `_checked` now takes `root`, `grants`, `mounts` and `max_file_calls`, and runs
    `_check_places` last. The order of refusals is unchanged: tools, then limits, then inputs,
    then places.
  - The one read goes to `_check_tools` (a new optional `limits`; the unit tests call it with
    four arguments) and to `_check_places` (a required `limits`).
  - The read's `async_workers` is kept as `checked["async_workers"]`. `_submit(executor,
    workers, fn, *args)` sizes the pool from it.
  - `host` is annotated `Callable[[bytes], bytes | bytearray | memoryview] | None` in `run` and
    `run_async`.
  - Four fields of `Defaults` are annotated `… | None`.
  - The docstrings of `Completed`, `Defaults`, `Grant`, `run`, `run_async` and `stats` are
    rewritten. Specification citations move to `#` comments.
- `src/wasi_python/mounts.py`:
  - `Mount.provider: FileProvider`.
  - Docstrings for `Errno`, `Stat`, `FileProvider` and its three methods, `WritableFileProvider`
    and its five methods, `Mount`, `FileFault`, `RefusedWrite` and `FileRecord`.
- `src/wasi_python/py.typed`: new and empty.
- The judge:
  - `tests/harness/api.py` is new: the render, `--write`, `--check`, `--package`, `--snapshot`
    and `--readme`, and the rules as counts.
  - `tests/public_api.txt` is new: 240 lines.
  - `tests/checks/test_v1_4_public_api.py` is new: 10 checks.
  - `tests/harness/artifacts.py`: `wheel_errors` requires `wasi_python/py.typed`.
  - `tests/unit/test_artifact_rules.py`: the synthetic wheel gains `py.typed`, and a new
    stand-in, `test_a_wheel_must_carry_py_typed`, is added.
  - The 27 renamed lines in 5 files, as Decision 4 lists them. `perl -pi` was used with
    module-qualified patterns (`T.`, `wasi_python.`). The harness's own `KINDS` and
    `ARTIFACTS_ENV` and the guest's `PROTOCOL` are untouched. `git diff --stat` shows 27
    insertions and 27 deletions.
- `README.md`:
  - `## API reference` is added before `## Safety`: a hand-written paragraph with Decision 8's
    promise (two final minor releases), then the generated block.
  - The six spans are rewritten.
  - The pool bound gains its sentence.
- `CHANGELOG.md`: a spec 049 entry under 0.1.0a4 (Added, Changed, the promise).
- `context/README.md`: Decision 13's sentence, written on this branch at the end of the
  `specifications/` bullet (condition C2).

**Seen failing first.**
- Against main `1c0123c`, step 1 (`build/step1-seen-failing.log`): 9 of the 10 checks fail. The
  guard `test_nothing_private_is_re_exported` passes.
  - Criterion 1: "no snapshot: run … --write".
  - Criterion 2: 44 findings: `wasi_python` lacks `Defaults`, `defaults`, `set_defaults` and
    `stats`, and `wasi_python.tools` has no `__all__`.
  - Criterion 3: **29** names. The spec's 20 assumed `tools` already had its `__all__` of 9.
    Without one, all 26 public names of `tools` count, plus `__init__`'s 3.
  - Criterion 5: method docstrings 8 (`FileProvider`'s 3 and 034's 5), `Args` entries 48,
    `Attributes` entries 34, `Raises` 4, spec references 12. Only names already in an `__all__`
    count here, so `Defaults` and `tools` are left out.
  - Criterion 6: 6 hits in docstrings and 6 README spans.
  - Criterion 7: 7 of 94 evaluated annotations fail (`Host` twice, and `Tool`, `ToolCall`, `ToolRecord`,
    which `tools` did not yet export).
  - Criterion 8: `py.typed` is missing.
  - Criterion 9: 0 blocks.
  - Criterion 10: `AttributeError: … no attribute 'defaults'`.
- After step 2's exports and before the docstrings (`build/step2-checks.log`), the counts are
  the spec's, grown by 034:
  - `run` alone: 19 undocumented arguments;
  - 66 public fields without an `Attributes` entry: the spec's 57, plus 034's 9;
  - 9 methods without a docstring: 3, plus 034's 5, plus `Tool.__call__`;
  - 6 `Raises` sections missing;
  - 17 spec references: 14 on the spec's main, plus 034's;
  - 7 docstring hits, the spec's 7, with `Defaults` now public;
  - 6 README spans;
  - 2 of 149 annotations fail (`Host`).
- Criterion 10's one read: the stand-in that kept three reads (`_current_defaults()` called in
  `_checked`, `_check_tools` and `_check_places`) failed with `assert (3, 1) == (1, 1)`
  (`build/step2-three-reads.log`). Then the one-read change passed.

**Acceptance, with evidence.**
1. `test_the_public_api_matches_its_snapshot` passes. Its stand-in is a scratch copy with
   `size: int = 1`. Its diff is exactly `-  field size: int = 0` and `+  field size: int = 1`.
2. `test_public_modules_export_exactly_their_all` passes. `import *` binds the 20 names and the 9.
3. `test_private_names_carry_an_underscore` passes: 0 names.
4. `test_nothing_private_is_re_exported` passes. Its stand-in (`from .runner import _UNSET as
   UNSET`, exported) gives exactly `["wasi_python.UNSET is _UNSET"]`.
5. `test_every_public_name_is_documented` passes: every count is 0. The stand-in counts a
   dataclass whose docstring is generated and a `RuntimeError` subclass with none as
   `["m.Bare", "m.NoDoc"]`.
6. `test_public_docs_name_nothing_internal` passes: 0 docstring hits and 0 README hits, the
   generated block and the new prose included. C1's stand-ins use a synthetic README (`FENCED`):
   - the scanner finds 6;
   - one that pairs backticks naively finds 0;
   - one that blanks only fences at the start of a line finds 3;
   - an indented fence before a bare `` `DEFAULTS.file_calls` `` still counts that span, at
     line 7;
   - a fenced `wasi_python.runner.DEFAULTS = x` is a hit.

   On today's README all three scanners found 6 before this change, so the stand-in must be
   synthetic: 034's text had changed where the backtick counts fell. After 034 the README held
   **51** internal constants and **6** spans (lines 558, 850, 857, 978, 1010, 1239). That
   matches the review's count on 034's branch.
7. `test_public_annotations_resolve` passes. 171 annotations are evaluated (149 and the two overloads' 22) and 0 fail.
   - Overload 1 is `("fn", "positional-only", "Callable[..., Any]", "Tool")`.
   - Overload 2 is `fn: None` and returns `Callable[[Callable[..., Any]], Tool]`.
   - Both take the implementation's keywords.
8. `test_the_package_is_typed` passes, and the marker is tracked. `test_a_wheel_must_carry_py_typed`
   gives exactly `["wasi_python-0-py3-none-any.whl lacks wasi_python/py.typed"]`.
   `uv build --wheel --offline`, run from the cache into the worktree's `build/` and then deleted,
   holds `wasi_python/py.typed`. The v1.1 wheel check itself is blocked here ("wheel").
9. `test_the_readme_reference_matches_the_api` passes: one block, equal to the render. Markers
   inside a fence give `(0, None)`.
10. `test_set_defaults_changes_what_run_reads` passes.
    - `set_defaults` returns the old value.
    - The lock stand-in sees `[("enter", before), ("exit", new)]`, and one enter and one exit per
      call.
    - `_checked` carries the new `memory_bytes`.
    - `None` and `{}` raise `TypeError`.
    - The old value is restored.
    - 0 artifact lookups.
    - `run(…, tools=[noop])` reads the defaults once and `run_async` once.
11. The render is the same on every supported Python. Each command exited 0:
    - `uv run --no-project --offline --python 3.11 python tests/harness/api.py --check` (3.11.14);
    - the same with `--python 3.12` (3.12.12) and `--python 3.13` (3.13.11);
    - `uv run python tests/harness/api.py --check` (3.14.2).

    `--no-project` keeps the worktree's 3.14 venv from being replaced by a 3.11 one. The render
    needs only the standard library and the package's source. `--check` covers both outputs.
12. The update path was run once, in a scratch copy, with `--package`, `--snapshot` and `--readme`
    pointed at copies:
    - `run` gained `throwaway: bool = False`.
    - `--check` exited 1 with one added snapshot line, `+  param throwaway: bool = False
      keyword-only`, and one added signature line in the block.
    - `--write` exited 0, and `--check` then exited 0.
    - The README changed by the signature line and one `Args` entry (`` - `throwaway`: ``).
    - The snapshot changed by that one line.
13. Every existing check passes with the renamed constants. `ruff check` and `ruff format --check`
    are clean on `src` and `tests`. The judge is below: lost 0, grew 0.

**The judge.** The command was `WASI_PYTHON_ARTIFACTS=<main>/build/sets/s-f94dec535086b06c uv run
pytest`, run once, at the end (AGENTS.md rule 3a), on `e700ce8`. Its log is
`build/judge-final.log`:
- `wasi_python v1: 275/286 pass · 0 gap · 11 blocked · 0 fail (unit suite 934/942, 8 skipped)`;
- v1.4 135/135;
- `ratchet vs 01238501f8: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 10 · grew 0 ·
  judge changed: tests/checks/test_v1_4_public_api.py, tests/harness/api.py,
  tests/harness/artifacts.py and 7 more`;
- `1209 passed, 19 skipped`.

Before the build (`build/judge-before.log`, the same set): `265/276 pass · 11 blocked`, `1198
passed, 19 skipped`. The 11 blocked checks are the worktree's own: no source trees, no oracle, no
wheel, no prior-art clones, and one machine instead of three systems. The lane accepts with
`--accept-judge`. The judge change is the new check file, the harness, the snapshot, the wheel
rule, its unit stand-in, and the 27 renamed lines.

**Where the specification was silent, the builder decided.** The reviewer should judge each one:
- *A constant cannot have a docstring of its own.* `PROTOCOL` is an int. The rule chosen: a
  constant must be named in backticks in its module's docstring. The README shows the first
  paragraph that names it.
- *Internal names, for both documents.* A plain assignment counts (`X = …`), and so do a `def`
  and a `class`. Names unpacked together (`EBADF, EIO = 8, 29`) are preview1's own numbers, the
  words a document uses for them, so they do not count. Dunders do not count, and neither do
  `Errno`'s members. Counted this way, the README's constants number 51, the review's count.
  Counting unpacked names gave 81 and flagged `EMFILE` and `O_CREAT`.
- *The docstring rule also catches a span naming `wasi_python.runner|mounts|cli`.* The README rule
  already did. None was found.
- *Criterion 4 also catches `X = _y`*, not only imports.
- *The README reference leaves out the command's entry point.* `wasi_python.cli:main` names an
  internal module, so the README rule refuses it. The snapshot keeps it
  (`command wasi-python = wasi_python.cli:main`).
- *Criterion 10 passes `tools=`.* `_check_tools` reads a default only when tools are given.
  Without them, the three-read stand-in counted 2, not the spec's 3.
- *`Tool.__call__` gets a docstring* and counts among the methods.
- *The reference's "summary" is the docstring's first paragraph.* A class's methods are listed
  under **Methods:**, each with its `Args`. `tool` shows the implementation's signature, then
  each overload.
- *`run`'s and `run_async`'s `Raises:` sections* name `wasmtime.WasmtimeError` and `BaseException`
  as entries: `RUN_RAISES` and `RUN_ASYNC_RAISES` in `api.py`. `run_async` has
  `asyncio.CancelledError` in place of `KeyboardInterrupt`.
- *Exit-code labels* are read by running the command's `main` with a stand-in `run`: 0 a result,
  1 run raised, 2 a usage error, 130 interrupted.
- *The README grew from 1,413 to 2,146 lines* (INFERRED from `wc -l`). The review estimated 300 to
  400 more; the generated block is about 700.

**For the build review.** Look hardest at:
- `runner._checked`: the one read, `_check_places` moved inside, and `checked["async_workers"]`
  passed to `_submit`.
- `set_defaults` and its lock: the module global `_runner.DEFAULTS` is still what `run` reads, so
  `monkeypatch.setattr(runner, "DEFAULTS", …)` keeps working.
- `api.code_spans` and `api.fenced` (C1), and the `FENCED` stand-in.
- `api.sections`, the Google-style parser, written by the harness itself; `tools._HEADINGS` is
  untouched.
- The `Raises:` texts against Decision 6.
- The 034 checklist in the snapshot. Each item appears exactly:
  - `RefusedWrite`'s six fields;
  - `WritableFileProvider`'s five methods;
  - `Mount.writable … kw_only`;
  - `FileRecord.refused` and `refused_total`, last;
  - 20 names.
- The README paragraph's terms against Decision 8 and question 88.
- Every new docstring's claims against the code. These are READ by the builder, not
  machine-checked: the gate's allow/refuse values, `cache_dir=True`, and "within 5 ticks".

**Open items.** None blocks the build:
- The spec's seen-failing counts were written assuming the final `__all__`s. The real counts on
  main are recorded above.
