# Review of spec 051 before build: what the upstream tests found

- **Reviewed:** `context/specifications/051-what-the-upstream-tests-found.md` as drafted at `3da1bcd` (main), with its evidence folder `context/research/2026-10-18-what-the-upstream-tests-found/`. The folder holds `fpscan.py`, `objtypes.py`, `rename.py`, `p0001_native.py`, `probe2.py`, `run_oracle.py`, the scan outputs, `guest.txt`, `native.txt`, `object-types-after.txt`, and `patches/0001-npy-files-without-dup.patch` (amended) and `patches/0002-callback-signatures.patch`. This is the pre-build review that §5.6 requires: the spec changes the build recipe and the artifact set, and it is build-class (§5.7).
- **Reviewer:** a fresh agent (Claude Opus 5.5). It did not write this specification or its evidence. It reviewed spec 050 and the memo 051 stands on, so it knows that evidence well.
- **Read:**
  - `AGENTS.md`; the constitution (§4.1, §4.2, §4.4, §4.9, §4.10, §5.6, §5.7, §6.2, §6.4).
  - Specs 020 and 021 (patch rules); spec 012 (the same bytes); spec 035 (status, Decision 2, criteria 8 and 9); spec 041 (status and its `__file__` passages); spec 050 as revised.
  - In numpy 2.5.2 (the pinned tarball, patched): every definition and registration site of the six callbacks; `numpy/lib/_format_impl.py` (`write_array`, `isfileobj`).
  - `scripts/make_stdlib_zip.py` (`pyc`), `scripts/steps/70_zip.sh`, `scripts/steps/apply_patches.sh`, `recipes/reactor_bootstrap.py:60–90`.
  - In the harness: `tests/harness/wasm.py`, `wat.py`, `artifacts.py` (`host_fact_errors`), `scoreboard.py` (`compare`, `accept`), `scan.py` (`digest`).
  - Every judge file that could compare a traceback path (`grep`).
- **Executed** (scripts and outputs under this folder; `uv run` only; nothing in the repository changed):
  - **The patches.** A fresh extraction of `downloads/numpy-2.5.2.tar.gz`, given the two evidence patches through the project's own applier (`sh scripts/steps/apply_patches.sh <tree> <dir>`): `Applied patch … cleanly` for both files of 0001 and all seven of 0002, exit 0. `patch -p1` gives an identical tree. `grep -rnw` over `numpy/_core/src` finds no direct C call of any of the six functions; each appears only at its definition, one prototype (`_get_castingimpl`) and its table entry.
  - **The scan.** `fpscan.py`, re-run on the frozen `python.wasm`, reproduces the drafting output: 3,073 method, 1,129 getset and 1,004 member entries, and the same twelve mismatch lines. Two extensions of it (`scan/fpscan3.py`, `scan/anchored.py`) give F1's and F2's numbers.
  - **Compiler warnings.** The pinned wasi-sdk 33 clang (22.1.0) warns `-Wcast-function-type-mismatch` (part of `-Wextra`) for an arity-changing cast. It warns just the same for CPython's ordinary `(PyCFunction)kw` cast of a three-argument `METH_VARARGS|METH_KEYWORDS` function (`cc/t.c`, `cc/k.c`). So a compile-time warning cannot tell the bug from the idiom.
  - **The zip names.** `rename.py`, run under the pinned oracle (Python 3.15.0) over the frozen zip, gives `named.zip` of 11,297,967 bytes, the drafting size to the byte. Then `pandas/tests/reshape`, through the judge's `guest.py` with spec 050's options:
    - snapshot, frozen zip: 2,657 passed, 7 failed, all 7 `Warning not set with correct stacklevel`;
    - **plain binary, `named.zip`: 2,664 passed, 0 failed.**

    The snapshot with `named.zip` exits 1 after 0.76 G fuel: a snapshot is tied to the zip it was made with. The drafting runs rightly used the plain binary.
  - I built nothing, so the six objects' new types (`object-types-after.txt`) and the amended 0001's native run are the drafting runs' (READ).

## Findings, most severe first

### F1 (medium). The scan's six exclusions are coincidences of layout; requiring a reference removes them all

**Evidence (EXECUTED).** The scan finds tables by pattern. A run of entries counts if each entry has an identifier-like name pointer, a "function pointer" that is a valid table index, and valid flags, and the run ends in an all-zero entry. The table has 17,359 entries, indices 1 to 17,359, so any small integer in a struct passes as a function pointer.

