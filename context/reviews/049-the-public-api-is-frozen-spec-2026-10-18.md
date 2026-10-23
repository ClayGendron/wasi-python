# Review of spec 049 before build: the public API is frozen and documented

- **Reviewed:** `context/specifications/049-the-public-api-is-frozen.md` as drafted at `ff8cfb2` (main). This is a voluntary pre-build review. §5.6 does not require one, because the spec changes no guest import or export, no artifact and no recipe. The spec asks for one anyway.
- **Reviewer:** a fresh agent (Claude Opus 5.5). It did not write the specification or the survey.
- **Read:** `AGENTS.md`; the constitution (§3, §4.5, §4.9, §4.10, §4.13–§4.15, §5.2, §5.4–§5.7, §6); owner question 88 in `context/questions-for-the-owner.md`; the drafter's survey (`survey.py`, `probe_annotations.py`, `probe_internal_names.py` and their outputs, beside the draft in the scratchpad); `src/wasi_python/__init__.py`, `tools.py` (head, `tool`), `runner.py` (`Defaults`, `DEFAULTS`, `Completed`, `Grant`, `run`, `run_async`, `_submit`, `_checked`, the `raise` sites), `mounts.py` (`Errno`, `FileProvider`), `cli.py` (`_parser`, `main`); `README.md` (every `DEFAULTS` and `wasi_python.runner` line, the Grants and Safety passages on exceptions, the tools examples); `pyproject.toml`; `.gitattributes`; `.github/workflows/release.yml` (its Python and OS matrix); `tests/harness/paths.py` (`JUDGE_PATHS`, `judge_files`) and `artifacts.py` (`wheel_errors`); every test line that names a constant to be renamed; spec 034's branch `spec/034-writable-mounts` at `9822812`, its diff against main and its build review; `context/roadmap.md` (milestone 6, the agent-runtime features).
- **Executed** (scripts in this folder, `uv run` only, nothing in the repository changed):
  - `determinism.py`, run with `uv run --no-project --python 3.11|3.12|3.13|3.14`. It renders every public parameter (kind, annotation, default `repr`), every dataclass field and every `Errno` member. Output, shortened: `3.11.14 sig sha 8714031ef100 raw __doc__ sha 871466297d5a cleandoc sha e5eccc615a8d`, `3.12.12 … 8714031ef100 … 871466297d5a … e5eccc615a8d`, `3.13.11 … 8714031ef100 … 8565a192242a … e5eccc615a8d`, `3.14.2 … 8714031ef100 … 8565a192242a … e5eccc615a8d`. `diff sig-311.txt sig-314.txt` prints nothing. On every version, an undocumented dataclass gets `__doc__ == "NoDoc(a: int, b: 'str | None' = None)"`. On every version, `inspect.getdoc` of an undocumented `RuntimeError` subclass returns `"Unspecified run-time error."`.
  - `probe_internal_full.py` repeats the drafter's internal-name probe more widely: all 18 tools constants, the three `__init__` constants, both module docstrings and method docstrings. It finds `docstring hits: 7`, the same seven the spec lists, and `spec references in public docstrings (all paragraphs): 14`.
  - `probe2.py` found the following. All 12 public dataclasses are frozen. `Defaults(…, file_calls=None)` is accepted. `stats()` gives `{'compiled': 0, 'loaded': 0, 'written': 0, 'tool_threads_running': 0}` without importing wasmtime. `FileProvider.stat/list/read` and `Tool.__call__` have no docstring.
  - A short inline run (`uv run python -c …`) shows that `Defaults` accepts `None` for `memory_bytes`, `deadline_s`, `output_bytes`, `tool_calls` and `file_calls`.
  - `readme_probe.py`: a rough count of backticked README tokens that are internal module-level names. It is used only to show that a general rule would be noisy (`os` 18, `EPERM` 5, …).
  - `grep -rnwE` over `tests scripts src recipes .github pyproject.toml` for the 21 names to be renamed found 38 lines (listed in F10).
  - I did not run the judge (`uv run pytest`). Nothing has been built, and this review judges a design.

A term used below. A **render** is the plain-text description of the public surface that `tests/harness/api.py` would print (Decision 9). The snapshot file and the README block are both made from it.

## Findings, most severe first

### F1 (medium). `tool`'s first overload rejects the README's own call form

**Evidence (READ).** Change 3 declares `tool(fn: Callable[..., Any], /) -> Tool` and `tool(*, name=…, …) -> Callable[[Callable[..., Any]], Tool]`. The README calls `tool` with a function *and* keywords:

- `README.md:876`: `return tool(call, name=lc_tool.name, description=lc_tool.description, …`
- `README.md:901`: `return tool(call, name=listed.name, description=listed.description or "", …`

