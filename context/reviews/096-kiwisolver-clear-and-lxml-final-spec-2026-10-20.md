# Review of 096 — kiwisolver's `tp_clear` returns `int`, `lxml.html.diff` imports, and the scan reads type slots (pre-build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the author; pre-build review (constitution §5.6:
  the specification changes the build recipe and the artifact set)
- **Reviewed:** the specification as drafted, `spec/096-kiwisolver-clear-and-lxml-final` at
  `7f4f7b8` (base main `1ce7381`), with its upstream drafts `context/upstream/28-…/` and `29-…/`
  and its research folder `context/research/2026-10-20-the-slot-scan/`
- **Run:** none. This is a pre-build review, so there is no build and no release-workflow run.
- **Time box:** 40 minutes (build-class)
- **Re-ran** (all in the worktree; `build/lane.lock` was absent each time):
  - `uv run pytest tests/checks/test_rules.py::test_carried_patches_follow_the_rules
    tests/checks/test_rules.py::test_every_package_names_its_own_suite tests/unit/test_callbacks.py`
    → 13 passed, exit 0.
  - The drafting scanner over main's set (`build/artifacts/python.wasm` `b6953170…`, `SHA256SUMS`
    `4eaf1c3d…`) gives output identical to `slotscan-main-4eaf1c3d.txt` (`diff`: no difference).
  - The real applier, `scripts/steps/apply_patches.sh`, on fresh extractions of both pinned
    tarballs. Both hashes match `downloads/SHA256SUMS`. kiwisolver takes 0001, then 0002, and
    lxml takes 0001, all "cleanly", with no offset, exit 0.
  - The reviewer's own probe of what the scanner's rules drop without saying so (finding 1). It
    is in the scratchpad (`096-scripts/drops.py`), not on the branch.

## The patches against upstream (EXECUTED)

Each upstream commit was fetched read-only into a new, empty scratch folder, as
`github.com/<repo>/commit/<sha>.patch` and `.diff`. Its hunks were then `diff`ed against the
carried file.

- **kiwisolver.** Commit `4df2f39c016e90a5ffb3c6e71470146077100200` is pull request #245, merged
  (GitHub API: `merged true`, the same merge sha). It is one commit after the `1.5.1` tag, and it
  is on `main`. The newest tag is still `1.5.1`. The commit changes `ci.yml`, `release.yml` and
  four `py/src/*.cpp` files.
  - Its four C++ sections and `fix.patch` differ **only in the four `index` lines** (the blob
    hashes). Every hunk header, every context line and every `+` and `-` line is identical.
  - The blob hashes have to differ: the carried file is made against 1.5.1 with 0001 applied,
    and upstream's is made against `main`.
  - So the draft's claim, "its changed lines equal the commit's byte for byte", holds as worded.
    The briefing's "byte for byte" holds for the hunks, not for the whole file.
- **lxml.** Commit `dce45bd6e99b1368b24c32325ed8ac8156e81766` is #477's merge commit, merged. It
  has diverged from `lxml-6.1`.
  - Its `src/lxml/html/diff.py` section is one hunk with one line added, and its `index` line
    is `7ba79ef7f..a44e5f568`. That is the same pair of blobs as `fix.patch` (`7ba79ef..a44e5f5`).
  - So 6.1.3's `diff.py` is exactly upstream's file before the commit, and the patched file is
    exactly upstream's file after it. After the applier ran, `git hash-object` of the patched
    file gave `a44e5f568…`.
  - The only other difference is the hunk header's function context (`except ImportError:`
    against `class fake_cython:`). `git apply` ignores that text.
- **SHA-256** of the drafts as drafted: `138e3cbe…643e` and `0291f7c0…9334`, as the spec states.

## Acceptance criteria against evidence (as designed; nothing is built yet)

1. **The checks exist and were seen failing first.** Met as a plan.
   - Check 1: `kiwi_cycle_flushed.out` and `drafting-runs.out` show both binaries trapping
     (EXECUTED).
   - Check 2: `drafting-runs.out` and `guest_patched_diff.out` show the `TypeError` on both
     binaries (EXECUTED).
   - Check 3: the drafting scanner's four findings (re-run here and identical). The builder must
     re-see the failure with the judge's own code, and the spec says so.
   - The unit rows and their † mutants are the builder's to record.
2. **The build: both patches apply with no offset.** Met for the patches (EXECUTED above). The
   rest is the builder's.
3. **The same bytes everywhere.** The builder's.
4. **Each patch equals its draft.** The hashes are stated, and the drafts match upstream as
   described above.