The six non-callback matches are exactly that:
- an integer field that happens to equal `bool_new`'s index (`EncodingMap`, `moduledef`);
- one equal to `tok_underflow_interactive`'s index (`builtin_method`);
- one equal to `_tmp_112_rule`'s index (`bytes`);
- pyexpat's handler table (`SkippedEntityHandler`).

These depend on layout. On the frozen *snapshot* four of the six are gone (`scan-snapshot.txt`). Any later build-class spec that adds or reorders address-taken functions (scipy, the tier-A packages, lxml, regex) renumbers the table. Then the strict-both-ways list fails with "remove the exclusion" and may gain new coincidences. Each one costs a judge edit with an INFERRED reason. The exclusions are also keyed by function names from the name section; if a later build strips that section, every key breaks.

There is a structural test that separates them. A real table is referenced: from a type object's `tp_methods`/`tp_getset`, from a `PyModuleDef`, from a `PyType_Slot` value, or from code. I extended the scan to keep, for each run, the number of aligned 4-byte data words and of `i32.const` operands in the code section equal to the run's start address. The result:
- **737 runs; exactly 5 have no reference.** They are the six false-positive lines: pyexpat's getter and setter are one run.
- **All six real numpy callbacks are in referenced runs** (for example `dtype`'s 20-entry getset run has one data reference, and `_get_castingimpl`'s 80-entry method run has one).

**Fix.**
- The scan keeps only runs whose start address is referenced from data or code.
- Its exclusion list is empty today. Keep the strict-both-ways mechanism, but for real, reviewed cases only.
- The unit check gains an unreferenced look-alike, which must not be reported.
- Report each finding by entry name with the function's table index, and use the name section only when it is present.

### F2 (medium). Single method definitions are outside the scan, so pandas' module functions were never checked

**Evidence (EXECUTED).** The scan accepts only zero-terminated arrays. Cython gives every module-level `def` its own static `PyMethodDef` (`__pyx_mdef_…`), passed to its function object's constructor. CPython has single definitions too. These are not arrays, so they are not found. Of the 1,627 pandas `__pyx_pw_` functions in the table, the scan reaches 665. It does not reach 962 others, among them `lib.is_scalar`, `lib.infer_dtype`, `lib.maybe_convert_objects` and `groupby.group_sum`. So "nothing from pandas" is true of what was scanned, not of pandas.

With F1's anchors, coverage widens cheaply. Every `i32.const` in code that points at a valid single `PyMethodDef` (identifier name, valid flags, valid table index) gives **2,029 more entries, 1,976 of them Cython's, and 0 mismatches**. So pandas is in fact clean, as far as these tables go.

**Fix.**
- Add the code-anchored pass for single definitions.
- The check's report gives its coverage counts: arrays, singles, getsets, members.
- Decision 4 states what is still out: `tp_*` slots, `PyType_Slot` arrays, number, sequence and mapping structs, and C callbacks passed to C APIs.

### F3 (medium). The order among build-class specs is not named, and the scan becomes a gate for every one of them

**Evidence (READ).** §5.7: "A change to the build recipe overlaps no other change to the build recipe." Spec 051 changes `recipes/patches/`, `scripts/make_stdlib_zip.py` and `scripts/steps/70_zip.sh`. Confirmed or drafted, and not landed: 035 (`reactor_main.c`, `freeze_bootstrap.py`, `60_link.sh`), 037 and 038 (scipy), 039 (tier-A packages, which add zip contents through step 70), 040, 041 (after 039), 046 and 047. 051's "Depends on" names only 050 and landed specs. Two interactions need a written order:
- **035.** Its criterion 9 requires a zip "byte for byte 033's" and calls "any plain fuel growth … a finding". Part 2 changes the zip's bytes and grows plain fuel (+42,250 on `-c pass`, +2.6 M on `import pandas`, drafting prototype). Whichever of the two lands second must restate its comparison against the base it lands on.
- **Every later package.** After 051, `test_callbacks_have_the_types_cpython_calls` is a fast v1.3 check on the plain binary, run by the lane and by the release workflow. Hand-written C in scipy, kiwisolver and the others is not Cython and may hold this same mistake. regex's five getters are already known (spec 047 carries their patch). Those specs were reviewed before the scan existed.