The judge does the same: `tests/unit/test_tools.py:235–259` has `tool(square, input_schema=…)` and `tool(square, timeout_s=…)`. Neither overload accepts that form. Once `py.typed` ships, every type checker rejects the README's MCP and LangChain adapters. The implementation's `fn` is also positional-or-keyword (`tools.py:211`), so `tool(fn=f)` works at run time. The `/` would declare a narrower promise than the code keeps, and it would freeze that promise.

**Fix.** Write the overloads as:

- `tool(fn: Callable[..., Any], /, *, name: str | None = None, …) -> Tool`
- `tool(fn: None = None, /, *, name: …, …) -> Callable[[Callable[..., Any]], Tool]`

Then decide in Decision 5 whether `fn=` by keyword is promised. The reviewer suggests it is not: keep the `/`, and say so. Criterion 7 should also evaluate each overload's annotations, not only count them.

### F2 (medium). Frozen annotations are narrower than the values `run` accepts

**Evidence (EXECUTED and READ).** `Defaults.memory_bytes: int`, `deadline_s: float`, `output_bytes: int` and `file_calls: int` all accept `None` (EXECUTED above). The README says "pass `None` for no limit" (`README.md:1081`). Under `py.typed`, a checker would reject `set_defaults(dataclasses.replace(defaults(), deadline_s=None))`, which is the spec's own idiom with a `None`. Only `tool_calls` says `int | None`.

The same problem affects Change 1. It writes `host` as `Callable[[bytes], bytes] | None`, but `run` accepts any of `bytes | bytearray | memoryview` from a host (`runner.py:2605`). Decision 12's check only tests that an annotation *evaluates*, so it cannot see either defect.

**Fix.** Add a fourth change: annotate the five `Defaults` limits as `int | None` or `float | None`. Write `host` as `Callable[[bytes], bytes | bytearray | memoryview] | None`. Each change is one line and changes no behaviour. Fixing these after 0.1.0 would change a frozen field type, and Decision 8 does not clearly allow that as an addition.

### F3 (medium). The README check misses the bare `DEFAULTS`, and the Scope keeps three of them

**Evidence (READ).** Decision 10 checks the README only for dotted `wasi_python.runner|mounts|cli` references. Three more lines name the internal binding with no module prefix:

- `README.md:533` `` `DEFAULTS.file_calls` ``
- `README.md:690` `` `DEFAULTS.async_workers` ``
- `README.md:818` `` `DEFAULTS.tool_calls` ``

Line 697's `dataclasses.replace(DEFAULTS, …` goes away with the dotted rewrite. The other three survive. The Scope says "the README's prose sections stay as they are apart from the three references", so the builder may not touch them. After this spec, `wasi_python.DEFAULTS` does not exist. A user who reads `DEFAULTS.file_calls` has nothing to type.

**Fix.** Count `DEFAULTS` as a fourth README pattern, matched as the backticked token `DEFAULTS` with or without a dot. The README count seen failing first becomes 6, not 3. Replace each with `defaults().file_calls` and so on, and widen the Scope to cover them. More generally, the README rule can name every upper-case module-level constant *defined* (not imported) in an internal module, minus `Errno`'s member names. That does not collide with ordinary words such as `main`.

### F4 (medium). Decision 6's list of exceptions is incomplete, and Decision 8 then freezes it

**Evidence (READ).** Decision 6 says that once work starts, `run` raises only `RuntimeError` (a fork, or shutdown), `KeyboardInterrupt` or `CancelledError`. It also says "nothing a guest, a provider or a tool does makes either raise". The code and the README say more:

- `README.md:438–439`: a swapped folder raises `RuntimeError`, and a folder removed before wasmtime opens it raises **wasmtime's `WasmtimeError`**.
- `runner.py:632` raises `FileExistsError` and `runner.py:1321` raises `NotADirectoryError` while a root is prepared. `runner.py:1248/1253` raise `ctypes.WinError` (an `OSError`). `runner.py:1436/1545/2007` raise `RuntimeError` for a changed zip copy, a changed folder and "lost track of a call".
- `README.md:1101–1103`: "a `BaseException` that is not an `Exception` is raised" from a provider, and the same holds for a door host. So host code can make `run` raise.

Decision 6 also says "a new failure is raised as one of the types the function already documents". With that rule, the undocumented `OSError` and `WasmtimeError` are either a broken promise on day one, or a change that needs a deprecation later.

**Fix.** Write the list as it is, with no change in behaviour (the Scope rules that out):

