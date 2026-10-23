# Review of 051 — What the upstream tests found (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, its pre-build review or its confirmation. I read `AGENTS.md`, the constitution, specification 051 with its landing notes, the pre-build review with its Disposition and Confirmation, the parts of 035 and 050 that 051 names, and the diff (`git log -p main..HEAD`; the branch's base is main's tip `fe67910`, so no rebase is pending). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/051-what-the-upstream-tests-found` in `../wasi_python-051`: `19d0db5` (Part 1), `44ede8a` (Part 2), `fffd8ad` (Part 3), `d41b434` (landing notes; it touches only the specification). The worktree's own `build/artifacts/` (`SHA256SUMS` lines `python.wasm 5648e4c5…`, `python-snapshot.wasm f94dec53…`, `python-stdlib.zip daf2cdd8…`, `MANIFEST c4474f76…`). The builder's base set, in its scratch folder (`051/base-artifacts/`, `python.wasm 4befe9de…`, the frozen set's).
- **Edited nothing in any repository tree.** My work is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/051-buildreview/` (below, `$R`). Every mutant was restored from a byte copy (`$R/backup/`, with `SUMS`), checked with `cmp`, and `git status --short` is empty at the end (EXECUTED). The judge writes `build/progress/latest.json` (ignored); I put back the copy from my full judge run. One slip: I read `latest.json` once with a bare `python3` (a JSON read, nothing run from the tree). Every other command went through `uv run`.

## What I ran (EXECUTED unless labelled)

- **The full judge**, `uv run pytest` (slow included, no `--accept`), in the worktree on its own artifacts (`$R/judge-full.txt`). Also `uv run ruff check src tests` and `uv run ruff format --check src tests`.
- **Each intermediate commit.** `git archive` of `19d0db5`, `44ede8a` and, as a control, `main`, into `$R/c-*`. In each: `ruff check`, `ruff format --check`, and `pytest tests/unit`.
- **The scan, reproduced**, on the base and the new `python.wasm` (`$R/scripts/scanboth.py`).
- **Scan probes**, all read-only on the binaries:
  - `$R/scripts/probe.py`: the scan without the member pass, and how member tables overlap getset runs.
  - `$R/scripts/members.py`: every member-pass entry's type code, offset and flags.
  - `$R/scripts/unref.py`: every unreferenced pattern run, type-checked.
  - `$R/scripts/dropped.py`: data-referenced entries that sit in no kept table.
- **Eleven scan mutants** (`$R/scripts/runmut.sh`, `$R/mutants-scan.txt`). Each one is applied to `tests/harness/callbacks.py`. Then `tests/unit/test_callbacks.py` runs, and the scan runs on both binaries. Then the original is restored.
- **Three patch mutants** (`$R/mutants-patches.txt`). Each edits a carried patch in place, then runs `test_source_tree_matches_its_tarball`, `test_manifest_recipes_match_the_tree` and `test_carried_patches_follow_the_rules`, then restores the patch.
- **0001's behaviour, natively** (`$R/mutants-0001-native.txt`). A fresh extraction of the pinned numpy tarball got both patches through `scripts/steps/apply_patches.sh` (both "applied", every file "cleanly"). Then numpy's three tests ran under the pinned oracle with WASI simulated, through the author's runner, which I pointed at my files. I ran the unchanged module and three mutants.
- **Registration sites** of the six callbacks in the patched tree (`grep`), against their flags.
- **Fuel probes, base set against new** (`$R/scripts/snapprobe.py`): `-c pass`, the GC state at start, and `gc.disable()`, on both binaries.
- **A traceback**, `json.loads('{')`, on both binaries of both sets (`$R/scripts/tb.py`).
- **The zips compared** (`zipfile`, host Python): members, order, dates, compression, modes.
- **The Linux rebuild's outputs** (READ, the builder's `051/linux/`). I diffed its `SHA256SUMS` with the worktree's and hashed its `python.wasm`. I did not redo the container build.
- **An extended-const data offset** (built with `wat.build`) given to `wasm.parse_file`.

## The judge (EXECUTED, `$R/judge-full.txt`)

`1165 passed, 10 skipped in 213.87s`. Scoreboard: `251/254 pass · 0 gap · 3 blocked · 0 fail`; v1.3 27/27, v1.5 18/18. Blocked: `prior-art clones`, `three systems`, `wheel`, as on main. Ratchet against `4430c5a662`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 6 · grew 36`, `RED: 36 metric(s) grew`. The one "unrun locally" is `test_every_prior_art_clone_has_its_licence_recorded`: the worktree has no clones. It is not red, and the main tree has them. The landing notes say `unrun 0`, which is right, but they do not mention it. The six gains are the six new checks. The 36 growths are exactly the landing notes' list. The judge-changed files are exactly the nine this change touches. `ruff check` and `ruff format --check` are clean (67 files).

Each new check passed: the scan, whose reason reads `scanned 3072 method-array entries, 1989 single definitions, 1125 getset entries, 429 member entries`; the golden job on both binaries; the warning check on both; the zip's code names; `test_npy_files_round_trip` on both; and `test_goldens_reproduce_under_the_pinned_oracle`, which runs `callbacks` under the oracle at two hash seeds.

