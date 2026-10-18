# 049 — The public API is frozen and documented

- **Status:** drafted 2026-10-18. Not yet reviewed. It changes neither the guest's imports nor
  its exports, the artifact set nor the build recipe, so §5.6 asks no review before build. One
  is asked for anyway: the promise in Decision 8 binds every later specification that touches
  the package, so a wrong rule here costs more than a wrong line of code.
- **Owner:** Clay Gendron
- **Kind:** the package's two public modules (`src/wasi_python/__init__.py`:
  `__all__`, three renamed constants, `defaults()`, `set_defaults()`, `stats` re-exported, the
  module docstring; `src/wasi_python/tools.py`: `__all__`, eighteen renamed constants, `tool`'s
  two overloads), the docstrings of every public name where it is defined (`runner.py`,
  `mounts.py`, `tools.py`), two annotations (`run`'s and `run_async`'s `host`; `Mount.provider`),
  `src/wasi_python/py.typed` (new, empty), judge additions (`tests/harness/api.py`,
  `tests/public_api.txt`, `tests/checks/test_v1_4_public_api.py`) and a judge change (the
  renamed constants where tests and the harness name them; the wheel rule), `README.md`,
  `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or release workflow.
- **Depends on:** 001 (the runner, `artifacts()`), 013 and 014 (arguments checked first), 015
  (`run_async`, `Defaults.async_workers`), 017 (`Grant`), 019 and 022 (the command line), 028
  (wasmtime a plain dependency, the lazy import), 031 and 036 (`wasi_python.tools`, `tools=`),
  032 (`Mount`, `FileRecord`), 048 (the guard linker): all landed. **034 (writable mounts) is in
  its build review** and adds public names; it and this specification may be built in parallel,
  and whichever lands second rebases onto the other (Decision 13 says exactly what 034's rebase
  adds if this lands first).
- **Research it stands on:** the roadmap's milestone 6, "the public API frozen and documented"
  (`../roadmap.md`); this specification's survey of main at `77bd08e` (EXECUTED, quoted in "The
  problem" and Decision 10: `survey.py`, `probe_annotations.py` and `probe_internal_names.py`,
  run with `uv run python` on Python 3.14.2; the scripts and outputs were kept beside this
  draft, and the lines that matter are quoted here);
  the package's source and `README.md` as they stand (READ); the constitution's §4.13 (no
  dependency without a written reason), §4.15 (a looser default needs the owner) and §5.5 (a
  security fix is a reason to release). The conventions of PEP 8 ("Public and internal
  interfaces": `__all__`, and a leading underscore for what is internal), PEP 561 (`py.typed`)
  and PEP 387 (CPython's own deprecation rule) are used as published; they were not re-read for
  this draft (INFERRED from their known text).

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
- The README sends users into an internal module three times: `wasi_python.runner.DEFAULTS`
  twice (one of them as the way to size `run_async`'s pool, by assigning it) and
  `wasi_python.runner.stats()` once. `run`'s docstring names `BASE_ENV` and `CANCEL_TICKS`,
  constants of that module.
- Every public name has a docstring. None has an `Args:` section; dataclass fields are
  explained by `#` comments, which neither `help()` nor a generated reference can read.