- `OSError`, for a host filesystem failure while preparing the root, the private folders or the cache;
- `RuntimeError`, for a folder or zip that changed between its check and its use;
- `wasmtime.WasmtimeError`, while the runner lets it through. Promise it only as "an error from wasmtime-py", or say that it is not promised;
- any `BaseException` that is not an `Exception`, raised by the embedder's own `host`, provider, tool or gate, propagates.

Change "nothing a guest, a provider or a tool does" to "no `Exception` a provider or tool raises, and nothing a guest does". The `Raises:` sections in Decision 10 should then name the same types.

### F5 (medium). Docstrings are not deterministic across Python versions as a render would read them

**Evidence (EXECUTED).** Decision 9 makes the *signature* render version-proof, and that holds: the same SHA on 3.11 to 3.14. But the README block (Decision 11) is built from docstrings. Raw `__doc__` differs between 3.12 and 3.13 (`871466…` against `8565a1…`), because 3.13 strips the indentation when it compiles. `inspect.cleandoc` gives the same text on all four versions.

Two more traps would make criterion 5 pass on an undocumented name:

- A dataclass with no docstring gets the auto-generated `__doc__` `"NoDoc(a: int, …)"`. That text also prints annotations in a version-dependent form.
- `inspect.getdoc` inherits a base class's docstring: `"Unspecified run-time error."`.

The spec does not pin how docstrings are read, or whether `api.py --check` covers the README block. Criterion 11 runs only `--check` on 3.11.

**Fix.** Decision 9 should say three things:

1. Docstrings are read as `inspect.cleandoc(vars(obj).get("__doc__") or "")`, or with `ast.get_docstring` from the source.
2. A dataclass whose `__doc__` starts with `f"{cls.__name__}("` counts as undocumented.
3. `--check` compares both the snapshot and the README block, so criterion 11 covers both.

Also pin how annotations are read. Use the stored string, which the `from __future__ import annotations` in every public module guarantees, and assert that import in the render. On 3.14, `inspect.signature` without it evaluates annotations, and the names imported under `TYPE_CHECKING` (`Tool`, `ToolCall`, `ToolRecord` in `runner.py:55`) would raise `NameError`.

### F6 (medium). Order with spec 034: build after it, not beside it

**Evidence (READ).** 034 is past its build review and has been revised (`9822812`). Its worktree still has uncommitted changes. Its diff rewrites `run`'s docstring (`runner.py:285–291`), and that rewrite keeps `DEFAULTS.file_calls`. It also adds `WritableFileProvider`, `RefusedWrite`, `Mount.writable` and two `FileRecord` fields, and 172 README lines. 049 rewrites the same docstrings (`run`, `Mount`, `FileRecord`, `FileProvider`) and the README.

034's new public docstrings put the spec number in the summary line. For example, `WritableFileProvider`'s first line is "A writable mount's provider (spec 034, for type checkers)". That breaks Decision 10's summary rule. Decision 13's "if this lands first" path therefore makes a reviewed 034 grow by about 16 documented items, a regenerated README block and a snapshot diff. 034 would then need its review again.

**Fix.** Say in Depends on and Decision 13 that **034 lands first**. 049 starts from main after that. It may build its render and checks (Decisions 9 and 11, criteria 1–4 and 7–9) before then, because those touch only `tests/`. Its docstring pass waits. Keep the "rebases and adds exactly" list as the reviewer's checklist for the snapshot diff, not as 034's work.

### F7 (medium-low). `set_defaults` with threads and `run_async`: three reads, a racy swap, and pools that overlap

**Evidence (READ).**

- One call reads `DEFAULTS` three times: `_checked` (`runner.py:817`), `_check_tools` (`:882`) and `_check_places` (`:975`). A `set_defaults` on another thread between those reads gives one call a mix of the old and new limits. It can do this today by assignment, but now it is the blessed API.
- "Returns the previous one" is a read followed by a write. Two threads that race can both get the same "previous" value and lose a restore.
- `_submit` (`runner.py:438–445`) builds a new pool when `async_workers` changes, and calls `shutdown(wait=False)` on the old one. Both the old pool's running calls *and its queued calls* still run. So after shrinking from 8 to 4, up to 12 guests can run at once. The README's "8 workers bound one process at about 8.3 GiB" is then briefly false.

`run_async` checks its limits on the caller's thread when it is called. That part is sound.

**Fix.** State the rule in Decision 2: "a call reads the defaults once, when it is made; a call already made keeps what it read". Make `_checked` take the one read and pass it to `_check_tools` and `_check_places`. That keeps behaviour on one thread and is a small runner change, so name it in the Scope. Do the swap in `set_defaults` under a lock. Have the `set_defaults` docstring (`Args:` and a note) say that a new `async_workers` applies to calls submitted afterwards, and that calls already queued on the old pool still run there. Criterion 10 can count the reads: one `DEFAULTS` read per call, through a stand-in object that counts attribute reads.

