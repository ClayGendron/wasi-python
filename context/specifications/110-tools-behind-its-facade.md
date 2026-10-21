# 110 — `tools.py` behind its public facade

- **Status:** **drafted 2026-10-21** on `spec/110-tools-behind-its-facade` from `b14b68c` (the
  chain's tip before its rebase onto main), awaiting its pre-build review. It is written after
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
  names live in a `wasi_python._<name>` module, the letter of the rule meets them.

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

The judge reads 23 private names through the module (EXECUTED, `grep -rhoE "\bT\._[A-Za-z_]+"
tests/`, five files that bind `from wasi_python import tools as T`): `_ToolHost` 60 times,
`_Bounded` 12, `_Validator` 9, `_TOOL_REQUEST_BYTES` 9, `_bound_keywords` 7, `_Slot` 6,
`_ToolLoop` 4, `_TOOL_VALIDATION_STEPS` 4, `_Post` 4, `_KINDS` 4, and `_shown`, `_encode`,
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
patched, and `runner._check_tools` imports `tool` by name as it does now.

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
   three, no top-level name is bound twice. `BESIDE` becomes `("mounts",)`, and the existing
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
   `process()` has no field for them. That reason is the concern's, not the file's. So
   `RUNNER_MODULE` in `tests/harness/scan.py` keeps `tools`, `_tool_schema` and `_tool_host`
   outside the rule (`_(?!tool_)\w+`, or the two names spelled out; the builder's choice), the
   comment above it says why in words, and `tests/unit/test_scan.py`'s seam row gains one case:
   `from wasi_python import _tool_host as H; monkeypatch.setattr(H, '_x', 1)` is no hit. Red
   before: that case reports `_tool_host._x`. `SEAM_ALLOWED` is not touched. This is a judge
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
response-cap sites could take a keyword that `max_bytes` already models, but the four counting
sites (`_key`, `_TOKEN`, `_parse`, `_encode`) would be parameters only the judge passes, the
test-only hooks the rubric's R6 forbids; and the cap as a parameter is a design change in a
specification that moves text. *Add the five names to `SEAM_ALLOWED`*: the list is never added
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
   green with `SEAM_ALLOWED` unchanged; the scanner's rule names the three tool modules outside
   it and `test_scan.py`'s new case is green.
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
    the three modules is 74 and the `type: ignore` count 3, not more, recorded;
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
  (one regex and its comment), `tests/unit/test_scan.py` (one case), `tests/harness/api.py` (two
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
  --accept-judge "110: ALLOWED loses tools.py and LONG_FUNCTIONS its two tools.py entries; one unit check holds the three tool modules' import order, docstrings and once-bound names; the by-name check reads the two private modules; the seam scanner keeps the tool protocol's three modules outside its rule, as it kept tools.py, with one unit case; api.py lists the two modules as internal; five judge files name the defining module; no existing expectation edited"
  ```

- **Dry-run needs:** the builder's one dispatch on its tip; nothing platform-specific (the
  three modules have no platform branch), so the Windows shards are the matter-of-course run.

## One line

`wasi_python.tools` keeps its public names and sheds its machinery into two private modules,
the schema rules below it and the frame host above it, each under the ceiling and importing
one way, with two allowances shorter and no verdict moved.

## Landing notes

Written by the builder.