- 106 annotations on public signatures and fields evaluate in a namespace of public and
  standard names; 2 do not: `run`'s and `run_async`'s `host: Host | None`, where `Host` is an
  alias inside `runner.py` (EXECUTED, `probe_annotations.py`: "annotations evaluated: 106
  failed: 2").
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

2. **`wasi_python.__all__` is exactly these 18 names**, sorted:

   | name | what it is | defined in |
   |---|---|---|
   | `Artifacts` | the artifact set's four paths (result) | `__init__.py` |
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
   | `stats` | how this process got its compiled modules; tool threads alive | `runner.py` |

   `__version__` is public too, outside `__all__`, as is usual.

   **`defaults()` and `set_defaults(new: Defaults) -> Defaults` replace assigning
   `wasi_python.runner.DEFAULTS`.** Today the README tells a user to assign an attribute of an
   internal module. Re-exporting `DEFAULTS` would be worse: `wasi_python.DEFAULTS = x` would
   bind a second name that `run` never reads, and do nothing, silently. A function cannot be
   shadowed that way. `set_defaults` raises `TypeError` for anything but a `Defaults` (whose own
   checks have already run), swaps it in, and returns the previous one so a caller can restore
   it. The binding `run` reads stays `runner.DEFAULTS`, internal; so the judge's existing
   `monkeypatch.setattr(runner, "DEFAULTS", …)` keeps working unchanged, and code that still
   assigns it from 0.1.0a4's README keeps working until the internal name changes. The README's
   idiom becomes `set_defaults(dataclasses.replace(defaults(), async_workers=4))`.

   **`stats()` becomes public**, because the README already sends embedders to it to watch
   abandoned tool threads (spec 036). Its keys `compiled`, `loaded`, `written` and
   `tool_threads_running` are promised; a minor release may add keys.

3. **`wasi_python.tools.__all__` is exactly 8 names:** `Tool`, `ToolCall`, `ToolDenied`,
   `ToolError`, `ToolOutcome`, `ToolRecord`, `stubs`, `tool`. A `Tool`'s public attributes are
   `name`, `description`, `fn`, `validates_input`, `timeout_s`, `read_only`, `destructive`,
   `idempotent`, `open_world`, the properties `input_schema` and `output_schema`, the method
   `descriptor()`, and calling it. Only `tool()` makes one (spec 031), so its field order is not
   promised. The eighteen constants become private (Decision 4). Most are protocol 1's bounds,
   documented in the README's "The tool protocol" and fixed by the protocol's number; the rest
   (`MAX_ABANDONED`, `DEADLINE_MARGIN_TICKS`) are the runner's own policy, documented in
   "Tools" (spec 036). An embedder reads the numbers there, not from the host's module.

4. **Private means a leading underscore, in a public module.** Every module-level name that
   `__init__.py` or `tools.py` binds (by a `def`, a `class`, an assignment, or an import from
   inside the package, such as `from . import runner as _runner`) and that is not in its
   `__all__` starts with `_`. Imports from outside the package (`os`, `dataclass`) and dunders
   are exempt. So `ARTIFACT_DIR`,
   `ARTIFACTS_ENV` and `CHECKOUT_ARTIFACT_DIR` become `_ARTIFACT_DIR`, `_ARTIFACTS_ENV` and
   `_CHECKOUT_ARTIFACT_DIR`, and each of the eighteen constants in `tools.py` gains a `_`
   (`TOOL_REQUEST_BYTES` becomes `_TOOL_REQUEST_BYTES`, and so on). The renames are mechanical;
   every reference in `src/`, `tests/` and `tests/harness/` follows them, which is a judge
   change (about 35 lines in `tests/`, by `grep -w`: `ARTIFACTS_ENV` 7, `KINDS` 6,
   `TOOL_REQUEST_BYTES` 5, `ARTIFACT_DIR` 4, `TOOL_VALIDATION_STEPS` 4, and fewer for the
   rest). The guest package's own
   `PROTOCOL` in `recipes/guest/` is a different module's name and does not change.
   - **Nothing private is re-exported.** A name in a public `__all__` is public where it is
     defined too: `from .runner import _run as run` is refused, so a public name is never an
     alias for an internal object whose name says it may change.
   - **When in doubt, private.** A private name can be made public in any minor release at no
     cost. A public name can be removed only through a deprecation (Decision 8). So the
     surface starts small.

5. **The signatures and fields, frozen as they stand, with three changes.** The snapshot
   (Decision 9) records them all; this list says what each shape promises.
   - `run(argv, *, …)` and `run_async(argv, *, …)`: every argument after `argv` is
     keyword-only, so a new one can be added without breaking a call. A default shown as
     `<default>` means "read from `defaults()` when the call is made". `run_async` takes `run`'s
     arguments except `cancel`, plus `executor`.
   - **Change 1:** `host`'s annotation becomes `Callable[[bytes], bytes] | None`, written out,
     in both. `Host` stays an internal alias. A public signature names only public and standard
     names (Decision 12).
   - **Change 2:** `Mount.provider` is annotated `FileProvider` instead of `Any`. Nothing at run
     time changes: `run` checks a provider by its methods, as today. 034's
     `WritableFileProvider` is a sub-protocol, so it fits.
   - **Change 3:** `tool` gains two `typing.overload` declarations: `tool(fn: Callable[..., Any],
     /) -> Tool` and `tool(*, name=…, …) -> Callable[[Callable[..., Any]], Tool]`. The
     implementation is unchanged. A checker then knows `@tool` makes a `Tool`.
   - **Two kinds of dataclass.** Users make `Grant`, `Mount`, `Stat` and `Defaults` (the last
     through `dataclasses.replace`). For these the order of the existing fields is promised,
     since a user may pass them by position. The runner makes the rest (`Artifacts`,
     `Completed`, `FileFault`, `FileRecord`, `ToolCall`, `ToolOutcome`, `ToolRecord`); a user
     reads them. For these the field names and types are promised, not construction by
     position. Every public dataclass is frozen, and stays frozen.
   - **`Completed.trapped`** is `None`, or one of four fixed strings, `"out of fuel"`,
     `"deadline"`, `"cancelled"`, `"out of file calls"`, or a trap's plain name or an error's
     first line as wasmtime gives it. The four are promised; wasmtime's words are not.
   - **`ToolOutcome.outcome`** is `"ok"` or one of the protocol's kinds, listed in the README.
     The kinds belong to protocol 1 and change only with the protocol's number.
   - **`Errno`**'s members and numbers are promised. The set is closed today (spec 032); adding
     a member is an addition.
   - The values of `defaults()` when the package is imported are recorded too: 1 GiB of memory,
     a 60 s deadline, 16 MiB of output, 10,000 file calls, 1,000 tool calls, and
     `async_workers` from the machine's CPU count (recorded as `<factory>`, because it depends
     on the machine).