### F8 (low-medium). Decision 8 contradicts itself, and its process rule has no home that later drafters read

**Evidence (READ).** "Security … This is the only exception." But a few lines earlier, "a tighter default (a smaller limit) may come in a minor release". That is an incompatible change without a deprecation, so it is a second exception. A program that ran in 50 s breaks when the deadline drops to 30 s.

Decision 13 binds "every later specification" with a Kind-line phrase and a CHANGELOG rule. It is written only inside 049, so a drafter who never reads 049 never sees it. Question 88 also leaves out options the owner should see:

- where the promise is recorded (the constitution §5, the roadmap, or this spec);
- that the command line and its JSON keys are frozen too;
- that `stats()` keys are promised.

The "Owner's choices" text still says the question is in a `questions.md` beside the draft. It is already question 88 on main (`questions-for-the-owner.md:433`).

**Fix.**

- Name two exceptions: security, and a tighter default in a minor release, as a "Changed" line.
- Copy Decision 13's rules into `context/README.md`'s specification stage, or into the checked specification header (`test_specifications_have_their_header_and_sections`), so they bind by where they live.
- Add the record-it-where choice and the CLI line to question 88.
- Bring the stale sentence up to date.

### F9 (low). `Artifacts` is made by users, so its field order is promised

**Evidence (READ).** Decision 5 counts `Artifacts` among what "the runner makes". But `run(artifacts=…)` takes one, and the judge builds one by position: `tests/checks/test_v1_2_hostile_guest.py:239` has `wasi_python.Artifacts(probe, real.plain, real.stdlib_zip, real.manifest)`. So does `tests/unit/test_runner_tools.py:155`.

**Fix.** Move `Artifacts` to the user-made group, which promises field order.

### F10 (low). The rename count is off, and a blind `grep -w` would rename names that are not the package's

**Evidence (EXECUTED).** `grep -rnwE` over `tests scripts src recipes .github pyproject.toml` for the 21 names gives 38 lines. These are not renames:

- `tests/harness/wasm.py:15,144,149`: the harness's own `KINDS`, a wasm section table;
- `tests/harness/paths.py:37,92` and `tests/unit/test_checks_wiring.py:20`: the harness's own `ARTIFACTS_ENV`;
- `recipes/guest/host/__init__.py:9,62` and `recipes/guest/host/tools.py:18`: the guest's `PROTOCOL`, which the spec excludes.

The real renames are about 25 lines:

- `tests/test_api.py`: 8 lines;
- `tests/harness/paths.py:5,99`;
- `tests/unit/test_runner_tools.py`: 3 lines;
- `tests/unit/test_guest_tools.py`: 4 lines (`T.PROTOCOL`, `T.KINDS` ×3);
- `tests/unit/test_tools.py`: 11 lines, one of them a docstring.

The spec's "about 35" and "`KINDS` 6, `ARTIFACTS_ENV` 7" count the harness's own names (§4.10). No `scripts/`, `.github/` or `src/` file outside `tools.py` and `__init__.py` names them. That supports "not build-class".

**Fix.** List the files and lines. Tell the builder to rename by module-qualified references (`T.`, `wasi_python.`), never with a word-boundary replace.

### F11 (low). `PROTOCOL` becomes private on the host, while the guest exports it

**Evidence (READ).** `recipes/guest/host/__init__.py:62` has `PROTOCOL` in the guest package's `__all__`, and `tests/unit/test_guest_tools.py:283` asserts it. Decision 8 says that the protocol "is versioned by its number". After this spec, an embedder has no supported way to ask the host which protocol it speaks. "When in doubt, private" is a sound rule, but it should be applied on purpose here.

**Fix.** Keep `PROTOCOL` (or `PROTOCOLS`) public in `wasi_python.tools.__all__`, 9 names. Or state in Decision 3 why the number stays README-only.

### F12 (low). The size of the README reference, and spec numbers inside it

**Evidence (EXECUTED and INFERRED).** Decision 10 asks for about 116 described items: 53 `Args:` entries, 57 `Attributes:` entries and 6 `Raises:` sections. About 16 more come with 034. `run` and `run_async` share 18 arguments, which must have the same text. Rendered as Decision 11 says, the README gains roughly 300–400 lines, from 1,254 now (INFERRED, about two to three lines per item plus two 20-line signatures). The prose sections still teach the same arguments. The summary rule bans spec numbers only in the first paragraph. The other paragraphs hold 14 spec references today (EXECUTED), and they would print in the user-facing reference.