5. **The scan on the rebuilt set.** The design falls short. As drafted, the scan's coverage
   misses real tables without saying so (finding 1), and the minimums cannot see one package's
   tables disappear (finding 2).
6. **The numbers.** The builder's.
7. **The judge.** The builder's and the lane's.
8. **The release dry run.** The builder's.

## Findings, most severe first

1. **Medium. The "starts like a record" rule drops real static types without saying so.**
   (Decision 3, the static-type rule; `slotscan.py`'s `cstring` and the type loop)
   - **The defect.** A type candidate must have a `tp_name` that `cstring` accepts. `cstring`
     accepts only bytes from 0x21 to 0x7E, so a space is refused, and at most 120 characters. A
     static type whose name contains a space is therefore never a candidate. No finding is
     raised and nothing is counted.
   - **Seen on main's set (EXECUTED, the reviewer's probe).** Two of CPython's own types are
     dropped this way:
     - `<dummy key> type` (`Objects/setobject.c:3197`);
     - `symtable entry` (`Python/symtable.c:216`).

     Both carry the static refcount, both have `ob_type` set to the same address the scan uses
     for `type`, and both are referenced. Their `tp_dealloc`, `tp_repr` and the rest are never
     checked.
   - **A second silent skip.** The loop runs `continue` on a candidate whose `ob_type` is
     neither 0 nor a metatype, and counts nothing. Today exactly one candidate hits this: a
     non-type static object, `indices`, whose `ob_type` is `ellipsis`.
   - **The counts are not bounded.** Unreferenced type candidates are counted, and there are 0
     today, but no check bounds the number.
   - **So claim (3) is not met as drafted.** The claim is "anything that starts like a record
     but doesn't parse is a finding". Decision 3 never defines "a C string", so the judge's
     version could repeat the same rule.
   - **Fix text for Decision 3 and check 3:**
     - "A C string is 1 to 256 bytes in 0x20–0x7E, ending in NUL."
     - "A word holding the static refcount whose `ob_type` is 0 or a metatype, and which is
       referenced, but whose `tp_name` is not a C string, is a finding: `does not read as a
       type (tp_name)`."
     - "The report counts every record it drops, by reason: unreferenced type candidates;
       candidates whose `ob_type` is neither 0 nor a metatype; spec-shaped records whose slots
       lie past the image."
     - "Check 3 requires unreferenced type candidates = 0."
     - Unit rows: a type named with a space is checked; a static-refcount record with `ob_type`
       0, referenced, whose name pointer is not a C string, is a finding (†).
     - The coverage line then reads 480 static types.
   - **The evidence that closes it:** the rewritten Decision 3, and the drafting scanner (or
     the builder's judge) re-run, showing both types checked.

2. **Medium. The minimums cannot see one package's tables disappear.** (check 3, the minimums)
   - **The defect.** The floors (400 of 478 types, 380 of 454 specs, 120 of 149 module
     definitions, 4,500 of 5,354 functions) leave room for about 16 to 19 % of each kind to
     vanish. kiwisolver's 6 specs could all fall out with every floor still green, as could
     Pillow's types or `_regex`'s module definition.
   - **How it could happen.** A change to the compiler or the source could move a C++ slot array
     into dynamic initialization, so it lands in `.bss`. The scan reads nothing in `.bss`, and
     its first-entry rule would skip that spec silently.
   - **Fix text for check 3:**
     - "Besides the minimums, the report must have checked these named records: the specs
       `kiwisolver.Constraint`, `kiwisolver.Expression`, `kiwisolver.Term` and
       `kiwisolver.Variable`, each with its `tp_clear`; the types `type`, `numpy.ndarray` and
       `ImagingCore`; and the module definition `_regex`."
     - Add one record per compiled package that has a static record: a pandas Cython spec, one
       of lxml's types, and one of matplotlib's modules, each named by the builder from the
       scan's output.
     - This makes criterion 5's one-off print a standing check.
   - **The evidence that closes it:** a unit row or mutant that hides kiwisolver's specs (for
     example, zero one spec's `slots` word) turns check 3 red, while the minimums alone stay
     green.

3. **Low. A NULL function in a `PyType_Slot` hides a spec or raises a false finding.**
   (Decision 3, the spec rule)
   - **The defect.** `readable` requires a function slot's value to be a table index. CPython's
     legacy slot iterator accepts NULL in a function slot: `Python/slots.c` around line 362 only
     logs "unwanted NULL in legacy struct".
   - **Failure.** A spec whose first entry is `{Py_tp_clear, NULL}` is skipped silently. The
     same entry later in the run raises a false "unreadable" finding.
   - **Fix text:** "A function slot whose value is 0 is readable. It is skipped and counted,
     never checked." Add a unit row for each position.

4. **Low. What the scan still cannot see should be said in the docstring.** (Decision 3, *Out
   of the scan*)
   - **Measured.** A spec whose first slot entry is unreadable is invisible, and this is
     irreducible by shape. Tightening the filter by flags (bit 18) and `basicsize ≥ 8` still
     leaves more than 300 `PyMethodDef` look-alikes (EXECUTED).
   - **Fix text:** add to the out-of-scope list: "type objects, specs, slot arrays and module
     definitions that C++ dynamic initialization fills (they lie in `.bss`), and a spec whose
     first entry is neither a known id nor NULL."
   - The ids 92 to 110 of `slots_generated.h` (`Py_tp_slots`, `Py_slot_subslots`, `Py_tp_name`,
     `Py_mod_state_clear`, …) are, correctly, findings when they appear in the middle of a run.
     Name them in the docstring, so that a future finding naming one is understood.

5. **Low. Decision 8's fallback for "066 lands first" contradicts 066's confirmed text.**
   - **The conflict.** 066 at `82f2d6c` depends on 096 (built after it, or stacked on its
     reviewed tip). If 096 slips, 066 keeps kiwisolver `later` with `closes_with = "spec 096"`,
     and lxml gets the class `lxml-html-diff`, closed by spec 096. It has no "trap entry" and no
     "failures" list. Decision 8 still describes 066's older delta.
   - **Fix text:** "066 depends on 096 (066, Depends on). If 066 nonetheless lands first, 096's
     builder closes 066's kiwisolver `later` entry and its `lxml-html-diff` class: kiwisolver
     becomes a suite under 066's rules, with its caps from a measured run on 096's set. The
     builder names each change in `--accept-judge`, and drops that flag's words 'no existing
     expectation edited'. If the kiwisolver group then shows a failure other than the trap, the
     builder stops and hands it to 066; it adds no allowance."

6. **Low. The mutant evidence does not show "nothing else new".** (`slotscan_mutants.py`)
   - **The defect.** The script keeps only the findings that contain the mutated record's name,
     so `slotscan_mutants.out` cannot show that no other finding appeared.
   - **Fix text:** the builder's judge mutants print the total number of findings (4 + 1) next
     to each mutated one.

7. **Low (a note). The coverage wording is ambiguous.** In "2,374 functions checked: pandas'
   Cython types 265, …, kiwisolver's 6", the 6 counts kiwisolver's specs (Solver, strength and
   the four), not its functions. kiwisolver has about 55 function slots. Fix text: "(specs:
   pandas' Cython types 265, …, kiwisolver's 6)".