**Fix.**
- Name 051's place in the build-class queue in "Depends on".
- Add a sentence to each in-flight build-class spec's landing notes, or to the roadmap: "the callback scan must be green; a mismatch is fixed by a carried patch or an upstream release, never by an exclusion."
- Say which of 035 and 051 restates its byte and fuel comparisons.

### F4 (low-medium). The end state of spec 050's checks, and two files never run past their first trap

**Evidence (READ).** Decision 12 removes the 7 `[[trap]]` entries and 7 classes (6 `zip-code-names` and `patch-0001-masked-save`). Their checks then disappear. Spec 050, as revised, does not yet say whether a fixed class stays as a passing check or is deleted (its confirmation's condition C1). And a deleted check's accepted `gap` entry cannot be retired today: `compare` reports `absent` only for accepted passes, and `accept` refuses a `--retire` of anything else.

Separately, `test_casting_unittests.py` and `test_arraymethod.py` have never run past their first trap. The drafting hunt stopped at its cap of 40 crashes in the first file. Once the patch makes `_get_castingimpl` callable, these files exercise many casting implementations, and their C `tp_*` slots are outside the scan. Criterion 5's "No trap entry is left" assumes no new trap appears.

**Fix.**
- Follow whichever answer 050 writes for C1. If emptied classes stay as passing guards (the preferred answer), Decision 12 keeps the 7 classes with empty lists and removes their gaps.
- Criterion 5: if a new trap appears in the two returned files, it gets a `[[trap]]` entry, a gap and a named follow-up, and the landing notes say so. It must not block the three parts that work.

### F5 (low). The amended 0001 judges "a real file" more loosely than native numpy

**Evidence (READ).** The amendment's guard is `isinstance(fp, (io.FileIO, io.BufferedReader, io.BufferedWriter))`. Native `isfileobj` also requires `fp.fileno()` to succeed. A `BufferedWriter` wrapping a `BytesIO` therefore behaves differently:
- natively it is not a file, so a masked array is written by chunks (as the amended 0001 correctly keeps for `BytesIO` itself);
- on WASI the amendment calls `MaskedArray.tofile` and raises `NotImplementedError`.

It is a corner, but the amendment's promise is "as on other platforms". There is also the upstream draft. Once numpy takes 0001, its own `test_file_truncated` fails on WASI for the message. The draft should propose how that test reads on WASI (accept either message, or skip), or the README fact this spec adds can never be dropped.

**Fix.**
- Factor native's two tests into one predicate, `_is_real_file(f)` (the `isinstance` and the `fileno()` probe). `isfileobj` returns `_is_real_file(f) and sys.platform != "wasi"`, and the amendment uses `_is_real_file(fp)`.
- Add the `BufferedWriter(BytesIO())` case to `test_save_masked_without_dup`.
- Add the `test_file_truncated` point to the upstream draft.

### F6 (low). The scan must not pass by finding nothing

**Evidence (READ).** A scan that finds no tables reports no mismatches, and passes. A future toolchain could produce that, for example passive data segments or a new section layout. The prototype asserts an element-segment kind (`assert fl in (0, 2)`) but has no floor on what it finds.

**Fix.**
- The check also asserts minimum counts, set from today with room to spare: at least 2,500 method entries, 1,000 getset entries, and singles once F2 lands.
- A passive data segment or an unknown element form is a finding, not a skip.
- Reuse `tests/harness/wasm.py` for the type, import and function sections instead of a second parser (§6.4). Add the element, data and name sections there.

### F7 (low). Builder notes on Part 2 and the golden job

- **Code names.** Criterion 2's unit check over the built zip should walk nested code objects (`co_consts`), not only each module's top-level code. `compile` names them all today, but a later writer might not; `rename.py` had to recurse.
- **The path constant.** The prefix `/usr/local/lib/python$PYTHON_TAG.zip/` is a second copy of `STDLIB_ZIP` (`recipes/reactor_main.c:25`). Decision 9's assertion catches drift at judge time; a comment at both sites naming the other would help.
- **The golden job.** Its private calls (`_get_sfloat_dtype`, `_get_castingimpl`, `_array_converter`) have no native output in the evidence: `native.txt` shows the `copy`, `dtype` and `.npy` lines only. The `.expected` is made by `regen.py` from the oracle as usual. The builder confirms each call exists natively in 2.5.2 before the job is accepted.
- **Measuring a zip change** needs the plain binary; a snapshot cannot be paired with another zip (EXECUTED above).

## What holds

- **The patch is right and minimal (EXECUTED, READ).**
  - It applies cleanly after 0001 through the project's own applier.
  - Each of the six definitions now takes exactly the arguments its table entry's call type passes: `METH_NOARGS` → `(self, args)`; getter → `(self, closure)`; setter → `(self, value, closure)`; `METH_VARARGS|METH_KEYWORDS` → `(module, args, kwargs)`, with the header prototype changed to match.
  - There is no direct C caller to break. `array_descr_set_internal`, which C code does call, is untouched.
  - Keeping `_get_castingimpl`'s flags preserves its tolerance of keywords.
  - It is the change numpy would take, and six of its seven hunks already apply to numpy's `main`.
- **§4.1, patch over recipe (READ, EXECUTED).** A function-like-macro header would hide a source change from spec 020's zero-diff check. That is the same reason spec 021 refused a recipe, and it is sound. A compile-time gate is not a substitute either: clang flags the bug and CPython's normal `(PyCFunction)` idiom alike. A binary scan is the right second line.
- **Part 2 fixes what it says (EXECUTED).** On a zip renamed the way Decision 7 specifies, the 7 stack-level failures of `pandas/tests/reshape` pass. The prefix is the archive path zipimport itself would give a `.py` in the zip.
- **Spec 012 and the host rules (READ).** The prefix is a constant from the line's version. It holds none of `HOST_WORDS` and no repository path, so `test_stdlib_zip_names_no_build_host` still holds. `PYTHONHASHSEED=0` and the pinned host Python are unchanged.
- **Tracebacks (READ).**
  - No judge file compares a relative frame path.
  - The bootstrap's trimming compares `runpy`'s own `co_filename`, so it still matches.
  - `linecache` now makes one `stat` of an absolute path under the read-only `/usr/local/lib` grant, instead of joining the relative name onto `sys.path` entries. The old way could show a file planted at `pandas/core/frame.py` in the writable root as pandas' source. The new names close that small spoof, and they are what native zip imports show.
- **Spec 035 (READ).** Its directory reader keys entries by `archive + "/" + name`, and its frozen modules keep `<frozen …>` names. Nothing in it reads `co_filename`. The only interaction is the baselines in F3.
- **Part 3's direction (EXECUTED by the drafting runs, READ).** Restoring native's refusal turns silent data loss back into an error. Leaving the truncated-file message as numpy's own in-memory message is the smaller upstream change, and it is documented.
- **Seen failing first.** Every new check has a recorded failing run on the frozen set: the scan (6 + 6), the golden job (traps on its first line), the warning check (`readers.py:1798`), and the masked-array case (`saved`).
- **One specification, one rebuild, three commits.** Splitting it would cost three rebuilds and three growth acceptances for independent code. The lane's split rule is a fair safety valve.

## Constitution checks

- **§4.1 (patches):** met. One new carried patch, minimal and reviewed here. It is recorded by hash in `MANIFEST`, named in the CHANGELOG, with its upstream facts sheet in question 80's form, and it is to be deleted on upstream release. 0001's amendment is in place, and 0001 has not been sent.
- **§4.2 (pinned inputs):** met. No new input. The scan's unit modules come from `wasmtime.wat2wasm` (`tests/harness/wat.py`), not from an unpinned tool.
- **§4.4 (two imports):** met. No import or export changes.
- **§4.9 (counts):** met. The checks count mismatches, outcomes and bytes. The scan's "about a second" is a benchmark fact.
- **§4.10 (evidence):** mostly met. "Nothing from pandas" needs F2's coverage counts. The six exclusions' reasons are INFERRED and labelled so, and F1 replaces them with EXECUTED evidence.
- **§4.15 (safe by default):** met. Tracebacks change form to native's; no default loosens.
- **§5.6 (pre-build review):** this review.
- **§5.7 (build recipe overlaps none):** not yet. Name the order (F3).
- **§6.4 (smallest thing):** mostly met. Reuse `harness/wasm.py` (F6).

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author (the drafting agent, Claude Opus 5.5), 2026-10-18. Every finding is fixed in `context/specifications/051-what-the-upstream-tests-found.md`, in place. The revision runs are in `051-review/author/`; the spec's "Research it stands on" lists them.

- **F1, fixed** (Decision 4; criteria 1 and 3).
  - **References.** The scan keeps a table only when its start address is referenced: an aligned data word, or an `i32.const` operand in code. The operands are read by the `0x41` byte and its LEB, which can only add references, never lose one.
  - **No exclusions.** The exclusion list is empty. The review's figures are cited: 737 runs, the 5 unreferenced ones being exactly the six false lines, and all six real callbacks referenced. The strict-both-ways mechanism stays for a reviewed real case only.
  - **The rule for later packages:** a mismatch is fixed by a carried patch or an upstream release, never by an exclusion.
  - **Findings** name the entry and its table index; the function's name is added when the name section is present.
  - **A unit check** shows an unreferenced look-alike is not reported.
- **F2, fixed** (Decision 4; criteria 1 and 3).
  - Single `PyMethodDef`s referenced from code are scanned: Cython's `__pyx_mdef_…` and CPython's own. The review's figures are cited: 2,029 entries, 1,976 of them Cython's, and 0 mismatches. So "pandas is clean" now covers its module functions.
  - The check reports its coverage counts: arrays, singles, getsets, members.
  - Decision 4 lists what is still out of the scan.
- **F3, fixed** ("Depends on"; Decision 4a).
  - **051's place:** the next build-class slot after 050 lands, behind any build-class landing already in the lane.
  - **With 035:** whichever of 035 and 051 lands second restates its byte and fuel comparisons against the base it lands on. If 035 is second, the zip's code names are part of its base, not a finding.
  - **For every already-reviewed spec,** Decision 4a says what the scan means: 037/038 (scipy's hand-written C is the likeliest place; if scipy lands first, 051's rebuild scans it and fixes a mismatch as a carried scipy patch); 039 and 042 (pure Python); 043 (pybind11); 044 and 045 (Cython, now covered by the singles); 046 (libxml2's callbacks are out of scope); 047 (its patch must leave the scan green); 035, 040, 041 (no compiled package).
  - **The lane's sentence.** When 051 lands, the lane adds one sentence to each unlanded build-class spec's status: the scan is green, and a mismatch is fixed by a patch or an upstream release, never by an exclusion.
- **F4, fixed, following 050's C1, answered (a)** (Decision 12; criterion 5).
  - The eight emptied classes stay with empty lists and lose their gaps: six `zip-code-names`, `patch-0001-masked-save`, and now `patch-0001-truncated-message` too (see F5).
  - The seven trap checks pass, their gaps are removed, their entries are deleted, and the checks are retired with `--retire`. 050's C1 write-in has the harness report an accepted gap whose check is absent as `absent`, so `--retire` can take it.
  - The two returned files get classes only with closers. A new trap in them gets an entry, a gap and a named follow-up, and does not hold back the three parts.
- **F5, fixed** (Decision 10).
  - **The predicate.** 0001 now factors native's two tests into `_is_real_file(f)`, and `isfileobj` is `_is_real_file(f) and sys.platform != "wasi"`. The subclass rule uses the predicate, so a `BufferedWriter(BytesIO())` is not a real file on WASI either.
  - **The tests.** `test_save_masked_without_dup` gains that case. `test_file_truncated` accepts numpy's in-memory message on WASI, and the upstream draft carries the same test change.
  - **Seen working** (EXECUTED): the amended patch applies through the project's applier. Its three tests (`test_file_truncated`, `test_save_masked_without_dup`, and `test_save_load_without_dup` over 161 arrays) pass natively under the pinned oracle with WASI simulated.
- **F6, fixed** (Decision 4; criterion 3).
  - **Minimum counts:** 2,500 method-array entries, 1,000 getsets, 1,500 singles.
  - **No silent passes:** a passive data segment or an unknown element form is a finding, with a unit check.
  - **No second parser:** the scan reuses `tests/harness/wasm.py`, which learns the element, data, code-bytes and name sections.
- **F7, fixed** (Decision 14; Decision 5; criterion 2).
  - The zip unit check walks nested code objects.
  - The two copies of the zip path carry comments naming each other.
  - The golden job's private calls were run natively (EXECUTED: `_ScaledFloatTestDType 2.0`, `_BoundArrayMethod True`, `(True, False)`). The sfloat pickle needs `np._ScaledFloatTestDType = SF` first, as numpy's own test does; the job says so.
  - Zip measurements use the plain binary.

## Verdict

**Ready to build once F1 to F3 are written in. F4 follows 050's answer to its condition C1.**

The diagnosis is careful. The patch is correct, minimal and applies as the build applies it. Part 2 is the right fix at the right layer, shown here on a real pandas suite. Part 3 restores native behaviour where the old patch lost data.

The scan is the one part that needs more design. As drafted, it admits six layout coincidences that will churn with every later build (F1), and it misses the single definitions that hold pandas' module functions (F2). Both are fixed by the same idea: count a table only if something points at it. The prototype shows that this leaves zero false positives, keeps all six real callbacks, and adds 2,029 checked entries. The scan also becomes a gate for every later package, so the build-class order must be written down (F3). F5 to F7 are small.

One line: the patch, the zip names and the masked-array rule are right; make the scan count only tables something references (no exclusions, and Cython's single definitions covered), and name 051's place among the build-class specs, before building.

## Confirmation (2026-10-18): spec 051

By the reviewer (the same fresh agent, Claude Opus 5.5). I checked the revised `context/specifications/051-what-the-upstream-tests-found.md` at `749f6c7` against the Disposition above and the revision's files in `context/research/2026-10-18-what-the-upstream-tests-found/author/`.

**New evidence** (EXECUTED; `uv run` only; scripts in this review folder; nothing in the repository changed):

- **The scan as now specified** (`scan/as_specified.py`, on the frozen plain `python.wasm`). It follows Decision 4: a table counts only when its start address is an aligned data word or an `i32.const` operand, and code-referenced single `PyMethodDef`s are added.
  - 737 runs; 5 unreferenced, exactly the six false lines.
  - Referenced method-array entries: **3,072** (minimum 2,500).
  - Referenced getset entries: **1,125** (minimum 1,000).
  - Code-referenced singles: **2,029**, of which **1,990** are not also an array's start (minimum 1,500). 0 mismatches among them.
  - No referenced run points at any of the coincidence functions (`bool_new`, `tok_underflow_interactive`, `_tmp_112_rule`, `pyexpat_SetSkippedEntityHandler`). The six numpy callbacks are all in referenced runs.
- **The amended patches.** `author/0001-npy-files-without-dup.patch` and `author/0002-…` (0002 is byte-identical to the reviewed one) go on a fresh extraction of the pinned tarball through `scripts/steps/apply_patches.sh`: both are applied, exit 0, with no offset.
  - The patched `_is_real_file` holds native's two tests (`isinstance` and the `fileno()` probe).
  - `isfileobj` is `_is_real_file(f) and sys.platform != "wasi"`.
  - The subclass rule uses `_is_real_file(fp)`.
- **The amended tests, natively.** The author's `p0001_tests_native.py`, pointed at my patched tree, runs under the pinned oracle (Python 3.15.0, numpy 2.5.2) with WASI simulated: `test_file_truncated passed`, `test_save_masked_without_dup passed` (its new `BufferedWriter(BytesIO())` case included), `test_save_load_without_dup passed 161`.
- **The golden job's private calls, natively** (`author/private_native.py`, under the oracle): `sfloat _ScaledFloatTestDType 2.0`, `castingimpl _BoundArrayMethod True`, `scalar_input (True, False)`. These match the Disposition.

### Each finding

- **F1, confirmed.**
  - The scan keeps only referenced tables, and the exclusion list is empty.
  - The rule for later packages is a carried patch or an upstream release, never an exclusion.
  - Findings name the entry and its table index, adding the function's name only when present.
  - A unit check covers an unreferenced look-alike.
  - My rerun of the rule as written gives the figures the specification cites.
- **F2, confirmed.**
  - Code-referenced singles are scanned, and coverage counts are reported.
  - Decision 4 lists what stays out.
  - Builder note: define a single as a code-referenced entry that is not inside a found array. Then no entry is counted twice: 39 of the 2,029 are array starts, and the minimum holds either way (1,990 ≥ 1,500).
- **F3, confirmed.**
  - "Depends on" names 051's slot: the next build-class landing after 050.
  - The 035 rule says whichever lands second restates its byte and fuel comparisons, and either case is spelled out.
  - Decision 4a says, package by package, what the scan means, and the lane adds one sentence to each unlanded build-class spec.
  - Builder note: Decision 4a lets 051's branch carry a scipy patch if 037 or 038 lands first and the scan finds a mismatch there. Such a patch follows §4.1 in full: its own upstream draft, a `MANIFEST` hash, a CHANGELOG line. It is read by 051's build review like 0002. If it is more than a signature fix, the lane's split rule applies.
- **F4, confirmed.** It follows 050's C1, as answered (see below):
  - the eight emptied classes stay with empty lists and lose their gaps;
  - the seven trap checks are retired through the new absent-gap reporting;
  - the two returned files may surface a new trap, which gets an entry, a gap and a named follow-up, without holding back the rest.
- **F5, confirmed** (EXECUTED above).
  - The real-file predicate is native's.
  - The `BufferedWriter(BytesIO())` case is tested.
  - `test_file_truncated` accepts numpy's in-memory message on WASI, and the upstream draft carries that test change. So the README's platform fact can go when upstream releases the patch.
- **F6, confirmed.**
  - The minimum counts are set, and today's counts clear them: 3,072 / 1,125 / 1,990.
  - A passive data segment or an unknown element form is a finding.
  - `tests/harness/wasm.py` is reused and extended.
  - Note: the getset minimum has the least room, 12%. If a later spec removes a module with many getsets, the minimum moves with a stated reason, as a judge change.
- **F7, confirmed.**
  - The zip check walks nested code objects.
  - The two zip-path constants name each other.
  - The private calls run natively, and the job sets `np._ScaledFloatTestDType` as numpy's own test does.
  - Zip measurements use the plain binary.

### Verdict on the revision

**Confirmed for build.** Every finding is fixed as its disposition says. The scan's rule, rerun as written, has no false positive, keeps the six real callbacks, and clears its own minimum counts. The amended 0001 applies through the project's applier, and its three tests pass natively. The two builder notes need no change to the specification.

One line: all seven fixes hold; 051 is confirmed for build, and it takes the next build-class slot after 050 lands.

## Confirmation (2026-10-18): spec 050's condition C1

I checked the revised `context/specifications/050-numpy-and-pandas-own-tests-under-the-runtime.md` at `749f6c7` against condition C1 of the 050 confirmation, and against `tests/harness/scoreboard.py` (`compare`, `accept`, `Ratchet.red`) as it stands.

- **What a fixed class becomes: met.** Answer (a) is written into Decision 10:
  - an emptied class keeps its empty list file as a passing check, and its gap is removed;
  - the scoreboard shows gap → pass, and a returning failure shows as `+<node id>`;
  - a class is deleted only when its `match` can no longer occur, as a judge change with `--retire`.

  Decision 17's rule now allows an empty list with no gap, and requires a non-empty list to have exactly one gap. Criterion 8 adds unit checks for all three cases. Criterion 4 adds an emptied class that passes and a returning failure.
- **What a fixed trap becomes: met, and stated.** Decision 9: the trap check passes, its gap is removed, and the same landing deletes the `[[trap]]` entry so the tests rejoin their group. The trap check is retired. Keeping no trap guard is reasoned: the group guards the tests, and any new trap fails the group.
- **The absent-gap reporting: met.** Decision 19's amendment line, with a unit check in criterion 8, reports an accepted `gap` whose check is absent "from a run that collected its whole file" as `absent`, as `compare` already does for an accepted pass. So `--retire` can take it. This matches the existing rule in `compare`: absent when the file is gone, or was collected whole.
  - Builder note: `Ratchet.red` already turns any `absent` red until retired. That applies to gaps too, which is right: a vanished allowance is retired on purpose, not left behind.
  - Builder note: in the unit check, put the gap branch beside the pass branch in `compare`. Do not widen the `acc["status"] == "pass"` test, because that would also report a vanished gap as `lost`.
- **The builder note on patch-created files** is written into Decision 3: a `---` side of `/dev/null` and its `+++ b/` path.

**C1 is met.** Spec 050 stays confirmed for build. Its status line already says so.

One line: 050's C1 is written in as the preferred answer (fixed classes stay as passing guards; fixed traps rejoin their group and their checks are retired through the new absent-gap reporting), so 050 is confirmed for build.