**Fix.** In the README render, show `run_async` as "`run`'s arguments except `cancel`, plus:" and describe only `executor`. The docstrings stay complete for `help()` and for IDE hovers. Either extend "names no specification" to the whole public docstring, with spec citations moved to `#` comments, or strip `(spec NNN)` in the render. The reviewer prefers the first, because it can be checked.

### F13 (low). Notes for the builder, no change in decision

- **CLI actions.** The parser's actions are argparse's private classes (`_StoreAction`, `_AppendAction`, `_StoreTrueAction`), and `--root` uses the package's own `_Once` (`cli.py:89`). Render them through a fixed map (`store`, `append`, `store_true`, `once`), not by class name.
- **Calling a `Tool`.** "Calling it" is promised (Decision 3), but `__call__` is a dunder and has no docstring. Render it explicitly. Decide whether `*args, **kwargs` need `Args:` entries; the reviewer suggests they are exempt.
- **"Every public name has a docstring"** holds only for top-level names. `FileProvider.stat`, `list` and `read` have none (EXECUTED). Criterion 5's first count should include them.
- **`stats()`.** `compiled`, `loaded` and `written` describe the `.cwasm` cache, which Decision 8 leaves unpromised. Promise the keys and that they are counts, not what they count.
- **Stand-ins.** Let `api.py` take the package's path, so the scratch-copy stand-ins in criteria 1 and 4 can point the child interpreter at the copy. Write both files with `newline="\n"`. The release workflow runs the judge on Windows, and `.gitattributes` says LF.
- **Parsing docstrings.** Do not reuse or extend `tools._HEADINGS` to parse `Attributes:`. That tuple decides how a *tool's* description is cut for the guest, so changing it is a behaviour change. The harness gets its own small parser.
- **The CLI's `kind`.** Its JSON `kind` value on exit 1 is `type(e).__name__`. Since Decision 6 promises types, say that `kind` names one of them.

## What holds

- **The surface (READ).** Two modules, one command and two variables is the right size. Every name in the 18 and the 8 is reached by the README's teaching. `Defaults` must be public for `set_defaults` to be usable. A function is the right way to replace a re-exported `DEFAULTS`, for the reason Decision 2 gives: assigning `wasi_python.DEFAULTS` would silently do nothing. Leaving the internal modules' names alone avoids rewriting nearly every test.
- **Signature determinism (EXECUTED).** Built from `inspect.Parameter` strings and `dataclasses.fields` under the future import, the signature render has the same SHA on 3.11, 3.12, 3.13 and 3.14. Across platforms (READ), nothing in the surface depends on the OS except the CPU-count factory, which the spec renders as `<factory>`. The release workflow already runs the judge on Linux, Windows and macOS (`release.yml:213`).
- **The survey's numbers (EXECUTED).** The internal-name probe gives 7 docstring hits with the wider scope. 19 undocumented `run` arguments and 57 public fields match the survey's field lists. All 12 public dataclasses are frozen.
- **034's list (READ).** Decision 13's list matches the branch at `9822812` exactly: `RefusedWrite`'s six fields, `WritableFileProvider`'s five methods, `Mount.writable` (keyword-only) and `FileRecord.refused` / `refused_total` (last).
- **The wheel (READ).** `[tool.hatch.build.targets.wheel] packages = ["src/wasi_python"]` takes a tracked `py.typed` with no change to `pyproject.toml` (a judge file). The wheel rule's change is one line. `tests/public_api.txt` is under `tests/`, so it is in `JUDGE_PATHS`, and every API change shows as a judge change, as Decision 9 intends.
- **Size of the judge change.** It adds one check file (10 checks), `tests/harness/api.py` (INFERRED: 300–400 lines), a snapshot of about 200 lines, about 25 renamed lines in six test files, and one wheel-rule line with its synthetic-wheel stand-in. That is moderate. Each part is a counting check.
- **One builder (INFERRED).** The spec is not build-class and needs no artifact rebuild. One builder can do it in the stated order, once F6's order is followed.

## Constitution checks

- **§4.5 (embedder-neutral):** met. Nothing names an embedder.
- **§4.9 (tests count):** met. Every criterion counts names, lines or items, and none reads a clock. Criterion 10 can also count `DEFAULTS` reads (F7).
- **§4.10 (claims carry evidence):** mostly met. The rename count overstates (F10). The PEP claims are honestly marked INFERRED.
- **§4.13 (tooling, no dependency without a reason):** met. No dependency is added, and the reason for leaving out mypy and pyright is written. `typing.get_overloads` exists from 3.11.
- **§4.15 (safe by default):** met. No default is loosened. Decision 8 restates that loosening is the owner's call. F2's annotation fixes change no value.
- **§5.2 (no open questions):** met for the build. Question 88 is a confirmation, and the spec decides. Bring the stale sentence up to date (F8).
- **§5.4 and §5.7 (one landing at a time):** met, but name the order with 034 (F6).
- **§5.6 (pre-build review):** not required. This review was asked for.
- **§6.4 (smallest thing):** mostly met. The README reference is the largest part, so trim its duplication (F12).