8. **Note. The metatype rule over-includes, in the safe direction.** Any static type with
   `ob_type` 0 and `tp_basicsize ≥ 212` counts as a metatype. That can only add records to read
   (a possible false red), never hide one. 10 today. No change asked.

9. **Note. Main has moved.** Main has moved to `c091f3d` (roadmap only: the 095–098
   reservations). The builder rebases and restates the base. The roadmap's line for 096 matches
   this spec's scope.

## Checked and found sound

- **Slot numbers (READ, `build/Python-3.15.0/Include/slots_generated.h`).**
  `_Py_SLOT_COMPAT_VALUE(OLD, NEW)` gives NEW unless `Py_LIMITED_API` is below 3.15. In a type
  slot array, ids 1–4 and 88–91 are `bf_getbuffer`, `bf_releasebuffer`, `mp_ass_subscript` and
  `mp_length`. In a module's `m_slots`, ids 1–4 and 84–87 are `Py_mod_create`, `Py_mod_exec`,
  `Py_mod_multiple_interpreters` and `Py_mod_gil`. The scanner reads each table kind with its
  own map, so it never confuses the two. The unit row "`mp_length` as 4 and as 91" covers it.
- **The refcount constant and the layout (READ).**
  - `_Py_STATIC_IMMORTAL_INITIAL_REFCNT` is `7L << 28` (`Include/refcount.h:67`).
  - `PyTypeObject` ends with `tp_watched` (204), `tp_versions_used` (206) and `_tp_iteritem`
    (208), so the struct is 212 bytes.
  - `_Py_iteritemfunc` returns a two-word struct, so on wasm32 its type is
    `(i32, i32, i32) -> ()`, as the table says.