## Findings, most severe first

### 1. Medium (the lane's, before either lands): the order with 050 is written on one side only, and 050 is nearly ready

- **What 051 says.** Its "Depends on" and landing notes say: 050 has not landed, so 051 lands first, and 050 re-drafts its tables from the rebuilt set (READ).
- **What 050 says.** 050's specification assumes the opposite order (READ):
  - line 42: 051 "edits this specification's files when it lands after this one";
  - line 370: each trap gap "closes with spec 051";
  - lines 450–460: eight classes, each with "spec 051" as its closer;
  - line 469: "051 moves the closers when it lands".
- **Where 050 stands.** It is not waiting. Its worktree (`../wasi_python-050`, `0d505d0`, "the build review's F1 to F6 fixed") holds `tests/upstream/numpy.toml` with the `[[trap]]` entries (READ, read-only). So whichever lands second meets work that nobody has written down.
  - **If 050 lands first,** 051 cannot land as built. Decision 12 and criterion 5 then apply:
    - delete the 7 traps and retire their checks;
    - empty the 8 classes and remove their gaps;
    - run the two returned files.

    That needs a new full judge run with 050's suites. The landing notes say plainly that this was not done.
  - **If 051 lands first,** 050's tables are wrong on the new set:
    - the 7 trap entries and their gaps;
    - the `zip-code-names` and `patch-0001-*` classes;
    - `test_casting_unittests.py` and `test_arraymethod.py` in `not_selected`;
    - the `passes` figures.

    050's builder must judge again on 051's set and re-draft. Nothing in 050's text tells them so.
- **Fix.** Before either lands, the lane picks the order. Then one line goes into each specification's status saying who restates what.
  - **I lean to 051 first.** It fixes the product. 050 then sets its baselines on the fixed product. Seven trap checks are then never created only to be retired.
  - **050's builder needs the line now,** because 050 is in flight.

### 2. Low-medium: three scan rules have no unit check, and after landing nothing else guards them

The unit suite and the judge on today's binary both pass with these mutants in place (EXECUTED, `$R/mutants-scan.txt`):

| mutant | unit checks | new binary | base binary |
|---|---|---|---|
| M2: setters not checked | 7 passed | pass | 5 findings: **`array_descr_set` lost** |
| M11: code references ignored (data words only) | 7 passed | pass (arrays 2,952 ≥ 2,500) | 5 findings: **`gentype___copy__` lost** |
| M8: results not compared | 7 passed | pass | 6 (the params differ too) |