## Disposition (filled in by the author, then confirmed by the reviewer)

The author (the drafting agent) revised `context/specifications/049-the-public-api-is-frozen.md` in the main tree on 2026-10-18, and question 88 in `context/questions-for-the-owner.md`. Every finding is fixed; none is declined. New evidence for the revision (EXECUTED, `uv run python` on 3.14.2 at `44faa43`; scripts beside the draft in the scratchpad): `probe_readme_constants.py` finds 6 README spans naming `DEFAULTS` or `wasi_python.runner` (lines 534, 690, 697, 818, 850, 1079), with backticked spans allowed to wrap a line; a `grep` for module-qualified references finds the 27 rename lines in 5 files that F10 lists.

- **F1, fixed.** Decision 5, change 3: the overloads are `tool(fn: Callable[..., Any], /, *, name=…, …) -> Tool` and `tool(fn: None = None, /, *, name=…, …) -> Callable[[Callable[..., Any]], Tool]`, with the implementation's keywords and defaults. `fn=` by keyword is not promised (the `/` stays, as the reviewer suggested); the implementation keeps accepting it, unpromised. Criterion 7 evaluates each overload's annotations and checks each one's shape.
- **F2, fixed.** Decision 5, change 4: `Defaults.memory_bytes`, `output_bytes`, `file_calls` are `int | None` and `deadline_s` `float | None`. Change 1: `host` is `Callable[[bytes], bytes
  | bytearray | memoryview] | None`. Decision 12 now says the evaluation check cannot see a
  narrow annotation, and that the review of each later change reads the snapshot's types.