6. **Exceptions are promised by type, never by message.** The public classes are
   `ArtifactsMissing` (a `RuntimeError`), `ToolError` and `ToolDenied` (a `ToolError`). `run`
   and `run_async` raise, before any work: `TypeError` or `ValueError` for a bad argument;
   `ArtifactsMissing` when there is no artifact set; `ImportError` when wasmtime-py cannot load
   (its own error chained, spec 028). After work starts: `RuntimeError` in a process forked
   after a guest ran, and for `run_async` after interpreter shutdown; `KeyboardInterrupt` for
   Ctrl-C (`run`); `asyncio.CancelledError` when the awaiting task is cancelled (`run_async`).
   Nothing a guest, a provider or a tool does makes either raise (specs 006, 032, 036). A new
   failure is raised as one of the types the function already documents, or as a new subclass
   of one, so an existing `except` still catches it. Messages may change in any release.

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
     incompatibly only what an earlier final minor release deprecated.
   - **A deprecation** is announced in three places at once: a `DeprecationWarning` where the
     deprecated thing is used (with `stacklevel` pointing at the caller's line); the docstring's
     first line, "Deprecated since 0.N: use X instead.", which the README's reference then
     shows; and a "Deprecated" line in the CHANGELOG. The thing keeps working for at least one
     final minor release. Its removal is a "Removed" line in the CHANGELOG.
   - **Defaults' values.** A tighter default (a smaller limit) may come in a minor release, as a
     "Changed" line. A looser one needs the owner's decision (§4.15). Either is a visible
     snapshot change.
   - **Security.** A change that closes a hole may break the surface in any release, without a
     deprecation, named under "Security" in the CHANGELOG (§5.5 makes a security fix a reason
     to release). This is the only exception.
   - **Not promised:** exception messages; `repr`s; help text; internal modules and names;
     wasmtime's trap names; timings; fuel counts, which follow the guest's code; the `.cwasm`
     cache's layout; and the guest's contents (package versions are release policy, spec 004).
     The door's ABI and the tool protocol carry their own contracts: the door is the
     constitution's (§4.4), and the protocol is versioned by its number.
   - **At 1.0** the same rules hold with "major" in place of "minor". When 1.0 comes is the
     owner's decision, not this specification's.

9. **A machine-checked snapshot of the surface: `tests/public_api.txt`.** It is a judge file
   (under `tests/`), so any change to the public API changes the judge's hash and shows in
   review as a judge change. It is written by `tests/harness/api.py` (`uv run python
   tests/harness/api.py --write`; `--check` verifies and exits 1 on a difference), which renders
   the live surface as plain text, one fact per line, so a change is a small diff:
   - per public module, in `__all__` order: each name's kind (`def`, `async def`, `class`,
     `dataclass`, `protocol`, `enum`, `exception`);
   - a function: one line per parameter with its kind (positional, keyword-only), its
     annotation as written, and its default's `repr`; then the return annotation; for `tool`,
     each overload's parameters too (`typing.get_overloads`);
   - a dataclass: `frozen`, then one line per public field (no leading `_`) with its annotation,
     its default (`required`, a `repr`, or `<factory>`) and `kw_only`;
   - a class: its public bases; each public method and property defined on it, with its
     parameters; an enum's members and values; an exception's base;
   - `defaults()`'s values on import; `stats()`'s keys; the protocol's outcome kinds; the two
     environment variables' names;
   - the command: its entry point from `pyproject.toml`, each option of the parser with its
     action and metavar, and the JSON keys of a result and of an error, read by running the
     command's `main` with a stand-in `run` (as `tests/unit/test_cli.py` does).

   The render is built from `inspect.Parameter`, `dataclasses.fields` and `ast`, never from
   `str(inspect.Signature)`, whose quoting differs between Python versions, so the file is the
   same on every Python the package supports (3.11 and up). It runs in a child interpreter, so
   nothing a test changed in the judge's process (a patched `runner.DEFAULTS`) reaches it. On a
   difference the check prints the unified diff and the `--write` command.