- **The recipe alternatives for lxml (Decision 4) hold.**
  - A stand-in `cython` in the zip would change `import cython` for every program in the guest.
  - A `sed` in step 54 would escape the tree check.
  - `import cython` is absolute, so no file beside `diff.py` can answer it.
  - Compiling with Cython is spec 046's declined Decision 1.
  - One more option was weighed and refused: a whole replacement `diff.py` under `recipes/` is
    a source change by another name, and a larger one.
  - So a carried patch is the right form, and it is upstream's own line.
- **The claim list and the flags are right for the design.**
  - Five new nodes: 2 + 2 + 1.
  - About twelve unit rows.
  - No retired check and no lost pass.
  - Growth: both binaries' byte rows and the zip.
  - The judge-hash files are named.
  - The README count goes from 10 to 12 (EXECUTED: 10 patches today), and the list at
    `README.md:424` becomes the twelve.
- **Upstream folder numbers.** 28 and 29 are free across main and every open branch (EXECUTED:
  25 is main's; 26 and 27 are 037's, 038's and 044's).
- **The other specifications.**
  - 037, 038 and 044 have no built set yet. Their hand-written scipy types will meet the
    widened scan, under the same "fixed by a carried patch or an upstream release, never an
    exclusion" rule that 051's Decision 4a set.
  - 043's contourpy and pybind11 types are heap types made at run time, which is outside the
    scan, and that is stated.
  - 043's own carried patches share only text (the count and the CHANGELOG), which the lane
    merges.
- **AGENTS.md rule 4 holds.** No check, golden output, gap, allowance or progress file is
  edited. The new minimums only add, and 051's `scan()` and its check are untouched. The only
  edit to an expectation would come in the "066 first" fallback, as a named judge change
  (finding 5 sharpens it).

## Constitution checks

- §4.1: both changes are carried patches. Each is upstream's merged change; it has its draft,
  it will be hashed in `MANIFEST` and named in the CHANGELOG, and the draft says when to delete
  it. The reasons no recipe file can do the job are stated and hold.