- **F3, fixed.** Decision 10's README rule now catches backticked spans (which may wrap a line) that hold `wasi_python.runner|mounts|cli` or an upper-case constant assigned at module level in an internal module (46 names, `Errno`'s members left out). Seen failing first: 6 on main, not 3 (criterion 6). Each `DEFAULTS` becomes `defaults().…`; the Scope covers the six spans.
- **F4, fixed.** Decision 6 lists today's exceptions without changing any: `OSError` and its subclasses during preparation; `RuntimeError` for a fork, shutdown, and a folder or zip copy that changed; an error from wasmtime-py, today `WasmtimeError`, named and not promised; `KeyboardInterrupt`, `CancelledError`; any non-`Exception` `BaseException` from the embedder's own host, provider, tool or gate propagates. "Nothing … makes either raise" becomes "nothing a guest does, and no `Exception` a provider, tool or gate raises". The `Raises:` sections must name exactly these types (Decision 10); the CLI's `kind` names one of them (F13's note).
- **F5, fixed.** Decision 9: docstrings are read as `inspect.cleandoc(vars(obj).get("__doc__") or "")`; an empty, inherited or `dataclasses`-generated docstring counts as undocumented (criterion 5 has a stand-in for each); annotations are read as stored strings and the render asserts `from __future__ import annotations` in the four modules defining public names; `--check` compares the snapshot and the README block, so criterion 11 covers both.
- **F6, fixed.** Status, Depends on and Decision 13: 034 lands first. 049's builder may write the render and checks (tests only) earlier; the renames, docstrings, annotations and README start from main after 034 and cover 034's names (their spec numbers removed there, not in 034). The list of 034's snapshot lines stays as the reviewer's checklist. Criterion 2 counts 20 names in `wasi_python`.
- **F7, fixed.** Decision 2: the runner reads the binding through one helper, `_current_defaults()`, once per call in `_checked`, passed to `_check_tools`, `_check_places` and, for `run_async`, `_submit`; `set_defaults` reads the old value and writes the new one under one lock; its docstring and the README's pool bound say that calls already running or queued on the old pool still run there (up to 12 at once after 8 → 4). The Scope names this runner change. Criterion 10 counts one helper call per `run` and per `run_async`, and one lock acquisition per `set_defaults`.
- **F8, fixed.** Decision 8 names two exceptions, a tighter default in a minor release and security, and says where the promise lives. Decision 13 gives one sentence the lane adds to the end of `context/README.md`'s `specifications/` bullet at landing (the place every drafter reads; not a judge file). Question 88 now covers the command line and its JSON keys, the exception types, `stats()`'s keys, and where the promise is recorded (README and spec, the constitution's §5, or the roadmap); its blank line under the heading is gone. "The owner's choices" points at question 88, not a `questions.md` beside the draft.
- **F9, fixed.** Decision 5: `Artifacts` is in the user-made group, whose field order is promised; Decision 2's table says so.
- **F10, fixed.** Decision 4 lists the 27 lines in 5 files, and tells the builder to rename by module-qualified reference, never by a word-boundary replace, naming the harness's own `KINDS` and `ARTIFACTS_ENV` and the guest's `PROTOCOL`.
- **F11, fixed.** Decision 3: `PROTOCOL` stays public, so `wasi_python.tools.__all__` has 9 names and 17 constants become private (criterion 3 now lists 20 names); the snapshot records its value. `PROTOCOLS` stays private.
- **F12, fixed.** Decision 11 renders `run_async` as "`run`'s arguments except `cancel`, plus:" with only `executor` (its docstring stays complete). Decision 10 bans spec numbers in every paragraph of a public docstring (the reviewer's preference, as it can be checked); citations move to `#` comments. Criterion 5 counts them (14 on main).
- **F13, taken in.** Decision 9: CLI actions through a fixed map (`store`, `append`, `store_true`, `once`); `Tool.__call__` rendered explicitly and its `*args, **kwargs` exempt from `Args:` (Decisions 3 and 10); `FileProvider`'s three methods in criterion 5's first count; `stats()` promises its keys and that they are counts, not what the cache counts count (Decisions 2 and 8); `api.py --package PATH` for the stand-ins, files written with `newline="\n"`; the harness's own docstring parser, `tools._HEADINGS` untouched (Decision 10); the JSON `kind` names one of Decision 6's types.

## Verdict

**Ready to build once F1 to F7 are written in.** The design is sound: a judge-hashed snapshot, an underscore rule checked by `ast`, functions instead of an assignable global, and a promise with its own rules. No finding is high. Four would freeze a mistake into 0.1.0: the overload (F1), the narrow annotations (F2), the incomplete exception list (F4) and the leftover `DEFAULTS` (F3). Two would make the README check unstable (F5) or force 034 to grow after its review (F6). F7 makes `set_defaults` say what it does under threads. F8 to F13 are wording and builder notes.

One line: the frozen surface is the right one, but fix `tool`'s overload, the `None`-taking annotations, the exception list and the README's bare `DEFAULTS` before freezing, read docstrings with `cleandoc`, and land 034 first.

## Confirmation (2026-10-18)

The same reviewer checked each disposition against its finding. The revised spec, question 88 and the Disposition were read at `d695696` on main. Nothing in the repository was edited.

**What I ran (EXECUTED, `uv run` only, scripts in this review's scratch folder):**

- `probe_readme_consts.py`. It applies the revised README rule of Decision 10 to `README.md`. The rule looks for backticked spans that hold `wasi_python.runner|mounts|cli`, or that hold an upper-case constant assigned at module level in `runner.py`, `mounts.py`, `cli.py` or `__main__.py`, minus `Errno`'s members.
  - On main it finds `constants: 46` and `spans: 6`, at lines 534, 690, 697, 818, 850 and 1079. There are no false positives.
  - On 034's branch (`9822812`) it finds `constants: 51` and `spans: 6`, at lines 535, 827, 834, 955, 987 and 1216. So 034 adds no new span, and the count the builder records after 034 stays 6.
- A first, naive version of the same probe paired backticks across the whole file. It found **0 spans**. A second version blanked only fences at the start of a line and found **3**. Only after blanking indented fences as well (`README.md:784–794`, a ```` ```python ```` block inside a list) did it find 6. The drafter's own `probe_readme_constants.py` does not blank fences. It reaches 6 only because the two indented fences hold six backticks, which keeps the pairing even. See condition 1.
- The type and docstring probes from the first review were rerun where they still apply:
  - `Defaults` accepts `None` for all five limits. This is unchanged, so change 4 is right.
  - `vars(cls)["__doc__"]` is `None` for an undocumented class or exception, so nothing is inherited.
  - A dataclass's generated docstring starts with `f"{cls.__name__}("`.
  - `cleandoc` gives the same text on 3.11 to 3.14.

  So Decision 9's reading rule does what it says. The annotations and overloads cannot be probed until they are built. Criterion 7 now checks their shape and evaluates both overloads.
- The rename lines were checked against `grep`. The spec says 27 lines in 5 files: 8 in `tests/test_api.py`, 2 in `tests/harness/paths.py`, 3 in `tests/unit/test_runner_tools.py`, 3 in `tests/unit/test_guest_tools.py` (`T.KINDS`; `T.PROTOCOL` stays) and 11 in `tests/unit/test_tools.py`. That matches what I found.

**Each finding against its disposition:**

- **F1, confirmed.**
  - The first overload is now `tool(fn, /, *, name=…, …) -> Tool`, which accepts the README's `tool(call, name=…)` and the tests' call form.
  - The second overload is `fn: None = None, /`, and it covers `@tool(...)`.
  - Leaving `fn=` unpromised is stated, so a call written that way is not frozen.
- **F2, confirmed.** Change 4 annotates the four limits as `… | None`. Change 1 annotates `host` to return `bytes | bytearray | memoryview`. `async_workers` stays `int`, which is right, because `_check_workers(None)` raises. Decision 12 now says the evaluation check cannot see an annotation that is too narrow.
- **F3, confirmed with condition 1.** The rule now catches all six spans, and catches nothing else, but only if fenced blocks are handled. The Scope covers the six spans.
- **F4, confirmed.**
  - Decision 6 now lists what `run` raises today: `OSError`, `RuntimeError` (fork, shutdown, a changed folder or zip copy), wasmtime-py's error (named but not promised), and any non-`Exception` from the embedder's own code.
  - The "never raises" sentence is narrowed correctly.
  - One `RuntimeError` site is not named: "lost track of a call" (`runner.py:2007`). Its type is already promised, so this needs no change.
  - The gate fits the narrowed sentence, as `README.md:798–802` and `1026–1029` show: it refuses and records.
- **F5, confirmed.** The way docstrings and annotations are read is pinned. The `from __future__ import annotations` line is asserted. `--check` covers both the snapshot and the README block, so criterion 11 covers both too. Criterion 5 has stand-ins for a generated docstring and an inherited one.
- **F6, confirmed.** 034 lands first. The render and the checks may start earlier, because they touch only `tests/`. The list of 034's lines is kept as a checklist. Criterion 2 counts 20 names.
- **F7, confirmed.**
  - `_current_defaults()` is read once, in `_checked`, and passed down. `run_async` reads it on the caller's thread and gives `async_workers` to `_submit`.
  - The swap is done under one lock.
  - The behaviour of the two pools is documented, including "up to 12 at once".
  - Criterion 10 counts both the reads and the lock.
  - `monkeypatch.setattr(runner, "DEFAULTS", …)` still works, because the helper reads the module global.
- **F8, confirmed with condition 2.**
  - Decision 8 names its two exceptions.
  - Question 88 now covers the command line, the JSON keys, the exception types, `stats()` and where the promise is recorded.
  - The stale sentence is fixed.
- **F9 to F13, confirmed.**
  - `Artifacts` is made by the user, so its field order is promised.
  - The 27 lines are listed, with the rule to rename by qualified reference.
  - `PROTOCOL` is public, with 9 names in `wasi_python.tools.__all__` and 17 constants made private.
  - `run_async` is shortened in the README reference.
  - Spec numbers are banned in every paragraph of a public docstring, with 14 counted on main.
  - Every builder note from F13 is written in: the action map, `Tool.__call__`, the three `FileProvider` methods, what `stats()` promises, `--package`, `newline="\n"`, the harness's own parser, and the JSON `kind`.

### Conditions (write into the specification before the build starts)

1. **Fenced code in the README check (Decision 10, criteria 6 and 9).** The span scanner must handle fenced blocks first, including indented ones. It should search their content for the same internal names, because a code example that names `wasi_python.runner` misleads as much as prose does. It then pairs inline backticks only outside the fences. Without this, one README block with an odd number of backticks silently hides every later hit. Evidence above: 0 spans, then 3, then 6.
   - Add a stand-in to criterion 6: a scratch README with an indented fence before a bare `` `DEFAULTS.file_calls` `` still counts that span.
   - The same parser finds the generated block's markers. Make it ignore marker text that appears inside a fence.
2. **The `context/README.md` sentence goes in the branch, not in the lane (Decision 13, Design).** §5.7 has the lane compare the branch with what was reviewed. An edit the lane makes at landing is a change nobody reviewed. The builder adds the sentence in the branch, and the build review reads it like any other line. This changes no check, because the file is not a judge file.

### Builder notes (no change to the specification needed)

- Line numbers move after 034. On `9822812` the six spans are at 535, 827, 834, 955, 987 and
  1216. Criterion 6 records the counts at build time, as the spec says.
- The README pool sentence (Decision 2) and the `## API reference` section are new prose. Run the README check over them too.

### Verdict on the revision

**Confirmed for build, with the two conditions above written in.** Every finding is fixed as its disposition says. The two conditions are small. Condition 1 closes a hole in a check that the revision itself introduced. Condition 2 keeps the landing to exactly what was reviewed. The order is unchanged: 034 lands first, and 049's render and checks may begin before it.

One line: all thirteen fixes hold, so 049 is confirmed for build once the README scanner handles fenced blocks, indented ones included, and the `context/README.md` sentence rides in the branch, not in the lane.
