# Review of 110 — `tools.py` behind its public facade (the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude Opus 5.5), started by the lane; wrote none of spec 110
  and reviewed none of it before this (the pre-build review,
  `110-tools-behind-its-facade-spec-2026-10-21.md`, is another agent's).
- **Reviewed:** `5af0a42..54fe623` on `spec/110-tools-behind-its-facade`; the code tip is
  `e6728fa`, and `54fe623` adds only the landing notes (`git diff --stat e6728fa..54fe623`: the
  specification alone). Commits: `bf208e6` (the checks), `8199c0a` (the two splits in place),
  `159e6a0` (the move), `e6728fa` (the CHANGELOG line), `54fe623` (the notes).
- **Run:** the builder's 39546608171, on `e6728fa`, the exact code commit reviewed (the owner,
  2026-10-20: the reviewer reads the builder's run when it is on that commit). Read back
  (EXECUTED, `gh run view 39546608171 --json headSha,jobs`; `gh run download 39546608171 -n
  release-record-1`): `headSha` `e6728fa6`; 43 jobs, every judge and verify job green on three
  systems, Windows' five (`verify`, `own-guest`, `own-embedding`, `own-runner`,
  `upstream-windows`) included; `gather the shards' records` red on one line, `RED: G7 the
  newest acceptance is not on the release's set (SHA256SUMS)`, and the three publish jobs skipped
  after it. The record's scoreboard: v1 772/864 pass, 85 gap, 7 blocked, 0 fail; unit suite
  4,638/4,668, 30 skipped. No GREW line.
