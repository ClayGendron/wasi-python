# 110 — `tools.py` behind its public facade

- **Status:** **landed 2026-10-21 in wave 10** (045, 110, 111, and the lane's oracle-lock check) on main `b2d4ccd0`: accepted on `81155492`, history line 92, 802/889 pass, 0 fail, on a set rebuilt from the same pins in the main tree (`SHA256SUMS` `d0d91cef`, equal to CI's; the wheel 98,259,192 bytes); the integration review `../reviews/wave-10-integration-2026-10-21.md` and the lane's addendum. Before: **drafted 2026-10-21** on `spec/110-tools-behind-its-facade` from `b14b68c` (the
  chain's tip before its rebase onto main); **reviewed before build 2026-10-21**
  (`../reviews/110-tools-behind-its-facade-spec-2026-10-21.md`: fit to build, six Lows written
  in by the reviewer); **built 2026-10-21** on `spec/110-tools-behind-its-facade` from
  `727bd4c` and rebased onto `5af0a42` (main plus the chain 103 to 109 and the lane's two
  fixes, main's tip once the chain lands), release run 39546608171 on `e6728fa`: every job
  green on three systems, the one red line G7 (see *Landing notes*). It is written after
  the structural chain 103 to 109 and is not a link of it: it builds on main once the chain's
  wave has landed, from main's tip, as the normal rule (constitution §4.14). A different agent
  reviews it before the build (AGENTS.md, rule 8: runner code) and a different one after.
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**: `src/` only, plus the unit checks and rules checks that hold the
  new shape, the harness's module lists, and the import lines of five judge files. It **changes
  no line of `tests/public_api.txt`**, no artifact byte, no fuel row, no golden output, no gap and
  no progress file. By spec 108's Decision 1 none of the five structural triggers fires: it adds
  no module-level mutable, no private-API use, no platform branch and no test seam, and it takes
  no module past the ceiling; it shrinks two allowances. It is still the runner's code, so the
  pre-build review is required (AGENTS.md, rule 8), and that reviewer may score it against
  108's rubric in its "Structure" line (reviews README, 4a). Build-class it is not: it touches
  nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow.
- **Depends on:** **104** (the runner as a package, the 1,500-line ceiling and its allowance
  `ALLOWED`, the written import order and the two forms of reaching a name), **106** (the typed
  call state and `mypy --strict` in the judge), **107** (the citation rule for `src/`, so the new
  modules' docstrings keep their reasons in words), **108** (the function ceiling and its
  allowance `LONG_FUNCTIONS`, the seam check and its scanner, the structural triggers). Landed:
  052 (the sameness line), 055, 056, 057 and 058 (the tool protocol, whose behaviour this
  specification moves and does not change).
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md` (section
  3, item 7: `tools.py`'s shape is the model; L2: its friend-class coupling; section 5: no module
  over 1,500 lines, no function over 80; section 8's table, which names `tools.py`'s two long
  functions by way of 108), and the owner's direction of 2026-10-21, given after the chain
  landed on the PR branch: `tools.py` is three things in one file, the public surface, the
  schema rules and the host side of a call; split it into the facade plus two private modules,
  one concern each, under 104's ceiling; remove its size allowance; settle 108's two long
  functions, preferring the split; move no verdict.

## The problem

`src/wasi_python/tools.py` is 2,449 lines (EXECUTED on `b14b68c`, `wc -l`). It is the one module
of the package that 104's package split did not touch, and it holds three concerns a reader
must separate by section comment. Measured by `ast` over its 117 top-level definitions
(EXECUTED, `build/110/groups.py` and `build/110/partition.py`; a definition's lines run from
its first decorator to its last line; 2,207 lines are inside definitions, the rest is the
docstring, 20 import lines, section comments and blanks):

1. **The public surface.** `ToolError` (3 lines), `ToolDenied` (2), `Tool` (66), `ToolCall`
   (15), `ToolOutcome` (26), `ToolRecord` (18), the `tool` decorator (two overloads, 15 each,
   and the body, 64), `_make` (82) and its helpers `_is_async_generator`, `_bound_keywords`,
   `_timeout`, `_doc`, `_summary`, `_args_section`, `_type_hints` (110 together), the prompt
   stubs (`stubs`, public, and its helpers, lines 2273 to 2437, 165), the constants only they
   read, and `__all__`. **603 lines in 36 definitions.** `wasi_python.tools` is one of the two
   public modules `tests/public_api.txt` records (line 208, `module wasi_python.tools`, and the
   93 indented lines after it, to the end of the file: `PROTOCOL`, the four dataclasses, the two
   exceptions, `stubs` and `tool` with its overloads). The module's name and its names do not
   move.
2. **The schema rules**, which know nothing of the guest: deriving a schema from a signature
   (`_derived` 46, `_schema_of` 28, `_plain` 20, `_scalar`, `_admits_none`), vetting a given one
   (`_vet`, `_Vetting` 113, `_malformed` 52, `_children`, `_resolve`), checking a value against
   it (`_Validator` 178, `_keysets`, `_key` 32, `_where`, `_is_type`, `_kind_of`, `_TooComplex`,
   `_Invalid`), and the JSON-value helpers both sides use (`_to_json` 36, `_NotJSON`, `_echo`,
   `_shown` 20). **693 lines in 40 definitions.**
3. **The host side of a call**: the frames (`_parse`, `_decoded`, `_nesting`, `_encode`,
   `_Refused`, `_error`, `_bounded`, `_described`, `_fault`), the work (`_Work` 85, `_Done`,
   `_Interrupted`, `_inline`), the loop (`_ToolLoop` 178, `_Post` 27, `_NotStarted`,
   `_close_awaitable`, `_cancel_post`), the bound (`_Bounded` 180, `_Ops` 25, `_Slot` 14) and
   the frame host (`_ToolHost` 227). **911 lines in 41 definitions.**

A *facade* here is the module whose names are the public API; the two private modules are the
machinery behind it. The owner's estimate was 300, 450 and 750 lines; the measured partition
is larger on every side because the stubs and `_make`'s helpers stay with the facade, the
schema derivation and the JSON-value helpers join the schema rules, and the frames join the
host. Nothing is left over: `partition.py` reports no unassigned definition.

Three allowances name the file today, each written to shrink and never grow:

- `ALLOWED = {"mounts.py": 2206, "tools.py": 2449}` in `tests/checks/test_rules.py` (104's
  size ceiling; READ at line 163).
- `LONG_FUNCTIONS` holds `"tools.py:_make": 82` and `"tools.py:_ToolHost._answer": 83` (108's
  function ceiling; READ at lines 1034 and 1035). The function ceiling's key is
  `<file>:<qualname>`, so a function moved to another file changes its key, and a stale key is
  red.
- The seam scanner's rule (108's `tests/harness/scan.py`, `RUNNER_MODULE`, line 1967) covers
  `runner`, `mounts` and every `wasi_python._<name>` module, and leaves `tools` outside by name.
  `SEAM_ALLOWED` names no `tools` name (EXECUTED, `grep -n tools tests/checks/test_rules.py`
  in the tuple: none). But the judge patches ten names of `tools` by `monkeypatch.setattr(T,
  …)`, all in `tests/unit/test_tools.py` (EXECUTED, `grep -rn "setattr(T," tests/`): `_key`
  (line 764), `_TOKEN` (922), `_parse` (1270), `_encode` (1338) and `_TOOL_RESPONSE_BYTES`
  (1348, 1372, 1381, 1396, 1403, 1408); and two class attributes, `_ToolHost._list_answer`
  (1371) and `_ToolHost.__call__` (`tests/checks/test_v1_4_embedding.py:5018`), which the rule
  never counts. Each of the ten is a bound the judge lowers to reach a limit, or a function it
  wraps to count its calls; 108 said so when it put `tools` outside the rule. The day those
  names live in a `wasi_python._<name>` module, the letter of the rule meets them, in both of
  the scanner's forms: `RUNNER_MODULE` reads a local name the file's imports bind, and
  `SEAM_BY_PATH` (line 1971) reads the dotted-string form `setattr("wasi_python._x._name", …)`.

The import graph is simple and must stay so (EXECUTED, `grep -nE "tools" src/wasi_python/*.py`
and the file's lines 30 to 49): `tools.py` imports no sibling, only the standard library. No
sibling imports it at module level. `_call.py:39`, `_sessions.py:50` and `runner.py:45` import
its names under `TYPE_CHECKING`; `_call.py:1267` (in `_tool_host`), `_sessions.py:701` (in
`_session_tool_host`) and `:1083` (in `_open_session`) import `_Bounded`, `_ToolHost` and
`_ToolLoop` inside the function; `runner.py:678` (in `_check_tools`) imports `Tool`,
`_is_async_generator` and `tool` inside the function. `__init__.py` and `_places.py` name it
nowhere. The promise `import wasi_python` leaves `wasi_python.tools` unloaded is a unit check
(`tests/unit/test_tools.py::test_importing_the_package_does_not_load_the_tools`) and 104's
import-order check lists those four late imports in `LATE`
(`tests/unit/test_runner_package.py`, lines 46 to 55) and holds `tools` to "no package module
at module level" (`BESIDE`, line 41).

Inside the file the three groups reach each other in one direction but for one constant
(EXECUTED, `partition.py`, every `ast.Name` and every name inside a string annotation):

| reader | owner | names |
|---|---|---|
| facade | schema | `_Json`, `_KeySets` (aliases); `_vet`, `_keysets`, `_derived`, `_plain`, `_schema_of`, `_scalar` (functions) |
| host | facade | `PROTOCOL`, `Tool`, `ToolCall`, `ToolOutcome`, `ToolRecord`, `ToolError`, `ToolDenied` (the `tool` the walk also lists is a parameter named `tool`, not the decorator) |
| host | schema | `_Json`, `_TOOL_NESTING`, `_ECHO_CHARS` (constants); `_Validator` (class); `_echo`, `_where`, `_to_json` (functions) |
| schema | host | none, once `_TOOL_NESTING` lives with the schema: `_VALUE_NESTING` (line 57), which `_to_json` reads, is defined as `_TOOL_NESTING - 2`, and the frames read `_TOOL_NESTING` at lines 1293 and 1335 |

The facade never reads the host. The schema reads neither. So the layering is
`_tool_schema` below `tools` below `_tool_host`, with no cycle and no late import needed among
the three.

The judge reads 22 private names through the module (EXECUTED, `grep -rhoE "\bT\._[A-Za-z_]+"
tests/`, five files that bind `from wasi_python import tools as T`): `_ToolHost` 60 times,
`_Bounded` 12, `_Validator` 9, `_TOOL_REQUEST_BYTES` 9, `_bound_keywords` 7, `_Slot` 6,
`_ToolLoop` 4, `_TOOL_VALIDATION_STEPS` 4, `_Post` 4, `_KINDS` 3, and `_shown`, `_encode`,
`_cancel_post`, `_SAME_VALUE_CHAIN`, `_parse`, `_nesting`, `_key`, `_WRAPPER_DEPTH`, `_TOKEN`,
`_RECORD_OUTCOMES`, `_NotStarted`, `_MAX_ABANDONED` once or twice each. By file:
`tests/unit/test_tools.py` (13 names), `test_runner_tools.py` (6), `test_async_tools.py` (7),
`test_guest_tools.py` (2), `tests/checks/test_v1_4_embedding.py` (2). Every one of them keeps
working through the module that defines it after the move; only the import line changes.

The type counts, so the criteria can say they do not grow (EXECUTED, `grep -oE '(: |-> )Any\b'`
per definition, summed by group): 74 `Any` annotations in the file, 24 in the facade's
definitions, 34 in the schema's, 16 in the host's; 3 `type: ignore` comments, all three in
`Tool` (the public API text says `dict`).

## Decisions

### 1. Three modules: the facade keeps its names; `_tool_schema.py` and `_tool_host.py` take one concern each

**`tools.py`, the facade.** Keeps its docstring, `PROTOCOL`, `_KINDS`, `ToolError`, `ToolDenied`,
`_MAKING`, `Tool`, `ToolCall`, `ToolOutcome`, `ToolRecord`, `tool` and its overloads, `_make`,
`_is_async_generator`, `_bound_keywords`, `_timeout`, `_doc`, `_summary`, `_args_section`,
`_type_hints`, the stubs section whole (`_Hint`, `_Omitted`, `_OMITTED`, `_TYPE_TEXT`,
`_hint_text`, `_default`, `_signature`, `_docstring`, `stubs`), the constants only these read
(`_WRAPPER_DEPTH`, `_PARTIALMETHOD`, `_C_SLOTS`, `_NAME`, `_HEADINGS`, `_HINTS`) and `__all__`.
603 definition lines today; about 720 lines as a file with its docstring, imports and blanks
(INFERRED). Why the stubs stay: `stubs` is public and 165 lines; it renders a `Tool`'s signature
for a prompt and reads one schema helper (`_scalar`); a fourth module for it would be a module
for one function. Why `_make`'s docstring readers stay: `_doc`, `_summary` and `_args_section`
read the function's docstring for the description; they are the facade's view of a function,
not a schema rule. Why `_KINDS` stays: it is the closed set of outcome kinds a `ToolOutcome`
carries, read by the judge four times and by no code, so it sits beside `PROTOCOL` as the
protocol's vocabulary.

**`_tool_schema.py`, the schema rules.** What a tool's input schema may say, how one is derived
from a signature, and how a value is checked against it, with no knowledge of frames, threads
or the guest: `_Json`, `_TOOL_VALIDATION_STEPS`, `_TOOL_NESTING`, `_VALUE_NESTING`, `_ECHO_CHARS`,
`_TOO_COMPLEX`, `_SAME_VALUE_CHAIN`, `_JSON_TYPES`, `_CHECKED`, `_IGNORED`; `_derived`,
`_schema_of`, `_scalar`, `_admits_none`, `_plain`; `_vet`, `_Vetting`, `_children`, `_resolve`,
`_count`, `_number`, `_malformed`; `_TooComplex`, `_Invalid`, `_EMPTY`, `_DELEGATES`,
`_OBJECT_WORDS`, `_ARRAY_WORDS`, `_KeySets`, `_keysets`, `_Validator`, `_where`, `_is_type`,
`_type_name`, `_kind_of`, `_key`; `_echo`, `_shown`, `_NotJSON`, `_to_json`. 693 definition
lines; about 800 as a file (INFERRED). Why the JSON-value helpers are here and not in the host:
`_to_json` is what `_derived` uses for a parameter's default and what `_Work` uses for a
result; `_echo` and `_shown` are what the validator's messages and the host's refusals both
use; the lower module owns what both read. Why `_TOOL_NESTING` is here: `_VALUE_NESTING` is
defined from it and `_to_json` reads that, while the frame decoder reads `_TOOL_NESTING`
itself, so the pair lives below both readers. Its docstring says, in words: the
subset of JSON Schema the protocol admits, how a Python signature maps into it, and how a
value is checked against a budget, so that an answer is the same on every host.

**`_tool_host.py`, the host side of a call.** The frames, the work, the loop, the bound and the
frame host: `_PROTOCOLS`, `_TOOL_REQUEST_BYTES`, `_TOOL_RESPONSE_BYTES`, `_INT_CHARS`,
`_MESSAGE_CHARS`, `_FAULT_CHARS`, `_RECORD_OUTCOMES`, `_MAX_ID`, `_MAX_ABANDONED`,
`_DEADLINE_MARGIN_TICKS`, `_SURROGATE`, `_TOKEN`; `_Refused`, `_nesting`, `_no_constant`,
`_finite`, `_bounded_int`, `_unique_keys`, `_parse`, `_decoded`, `_encode`, `_bounded`,
`_described`, `_fault`, `_message_of`; `_Done`, `_Interrupted`, `_Work`, `_error`, `_inline`;
`_LOOP_THREAD`, `_LOOP_POLL_S`, `_NotStarted`, `_Post`, `_close_awaitable`, `_cancel_post`,
`_ToolLoop`; `_Ops`, `_Slot`, `_Bounded`; `_ToolHost`. 911 definition lines; about 1,030 as a
file (INFERRED), the largest of the three and a third under the ceiling. Its docstring says:
the host half of the protocol, which parses a frame, runs the tool on a thread under a budget
and a deadline, and answers; it imports the facade's types and the schema's validator and is
imported only when a call is given tools.

**The names.** `_tool_schema` and `_tool_host`, the owner's provisional names, kept: each says
its concern in two words and sorts beside `tools.py` in a listing. Why not `_schema.py` and
`_host.py`: `_host` would read as the host process, which `_process.py` already is; the `_tool_`
prefix also lets the seam scanner name the concern (Decision 4).

**Rejected.** *Two modules, the schema rules folded into the facade* (about 1,300 lines): under
the ceiling, but the facade would carry 450 lines of validator a reader of the public surface
never needs, and the owner named three things. *Four modules, the frames apart from the host*
(the frames are 220 lines): `_Work` is a frame's answer and the host's work at once, and the
owner's split names one host concern. *A `_tools/` subpackage*: 104's import order and its
checks walk `*.py` in one folder; a subpackage would be a second shape for one package.

### 2. The import direction: machinery imports the facade, the facade imports only the schema

The direction follows the measured graph. `_tool_schema` imports no package module.
`tools` imports `_tool_schema` at module level and nothing else from the package. `_tool_host`
imports `tools` and `_tool_schema` at module level. No runner module imports any of the three
at module level; `_call`, `_sessions` and `runner` keep their late imports, re-pointed:
`_call._tool_host` and `_sessions._session_tool_host` and `_sessions._open_session` import
`_Bounded`, `_ToolHost` and `_ToolLoop` from `._tool_host`; `runner._check_tools` keeps
importing `Tool`, `_is_async_generator` and `tool` from `.tools`; the three `TYPE_CHECKING`
blocks name the module that now defines each class. The promise that `import wasi_python`
loads no tool module holds as today, since every path into the three starts in a function that
runs only when a call is given tools.

**No late import among the three, and no cycle risk.** The facade never reads the host (the
table in *The problem*: no facade name reaches a host name), so the one cycle the owner asked
about, facade to host at import time, does not arise. If a later change needed the host from
the facade, the rule is the one 104 wrote for the runner: a late import inside the function,
listed in `LATE`, never a module-level one; the unit check of Decision 4 refuses any other.

**The two forms of reaching a name** (104, Decision 2) apply to the two private modules as they
apply to the runner's: a class, a generic alias, an immutable constant or a sentinel may be
bound by `from ._tool_schema import _Json, _KeySets`; a function is reached as
`_tool_schema._vet(...)`, through `from . import _tool_schema`, so a function the judge wraps
(`_key`, `_parse`, `_encode`) is looked up at call time in the module that defines it and the
wrapper is seen by every caller. The facade's six function reads of the schema and the host's
three become attribute reads; the constants and classes stay by-name. The public facade's own
names are outside the by-name rule, as today: they are promised by `tests/public_api.txt`, never
patched, and `runner._check_tools` imports `tool` by name as it does now. `_call.py` keeps the
by-name form for the three classes for one more reason: its function `_tool_host` (line 1253)
shares the module's name, and `from . import _tool_host` there would rebind it.

**Rejected.** *The facade re-exports the private names* (`from ._tool_host import _ToolHost` in
`tools.py`, so `T._ToolHost` keeps working in the judge): it makes the facade import the host at
module level, the one edge the layering forbids, and a patched constant would be patched on the
facade's copy, which `_Work` never reads. The judge names the defining module instead, as 104
made 25 judge files do. *All three imported lazily by each other*: the annotations would need
`TYPE_CHECKING` blocks in all three and the check would need six `LATE` rows for what one
written order says.

### 3. The two long functions are split, not re-keyed

`LONG_FUNCTIONS` loses `"tools.py:_make": 82` and `"tools.py:_ToolHost._answer": 83`, and no
entry takes their place. Each function is cut once, at a seam the text already has, before the
text moves (Design, commit 2), so the move is verbatim and the review reads a 20-line diff
rather than a moved function that changed:

- **`_make`** (lines 371 to 452): the `input_schema is not None` arm (lines 404 to 423: a model's
  `model_json_schema()`, the Mapping check, `_plain`, and the check that no bound keyword is
  named) becomes `_given(name, input_schema, fixed) -> _Json`, 22 lines with its docstring, and
  `_make` calls it in one line: `_make` is 63 lines (INFERRED from the line ranges; the builder
  measures).
- **`_ToolHost._answer`** (lines 2188 to 2270): the `call` arm (lines 2231 to 2270: the tool's
  name, the arguments, the validator, the bound keywords, the work and its outcome) becomes
  `_call_answer(self, seq, request, frame_id, size, failed) -> bytes`, about 44 lines, and
  `_answer` keeps the envelope (parse, id, version, `list`, the unknown operation) at about 46
  lines (INFERRED; the builder measures). `failed` is the local closure `_answer` already
  builds; it is passed, not rebuilt, so every outcome is still noted once.

Why split: the memo's section 5 prefers it, 108's allowance exists to shrink, and each cut is
one named concern (a given schema; a call's answer) that the comment in `LONG_FUNCTIONS` already
describes as "one concern each a helper would take". Why not re-key `_answer` to
`_tool_host.py:_ToolHost._answer`: a re-key is an addition to a list that only shrinks, and it
would carry a stale reason into the new file.

**Rejected.** *Re-key both with a reason*: the allowance rule says "none is ever added", and a
moved key is a new entry by the check's letter. *Split only `_answer` and re-key `_make`*: the
same objection, for one entry.

### 4. The checks first: the allowances shrink, the order is written, the scanner names the concern

Each is committed before the code and seen red by node id (Design, commit 1); every edit to
the judge is a shrink, an extension to the new modules, or one scope line, and no existing
expectation is edited.

1. **`ALLOWED` loses `"tools.py": 2449`** (`tests/checks/test_rules.py`, 104's check). Red
   before: `src/wasi_python/tools.py: 2,449 lines, over 1,500`. Green after, with every module
   under the ceiling. The comment above it, which says two files are over the ceiling today,
   says one.
2. **`LONG_FUNCTIONS` loses its two `tools.py:` entries** (108's check). Red before:
   `src/wasi_python/tools.py:371: _make (82 lines)` and `:2188: _ToolHost._answer (83
   lines)`. Green after commit 2, before the move.
3. **A new unit check, `tests/unit/test_runner_package.py::test_the_tool_modules_import_in_their_written_order`.**
   `TOOLS = ("_tool_schema", "tools", "_tool_host")`, the order of Decision 2. It holds: each
   of the three imports at module level only modules before it in `TOOLS`, and no runner
   module; no runner module imports any of the three at module level; a late import of one of
   them is one of `LATE`, whose four tool rows now name `_tool_host` for `_call` and
   `_sessions` and `tools` for `runner`; each of the three begins with a docstring; over the
   three, no top-level name is bound in two modules (a name bound twice in one module, `tool`'s
   two `@overload` stubs and its body, is one binding: the walk counts a name once per module,
   where the runner's `_once_errors` counts every `def`). `BESIDE` becomes `("mounts",)`, and the existing
   order check's special case for `tools` (`if module == "tools"`) becomes the `TOOLS` rule.
   Red before: `_tool_schema.py` and `_tool_host.py` do not exist. Why a new check and not
   three tuples folded into the runner's: `tools` stands beside the runner's order, as 104 put
   it, and a reader finds the three modules' order under one name.
4. **The by-name check reads the two private modules** (104's
   `test_a_module_imports_by_name_only_what_never_changes`): `_from_imports` and `_patched`
   cover `_tool_schema` and `_tool_host` beside `RUNNER_MODULES`. It then holds what the ten
   patches rest on: a constant the judge patches (`_TOOL_RESPONSE_BYTES`, `_TOKEN`) is read only
   in its defining module, and a function it wraps (`_key`, `_parse`, `_encode`) is reached by
   attribute. Red before: the modules do not import.
5. **The seam scanner names the concern.** 108 put `tools` outside the seam rule because its
   patched names are bounds the judge lowers and functions it counts, not process state, and
   `process()` has no field for them. That reason is the concern's, not the file's. So both
   regexes in `tests/harness/scan.py` that name a runner module, `RUNNER_MODULE` (the local-name
   form) and `SEAM_BY_PATH` (the dotted-string form), keep `tools`, `_tool_schema` and
   `_tool_host` outside the rule, the two names spelled out (`_tool_schema|_tool_host`, not a
   prefix), so the exemption is exactly two modules and a later `_tool_<x>` module joins it by
   hand with a reason; the comment above them says why in words; and `tests/unit/test_scan.py`'s
   seam row gains two cases, `from wasi_python import _tool_host as H; monkeypatch.setattr(H,
   '_x', 1)` and `monkeypatch.setattr('wasi_python._tool_host._x', 1)`, each no hit. Red
   before: each case reports `_tool_host._x`. `SEAM_ALLOWED` is not touched. This is a judge
   change the lane accepts with `--accept-judge`, with this reason; it widens no allowance list,
   it keeps one rule's scope on one concern.
6. **The harness's module lists**: `tests/harness/api.py`'s `INTERNAL_FILES` and
   `INTERNAL_MODULES` gain the two modules beside `mounts.py`; `DEFINING` keeps `tools.py`,
   since every public name is still defined there. `uv run python tests/harness/api.py --check`
   stays silent and `tests/public_api.txt` is byte-identical.
7. **The judge's import lines**: the five files that read a private name through `T` (the list
   in *The problem*) bind `from wasi_python import _tool_host as H` or `_tool_schema as S`
   for the names that moved, and keep `T` for `_bound_keywords`, `_KINDS`,
   `_WRAPPER_DEPTH` and the public names. The ten patch sites patch `H` or `S`. No assertion
   changes.

**The existing checks that hold the behaviour** are the ones the chain used: the tool rows of
`tests/checks/test_v1_4_embedding.py` and `tests/checks/test_v1_2_hostile_guest.py`,
`tests/unit/test_tools.py`, `test_runner_tools.py`, `test_async_tools.py`, `test_guest_tools.py`,
and `tests/unit/test_tools.py::test_importing_the_package_does_not_load_the_tools`.

**Rejected.** *Convert the ten patch sites to constructor parameters* (`_ToolHost(...,
response_bytes=100)`, `_nesting(text, token=...)`, `_Validator(..., key=...)`): the six
response-cap sites could take a keyword of `_ToolHost` that `max_bytes` already models, which
is the seam form the rubric's R6 prefers and the Scope reserves; the four counting sites
(`_key`, `_TOKEN`, `_parse`, `_encode`) would be parameters no production caller passes;
either way a design change, not a move. *Add the five names to `SEAM_ALLOWED`*: the list is never added
to. *Leave the scanner alone and let the ten sites be hits*: the fast tier would be red on a
rule whose own reason says the names are not seams.

### 5. No verdict moves

The judge of "nothing a guest sees changed" is the chain's (the memo's section 8), as 107's
Decision 5 states it:

- **The baseline set** is the release's, verified against its `SHA256SUMS`, frozen in the
  worktree. This specification builds no artifact: no file under `recipes/`, `scripts/` or the
  guest package changes, so no fuel row and no byte row can move.
- **The fast tier** runs on the built commit in the worktree once the lane grants a slot;
  `build/progress/latest.json` is compared with main's record by `uv run python
  tests/harness/sameness.py --claims build/110/claims.toml A.json B.json`. The claim list is
  one new node, `test_runner_package.py::test_the_tool_modules_import_in_their_written_order`;
  every other node keeps its id and its verdict. Any other line is a finding.
- **The tool checks pass unchanged** but for import lines: `git diff main..HEAD -- tests/`
  touches, in the five judge files, only import lines and the module operand of the ten
  `setattr` sites; `tests/checks/test_v1_4_embedding.py` keeps every parity table and every tool
  row's assertions; `tests/unit/test_runner_tools.py` changes only its import block.
- **The public API** is unchanged: `uv run python tests/harness/api.py --check` prints nothing
  and `tests/public_api.txt` is byte for byte the same.
- **The type checker**: `test_src_type_checks_under_mypy_strict` green; the `Any` count over
  the three modules is 74 and the `type: ignore` count 3, not more (the counts in *The
  problem*, re-measured on the built commit with the same commands).
- **The citation rule**: `test_src_names_no_context_document` green; the two new docstrings and
  the moved section comments name no specification, memo, review, finding ID or `context/` path.
  The comment `as unknown (056)` at `tools.py:2250` (READ) is a bare number 107's regexes do not
  see; it moves with `_call_answer` and the builder rewrites it in words, since the line is
  touched anyway.

### 6. Kind: parallel-safe, reviewed before the build as runner code

By 108's Decision 1 none of the five triggers fires: no module-level mutable or lock is added
(the module constants are immutable ints, strings, tuples, frozensets and compiled regexes, and
`_MAKING` is the `contextvars.ContextVar` the facade already holds); no use of wasmtime-py's
private API (the three modules never import `wasmtime`); no platform branch; no test seam (the
ten the judge uses today move with their defining text; none is added); no module past the
ceiling and no function past 80 lines (two leave the list). So the Kind line is
**parallel-safe**, not **structural**. It is the runner's code all the same, so the pre-build
review is required (AGENTS.md, rule 8, the owner's rule of 2026-10-19), and its reviewer writes
the "Structure" line of the reviews README's 4a, which may score the change on R3 (layering: one
edge direction among three modules) and R7 (evolvability: three modules under the ceiling, two
fewer long functions). The build review is by a different agent.

### 7. Where it lands: on main after the chain's wave, alone, one dispatch

The chain 103 to 109 lands as one wave; this specification is not in it. Its branch is made
from main's tip once the wave has fast-forwarded main, not stacked on the chain's PR branch:
every file it touches is on main by then, and a stacked build would buy nothing but a delta
review. One builder; one dispatch of the release workflow on its tip before it writes "built"
(the normal rule, AGENTS.md 2); the run id in the landing notes; the reviewer reads that run
when it is on the reviewed commit. It may land alone or as the parallel-safe entry of a later
wave; its rebase names any conflict, which can only be in `tests/checks/test_rules.py`'s two
allowance dicts, `tests/unit/test_runner_package.py` and `tests/harness/api.py`'s lists, the
files other specifications also append to.

## Intent

After this specification a reader of `wasi_python.tools` sees the public surface and nothing
else: the four records, the two exceptions, the decorator, the stubs and the protocol number,
in a file that fits in one sitting. A reader who asks "what may a schema say" opens
`_tool_schema.py` and finds the subset, the derivation and the validator with no thread in
sight. A reader who asks "what happens to a frame" opens `_tool_host.py` and finds the frames,
the work, the loop, the bound and the host in one file a third under the ceiling. The three
import in one direction, written down and checked. Two allowances are shorter and no new one
exists. Nothing the guest or the embedder sees has moved: not a name, not a message, not a
byte.

## Design

### The commits, in order

1. **The checks** (`tests/checks/test_rules.py`, `tests/unit/test_runner_package.py`,
   `tests/unit/test_scan.py`, `tests/harness/scan.py`, `tests/harness/api.py`): Decision 4's
   seven items. Each check named there is run by node id on this commit and its red line kept
   under `build/110/` for the landing notes.
2. **The two splits, in place** (`src/wasi_python/tools.py` only): `_given` out of `_make`,
   `_call_answer` out of `_ToolHost._answer`; the `(056)` comment rewritten in words.
   `test_no_function_is_over_eighty_lines` green; `test_no_module_under_src_is_over_the_line_ceiling`
   still red (the file is longer by two signatures and two docstrings).
3. **The move** (`src/wasi_python/`): `_tool_schema.py` and `_tool_host.py` created with their
   docstrings; the definitions of Decision 1 moved verbatim in the file's own order, so
   `git diff --color-moved=dimmed-zebra` shows blocks moved and no line changed inside a block
   but the nine function reads that gain a module prefix and the import lines; the facade's
   top comment (lines 27 and 28 today) becomes the map of the three modules; `_call.py`,
   `_sessions.py` and `runner.py` re-point their imports; the five judge files re-point theirs.
   Every check of commit 1 green; `ruff check`, `ruff format --check` and `mypy` clean.

### `tools.py` after the move

The docstring unchanged (the API inventory reads it, and every public name it names is still
there). Imports: the standard library it needs, then `from . import _tool_schema` and
`from ._tool_schema import _Json, _KeySets`. Then `PROTOCOL`, `_KINDS`, the six facade
constants, the two exceptions, `_MAKING`, the four dataclasses, `tool`, `_make`, `_given`, the
seven helpers, the stubs section, `__all__` as today. The section comments "Tools" and "Stubs
for a prompt" stay; "Vetting a schema", "The validator", "Frames" and "The tool loop" go with
their text.

### `_tool_schema.py` and `_tool_host.py`

Each begins with its docstring (Decision 1's words), then its imports, then its constants, then
its definitions in today's order. `_tool_host.py` imports `from . import _tool_schema` and
`from ._tool_schema import _Json, _TOOL_NESTING, _ECHO_CHARS, _Validator`, and
`from .tools import PROTOCOL, Tool, ToolCall, ToolDenied, ToolError, ToolOutcome, ToolRecord`.
The nine function reads become `_tool_schema._vet(...)`, `._keysets`, `._derived`, `._plain`,
`._schema_of`, `._scalar` in the facade and `_tool_schema._echo(...)`, `._where`, `._to_json` in
the host; the builder lists the line of each in the landing notes.

### The CHANGELOG line

Under the one unreleased section:

> **`tools.py` is three modules behind one public facade** (spec 110). `wasi_python.tools` keeps
> every public name and nothing else of weight; the schema rules (what a tool's schema may say,
> how one is derived from a signature, how a value is checked) live in `_tool_schema.py` and the
> host side of a call (the frames, the thread, the budget, the slot table) in `_tool_host.py`,
> each under the 1,500-line ceiling, importing in one written direction; `tools.py` leaves the
> size allowance and its two functions leave the long-function allowance, split at a seam each.
> No public name, message, artifact byte or fuel count changes.

### The roadmap line

> Reserved: 110 (`tools.py` behind its public facade: the public surface stays in
> `wasi_python.tools`; the schema rules move to `_tool_schema.py` and the host side of a call to
> `_tool_host.py`, each under the ceiling, importing in one written order; the size allowance
> entry and the two long-function entries gone; parallel-safe, reviewed before build as runner
> code; after the chain's wave, from main; the owner, 2026-10-21).

## Scope

In: Decisions 1 to 7. Out:

- **The friend-class coupling** (the memo's L2: `_Work` reads `host._gate`, `host._size`,
  `host._loop`; `_Ops` reads `bound._lock` and calls `bound._begin`): all of it is inside
  `_tool_host.py` after the move, where the memo said it is fine; a later specification may
  give `_Work` its three values as arguments.
- **The response cap as a constructor parameter** of `_ToolHost`: a design change, not a move
  (Decision 4, rejected).
- **Any change to what the guest sees**: no frame, no message, no limit, no default, no kind.
- **Any change to `tests/public_api.txt`, the README's generated reference, or the facade's
  docstring.**
- **Citations in the judge's docstrings** (for example `Decision 1:` in
  `tests/unit/test_tools.py:166`, READ): spec 109's rule and check.

## Acceptance criteria

1. **The checks were seen red first**: the two allowance shrinks, the new unit check, the
   extended by-name check and the scanner's new case, each by node id on commit 1, the output
   under `build/110/` and quoted in the landing notes (Decision 4).
2. **Three modules, each under the ceiling**: `wc -l src/wasi_python/tools.py _tool_schema.py
   _tool_host.py` recorded, each at most 1,500; `ALLOWED` is `{"mounts.py": …}` alone;
   `test_no_module_under_src_is_over_the_line_ceiling` green.
3. **Two functions split**: `LONG_FUNCTIONS` holds no `tools.py:` or `_tool_host.py:` key;
   `test_no_function_is_over_eighty_lines` green; the lengths of `_make`, `_given`, `_answer` and
   `_call_answer` recorded.
4. **One import direction**: `test_the_tool_modules_import_in_their_written_order` green;
   `grep -nE "^from \.|^import wasi_python" src/wasi_python/_tool_schema.py` lists nothing,
   the same for `tools.py` lists only `_tool_schema`, for `_tool_host.py` only `tools` and
   `_tool_schema`; `test_importing_the_package_does_not_load_the_tools` green.
5. **The two forms hold over the private modules**:
   `test_a_module_imports_by_name_only_what_never_changes` green with `_tool_schema` and
   `_tool_host` in its lists; the nine function reads are attribute reads, each named in the
   landing notes.
6. **The seam rule's scope**: `test_the_judge_patches_the_runner_only_through_the_process_object`
   green with `SEAM_ALLOWED` unchanged; both of the scanner's regexes name the three tool
   modules outside the rule and `test_scan.py`'s two new cases are green.
7. **The text moved verbatim**: `git diff --color-moved=dimmed-zebra <commit 2>..<commit 3> --
   src/` shows no changed line inside a moved block but the nine prefixed reads; the landing
   notes list every non-move line in `src/` with its reason.
8. **No verdict moved**: `sameness.py --claims` between the built commit's fast-tier record and
   main's prints nothing outside the one-node claim list (Decision 5).
9. **The public API is unchanged**: `tests/public_api.txt` byte for byte; `uv run python
   tests/harness/api.py --check` prints nothing; `INTERNAL_FILES` and `INTERNAL_MODULES` name
   the two modules.
10. **The judge's tool checks pass unchanged**: `git diff main..HEAD -- tests/unit/test_tools.py
    tests/unit/test_runner_tools.py tests/unit/test_async_tools.py tests/unit/test_guest_tools.py
    tests/checks/test_v1_4_embedding.py` touches only import lines and the module operand of the
    ten `setattr` sites; no assertion, parity table or golden line.
11. **`ruff check`, `ruff format --check` and `mypy --strict` are clean**; the `Any` count over
    the three modules is 74 by `grep -ohE '(: |-> )Any\b' <the three files> | wc -l` and the
    `type: ignore` count 3, not more, recorded; the rubric's line count (`grep -c '\bAny\b'`)
    is 98 today and 100 after, the two being the new modules' `from typing import Any` lines,
    which a release review does not read as growth;
    `test_src_names_no_context_document` green with `CITATION_ALLOWED` empty.
12. **The dispatch**: the release workflow on the built tip, every red line a growth line or
    G7; the run id in the landing notes.

Twelve criteria.

## For the lane

- **Kind:** parallel-safe; after the chain's wave, from main's tip; alone or as the
  parallel-safe entry of a later wave.
- **Files it shares with others:** `tests/checks/test_rules.py` (two dict entries removed and
  one comment line; a rebase against another specification's appended check is a trivial
  merge), `tests/unit/test_runner_package.py` (one new check, three tuples), `tests/harness/scan.py`
  (two regexes and their comment), `tests/unit/test_scan.py` (two cases), `tests/harness/api.py` (two
  list entries), `src/wasi_python/_call.py`, `_sessions.py`, `runner.py` (import lines only),
  the five judge files (import lines and ten `setattr` operands), `CHANGELOG.md`,
  `context/roadmap.md`.
- **The claim list** (`build/110/claims.toml`, each line "110:"):
  - 110: **new checks**: `tests/unit/test_runner_package.py::test_the_tool_modules_import_in_their_written_order`.
  - 110: **unit rows moved**: none; **retired checks**: none; **lost passes**: none; **fuel
    rows**: none; **bytes**: none.
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/unit/test_runner_package.py`,
    `tests/unit/test_scan.py`, `tests/harness/scan.py`, `tests/harness/api.py` and the five judge
    files.
- **The flags** (paste-safe):

  ```
  --accept "110: tools.py is the public facade alone, its schema rules in _tool_schema.py and the host side of a call in _tool_host.py, each under the ceiling, importing in one written direction, the two long functions split at a seam each; no public name, message, artifact byte or fuel count changes"
  --accept-judge "110: ALLOWED loses tools.py and LONG_FUNCTIONS its two tools.py entries; one unit check holds the three tool modules' import order, docstrings and once-bound names; the by-name check reads the two private modules; the seam scanner keeps the tool protocol's three modules outside its rule in both its regexes, as it kept tools.py, with two unit cases; api.py lists the two modules as internal; five judge files name the defining module; no existing expectation edited"
  ```

- **Dry-run needs:** the builder's one dispatch on its tip; nothing platform-specific (the
  three modules have no platform branch), so the Windows shards are the matter-of-course run.

## Disposition of the pre-build review

The review (`../reviews/110-tools-behind-its-facade-spec-2026-10-21.md`, commit `bd886ac`;
verdict "fit to build", no High, no Medium, six Lows, two Notes) re-ran the shape checks, the
nine node ids the specification rests on and `api.py --check`, re-measured the partition
(603, 693 and 911 definition lines, the draft's numbers exactly) and walked the cross-group
reads with a wider net than the draft's (every identifier in every string constant), finding
the same acyclic order. The reviewer wrote every Low into the specification's text in
`be6424f`, as the reviews README's item 7 allows; the writer read each write-in against the
Decisions it touches. None contradicts one; each is confirmed below.

1. **L1, both scanner regexes, the exemption spelled as two names**: confirmed. The draft
   named `RUNNER_MODULE` and missed `SEAM_BY_PATH`, the dotted-string form; with one regex
   edited the rule's two forms would disagree about the tool modules. Decision 4 item 5 now
   names both, spells the exemption as `_tool_schema|_tool_host` rather than a prefix, so a
   later `_tool_<x>` joins it by hand with a reason, and gives `test_scan.py` two cases, one
   per form; criterion 6, the shared-files list and the `--accept-judge` reason say "both
   regexes" and "two cases". The writer agrees with the reviewer's reading of the edit: it
   keeps a rule's scope on the concern 108 excluded, and widens no allowance.
2. **L2, `tool`'s overloads are one binding**: confirmed. `tool` is defined three times in
   the facade (two `@typing.overload` stubs, lines 271 and 288, and the body at 305), and a
   check that reused `_once_errors`'s every-`def` count would be red on the facade after the
   move. Decision 4 item 3 now says the new check counts a name once per module, which is also
   how the judge's existing rule reads the file today
   (`tests/checks/test_rules.py::test_no_module_level_name_is_bound_twice`, green on
   `tools.py` with its overloads).
3. **L3, `_call.py` keeps the by-name form**: confirmed. `_call.py:1253` defines a function
   named `_tool_host`, the one that will import from the module of the same name; `from .
   import _tool_host` there would rebind the function. Decision 2 already imported the three
   classes by name (they are classes, so the by-name form is the rule's own); the write-in
   says why the attribute form is not an option in that file, so the builder does not reach
   for it.
4. **L4, criterion 11 names the `Any` command and the rubric's rise**: confirmed. The draft's
   74 is by `grep -ohE '(: |-> )Any\b'`, annotations only; the rubric's `grep -c '\bAny\b'`
   counts lines and reads 98 today and 100 after the move, the two being the new modules'
   `from typing import Any` lines. Criterion 11 now names both commands and both numbers, so
   a release's structural review does not read the two import lines as growth.
5. **L5, 22 names and 3 reads**: confirmed, re-measured by the writer: `grep -rhoE
   "\bT\._[A-Za-z_]+" tests/ --include=*.py | sort -u`, 22 private names once `__all__` and
   `__name__` are left out; `grep -rnE "\bT\._KINDS" tests/`, 3 lines, all in
   `tests/unit/test_guest_tools.py` (272, 282, 287). The draft's 23 and 4 were a miscount.
6. **L6, the constructor-parameter rejection restated**: confirmed. The draft called a
   defaulted keyword on `_ToolHost` a test-only hook; it is the seam form R6 prefers, and the
   Scope reserves it. The rejection stands on the other ground, which the write-in keeps: a
   keyword for the response cap, and parameters for the four counting sites that no
   production caller would pass, are a design change in a specification that moves text.
7. **Note, the new node keeps its own id**: acknowledged, and kept: the existing order check
   stays green through commits 1 and 2 because it asserts no file's existence, so the new
   node is the one seen red first; one node per "seen red first" line keeps the claim list
   honest. The builder lets it share `_order_errors`'s walk rather than write a second one.
8. **Note, the roadmap line is the lane's**: acknowledged. Design's "The roadmap line" is
   the proposed text; the lane writes it into `context/roadmap.md` when it reserves the
   number, as it did for 109 in `1893ede`; the specification's commits touch only
   `context/specifications/`.

## One line

`wasi_python.tools` keeps its public names and sheds its machinery into two private modules,
the schema rules below it and the frame host above it, each under the ceiling and importing
one way, with two allowances shorter and no verdict moved.

## Landing notes

Written by the builder, 2026-10-21, on `spec/110-tools-behind-its-facade`: built on `727bd4c`,
then rebased onto `5af0a42` with no conflict (it adds the lane's digest-cache fix `2a878f0`,
whose files this specification does not touch). Commits after the rebase: `bf208e6` (the
checks), `8199c0a` (the two splits), `159e6a0` (the move), `e6728fa` (the CHANGELOG line), then
these notes. Before the rebase they were `61b3a1a`, `90a5011`, `64d8d76` and `806e1ab`; the
measurements below were taken there and the diff of `src/` and `tests/` is the same.

**Release runs.** 39546608171 on `e6728fa`: 39 jobs green, Windows' five included; `gather
the shards' records` red on its one line, `G7 the newest acceptance is not on the release's set
(SHA256SUMS)`. The first dispatch, 39541508092 on `806e1ab` (the base without `2a878f0`), was red
on Windows' `own-runner` shard twice (attempts 1 and 2) on one unit check this specification does
not touch, `tests/unit/test_runner_sets.py::test_a_same_size_same_mtime_replacement_is_hashed_again`
(`assert 3 == 2`, a digest hashed a third time): the intermittent Windows miss `2a878f0` fixes,
which is why the branch was rebased. Neither run's other shards had a red line.

### Re-measured on the base

Every number *The problem* states was drafted on `b14b68c`; on `727bd4c` each is the same
(EXECUTED): `tools.py` 2,449 lines; the partition 603, 693 and 911 definition lines, none
unassigned (`build/110/move.py`'s walk over `git show 727bd4c:src/wasi_python/tools.py`); 74
`Any` annotations, 98 `Any` lines, 3 `type: ignore`; the ten `setattr(T, …)` sites at the same
lines of `tests/unit/test_tools.py`; 22 private names read through `T`; the four late imports at
`_call.py:1267`, `_sessions.py:701` and `:1083`, `runner.py:678`. Two line numbers differ:
`LONG_FUNCTIONS`' two entries were at `tests/checks/test_rules.py:1054` and `1055` (not 1034 and
1035), and `_make`'s given-schema arm was lines 415 to 429 (the draft's 404 to 423).

### The checks, seen red first (commit `61b3a1a`, now `bf208e6`; criterion 1)

Each by node id, the output under `build/110/`:

- `test_no_module_under_src_is_over_the_line_ceiling`: `src/wasi_python/tools.py: 2,449 lines,
  over 1,500`.
- `test_no_function_is_over_eighty_lines`: `src/wasi_python/tools.py:2188: _ToolHost._answer (83
  lines)`; `src/wasi_python/tools.py:371: _make (82 lines)`.
- `test_the_tool_modules_import_in_their_written_order` (new): `_call.py:1267 (_tool_host imports
  tools late, not in LATE)`; `_sessions.py:701 (_session_tool_host imports tools late, not in
  LATE)`; `_sessions.py:1083 (_open_session imports tools late, not in LATE)`; `_tool_schema.py
  does not exist`; `_tool_host.py does not exist`.
- `test_a_module_imports_by_name_only_what_never_changes` (extended): `_tool_schema.py does not
  exist`; `_tool_host.py does not exist`. The extension needed one new line to be red before
  the move: a module the rule lists and the package lacks is a finding (a stale entry), since
  with no file there is no import to read.
- `test_scan.py::test_a_private_runner_name_the_judge_patches_is_a_hit`, its two new cases, each
  seen red alone: with neither regex edited, `t/test_a.py:2: _tool_host._x` (the local-name form);
  with `RUNNER_MODULE` edited and `SEAM_BY_PATH` not, `t/test_a.py:1: _tool_host._x` (the
  dotted-string form). Both regexes now share one lookahead, `NOT_TOOL_MODULE =
  (?!(?:_tool_schema|_tool_host)\b)`, the two names spelled out; probed: `_tool_hostx` and
  `_tool_x` are still runner modules to the rule.

The existing order check stayed green through commits 1 and 2: the walk is shared, and an
import made by or naming one of `TOOLS` goes to the new rule, every other to the runner's.

### Sizes and lengths (criteria 2, 3)

EXECUTED on `64d8d76`: `tools.py` 727 lines, `_tool_schema.py` 785, `_tool_host.py` 1,027 (the
draft's INFERRED 720, 800, 1,030). `ALLOWED` is `{"mounts.py": 2206}`. `LONG_FUNCTIONS` holds no
`tools.py:` or `_tool_host.py:` key; functions over 80 lines in the package: 7 (`runner.py` 4,
`_call.py`, `_process.py`, `_sessions.py` 1 each). `_make` 68 lines, `_given` 20, `_answer` 59,
`_call_answer` 46 (58 and 43 at commit 2, before the move wrapped two f-strings past 100
columns).

**One departure from Decision 3, with its reason.** The draft's cut gave `_call_answer` the whole
`call` arm, the tool's name included, with the signature `(self, seq, request, frame_id, size,
failed)`. That would change the record: `failed` is a closure that reads `op` and `name` from
`_answer`'s frame when it is called, so an `op` and a `name` bound inside `_call_answer` would
leave every `unknown_tool` and `invalid_arguments` outcome with `op` and `tool` `None`. The cut
falls after the tool is found instead: `_answer` keeps the envelope and binds `op = "call"` and
`name` before it hands on, and `_call_answer(self, seq, t, name, request, frame_id, size, failed)`
takes the arguments, the validator, the bound keywords, the work and its outcome; it binds `op =
"call"` once so its two `ToolOutcome` lines stay as they were. `failed` is passed, not rebuilt;
every outcome is still noted once.

### One import direction (criteria 4, 5)

`grep -nE "^from \.|^import wasi_python"`: `_tool_schema.py` none; `tools.py` lines 49 and 50,
`from . import _tool_schema` and `from ._tool_schema import _Json, _KeySets`; `_tool_host.py`
lines 26 to 28, `_tool_schema` twice and `.tools` once. `_call.py`'s and `_sessions.py`'s late
imports and `TYPE_CHECKING` blocks name `._tool_host`; `runner.py` is unchanged.
`test_importing_the_package_does_not_load_the_tools` green.

The "nine function reads" are nine functions at 17 sites, each now `_tool_schema.<name>(`:
`tools.py:377` `_derived`, `:380` `_vet`, `:384` `_schema_of`, `:397` `_keysets`, `:416` `_plain`
(in `_given`), `:596` and `:598` `_scalar`; `_tool_host.py:83`, `:99`, `:136`, `:143`, `:948`,
`:963`, `:977`, `:1007` `_echo`, `:274` `_to_json`, `:1006` `_where`.

### The move, verbatim (criterion 7)

`build/110/verbatim.py 90a5011` compares every top-level definition of the three modules with
the same definition in commit 2's `tools.py`, the `_tool_schema.` prefix taken away: no
definition missing or added, and two differences, both in `_ToolHost`, where a prefixed read
took a line past 100 columns and an f-string was split in two (`unknown operation …` in
`_answer`, `unknown argument …` in `_call_answer`; the same message bytes). The other non-move
lines in `src/`, each with its reason: the two new docstrings; the facade's top comment, now the
map of the three modules; the import blocks; two section comments in `_tool_schema.py` ("A
schema from a signature" above `_derived`, which sat under "Tools", and "JSON values: as a
message shows them, and as an answer carries them" above `_echo`, which sat under "Frames"); and
the two annotations of commit 2's new signatures narrowed from `Any` (`_given`'s `input_schema`
to `object`, `_call_answer`'s `frame_id` to `int | None`), so the `Any` count does not grow.
Commit 2 rewrote the comment `as unknown (056)` as `refused as unknown`.

### No verdict moved (criteria 8 to 11)

- **Sameness.** The fast tier on the base (`727bd4c`, `build/110/A.json`) and on the built
  tree (`806e1ab`'s files, `build/110/B.json`), both in this worktree against the main tree's
  artifact set cloned in, `-n 3`: 2,600 and 2,601 passed, 48 skipped each, 0 failed; v1 623/864
  pass, 0 fail, the same per goal. `uv run python tests/harness/sameness.py --claims
  build/110/claims.toml build/110/A.json build/110/B.json`: exit 0, "explained by claims: 110 1"
  (the one unit row). Without the claims: one line, the unit suite 1,977 to 1,978. After the
  rebase, the fast tier on `e6728fa`'s code (`build/110/C.json`): 2,603 passed, 48 skipped, 0
  failed, v1 623/864; against B, one line, the unit suite 1,978 to 1,980, the two unit checks
  `2a878f0` adds.
- **The public API.** `tests/public_api.txt` unchanged (`git diff 727bd4c -- tests/public_api.txt`
  empty); `api.py --check` silent; `INTERNAL_FILES` and `INTERNAL_MODULES` name the two modules
  through one tuple, `TOOL_FILES`.
- **The judge's tool checks.** In the five files, every changed line is an import line, one of
  the ten `setattr` operands, or the module operand of a private read (`T._X` to `H._X` or
  `S._X`; `build/110/judge_diff.py` finds no other). Beyond the draft's list: the three patches of
  `T.asyncio` in `tests/unit/test_async_tools.py` (lines 418, 552, 1122) now read `H.asyncio`,
  since the facade no longer imports `asyncio` (the same module object); and
  `tests/checks/test_v1_4_embedding.py`'s three by-name imports of `_ToolHost` (lines 2836, 2863,
  3523) now name `wasi_python._tool_host`. No assertion, parity table or golden line changed.
- **Clean.** `ruff check`, `ruff format --check` and `mypy --strict src/wasi_python` clean. `Any`
  annotations over the three modules 74, `Any` lines 100 (the two new `from typing import Any`
  lines), `type: ignore` 3, all in `Tool`. `test_src_names_no_context_document` green.

Three judge edits outside the draft's list of lines, all words: the docstring of
`test_no_module_under_src_is_over_the_line_ceiling` ("the two files ALLOWED holds" becomes "the
files"), the seam check's docstring (names the tool protocol's three modules), and one comment
in `tests/unit/test_scan.py` (`tools.py's own method` becomes `the tool host's own method`, where
`self._context()` now lives).

### Platforms

The three modules have no platform branch, and no moved line names a path or an OS. The judge's
edits change only which module object a name is read from; `H.asyncio` is `asyncio` on every
system. The Windows legs of the run are the matter-of-course check.

### For the lane

- **Kind:** parallel-safe; on main once the chain's wave has landed (`5af0a42` is its tip).
- **Claim list** (`build/110/claims.toml`):

  ```toml
  # Two unit rows: tests/unit/test_runner_package.py::test_the_tool_modules_import_in_their_written_order
  # and tests/unit/test_tools.py::test_a_refused_call_records_its_operation_and_tool
  [[claim]]
  spec = "110"
  new = []
  retired = []
  changed = []
  units = 2
  ```

  No check row is new, retired or changed; no fuel or byte row; no pass moved. The second unit
  row answers the build review's L2 (see *The build review's two Lows*).
- **Judge hash:** changes in `tests/checks/test_rules.py`, `tests/unit/test_runner_package.py`,
  `tests/unit/test_scan.py`, `tests/harness/scan.py`, `tests/harness/api.py` and the five judge
  files.
- **The flags:**

  ```
  --accept "110: tools.py is the public facade alone, its schema rules in _tool_schema.py and the host side of a call in _tool_host.py, each under the ceiling, importing in one written direction, the two long functions split at a seam each; no public name, message, artifact byte or fuel count changes"
  --accept-judge "110: ALLOWED loses tools.py and LONG_FUNCTIONS its two tools.py entries; one unit check holds the three tool modules' import order, docstrings and once-bound names; the by-name check reads the two private modules; the seam scanner keeps the tool protocol's three modules outside its rule in both its regexes, as it kept tools.py, with two unit cases; api.py lists the two modules as internal; five judge files name the defining module; one unit row holds the operation and tool recorded on a call refused before its tool runs; no existing expectation edited"
  ```

- **Dry-run needs:** none beyond the one run above.
- **Neighbours:** spec 111 is built beside it; neither touches the other's files.

### Rebase for wave 10

- **Rebase:** from `2e5ea17` (on `5af0a42`) onto `3b7f6abf`, 045 rebased onto wave 09's tip
  `265607bd`, wave 10's order being 045, 110, 111. One conflict hunk, in `CHANGELOG.md`: main's
  spec 100 entry (numpy on OpenBLAS) and 110's entry were both added after spec 109's; both kept,
  100's first, as main has it. No other file conflicted; main since `5af0a42` adds no read of a
  moved name (`grep` for `T._<moved name>`, `from wasi_python.tools import _…` and `setattr(T,`:
  none). After it (EXECUTED): `ruff check`, `ruff format --check`, `mypy --strict` clean;
  `tests/checks/test_rules.py` and the seven unit and judge files by name, 655 passed, 1 skipped;
  `api.py --check` silent; the fast tier in this worktree against a clone of 045's artifact set,
  `-n 3`: 2,648 passed, 51 skipped, 0 failed, v1 640/886 pass, 0 fail. No new release run: only
  the rebase changed; the wave's dry run judges it.

### The build review's two Lows

The review (`../reviews/110-tools-behind-its-facade-build-2026-10-21.md`, `7a51742`, verdict
"lands") found two Lows, both answered in the commit after `7a51742`:

- **L1**, two lengths of commit 2: *Sizes and lengths* now gives the built commit's, `_answer` 59
  and `_call_answer` 46, with commit 2's beside them.
- **L2**, no check held the tool recorded on an `unknown_tool` outcome, which the departure from
  Decision 3 was made to keep: `tests/unit/test_tools.py::test_a_refused_call_records_its_operation_and_tool`
  sends a call with `"tool": 7`, one naming a tool not offered, and one with `"args": []`, and
  holds `(op, tool, outcome)` for each. Seen failing first against a deliberately broken
  recording (`_answer` binding the name only for `_call_answer`, so `failed` never sees it):
  `At index 1 diff: ('call', None, 'unknown_tool') != ('call', 'nope', 'unknown_tool')`; green on
  the build, the unit file 183 passed. The claim list's units go from 1 to 2 and the
  `--accept-judge` string names the row. No new release run: a unit row only, which the wave's
  dry run judges.

### Self-check

- Rebased onto `5af0a42` (the chain's tip, main's once it lands) today, named in the Status
  line; no conflict.
- Release run 39546608171 on `e6728fa`, read: the one red line G7; the Windows legs green.
- Every number above re-measured on this base and labelled EXECUTED; the draft's INFERRED sizes
  replaced by the measured ones.
- "For the lane": the claim list, the two flags each beginning "110:", the kind, the dry-run
  needs.
- Every new check seen failing first (above); no Windows or Linux branch touched (Platforms).
- No gap, no reserved follow-up; `packages.toml` and README rows not touched (no package, no
  public name).
- The CHANGELOG line under the one unreleased section; no question for the owner.
- `ruff check`, `ruff format --check`, the fast tier: green, output in `build/110/`.