M11 matters most. numpy sets `tp_methods` for the generic scalar type in C code at run time, so `gentype_methods` is referenced only by an `i32.const` (INFERRED from M11's result). That is the callback behind `copy.copy`, the one users meet most. The minimum counts do not catch M2 or M11. Once the base binary is gone, only the unit suite can show these rules still work.

**Fix.** Add to `_module()`:
- a getset whose setter has the wrong type;
- a method array referenced only from code (an `i32.const` of its address, no data word).

Optionally, add a member array that would read as a getset mismatch without the member pass. M4 (no member pass) is otherwise caught only by the real binary (72 findings).

The other mutants are killed:
- **By the unit suite:** M1 (`METH_NOARGS` arity), M3 (no reference rule), M5 (operands read without overlap), M6 (no singles; the minimum count fails too), M9 (unread segments not reported), M10 (data references ignored).
- **By the real binary only:** M4 and M7 (the `METH_FASTCALL|METH_KEYWORDS` arity).

### 3. Low: the two intermediate commits fail `ruff format --check`

`19d0db5` and `44ede8a` each give "1 file would be reformatted". The file is `tests/checks/test_v1_3_data_stack.py`, which lacks one blank line before `# Spec 051, Decision 4`. That line arrives only in `fffd8ad` (Part 3's diff, `@@ -434,6 +454,7 @@`), an artefact of splitting the work through the index.

Otherwise each intermediate commit is green as far as it can be judged without its own build:
- `ruff check` is clean;
- `pytest tests/unit` gives 896 and 900 passed, with the same 1 failure and 3 errors as `main`'s own export. Those four come from not being a git checkout (the landing-lane tests).

AGENTS rule 9 says a commit on main is green on its own, and the lane fast-forwards all four commits. **Fix:** move the blank line into Part 1, or have the lane say how it treats a multi-commit landing. The final state is clean, so this costs nothing at run time; it matters for bisecting and for rule 9.

### 4. Low: an unknown constant expression now breaks the wall checks, not only the scan

`wasm.parse` used to skip the element, data and code sections. Now it reads them. `const_i32` raises `WasmError` on any constant expression other than `i32.const` or `global.get`.

EXECUTED: a module with an extended-const data offset (`i32.add (i32.const 16) (i32.const 16)`) raises `constant expression longer than one instruction`. `artifacts.module_errors` and the export checks share this parser. They catch the error and fail. So a toolchain that emits extended-const offsets (wasm-ld can, for PIC) turns the import and export checks red for a reason that is not the wall.

This fails closed, so nothing passes silently. But the landing note says unread segments are recorded "so the wall checks still read a binary the scan flags". That holds for passive and unknown-form segments, and not for this case. **Fix (either one):**
- read the extended-const opcodes to their `end` and record the segment in `unread`;
- or say in the docstring that an unknown constant expression stops every reader of the binary.

### 5. Low: 035's own text still says "a zip byte for byte 033's"

051's "Depends on" holds the rule: whichever of 035 and 051 lands second restates its byte and fuel comparisons. 035's builder, though, reads 035. Its criterion 9 and Decision 10 compare with 033's zip and call any plain fuel growth a finding (READ).

What 035 must restate, if 051 lands first:
- **Its zip comparison.** EXECUTED: 051's zip has the same 1,760 members, names, order, dates, compression and modes as the frozen zip. Only the 1,102 `.pyc` differ. 035's per-member directory figures read none of the `.pyc` bytes, so they should not move (INFERRED).
- **Its absolute fuel baselines.** These move: plain `-c pass` is +34,790.

035's directory reader keys entries by `archive + "/" + name`, and its frozen modules keep `<frozen …>` names. Neither touches `co_filename`, so the two changes do not otherwise interact (READ, as the pre-build review found).

**Fix:** at landing, the lane adds that line to 035's status, beside Decision 4a's sentence.

### 6. Informational: the table rule, and the getset-at-indices-1–20 limit

- **Can the member-first rule hide a real mismatch today?** No. Each point below is EXECUTED:
  - All 429 member-pass entries have valid `T_*` type codes (0, 1, 2, 4, 5, 6, 7, 12, 14, 16, 18, 19), offsets ≤ 660, and flags 0, 1 or 3.
  - No getset run overlaps a member table in part. 139 member entries also read as getsets, and all of them are members.
  - No data-referenced address holds a valid method or getset entry outside a kept table, on either binary.
  - Every unreferenced pattern run is a coincidence: 3 method runs and 25 getset runs. They are method arrays read at a 20-byte stride, members, pyexpat's handler table, and integers equal to a table index. None is a real callback table.
- **What remains possible.** In a later link, a referenced getset array could be read as members and never checked. Every one of its entries would need a getter at table index 0 to 20 and a NULL doc. Its closure would need to be NULL or a valid address. That is unlikely but silent. A cheap guard: when the name section is present, report a function at indices 1–20 that also appears as a callback in a kept table.
- **The "members" count is inflated.** About 104 of the 429 are not `PyMemberDef`s. They are Cython type-info records (`int64_t`, `uint8_t`, …, type 0, flags 0). This is harmless, since no minimum uses members, but the coverage line overstates them.
- **The rule differs slightly from the specification.** The specification keeps a table when its start address is referenced. The scan keeps a run from its first referenced entry instead. This keeps more than the specification asks, never less. The singles count, 1,989 against the review's 1,990, is explained in the notes (one entry inside an array but not its start).

### 7. Informational: the snapshot's fuel fall

Base against new (EXECUTED, `$R/scripts/snapprobe.py`):

| snapshot program | base | new | change |
|---|---|---|---|
| `-c pass` | 82,143,381 | 82,060,117 | −83,264 |
| GC state | 82,738,436 | 82,661,433 | −77,003 |
| `gc.disable()` | 82,238,486 | 82,131,069 | −107,417 |

The GC counts at start are equal: `(40, 0, 0)`, with `[52, 4, 1]` collections. So the fall is not a collection that moved. It also varies by program. That fits a different heap layout after restore (allocator state), but this is INFERRED and not studied.

A fall needs no acceptance. Every snapshot growth is in a check that imports modules after the snapshot, which the longer names explain. That includes `test_fuel_is_exact_across_tool_calls`, which imports the `host` package after the snapshot (INFERRED from step 70's note that the snapshot does not pre-import it). **The account is enough to accept.** The growth reason should say the fall was not studied.

### 8. Informational: no change needed

- **Patch 0002 is correct for each call type** (READ in the patched tree):
  - `gentype___copy__` and `sfloat___reduce__` are registered `METH_NOARGS` and now take `(self, args)`.
  - `_get_castingimpl` is registered `METH_VARARGS | METH_KEYWORDS`, at `multiarraymodule.c:4789`. It and its prototype now take `(module, args, kwargs)`.
  - The two getters take `(self, closure)`. `array_descr_set` is registered as a setter (`getset.c:787`) and takes `(self, value, closure)`.
  - CPython 3.15's `methodobject.h` and `descrobject.h` give exactly the arities the scan's `METH_CALLS`, `GETTER` and `SETTER` use. No flag is missing (`METH_STACKLESS` is 0 outside Stackless).
- **Patch 0001's amended predicate is native's, and its tests have teeth.** EXECUTED, natively, with WASI simulated: the unchanged module passes all three tests (`test_save_load_without_dup` over 161 arrays). Each mutant fails:
  - `_is_real_file` without the `fileno()` probe → `test_save_masked_without_dup` raises `NotImplementedError` at the `BufferedWriter(BytesIO())` line;
  - no subclass rule → `DID NOT RAISE`;
  - `test_file_truncated` without its WASI branch → `no match: EOF: reading array data …`.
- **The patch rules have teeth.** EXECUTED. Dropping 0002's `getset.c` hunk fails the zero-diff check, the `MANIFEST` check and the rules check. Changing one added line of 0002 fails the zero-diff and `MANIFEST` checks. So does making 0001's `isfileobj` WASI-blind. `MANIFEST`'s hashes for both patches, `reactor_main.c`, `make_stdlib_zip.py` and `70_zip.sh` equal the files'. The carried patches are byte for byte the author's reviewed ones. `fix.patch` in `13-…` is byte for byte 0002.
- **The golden job and its oracle evidence.** `callbacks.expected` reproduces under the pinned oracle at two hash seeds (`test_goldens_reproduce_under_the_pinned_oracle`, passed). Both binaries match it. The facts sheet's `guest-before.txt` and `guest-after.txt` record each call alone, before and after (READ). The private calls print only through `step`, so if a later pin renames one, the guest and the oracle fail the same way.
- **Step 90 refusing an untracked patch** is spec 012's rule (`assemble_artifacts.py:157`). `MANIFEST` is built from tracked recipe files, so a clean-clone build hashes the same. It worked as designed. Builders of later build-class specs should stage new recipe files before step 90.
- **`--code-prefix` under spec 012.**
  - The prefix is a constant from `PYTHON_TAG`. No host path enters, and `test_stdlib_zip_names_no_build_host` passes.
  - The Linux arm64 clean-clone build at `fffd8ad` wrote a `SHA256SUMS` byte-identical to the worktree's. Its `python.wasm` hashes `5648e4c5…` (EXECUTED diff and hash, of the builder's outputs).
  - The x86_64 and Windows rebuilds are the release workflow's, as the notes say.
- **Tracebacks** (EXECUTED). On the new set, both binaries print `File "/usr/local/lib/python315.zip/json/decoder.py", line 374, in raw_decode` where the base printed `File "json/decoder.py"`. The bootstrap's trimming still holds: no runpy or bootstrap frame. No source line is shown, as before. No judge check compares a relative path, since the full judge is green.
- **The facts sheet follows question 80's form** (READ). Question 80 is still the owner's to answer; this change follows its recommended form, as 041, 044, 045 and 048 did.
  - `pr.md` opens with "Read first" and numpy's AI policy, quoted: the disclosure clause and the two forbidden acts. It gives facts under numpy's template headings, with a suggested commit message and the facts for the AI disclosure.
  - `notes.md` records how the defect was found and checked. The draft has spec 020's six header lines, and its `Files:` names the seven paths. The rules check passes.
  - The Wasmtime 49 in the reproduction matches the pin (49.0.3).
  - **A wording nit:** `pr.md` says "every call of the table below", but the table is above.
- **0001's facts sheet `3-numpy-npy-wasi/fix.patch` predates the amendment.** Both drafts say so, and it is remade on rebase onto `main`. 0001's hunk headers lost their function context (`@@ -164,6 +164,7 @@`), which is cosmetic. Both are fine as they stand.
- **The plugin's `note`.** It sets a passing check's reason. `compare` and `accept` never read a pass's reason (READ, `scoreboard.py`), so it cannot change a verdict. It has no unit check of its own; the scan's check exercises it.

## Each Decision against the code

| Decision | Built as | Evidence |
|---|---|---|
| 1–2 the six callbacks, a carried patch | 0002, 7 files, `NPY_UNUSED` parameters, tables untouched | READ (patched tree); scan 0 findings, EXECUTED |
| 3 facts sheet, draft, README count, upstream table | `13-numpy-callback-signatures/`, the 0002 draft, README "2", row 13 | READ; rules check, EXECUTED |
| 4 the scan, references, singles, minimums, coverage | `harness/callbacks.py`, `wasm.py` readers, check with minimums and `note` | EXECUTED (reproduced 6 on base, 0 on new; probes; mutants) |
| 4a later specs | the lane's sentence at landing | not yet due |
| 5 golden job, seen failing first | `tests/jobs/callbacks.py`, `.expected`; traps on base | EXECUTED (judge), READ (`failing-first.txt`, `guest-before.txt`) |
| 6–9 zip code names | `--code-prefix`, step 70, comments at both sites, warning check, zip check in the guest | EXECUTED (judge; zip compare; traceback) |
| 10 0001 amended | `_is_real_file`, the subclass rule, two numpy tests, two guest cases | EXECUTED (natively with mutants; guest via judge) |
| 11 one branch, three commits | three parts plus notes; final state judged | EXECUTED; finding 3 |
| 12 050's TOML | not applied: 050 has not landed | finding 1 |
| 13 README, CHANGELOG | platform paragraph, patch count, tracebacks, six goldens | READ |
| 14 builder notes | nested walk; comments at both path sites; private calls confirmed; plain binary for zip measures | READ, EXECUTED |

## Acceptance criteria against evidence

1. **Seen failing first.**
   - The scan's six findings on the base binary, with the exclusions empty and the minimums met: EXECUTED.
   - The job traps on the base set; the warning check reports `readers.py:1798`; the masked case prints `saved`: READ (`051/failing-first.txt`, `evidence/guest-before.txt`).
   - **Met.**
2. **A full build.**
   - Step 40 applied both patches: READ (the notes; my own extraction gives "applied" for both).
   - The zero-diff check passes with the two patches: EXECUTED.
   - The scan is clean: EXECUTED.
   - Every code object, nested ones included, names the zip path: EXECUTED, as a guest check, because the host Python is 3.14.
   - The member list equals the frozen one: EXECUTED.
   - **Met.** The unit check over the built zip became a guest check; that is reasoned in the notes.
3. **After the build.**
   - The golden job equals the oracle on both binaries: EXECUTED.
   - The scan finds nothing, with no exclusion; coverage is 3,072 / 1,989 / 1,125, all above their minimums: EXECUTED.
   - The unit checks ask for: a referenced mismatch; an unreferenced look-alike; an exclusion that stops matching; a passive segment. All are present and pass: EXECUTED.
   - **Met, but see finding 2.** These checks do not guard the setter rule or code references.
4. **Spec 012.** A second host (Linux arm64) gave the same set: EXECUTED (diff of the builder's outputs). **Met.**
5. **050's suites.** N/A as built. **Open: depends on the order (finding 1).**
6. **The judge.** Green apart from growth; ruff is clean; lost 0: EXECUTED. **Met.** The flags are below.
7. **The documents.** README, CHANGELOG, both drafts, the facts sheet and the upstream table: READ. The rules check passes with two patches: EXECUTED. **Met.**

## The implementer's flags

- **Coverage figures and the table rule.** Reproduced exactly. The members-first limit hides nothing today (finding 6). It is load-bearing (M4: 72 false findings without it) but has no unit check (finding 2).
- **`wasm.py` raising against recording.** Recording unread segments is right. Raising on an unknown constant expression fails closed, but it couples the wall checks to the scan's reader (finding 4).
- **The commits split through the index.** Two intermediate commits fail `ruff format`. Everything else is green as far as it can be judged without their own builds (finding 3).
- **The golden job.** Sound (finding 8).
- **Step 90 and staging.** Spec 012's rule, working as designed (finding 8).
- **The snapshot fuel fall.** Probed: GC is not the cause. It is acceptable without further study (finding 7).

## Constitution checks

- **§4.1 (carried patches): met.**
  - One new patch, minimal, and correct for each call type.
  - Both patches are hashed in `MANIFEST`, named in the CHANGELOG, and drafted for the owner, with a facts sheet in question 80's form.
  - The zero-diff check passes with exactly the two patches, and fails on every patch mutant.
  - 0001 is amended in place. It has not been sent.
- **§4.2 (pinned inputs): met.** No new input. The scan's unit modules come from `wasmtime.wat2wasm`.
- **§4.3, §4.4 (one target; two imports): met.** No import or export changes; the wall checks pass.
- **§4.6 (artifacts out of git): met.**
- **§4.7 (prior art): met.** Nothing is drawn from `context/prior_art/`.
- **§4.8 (downloads untrusted).** The build and the judge are unchanged.
  - My native runs of numpy's own Python under the pinned oracle used the pinned tarball's source. The pre-build review ran it the same way.
  - The C sources were only read.
- **§4.9 (counts): met.** The scan counts mismatches and coverage. Its run time is not asserted.
- **§4.10 (evidence): met.** Every number in the notes that I re-ran matches: the scan, the ratchet, the growth list, the fuel figures, the zip sizes and the Linux hashes. Two gaps:
  - the snapshot fall is labelled "not studied", which is honest;
  - the notes do not mention "unrun locally 1", which is harmless.
- **§4.13 (tooling): met.** `uv` only in the change, and ruff is clean. My one bare `python3` read is disclosed above.
- **§4.14 (git): met.** One `spec/051-…` branch in its worktree. Nothing is pushed.
- **§4.15 (safe by default): met.** Tracebacks take native's form, and no default loosens.
- **§5.6 (reviews): met.** The pre-build review was confirmed. This is the build review.
- **§5.7 (one build-class landing at a time): met for the recipe.** The order with 050 and 035 must be written on both sides (findings 1 and 5).

## Disposition (filled in by the author, then confirmed by the reviewer)

By the builder (Claude Opus 5.5), 2026-10-18, in `../wasi_python-051` on `spec/051-what-the-upstream-tests-found`. The branch was rewritten (F3); the old tip was `d41b434`. Scratch evidence: the builder's `051/mut/` (mutants) and `051/judge-full-2.txt`.

- **F1, fixed (the order written on both sides).** The lane chose: 051 lands first; 050 rebases onto 051 and re-derives its tables on 051's set.
  - 051's Status and landing notes say so; Decision 12 and criterion 5 are 050's work.
  - 050's status gains one line: it rebases onto 051 and re-derives its seven traps and their gaps, the six `zip-code-names` and two `patch-0001-*` classes, the two files leaving `not_selected`, and each group's `passes`, doing itself what its text said 051 would do.
  - Decision 4a's sentence is now in the status of every unlanded specification it names (035, 037, 038, 039, 041, 042, 043, 044, 045, 046, 047; 040 has landed), on this branch, so this review sees what lands rather than the lane writing it.
- **F2, fixed.** `tests/unit/test_callbacks.py`'s module gains three entries: a getset `st` whose setter is `$two` (2 parameters, called with 3); a method array `{coded}` at 1700 that only an `i32.const 1700` points at; a method `void` whose function `(i32, i32) -> ()` returns nothing. Each of your mutants, applied to `tests/harness/callbacks.py` and restored (`cmp` identical), now fails `test_a_referenced_mismatch_is_found_and_a_look_alike_is_not` (EXECUTED):
  - M2 (setters not checked): loses `setter st: table index 22 has (i32, i32) -> (i32), called as (i32, i32, i32) -> (i32) (two)`;
  - M11 (data references only): `method coded` becomes `single method coded`, and the arrays count falls from 4 to 3;
  - M8 (params only): loses `method void: table index 24 has (i32, i32) -> (), called as (i32, i32) -> (i32) (void)`. The optional member-pass case was not added; M4 stays guarded by the real binary (72 findings).
- **F3, fixed by recreating the three commits.** `git reset --soft fe67910`, `git read-tree fe67910` (the index only), then each part staged with explicit paths, the three shared files (`test_v1_3_data_stack.py`, `README.md`, `CHANGELOG.md`) staged as blobs per part. The blank line now arrives in Part 1. Each part's tree, exported with `git archive` of the index before its commit, passes `ruff check` and `ruff format --check` (67 files) on its own (EXECUTED). The split stays three parts plus a notes commit; no squash was needed. The new parts differ from the old ones only by F2, F4 and the nit (`git diff fffd8ad <new Part 3>`: `pr.md`, `wasm.py`, `test_callbacks.py`).
- **F4, fixed.** `const_i32` reads a constant expression to its `end`. One `i32.const` gives the offset; any other expression of the extended-constant proposal (`i32.const`, `i64.const`, `global.get`, `i32`/`i64` `add`, `sub`, `mul`) records its segment in `unread` ("an offset that is not one i32.const"); only an opcode outside it raises, since its end cannot be found. The docstring says so. New unit check `test_an_extended_constant_offset_is_recorded_not_raised`: your module's data offset `i32.add (i32.const 16) (i32.const 16)` is in `unread`, the next segment is read, and `wall_errors` is `[]`. Seen failing on the old reader (EXECUTED): `WasmError: constant expression longer than one instruction`.
- **F5, fixed.** 035's status gains the line: 051 lands first; 035's absolute byte and fuel baselines (criterion 9, Decision 10) are restated against 051's set, and that difference is 051's, not a finding; its per-member directory figures hold, the member list unchanged.
- **F6, F7: noted.** The member-first limit stays documented in the scan's docstring; the inflated member count is harmless and named here. The snapshot fall: the landing notes say it was not studied; your GC probe is the evidence that it is not a moved collection.
- **The facts sheet's nit, fixed.** `pr.md` says "each call named in the next point", and that `_supports_unaligned` cannot be reached until `_get_castingimpl` works.
- **"unrun locally 1"** is now named in the landing notes.

No recipe byte or artifact changed: `build/artifacts/` is still `5648e4c5…`, `f94dec53…`, `daf2cdd8…`, `MANIFEST` `c4474f76…`. The full judge on it after the rewrite: 1,166 passed, 10 skipped; `251/254 pass · 0 gap · 3 blocked · 0 fail`, v1.3 27/27; `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 6 · grew 36` (red for growth only); `ruff check` and `ruff format --check` clean (EXECUTED, at `06f61aa` plus the notes and status edits).

## Verdict

**Land after findings 1 to 3. Findings 4 and 5 can be text, or go in the same follow-up commit.**

- **Finding 1** is the lane's decision, and one status line in 050 (or, if 050 goes first, 051 returns to its builder for Decision 12).
- **Finding 2** is two cases added to the unit module.
- **Finding 3** is a blank line moved into Part 1.

None of the three changes a recipe byte or an artifact, so the set judged here stands.

The build does what the specification asks:
- The patch is minimal and right for every call type.
- The scan reproduces its six findings on the frozen binary and none on the new one. No data-referenced callback table escapes it in this link.
- The zip's code objects carry the path zipimport would give, so pandas' warnings point at the caller.
- 0001 refuses a masked array again, and its tests have teeth.
- Linux arm64 rebuilds the same bytes.

**The lane's flags,** in the main tree on this set:

```
uv run pytest --accept "<spec 051: numpy callbacks get CPython's signatures (patch 0002); the zip's code objects carry the zip path; patch 0001 amended (masked arrays refused as natively)>" \
  --accept-judge "<spec 051: test_callbacks_have_the_types_cpython_calls (the scan, harness/callbacks.py, wasm.py's function/element/data/code/name readers, the plugin's note); test_callbacks_job_matches_native[plain|snapshot] with the golden job tests/jobs/callbacks.py and its .expected (jobs.JOBS); test_a_pandas_warning_names_the_callers_line[plain|snapshot]; test_zip_code_objects_carry_the_zip_path; test_npy_files_round_trip's masked and truncated cases; unit checks test_callbacks.py and test_build_scripts.py's code-prefix checks>" \
  --accept-growth "<zip +28,115 bytes (11,175,028 -> 11,203,143) and snapshot +23,169 bytes: every code object's co_filename now carries /usr/local/lib/python315.zip/; plain fuel +0.009% to +0.093% (-c pass +34,790, import pandas +3,448,744): the longer names unmarshalled at import; snapshot fuel grows only where modules load after the snapshot (+12,476 to +390,672), and falls elsewhere (not studied; GC counts at start unchanged); test_npy_files_round_trip +8.5% plain, +1.7% snapshot: two new cases, a judge change>"
```

- No `--retire`: no trap check exists while 050 is unlanded.
- No `--partial` on a machine with the artifact set.
- The artifacts' hashes must be `5648e4c5…`, `f94dec53…`, `daf2cdd8…`, with `MANIFEST` `c4474f76…`.
- At landing, the lane adds Decision 4a's sentence to each unlanded build-class specification, and finding 5's line to 035.

## One line

The patch, the scan, the zip's names and 0001's amendment all do what 051 says, and Linux rebuilds the same bytes. Before landing, settle the order with 050 in both texts, add the two unit cases that guard the setter rule and code references, and fix the intermediate commits' formatting.

## Confirmation (2026-10-18)

By the reviewer (the same fresh agent, Claude Opus 5.5). I checked the rewritten branch `spec/051-what-the-upstream-tests-found` (`fc6fe74`, `24b8ef5`, `06f61aa`, `d0fa87a`; the old tip was `d41b434`; the base is still main's `fe67910`) against my findings and the Disposition above. As before, I edited nothing in any repository tree. Every mutant was restored from a byte copy and checked with `cmp`. `git status --short` is empty at the end. Outputs are in `$R`: `judge-confirm.txt`, `mutants-scan-confirm.txt` and `mutants-wasm-confirm.txt`.

### What changed, and what did not (EXECUTED)

- **No recipe change.** `git diff --stat d41b434 HEAD -- recipes scripts downloads .github src` is empty.
- **The artifacts are unchanged.** `build/artifacts/` still hashes `5648e4c5…`, `f94dec53…` and `daf2cdd8…`.
- **What the rewrite touched.** Against the old parts, the new ones differ only in these files:
  - `tests/harness/wasm.py`;
  - `tests/unit/test_callbacks.py`;
  - the facts sheet's `pr.md`;
  - Part 1's blank line;
  - the status lines and landing notes.
- **Part 2's tree.** `git range-diff` shows Part 2's own diff unchanged. Its tree differs from the old one only by Part 1's carried changes.
- **The Linux same-bytes run was at `fffd8ad`.** It still stands, since no recipe byte moved.

### Each finding

- **F1, confirmed.** The order is now written on both sides.
  - **What 051 says.** Its Status and landing notes say: 051 lands first, and Decision 12 and criterion 5 are 050's work.
  - **What 050 says.** Its new status line says: rebase onto 051 and re-derive the seven `[[trap]]` entries and their gaps, the six `zip-code-names` and two `patch-0001-*` classes, the two files that leave `not_selected`, and each group's `passes`. It also says 050 now does itself the work its text gave to 051.
  - **The counts match 050's worktree** (READ, read-only): `numpy.toml` holds 7 `[[trap]]` entries. There are 6 `zip-code-names` classes (1 in numpy, 5 in pandas) and the two `patch-0001-*` classes.
  - **One limit of my check.** I take "the lane's order" as the coordinator's decision, as the Disposition reports it (READ).
- **F2, confirmed.** The unit module gains three cases:
  - a getset `st` with a two-parameter setter;
  - a method array `coded` that only an `i32.const` points at;
  - a method `void` with no result.

  I re-ran all eleven of my scan mutants against the new unit suite:
  - **Now killed by the unit suite** (each "1 failed, 7 passed"): M2 (setters not checked), M8 (results not compared), M11 (code references ignored).
  - **Still killed by the unit suite:** M1, M3, M5, M6, M9, M10.
  - **Still survive the unit suite:** M4 (no member pass) and M7 (`METH_FASTCALL|METH_KEYWORDS` arity). The real binary kills both: 72 and 2,576 findings. The Disposition says so, and I accept it.
- **F3, confirmed.** For each of `fc6fe74`, `24b8ef5` and `06f61aa`, exported with `git archive`:
  - `ruff check`: "All checks passed!";
  - `ruff format --check`: "67 files already formatted";
  - `pytest tests/unit`: 897, 901 and 901 passed. The only failures are the same 1 failure and 3 errors that `main`'s own export gives, which come from not being a git checkout.

  `d0fa87a` changes only text. The final tree is clean.
- **F4, confirmed.**
  - **What `const_i32` does now.**
    - It reads a constant expression to its `end`.
    - A lone `i32.const` gives the offset.
    - Any other expression from the extended-constant set records its segment in `unread`. That set is `i32.const`, `i64.const`, `global.get`, and `i32` or `i64` `add`, `sub` or `mul` (`0x6A`–`0x6C`, `0x7C`–`0x7E`, READ against the opcode table).
    - Only an opcode outside that set raises.
  - **The docstring matches the code.**
  - **The new unit check.** It shows the segment is recorded, the next segment is read, and `wall_errors` is empty.
  - **Both mutants are killed** (each "1 failed, 17 passed"):
    - W1: any expression's last `i32.const` is taken as the offset;
    - W2: `i32.add` raises again, the old behaviour.
  - **Not covered.** The `i64.const` skip has no unit case. A mistake there would make the parser lose its place, which fails loudly (INFERRED). It is acceptable.
- **F5, confirmed.** 035's status now carries both lines:
  - Decision 4a's sentence;
  - 051 lands first, so criterion 9's and Decision 10's absolute byte and fuel baselines are restated against 051's set, and that difference is 051's, not a finding.

  One nit: the line states "its per-member directory figures hold" as fact. That is INFERRED, from the unchanged member list, which is EXECUTED. It needs no change before landing.
- **The facts sheet's nit, fixed.** `pr.md` now says "each call named in the next point", and that `_supports_unaligned` cannot be reached until `_get_castingimpl` works.

### Decision 4a's status lines (READ)

The sentence is now in the status of 035, 037, 038, 039, 041, 042, 043, 044, 045, 046 and 047. It is word for word the same in each. It reads: "`test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion". It sits ahead of each specification's existing status text, and that text is kept intact, including 046's and 047's conditions. The words "written in when 051 landed" become true when the branch lands.

**One gap, new here (low, text only).** Spec **023** (matplotlib, the first milestone) is build-class and not landed. It is third in the roadmap's build-class queue, and it links C extensions:
- matplotlib's own;
- kiwisolver;
- Pillow's.

Its status has no line, because Decision 4a's list never named it. I missed it in my first review too. 043's own clause ("its first milestone's C extensions, if already linked, are scanned now") shows that the scan binds 023 just the same. **Fix:** add the same sentence to 023's status, in this branch before the lane runs or by the lane at landing. It holds nothing back.

### The judge (EXECUTED, `$R/judge-confirm.txt`, in the worktree at `d0fa87a`, no `--accept`)

- `1166 passed, 10 skipped`.
- `251/254 pass · 0 gap · 3 blocked · 0 fail`; v1.3 27/27; v1.5 18/18.
- Blocked: `prior-art clones`, `three systems` and `wheel`, as on main.
- Ratchet against `4430c5a662`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 6 · grew 36`. It is red for growth only, and the growth list is the same as at `d41b434`.
- `ruff check` and `ruff format --check` are clean.
- The one extra pass is the new unit check.

### Lands?

**Yes.** 051 lands ahead of 050, as the lane ordered. Add Decision 4a's sentence to 023's status, here or by the lane at landing. Every other finding is fixed and checked above. The set judged here is the set that lands.

**The lane's flags,** in the main tree on this set:

```
uv run pytest --accept "<spec 051: numpy callbacks get CPython's signatures (patch 0002); the zip's code objects carry the zip path; patch 0001 amended (masked arrays refused as natively); build review context/reviews/051-what-the-upstream-tests-found-2026-10-18.md>" \
  --accept-judge "<spec 051: test_callbacks_have_the_types_cpython_calls (the scan, harness/callbacks.py, wasm.py's function/element/data/code/name readers and its extended-constant handling, the plugin's note); test_callbacks_job_matches_native[plain|snapshot] with the golden job tests/jobs/callbacks.py and its .expected (jobs.JOBS); test_a_pandas_warning_names_the_callers_line[plain|snapshot]; test_zip_code_objects_carry_the_zip_path; test_npy_files_round_trip's masked and truncated cases; unit checks test_callbacks.py and test_build_scripts.py's code-prefix checks>" \
  --accept-growth "<zip +28,115 bytes (11,175,028 -> 11,203,143) and snapshot +23,169 bytes: every code object's co_filename now carries /usr/local/lib/python315.zip/; plain fuel +0.009% to +0.093% (-c pass +34,790, import pandas +3,448,744): the longer names unmarshalled at import; snapshot fuel grows only where modules load after the snapshot (+12,476 to +390,672), and falls elsewhere (not studied; GC counts at start unchanged); test_npy_files_round_trip +8.5% plain, +1.7% snapshot: two new cases, a judge change>"
```

- No `--retire`: 050 has not landed.
- No `--partial` on a machine with the artifact set.
- The artifacts must hash `5648e4c5…`, `f94dec53…` and `daf2cdd8…`, with `MANIFEST` `c4474f76…`.
- After landing, 050 rebases onto main and re-derives its tables, as its new status line says.

One line: every finding is fixed and has teeth. The intermediate commits are green on their own, and the order with 050 is written on both sides. 051 lands, with Decision 4a's sentence also added to 023.