- §4.2: no new input. §4.4 (the guest's imports and exports): unchanged. §4.12: BSD-3-Clause,
  `LICENSES/` unchanged.
- §5.6: this is the pre-build review. A different agent reviews the build.
- §7: nothing tripped.

## Verdict

**Ready once findings 1 and 2 are written into Decision 3 and check 3, with their unit rows.**

- Finding 1: the C-string rule and the drops counted and bounded, so the two space-named types
  are read and no silent skip remains.
- Finding 2: named records the check must see, beside the minimums.
- Findings 3 to 7 are Lows, with their fix text above.
- Both patches are upstream's own changes, confirmed byte for byte in their hunks.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, on the branch rebased onto main `c091f3d`; each is written into the
specification (its section *Disposition of the pre-build review* says where). The drafting
scanner and its mutants were re-run on main's set after the changes.

1. **F1, written in.** Decision 3: a C string is 1 to 256 bytes in 0x20–0x7E ending in NUL; every
   static record is classified and each drop counted by reason (5,188 static instances, 1 record
   whose `tp_name` is not a pointer, 24 spec-shaped records with slots past the image); a
   referenced type candidate whose `tp_name` points into the image at no C string is a finding,
   and one whose `tp_name` is 0 is read as a type named at run time (one today, a numpy DType).
   Check 3 holds unreferenced type candidates at 0 (0 today). Re-run: 481 static types, with
   `<dummy key> type` and `symtable entry` read; the four kiwisolver findings and no other. Unit
   rows for a space-named type, an unreadable name, a NULL name and an unreferenced candidate; a
   mutant on `numpy.ndarray`'s `tp_name` gives the finding (total 6).
2. **F2, written in.** Check 3's named records: the four kiwisolver specs each with `tp_clear`,
   `pandas._libs.tslibs.timestamps._Timestamp`, `type`, `numpy.ndarray`, `ImagingCore`,
   `lxml.etree._Element`, `_regex` and `ft2font`. The mutant that zeroes `kiwisolver.Term`'s
   `slots` word is red by the named records alone, every minimum met (total 5, 453 specs); a unit
   row holds it.
3. **L3, written in.** A NULL function slot is readable, skipped and counted; unit rows at the
   first and a later entry.
4. **L4, written in.** The out-of-scope list and the ids 92 to 110 in the docstring.
5. **L5, written in.** Decision 8 follows 066's confirmed text (`later`, `closes_with = "spec
   096"`, the class `lxml-html-diff`, no allowance added).
6. **L6, written in.** Each mutant line prints the total.
7. **L7, written in.** "specs: … kiwisolver's 6".
8. **N8, N9.** No change for the metatype rule; rebased onto `c091f3d`.

## Confirmation

- **Date:** 2026-10-20. **Reviewer:** the same agent. **Reviewed:** `db3b1f3` on main `c091f3d`
  (`git diff c07d87d db3b1f3`: the spec, the drafting scanner, its mutants and outputs, the roadmap,
  this review copied). Time box 20 minutes. `build/lane.lock` absent at every run.
- **Re-ran (EXECUTED):** `uv run pytest tests/unit/test_callbacks.py` → 11 passed; the revised
  `slotscan.py` on main's set (`python.wasm` `b6953170…`) → identical to the new
  `slotscan-main-4eaf1c3d.txt` (4 findings, 481 types, 5,360 functions, 0 unreferenced
  candidates); the revised `slotscan_mutants.py` → identical to the new `slotscan_mutants.out`
  (each total printed; `kiwisolver.Term`'s `slots` zeroed gives two named-record findings with 453
  specs, every minimum met; `numpy.ndarray`'s `tp_name` at a zero word gives the `tp_name` finding).

### The findings against their answers

- **F1: answered.** Decision 3 defines a C string (0x20–0x7E, 1 to 256 bytes); every static
  record is classified and each drop counted by reason; a referenced candidate whose `tp_name`
  points into the image at no C string is a finding; unreferenced candidates held at 0 by check 3;
  unit rows with †. `<dummy key> type` and `symtable entry` are now read. My own probe of the new
  drops (scratchpad `096-scripts/drops2.py`): of the 5,188 records dropped for their `ob_type`,
  every one is a static instance (`str` 2,250, `int` 2,060, `bytes` 515, `tuple` 310, `numpy.dtype`
  24, …) or one of 7 unreferenced, unnamed coincidences whose `ob_type` is a small integer; **none
  looks like a type** (named, `tp_dealloc` a table index, `Py_TPFLAGS_DEFAULT`'s bit 18 set: 0). The
  one "tp_name neither 0 nor in the image" record is unreferenced string-table bytes (`tp_name`
  `0x7372`).
- **F2: answered.** Named records per compiled package (kiwisolver's four specs with their
  `tp_clear` as "spec slot" records, a pandas Cython spec, `type`, `numpy.ndarray`, `ImagingCore`,
  `lxml.etree._Element`, `_regex`, `ft2font`), a finding for each not read, a unit row with †, and
  the mutant that turns the check red by the named records alone. A NULL `tp_clear` in kiwisolver
  would also leave its "spec slot" record unread, so L3's new tolerance cannot hide it there.
- **L3 to L7: answered** as written (NULL function slots readable and counted; the out-of-scope
  list and ids 92–110; Decision 8 now follows 066's `82f2d6c`, with no allowance added; mutant
  totals; the coverage wording).

### The departure: `tp_name` 0 read as a type named at run time

**Accepted. It is not a hole for a slot defect.** A candidate with `tp_name` 0 is not dropped: it is
read as a type, every function field and suite is checked, and a mismatch is a finding (named
`<tp_name NULL at <address>>`, with the function's name from the name section). So a real defect in
such a type is red, not hidden. Reporting the record itself would have been the false positive the
builder describes: main's one is referenced, its `ob_type` is a metatype (`numpy._DTypeMeta`), and
it is a numpy DType whose name numpy fills in. What the departure loses is only the name in a
message, and the risk it adds runs the safe way (a non-type read as a type can only go red).

**One interplay to bound** (Low, fix text): the metatype rule requires a C-string `tp_name`, so a
*metatype* named at run time would not count as one, and static types whose `ob_type` is it would
fall into "dropped: `ob_type` neither 0 nor a metatype", counted but not read. None today (EXECUTED:
no record has the run-time-named type as its `ob_type`; the only nameless metatype-shaped record is
the unreferenced string-table bytes above). Fix text, either is enough:
- check 3 holds **"static types named at run time" at most 1** (1 today), so a second one is a
  reviewed change, not a quiet one; and add to that rule: "a dropped record whose `ob_type` is a
  type named at run time is a finding";
- or, simpler: the metatype rule accepts `tp_name` 0 as well as a C string (it still refuses a
  `tp_name` outside the image), so a run-time-named metatype classifies its instances.

I recommend the bound "at most 1" plus the second rule's unit row; the builder may choose either
option and say which in its landing notes. No new review round is needed for it (a Low with its
fix text).

### Verdict

**Confirmed for build**, with the one Low above written in by the builder (the bound on
run-time-named types and its interplay with the metatype rule).