- **Box:** 60 minutes (the lane's); the reads, the probes and the measurements fit in about 35.
- **Re-ran** (all EXECUTED in the worktree, on `54fe623`; outputs under `build/110-review/`):
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` →
    153 files already formatted; `uv run mypy --strict src/wasi_python` → no issues in 20 source
    files; `uv run python tests/harness/api.py --check` → silent, exit 0; `git diff 5af0a42..54fe623
    --quiet -- tests/public_api.txt` → exit 0.
  - The six unit files the specification touches (`tests/unit/test_tools.py`,
    `test_runner_tools.py`, `test_async_tools.py`, `test_guest_tools.py`,
    `test_runner_package.py`, `test_scan.py`) → 576 passed, exit 0, run before
    `build/lane.lock` appeared in the main tree. After it appeared, single node ids only, and no
    fast tier: the lane's lock was held for the rest of the box.
  - By node id, each PASSED: `test_rules.py::test_no_module_under_src_is_over_the_line_ceiling`,
    `::test_no_function_is_over_eighty_lines`,
    `::test_the_judge_patches_the_runner_only_through_the_process_object`,
    `::test_src_names_no_context_document`, `::test_code_outside_src_names_no_context_document`,
    `::test_src_type_checks_under_mypy_strict`, `::test_no_module_level_name_is_bound_twice`,
    `::test_only_the_engine_seam_touches_wasmtimes_private_api`;
    `test_runner_package.py::test_the_runner_modules_import_in_the_written_order`,
    `::test_the_tool_modules_import_in_their_written_order`,
    `::test_a_module_imports_by_name_only_what_never_changes`,
    `::test_every_runner_name_is_defined_in_one_module`;
    `test_tools.py::test_importing_the_package_does_not_load_the_tools`.
  - `uv run python tests/harness/sameness.py --claims build/110/claims.toml build/110/A.json
    build/110/B.json` (the builder's records) → `note: explained by claims: 110 1`, exit 0; B
    against C (the rebased code) → one line, the unit suite 1,978 to 1,980, the two unit checks of
    `2a878f0`, which this specification does not touch.
  - A verbatim check of my own (`scratchpad/tools/verbatim.py`, not the builder's): every
    top-level definition of commit 2's `tools.py` against the three modules of commit 3, by
    `ast.dump` after taking away the `_tool_schema.` prefix, and every comment token by count →
    no definition missing, none added, none bound in two modules; two definitions differ,
    `_given` (`input_schema: Any` to `object`) and `_ToolHost` (`_call_answer`'s `frame_id: Any`
    to `int | None`), annotations only; the two wrapped f-strings compare equal as ASTs. The
    comments gone are the facade's old two-line top comment; the new ones are the three-module map
    (four lines), two section rules and two section headings in `_tool_schema.py`.
  - A behaviour probe (`scratchpad/tools/probe.py`): one `_ToolHost` over a decorated tool and a
    partial with a bound keyword, fed eleven frames, one per branch of the envelope and the call
    (not JSON, a wrong version, `batch`, `list`, a non-string tool, an unknown tool, args not an
    object, a type error, a bound keyword through an open schema, an ok call, an id over
    `_MAX_ID` with an unknown argument), run against `5af0a42`'s `src/` (unpacked by `git
    archive`) and the tip's → answers and `ToolOutcome` records byte-identical (`diff` empty),
    `op` and `tool` included: `('call', None, 'protocol')`, `('call', 'nope', 'unknown_tool')`,
    `('call', 'add', 'invalid_arguments')` three times, `('call', 'bound', 'invalid_arguments')`.

## The builder's self-check

Present at the end of the landing notes and complete: rebased onto `5af0a42` with no conflict,
named in the Status line; the run on `e6728fa` read, G7 its one red line, Windows green; the
numbers re-measured on the base and labelled; the claim list, the two flags beginning "110:",
the kind and the dry-run needs; every new check seen red (five red lines quoted, the scanner's
two cases each red alone); no platform branch; no gap; the CHANGELOG line under the one
unreleased section; ruff and the fast tier green with output in `build/110/`. One number is off
(finding 1).

## Acceptance criteria against evidence

1. **Checks seen red first** — met: READ, the five red lines in the notes and the files
   `build/110/red-allowances.txt`, `red-package.txt`, `red-scan-1.txt`, `red-scan-2.txt`; the
   checks are in `bf208e6`, before the code.
2. **Three modules under the ceiling** — met: EXECUTED, `wc -l`: `tools.py` 727,
   `_tool_schema.py` 785, `_tool_host.py` 1,027; `ALLOWED = {"mounts.py": 2206}`; the ceiling
   check PASSED.
3. **Two functions split** — met: EXECUTED, `LONG_FUNCTIONS` holds no `tools.py:` or
   `_tool_host.py:` key; the function check PASSED; `_make` 68, `_given` 20, `_answer` 59,
   `_call_answer` 46 (the notes say 58 and 43: finding 1).
4. **One import direction** — met: EXECUTED, the new order check and the package-import check
   PASSED; READ, `_tool_schema.py` imports no package module, `tools.py` only `_tool_schema`
   (lines 49, 50), `_tool_host.py` `_tool_schema` and `.tools` (26 to 28); `_call.py` and
   `_sessions.py` re-point their late and `TYPE_CHECKING` imports to `._tool_host`; `runner.py`
   unchanged.
5. **The two forms over the private modules** — met: EXECUTED, the by-name check PASSED with
   `BY_NAME_MODULES` naming both; READ, every function read of the schema from the other two is
   `_tool_schema.<name>(`, and the names bound by `from` are `_Json`, `_KeySets`,
   `_TOOL_NESTING`, `_ECHO_CHARS`, `_Validator`, none of them patched (the rubric's patch grep
   lists `H._encode`, `H._parse`, `H._TOKEN`, `H._TOOL_RESPONSE_BYTES`, `S._key` and four class
   attributes; each is read in its defining module).
6. **The seam rule's scope** — met: EXECUTED, the seam check PASSED, `SEAM_ALLOWED` untouched
   (READ, the diff of `test_rules.py`); both regexes share `NOT_TOOL_MODULE`, the two names
   spelled out; `test_scan.py`'s two new cases pass in the 576.
7. **Verbatim** — met: EXECUTED, my AST and comment comparison above; the non-move lines are
   the ones the notes list.
8. **No verdict moved** — met for the evidence available: EXECUTED, `sameness.py --claims` on the
   builder's records, exit 0, one unit row; READ, the release record's 0 fail on three systems.
   My own fast-tier record was not taken (the lane's lock); the lane's integration record is
   the independent one.
9. **Public API unchanged** — met: EXECUTED, `api.py --check` silent, `public_api.txt` no diff;
   READ, `INTERNAL_FILES` and `INTERNAL_MODULES` name both through `TOOL_FILES`; the facade's
   docstring is byte-identical (its first 26 lines `diff`ed against `5af0a42`).
10. **The judge's tool checks pass unchanged** — met: EXECUTED, `git diff --word-diff=porcelain`
    over the five files, every changed word tallied: each is `T.` to `H.` or `S.` on a private
    read, a `setattr` operand, an import line, or `T.asyncio` to `H.asyncio`; no assertion,
    parity table or golden line. Nine `setattr(T,` sites become eight `setattr(H,` and one
    `setattr(S,` (`_key`); the tenth patch the draft counted, `_ToolHost._list_answer`, is a
    class attribute and reads `H._ToolHost`.
11. **Clean, and the type counts** — met: EXECUTED, ruff, format and mypy clean; `Any`
    annotations over the three modules 74 (base 74); `Any` lines in `src/` 340 (base 338, the
    two new `from typing import Any`); `type: ignore` 3 in the three modules, all in `tools.py`
    (base 3), 25 in `src/` (base 25); the citation check PASSED, `spec NNN` in `src/` 0.
12. **The dispatch** — met: EXECUTED, 39546608171 read back, G7 its only red line.

## Behaviour, the brief's six points

- **Outcomes, messages, ordering, the recorded `op` and `tool`** — preserved: the probe's eleven
  answers and records byte-identical at base and tip; `failed` is the same closure, still noting
  each outcome once.
- **The departure** — right. `failed` reads `op` and `name` from `_answer`'s frame when it is
  called. With the draft's cut, `name = raw_name[:_ECHO_CHARS]` would have been bound inside
  `_call_answer`, so `failed` would have seen `name` still `None` on `unknown_tool` and on the
  three `invalid_arguments` refusals. That is a changed record. An existing check would have
  caught it: `tests/unit/test_tools.py:1247` asserts `r.outcomes[0].tool == "f" and
  r.outcomes[0].op == "call"` on an `invalid_arguments` outcome. The builder's cut keeps `op =
  "call"` and `name` in `_answer` and hands both on. `_call_answer`'s own `op = "call"` is a
  local for its two `ToolOutcome` lines; it never reaches `failed`, and `failed` has already
  seen `"call"`. No recorded outcome changes (the probe).
- **The async paths and cancellation** — the code is moved verbatim (`_ToolLoop`, `_Post`,
  `_cancel_post`, `_close_awaitable`, `_Work`, `_Interrupted`). `test_async_tools.py` passes,
  and its three `asyncio` patches now go through `H.asyncio`. That is the same module object,
  so the effect is the same. Windows' `own-runner` and `own-embedding` shards are green in the
  run.
- **The door's byte budget** — `_TOOL_REQUEST_BYTES` and `_TOOL_RESPONSE_BYTES` are defined
  and read only in `_tool_host.py`, at lines 278, 282, 847 and 849. The six response-cap
  patches name `H`, and the by-name check holds that no other module binds them.
- **No module-identity dependence** — none of the three modules reads `__module__` or
  `sys.modules`, or keys anything on its own name. `Tool` stays in `wasi_python.tools`, so
  `test_tools.py`'s pickled `Tool` still loads.

## Findings, most severe first

No High, no Medium.

1. **Low: two lengths in the landing notes are commit 2's, not the built commit's**
   (`context/specifications/110-tools-behind-its-facade.md`, *Sizes and lengths*). The notes
   say `_answer` is 58 lines and `_call_answer` 43, "EXECUTED on `64d8d76`" (the move). On the
   move and on `54fe623` they are 59 and 46 (EXECUTED, `ast` line spans). The move wrapped two
   f-strings past 100 columns: one line in `_answer` (`unknown operation …`) and three in
   `_call_answer` (`unknown argument …`). Failure: a later review that re-measures reads a
   function as grown by four lines. Fix text, in place of "`_answer` 58, `_call_answer` 43.":
   "`_answer` 59, `_call_answer` 46 (58 and 43 at commit 2, before the move wrapped two
   f-strings past 100 columns)." This touches only `context/`, so it needs no round.
2. **Low: no check holds the `tool` field of an `unknown_tool` outcome, the one the departure
   was made to keep** (`tests/unit/test_tools.py`). `test_tools.py:1247` holds `op` and `tool`
   on an `invalid_arguments` outcome. No check under `tests/` asserts `(op, tool)` on an
   `unknown_tool` or a non-string-tool `protocol` outcome (EXECUTED: `grep -rnE 'o\.op|o\.tool\b'
   tests` shows only `ok`, `too_large`, `timeout`, `tool_error` and `invalid_arguments` rows). The
   build is right today (the probe). Failure: a later cut of `_answer` that binds `name` after
   `failed` reads it would record `('call', None, 'unknown_tool')`, and the judge would stay
   green. Fix text: a unit row in `tests/unit/test_tools.py`,
   `test_a_refused_call_records_its_operation_and_tool`. It sends a frame with `"tool": 7`, then
   `"tool": "nope"`, then `"args": []` to one `H._ToolHost`, and asserts `[(o.op, o.tool,
   o.outcome) for o in host.record.outcomes] == [("call", None, "protocol"), ("call", "nope",
   "unknown_tool"), ("call", "<name>", "invalid_arguments")]`. That is a new check and a claim
   (`units = 2`), so it may instead be answered in writing as a follow-up for a later
   specification of the tool protocol. Rule 3 asks for it once the failure mode has been seen,
   and the builder has seen it.
3. **Note: the judge edits beyond the lists only re-point names.** These are the three
   `T.asyncio` patches (`test_async_tools.py:419, 553, 1123`), the three by-name imports of
   `_ToolHost` (`test_v1_4_embedding.py`, in the functions at 2836, 2863 and 3523; two of them
   now import `tool` from `.tools` on a line of its own), and one comment in `test_scan.py:1556`.
   Read against rule 4, none edits an expectation. The two docstring edits in `test_rules.py`
   and `test_runner_package.py` change words only. The new `BY_NAME_MODULES` stale-entry line in
   `_by_name_errors` adds a finding and removes none. The judge is not weakened. The seam
   exemption covers the same patched names it covered when they lived in `tools.py`. The by-name
   rule now also holds those names, so what each patch rests on is checked for the first time.
4. **Note: the private-API grep's one tool hit moves file.** The hit is `self._context()`,
   `_tool_host.py:686`. It was `tools.py`'s, and it is the frame host's own method, not
   wasmtime-py's. The rules check's `(?<!self)` lookbehind already excludes it, and that check
   PASSED. The rubric's raw grep counts it, now under `_tool_host.py`: 86 lines at base and 86
   at tip.

## Structure (reviews README 4a and the rubric)

4a, one line: the diff adds no concern, no lifecycle flag, no module-level mutable or lock, no
test seam, no platform branch, no private-API use, and no function past 80 lines. Two functions
leave the allowance, and one module leaves the size allowance. Its Kind line (**parallel-safe**)
is right, and no rubric row moves toward Weak.

Measurements, EXECUTED by the rubric's commands at the base `5af0a42` (unpacked by `git
archive`) and at `54fe623`:

| what (row) | at `5af0a42` | at `54fe623` | note |
|---|---|---|---|
| module sizes (R7) | `tools.py` 2,449; `mounts.py` 2,206; 12,873 in all; two over 1,500 | `tools.py` 727, `_tool_schema.py` 785, `_tool_host.py` 1,027; `mounts.py` 2,206; 12,964 in all; one over 1,500 | +91 lines: two docstrings, import blocks, two section headings, the wrapped lines; `ALLOWED` one entry |
| functions over 80 lines (R7) | 9 (`runner.py` 4, `tools.py` 2, `_call.py`, `_process.py`, `_sessions.py` 1 each) | 7 (`runner.py` 4, the other three 1 each) | `LONG_FUNCTIONS` two entries shorter, none added |
| module-level mutables and locks (R4) | 0 | 0 | the facade's `_MAKING` is a `ContextVar`; `_EMPTY`, a read-only `{}`, moves with its reader |
| private-API uses (R3) | 86 lines: `_wasmtime_ffi.py` 84, `_places.py` 1, `tools.py` 1 | 86 lines: `_wasmtime_ffi.py` 84, `_places.py` 1, `_tool_host.py` 1 | the two non-ffi hits are not the engine's (Note 4); the rules check PASSED |
| platform branches (R5) | 3, all in `_platform.py` | 3, all in `_platform.py` | none in the three |
| private names the judge patches (R6) | 30 distinct; `T._TOOL_RESPONSE_BYTES` 6 | 30 distinct; `H._TOOL_RESPONSE_BYTES` 6, `H._encode`, `H._parse`, `H._TOKEN`, `S._key` 1 each | same sites, the operand now names the defining module |
| `Any` / `type: ignore` (R7) | 338 / 25; in `tools.py` 98 lines, 74 annotations, 3 ignores | 340 / 25; in the three 100 lines (33, 44, 23), 74 annotations, 3 ignores | the +2 are the two `from typing import Any` lines criterion 11 named |
| the type checker (R7) | `mypy --strict` clean, 18 files | clean, 20 files; `test_src_type_checks_under_mypy_strict` PASSED | |
| citations of the archive (R7) | 0; 0 | 0; 0 | `(056)` rewritten as words in commit 2 |

The eight rows, against the last scorecard (the chain's integration review,
`wave-structural-chain-103-109-integration-2026-10-21.md`, at `1b85fe1`):

| row | then | now | reason |
|---|---|---|---|
| R1 Contract | Strong | Strong | `public_api.txt` byte-identical; `wasi_python.tools` defines every public name; the facade's docstring unchanged |
| R2 Safety | Strong | Strong | every bound is read in its defining module (the by-name check, now over the two private modules); no default or cap moved (the probe) |
| R3 Layering | Strong | Strong, firmer | the one file of three concerns becomes `_tool_schema` → `tools` → `_tool_host`, one direction and no cycle. The order is written as `TOOLS` and held by its own check. `import wasi_python` still loads none of the three. No private API |
| R4 Process state | Strong | Strong | no mutable or lock added; no lifecycle touched |
| R5 Portability | Strong | Strong | no platform branch in the three |
| R6 Testability | Adequate | Adequate | the ten tool patches stay module-level bounds and wraps, now named on the defining module and held by the by-name rule. The seam exemption is exactly two names wider in spelling and no wider in substance. The constructor-parameter form stays reserved (Scope). It does not move toward Weak |
| R7 Evolvability | Adequate | Adequate, toward Strong | modules over the ceiling go from 2 to 1 and functions over 80 lines from 9 to 7; the largest tool module is 1,027 lines; mypy clean; `Any` annotations flat at 74; ignores flat at 25; no citation |
| R8 Operability | Strong | Strong | the records and messages are byte-identical (the probe, the 0-fail scoreboard); `ToolRecord` and `ToolOutcome` unchanged |

Structural verdict: the structure holds.

## Constitution checks

- §4 constraints: the change is `src/` and the judge only. No input, artifact, recipe, patch or
  download moves, and no fuel or byte row changes (the release record has no GREW line). It uses
  uv only. The two new modules carry their reasons in words, and no `context/` citation is
  added. The judge-hash change is stated with its `--accept-judge` reason.
- §5.6: the build is reviewed by an agent that wrote none of it, on the builder's run on the
  exact code commit, read back; the pre-build review (required: runner code) is cited in the
  Status line.
- §7 never-do list: nothing tripped. No check, golden output, gap, allowance list or progress
  file is weakened. `ALLOWED` and `LONG_FUNCTIONS` only shrink, and `SEAM_ALLOWED` is untouched.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 —
2. Finding 2 —

## Verdict

Lands. The move preserves behaviour (verbatim by AST, byte-identical answers and records over
every envelope branch, green on three systems), the departure keeps the records, the judge is
only re-pointed, and the two Lows need no further round once they are answered in writing.

## One line

The tool protocol is three modules in one checked direction, each byte of its answers the same.
Lands, with two Lows: a length in the notes, and a record field no check yet holds.