10. **Every public name is documented, and the check says what is missing.** In Google style,
    the style `tool()` already reads for a tool's description (spec 031):
    - every name in both `__all__`s, and every public method and property defined on a public
      class (`FileProvider.stat`, `list`, `read`; `Tool.descriptor`, `input_schema`,
      `output_schema`), has a docstring;
    - every parameter of a public function or method is described in its `Args:` section;
    - every public field of a public dataclass is described in its class docstring's
      `Attributes:` section; the `#` comments that describe fields today move there;
    - `run`, `run_async`, `artifacts`, `artifact_dir`, `set_defaults` and `tool` have a
      `Raises:` section, and `run`'s and `run_async`'s name at least `TypeError`, `ValueError`
      and `ArtifactsMissing`;
    - an argument `run` and `run_async` share is described by the same text in both, so the
      two cannot drift;
    - the first paragraph (the summary) is written for a user: it names no specification;
    - **no public document names an internal name.** A backticked token in a public docstring
      or in the README that is a module-level name of an internal module, and not a public
      name, fails the check; so does any `wasi_python.runner`, `wasi_python.mounts` or
      `wasi_python.cli` in the README. Today that is 7 docstring hits and 3 README hits
      (EXECUTED, `probe_internal_names.py`): `run`'s `DEFAULTS` (three times), `BASE_ENV` and
      `CANCEL_TICKS`; `run_async`'s and `Defaults`' `DEFAULTS`; the README's
      `wasi_python.runner.DEFAULTS` twice and `wasi_python.runner.stats()` once. `DEFAULTS`
      becomes `defaults()`, and the two constants become the values they hold. The README is
      checked for these dotted references only, because ordinary words such as `main` are also
      internal names.

11. **The README's reference is generated from the same render.** A new `## API reference`
    section, before `## Safety`, opens with a short hand-written paragraph: what is public,
    that everything else is internal, and Decision 8's promise in four sentences. Below it, a
    block between `<!-- api reference: begin (generated by tests/harness/api.py) -->` and
    `<!-- api reference: end -->` holds, for each public name: a fenced signature (or a
    dataclass's fields), its summary, and its `Args:`, `Attributes:` and `Raises:` as lists;
    then the command's options and exit codes. `--write` rewrites the block; the check compares
    it with the render. The README's prose elsewhere keeps teaching; it no longer has to carry
    every argument, but it is not cut by this specification.

12. **Type hints: `py.typed` ships, and no type checker is added.**
    - `src/wasi_python/py.typed`, empty (PEP 561), is in the wheel; hatchling takes it as a
      package file, and the wheel rule (`tests/harness/artifacts.py`, `wheel_errors`) requires
      it.
    - Every public parameter, return value and dataclass field is annotated, and every
      annotation evaluates in a namespace holding only the builtins, `typing`'s and
      `collections.abc`'s names, `os`, `threading`, `concurrent.futures`, `pathlib.Path`, and
      the public names of both modules. That catches a missing annotation, a misspelt one and an
      internal name (`Host` today), with no new tool.
    - **No mypy or pyright in the dev group.** §4.13 asks a written reason for any dependency,
      and the reason is missing: a consumer's type checker reads only the package's public
      signatures, which the check above covers. Checking the internals strictly (6,000 lines,
      much of it ctypes and wasmtime-py values typed `Any`) would be a project of its own that
      changes nothing a consumer sees. If a consumer ever meets a typing defect the check
      missed, that defect becomes a check (AGENTS.md, rule 3), and a checker is added then, with
      its reason.

13. **How later specifications change the API.** A specification that adds, removes or
    changes anything the snapshot records:
    - says so in its **Kind** line ("changes the public API") and lists, in a Decision, the
      snapshot lines it adds, removes or changes;
    - documents what it adds to Decision 10's rules, regenerates `tests/public_api.txt` and the
      README block with `--write` in its own branch, and adds a CHANGELOG line under Added,
      Changed, Deprecated or Removed;
    - is reviewed with the snapshot's diff in view; the reviewer checks that the diff is
      exactly the listed lines, and that Decision 8 allows it for the next release;
    - lands with `--accept-judge`, as any judge change does.

    A change the snapshot shows but no specification lists is a finding. **Spec 034**, if this
    one lands first, rebases and adds exactly: `RefusedWrite` (a frozen dataclass: `mount`,
    `method`, `paths`, `errno`, `at`, `cause`) and `WritableFileProvider` (a protocol, a
    `FileProvider` with `write`, `mkdir`, `remove`, `rmdir`, `rename`) to `wasi_python.__all__`;
    `Mount.writable: bool = False`, keyword-only; `FileRecord.refused: tuple[RefusedWrite, ...]
    = ()` and `FileRecord.refused_total: int = 0`, last. Each comes with its docstring,
    `Attributes:` and `Args:` as Decision 10 asks, and a README block regenerated. 034's text
    already places the new fields last and the new flag keyword-only, so Decision 8's rules for
    a minor release hold without change. If 034 lands first, this specification's snapshot
    simply includes them.

14. **No version bump here.** The snapshot carries no version number. The CHANGELOG's
    unreleased section gains: Added, `defaults()`, `set_defaults()`, `stats()` at the top level,
    `py.typed`, and the API reference; Changed, the eighteen `wasi_python.tools` constants and
    three `wasi_python` constants are private, and the README no longer names
    `wasi_python.runner`; and a line stating Decision 8's promise and that it starts at 0.1.0.

## Intent

An embedder can tell from one page which names they may rely on. Any change to those names, or
to their signatures, fields or defaults, fails the judge until a specification lists it and a
review sees it.

## Design

```
src/wasi_python/__init__.py      __all__ (18); _ARTIFACT_DIR, _ARTIFACTS_ENV,
                                 _CHECKOUT_ARTIFACT_DIR; defaults(), set_defaults();
                                 stats re-exported; the module docstring names the public
                                 surface and says the rest is internal
src/wasi_python/tools.py         __all__ (8); eighteen constants gain "_"; tool's overloads;
                                 docstrings with Args/Attributes
src/wasi_python/runner.py        docstrings of Completed, Defaults, Grant, run, run_async,
                                 stats (Args, Attributes, Raises; no internal names); host's
                                 annotation written out
src/wasi_python/mounts.py        docstrings of Errno, Stat, FileProvider and its methods, Mount,
                                 FileFault, FileRecord; Mount.provider: FileProvider
src/wasi_python/py.typed         new, empty
tests/harness/api.py             the render, --write and --check (Decisions 9 and 11)
tests/public_api.txt             the snapshot
tests/checks/test_v1_4_public_api.py   the checks below (goal v1.4; no artifacts needed)
tests/harness/artifacts.py       wheel_errors requires wasi_python/py.typed
tests/ (several files), tests/harness/paths.py   the renamed constants
README.md                        ## API reference; three internal references replaced
CHANGELOG.md                     the unreleased section
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
command wasi-python = wasi_python.cli:main
  option --grant GUEST=HOST  append
```

The builder works in this order: the render and its checks first, each seen failing against
main; then the renames; then the docstrings, name by name, until the documentation check's count
of missing items is 0; then `py.typed`, the annotations and the overloads; then the README block
and `--write`.

## Scope

In: the above. Out: renaming the internal modules; a documentation site or Sphinx; the guest
side's API (`from host import tools`, the stdlib inside the guest), which the tool protocol's
number and the README govern; a strict type check of the internals; deciding when 1.0 comes;
changing any behaviour of `run`. The README's prose sections stay as they are apart from the
three references Decision 10 removes.

## Acceptance criteria

Every check is in `tests/checks/test_v1_4_public_api.py` (goal v1.4), needs no artifact set,
and is seen failing first against main as it stands at build time. Nothing measures time; each
check counts names, lines or items, and its failure message gives the counts and the first
items.

1. **`test_the_public_api_matches_its_snapshot`**: the render, made in one child interpreter,
   equals `tests/public_api.txt`. Seen failing first: with no snapshot file ("no snapshot:
   run … --write"). Stand-in: in a scratch copy of the package, `Stat.size`'s default changed to
   1; the check fails, and its diff is exactly one removed and one added line, both naming
   `size`.
2. **`test_public_modules_export_exactly_their_all`**: each `__all__` is sorted, has no
   duplicate, names no `_` name, and every name in it resolves; `from wasi_python import *`
   binds exactly the 18 names and `from wasi_python.tools import *` exactly the 8. Seen failing
   first: `wasi_python.tools` has no `__all__`, and `wasi_python` lacks `defaults`,
   `set_defaults` and `stats`.
3. **`test_private_names_carry_an_underscore`**: by `ast`, every name `__init__.py` or
   `tools.py` defines and does not export starts with `_`. Seen failing first: it lists 21
   names (3 and 18).
4. **`test_nothing_private_is_re_exported`**: by `ast`, no import in a public module binds a
   name in its `__all__` from a name that starts with `_`. A guard: it passes on main.
   Stand-in: `from .runner import _UNSET as UNSET`, with `UNSET` added to `__all__`, in a
   scratch copy of `__init__.py`, fails it with that one name.
5. **`test_every_public_name_is_documented`**: Decision 10's rules, each a count of what is
   missing (docstrings, `Args:` entries, `Attributes:` entries, `Raises:` sections, shared
   arguments whose text differs). Every count is 0. Seen failing first: on main, `run` alone
   has 19 undocumented arguments, and 57 public fields (from the survey's field lists,
   `Defaults` and `Tool`'s public fields included) have no `Attributes:` entry.
6. **`test_public_docs_name_nothing_internal`**: Decision 10's last rule; the count of hits in
   docstrings and the count in the README are both 0. Seen failing first: 7 and 3, as listed
   there.
7. **`test_public_annotations_resolve`**: every public annotation evaluates in Decision 12's
   namespace; the count evaluated is reported, and the count that fails is 0; `tool` has
   exactly two overloads. Seen failing first: 2 of 106 fail (`Host`), and `tool` has none.
8. **`test_the_package_is_typed`**: `src/wasi_python/py.typed` exists and is tracked. Seen
   failing first. The v1.1 check `test_wheel_carries_the_artifact_set` now also fails a wheel
   without `wasi_python/py.typed`; stand-in: a synthetic wheel without it (as
   `tests/unit/test_checks_wiring.py` builds them) fails with that one line.
9. **`test_the_readme_reference_matches_the_api`**: the README has exactly one block between
   the two markers, and it equals the render. Seen failing first: no block.
10. **`test_set_defaults_changes_what_run_reads`** (unit, no artifacts): `set_defaults` with a
    `Defaults` whose `memory_bytes` differs returns the previous one; `run`'s argument check
    (`runner._checked`, given no limits) then carries the new value; `defaults()` returns it;
    `set_defaults(None)` and `set_defaults({})` raise `TypeError`; the previous value is
    restored. Zero artifact lookups, counted as spec 036's criterion 1 counts them. Seen failing
    first: the names do not exist.
11. **The render is the same on every supported Python.** The builder runs `uv run --python 3.11
    python tests/harness/api.py --check` and the same with the dev environment's Python (3.14
    today); both exit 0. The commands and outputs go in the landing notes (§4.10). Not a check:
    the judge does not fetch interpreters.
12. **The update path works once, end to end.** In a scratch copy, the builder adds a throwaway
    keyword argument to `run`; criterion 1 fails with a diff of one added line; `--write` makes
    it pass and changes the README block by one entry. Recorded in the landing notes, not kept.
13. Every existing check passes with the renamed constants; `ruff check` and `ruff format
    --check` are clean; `uv run pytest` is green with `--accept-judge`; lost 0; grew 0 (the
    artifact set does not change).

## The owner's choices

Nothing waits on the owner for build. One choice is the agent's where the owner's decisions are
silent, and it is written for the owner in `questions.md` beside this draft (the lane numbers it
in `../questions-for-the-owner.md`): Decision 8's promise, its terms and that it starts at
0.1.0. The README states the promise, so the owner's answer is wanted before 0.1.0 is tagged.
An answer that changes the terms changes Decision 8 and one README paragraph, nothing else.

## Landing notes

Not built.
