# Review of 069 — The snapshot pre-imports no package (pre-build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude). I did not write the specification or the research it
  rests on.
- **Reviewed:** the specification as drafted, on `spec/069-the-snapshot-pre-imports-no-package`
  at `21dd92e` (`git diff 4a94c14..21dd92e`: one file, +642). I read it against these sources:
  - decision 34 (`context/decisions.md`) and constitution §2, §4.1, §4.2, §4.6, §4.9, §4.10,
    §4.15, §5.6 and §5.7;
  - AGENTS.md rules 3, 4 and 6;
  - the memo `2026-10-18-one-pre-import-rule-for-every-package.md`;
  - `recipes/reactor_main.c`, `scripts/steps/80_snapshot.sh` and
    `scripts/assemble_artifacts.py`;
  - `tests/harness/scoreboard.py` (`compare` and `accept`) and `tests/upstream/drive.py`;
  - the checks the spec edits or removes;
  - spec 055's revision on `spec/055-bounded-sessions` (Decision 8, and its addendum's section
    8: P10b, P11, P12);
  - spec 047's text and the 046/047 review's condition;
  - main's roadmap at `ef1441b` (065 and 071);
  - the draft's evidence under `build/reviews-evidence/069-spec/`.
- **Re-ran.** Everything below is in this review's folder, `probes/` beside this file. Each run
  used read-only inputs: the evidence's `set-A/`, the frozen set and the judge's driver
  (`tests/harness/guest.py`). Neither git tree was written.
  - `uv run pytest -p no:cacheprovider -q tests/checks/test_rules.py` in the 069 worktree: 38
    passed, 2 skipped (`rules-run.txt`). The tree stayed clean.
  - **R1** `flush_probe.py`: does a file left open lose its bytes at exit when `__main__`
    defines a function?
  - **R2** `unfreeze_cost.py`: what an unfrozen heap costs a bare run on A.
  - **R3** `names_probe.py`: the start set on A, and the names check (a) would derive from the
    zip.
  - **R4** `map_diff.txt`: A's and B's link maps (written by the evidence's `relink.py`)
    compared.
  - No snapshot was rebuilt. The evidence's `work/A`, `work/B` and `set-A` were enough.

## What was verified

- **The list is stdlib only (EXECUTED, R3).** All eight names are in the guest's
  `sys.stdlib_module_names`, `_colorize` included. A's start set is 70 modules. Every top-level
  name in it is the stdlib's or one of `__main__`, `_reactor` and `_zip_directory`, as
  `modules_at_start.json` says. `ast` and `linecache` are in it, so spec 055's claim still holds.
  `hashlib` and `random` are not.
- **The method reproduces the set (READ, evidence).** B relinks to the frozen `python.wasm`
  (`1655014314805b58…`) and to the frozen snapshot. B's relinked plain binary gives the frozen
  fuel exactly (`plain_fuel.txt`). So the +18,944 is caused by the shorter constant alone.
- **The judge run against A (READ, logs).** `judge-set-A.log` ends with 3 failed, 1,583 passed;
  the ratchet shows lost 3 and grew 45, and the three lost checks are exactly (a), (f) and (g).
  The upstream log shows 20 passed, 12 xfailed and grew 11. The tables match `metrics-set-A.md`:
  29 plain rows plus 16 snapshot rows make the 45.
- **The judge changes are honest restatements, not weakenings (rule 4).**
  - The removed `snap.fuel * 10 < plain.fuel` for `import pandas` is exactly the property that
    decision 34 gives up.
  - (f) keeps its intent, which is to tell the two binaries apart, with a new marker.
  - (g) restates spec 054's pinned numbers the way 054 asked a later set to.
  - (g) also gets stronger. Its `numpy` shadow is now a real test on the snapshot: before, numpy
    was pre-imported, so the shadow could never take effect there (INFERRED from the program).
  - Each change goes through `--accept-judge` with its reason.
- **The upstream kit shadows nothing at import time (READ).** `drive.py` puts `/upstream/kit`
  first (line 31) before it imports `path_packages`. The kit holds pytest, pluggy, iniconfig,
  packaging, pygments, hypothesis and sortedcontainers. The modules pandas' import brings in (B's
  non-stdlib names) include none of these. So "neither moves a result" is believable, and the
  upstream run confirms it.
- **The single source is sound (READ).** MANIFEST already carries
  `recipe <sha> recipes/reactor_main.c`, so the list is bound by the recipe's hash as well as by
  `x-preimport`. No code reads `x-preimport` (`paths.parse_manifest` skips `x-` lines; `src/`
  has no reference). One caveat goes with the README's `-D` sentence (F8).
- **Nothing gets looser by default (§4.15, INFERRED).** numpy and pandas now import inside the
  call, with the call's environment and import path. That is what the plain binary has done
  since spec 054, and the embedder sets both explicitly. No default changes. A pandas import
  (about 0.8 s on an M-series Mac) fits well inside the runner's 60 s default deadline and
  1 GiB default memory.

## Findings, most severe first

1. **F1 (medium): `run` on the snapshot still loses a left-open file's buffered bytes, and
   Decision 4 keeps `gc.freeze()` without restating why.**
   - **The defect persists.** Spec 055's addendum (P10b) found this on today's snapshot. On A
     it is the same (EXECUTED, R1). A `-c` program opens `/out.txt`, writes 100 bytes, defines a
     function and exits:

     | binary | bytes kept |
     |---|---:|
     | A's snapshot | 0 |
     | A's plain binary | 100 |
     | the frozen snapshot | 0 |

     Without the `def`, every binary keeps all 100. So 069 neither causes this nor fixes it.
     055's revision fixes it for sessions only: it unfreezes at close. Nothing owns it for
     `run`. No entry in `tests/known_gaps.toml` names it, although rule 3 asks for a check or a
     gap entry once a failure mode has been seen.
   - **The freeze is still worth keeping.** Decision 4 keeps it with the old comment ("what
     the imports left behind is frozen out of the collector's way"), but most of what the
     imports left behind is now gone. R2 measured the freeze on A (EXECUTED):

     | run on A's snapshot | fuel |
     |---|---:|
     | `-c pass` | 15,593,597 |
     | `gc.unfreeze()` first, then the same | 43,773,463 |

     On the frozen snapshot the same pair is 83.4 M against 308.2 M. So keeping the freeze is
     right, but the spec should give that reason.
   - **Check (b) would block one fix.** The obvious fix for `run`, undoing the freeze before
     `Py_FinalizeEx` as 055 does for sessions, would put A's bare run at about 43.8 M. That is
     3.8 times cheaper than plain, so (b), set at 8 times, would refuse it.
   - **Fix:**
     - Give Decision 4 one bullet. It keeps the freeze because of R2's figure, and it says that
       R1's defect stays on `run` with the snapshot.
     - Name who closes the defect: a gap entry with its closer (a judge change this spec
       already carries), or a question to the owner.
     - Say that a fix by whole-heap unfreeze in `run` must restate (b). A fix that keeps the
       heap frozen avoids that, for example a `__main__` created per run (INFERRED, not
       measured).

2. **F2 (low): the acceptance command misses `--retire`, so the lane's acceptance as written is
   refused.**
   - Removing `test_snapshot_preimports_the_stack` makes its node ABSENT.
   - `scoreboard.accept` refuses "absent checks not retired" unless the node is passed to
     `--retire` (READ, `scoreboard.py`: `absent = [n for n in ratchet.absent if n not in
     retire]`).
   - Decision 7's command has `--accept`, `--accept-judge` and `--accept-growth` only.
   - **Fix:** add `--retire tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack`
     to Decision 7 and to criterion 9.

3. **F3 (low): Decision 11 misses 065 and 071, which reached main after 069's base.**
   - Main is now at `ef1441b`. `e21623e` added the research
     `2026-10-18-cpythons-own-tests-under-the-runtime.md` and put 065 and 071 on the roadmap.
   - That research ran CPython's suite on today's snapshot (READ):
     - Its adaptation A1 exists because "the snapshot pre-imports numpy, which imports the
       stand-in", the `ctypes` stand-in that regrtest's `clear_caches()` then calls.
     - Its fixed start is "about 1.14 G before its first test".
     - Its 27,503 passes and its failure classes may move once the start set is the stdlib
       alone.
   - 071 is a build-class fix for C-level recursion. It may touch the same recipe or link step
     (INFERRED), so the two can conflict as text and in `python.wasm`'s bytes (criterion 3).
   - **Fix:** add 065 and 071 to Decision 11.
     - The one built second measures on the snapshot that is current then.
     - 065's drafter re-checks A1 and the fixed start on 069's snapshot if 069 lands first.
     - 071 and 069 land one at a time (§5.7), and the second restates criterion 3's hashes.

4. **F4 (low): the stated cause of the plain binary's +18,944 is contradicted by the link map.**
   - Decision 4 says the shorter constant shifts "every later static address" (INFERRED).
   - The two maps differ in one hunk only (EXECUTED, R4, map lines 72,703 to 73,385):
     - The merged C-string section (`<internal>:(.rodata)`) shrinks by 25 bytes (`fc3cb` to
       `fc3b2`).
     - The roughly 84 KB of `.rodata` after it, from `0x10fc3b4` to `0x1110e80` (the recipe's
       frozen modules, docstrings, `object.c`'s `static_types`), moves by 16 to 24 bytes.
     - At `_mi_page_empty` the alignment absorbs the shift, which is why the file keeps its
       size.
     - `.data` and `.bss` do not move.
   - The growth is also not a fixed per-run cost. It is +18,944 on `-c pass` but +149,263 on
     `test_npy_files_round_trip[plain]`, roughly 0.01% throughout. That fits routines whose
     cost depends on alignment (string and memory functions) working over literals that moved,
     some by an odd number of bytes (INFERRED).
   - **Fix:** replace the sentence with the measured fact. Also write "by 0.011% to 0.017%" in
     the growth reason, which says "by 0.011%". The largest plain growth is
     `test_uncaught_errors_print_as_native[plain]`, +0.0166%.

5. **F5 (low): check (b) is stable as packages land but brittle as plain gets cheaper. Its
   failure should say which of the two happened.**
   - The plain start grows with zip members (`test_a_plain_start_grows_at_most_30k_fuel_per_member`).
     The snapshot's start does not, because its zip directory is captured at build time. So new
     packages only widen the margin, and the memo projects 10.5 times at the roadmap's end.
   - A later specification could legitimately cut the plain start: a faster directory read, or
     the teardown skip that Scope names. F1's fix could raise the snapshot's start. Either one
     fails (b) with no package pre-imported.
   - **Fix:**
     - The check's message prints both counts and the ratio, and says that a failure means
       either a package was pre-imported (see (a)) or the snapshot's reason to exist must be
       restated.
     - The spec says that a specification which changes the plain start, the freeze or the
       teardown restates (b)'s factor as a judge change, with its numbers.

6. **F6 (low): check (a)'s two sets mislabel four names (EXECUTED, R3).**
   - `_host` is the reactor's own door module (`recipes/hostmodule.c`), not a package. It is
     neither in `sys.stdlib_module_names` nor in `REACTOR_MODULES`.
   - The derived "package names" include three things that are CPython's, not packages:
     `__hello__` and `__phello__` (its frozen test modules, outside `stdlib_module_names`) and
     `_sysconfigdata__wasi_wasm32-wasi` (its generated build data).
   - Two cases follow:
     - Today, (a) would name `_sysconfigdata__…` as a non-stdlib module if a later stdlib-only
       list loaded it.
     - Decision 2 says only the owner can lift that refusal.
   - The rule stays sound: a real package cannot hide behind a stdlib name. Such a package
     would have to replace the stdlib module in the one shared zip. The project's stand-ins
     under stdlib names (`ctypes`, `mmap`) are project code, and allowing them is right.
   - **Fix:**
     - Add `_host` to `REACTOR_MODULES`, or say why it is left out.
     - Count `_sysconfigdata_*` and CPython's `__hello__`/`__phello__` as stdlib in both
       bullets.
     - Or call the derived set "the zip's non-stdlib names" in the message.

7. **F7 (low): the stand-ins miss two paths.**
   - The first path is a package imported outside the `#define`: a second
     `run_private("import six")` in `wizer_initialize`, or an import in
     `recipes/reactor_bootstrap.py`. (c) and (e) pass then, and only (a) catches it. A
     stand-in **S8** with exactly that edit, expecting (a) to fail naming `six` and (c) to pass,
     shows that (a) does not lean on the text.
   - The second path is Decision 3's failure mode: no `#define`, or two. It has no check. A
     unit test of the reader is enough, or a stand-in where `assemble_artifacts.py` exits
     naming the file.
   - The derivation's non-vacuity guard (numpy, pandas and host present) is never seen failing.
     That is cheap to add with a scratch zip.
   - Nit: S7 is listed between S3 and S4.

8. **F8 (low): the README's `-D` sentence makes MANIFEST misstate a self-built set.**
   - Decision 3 reads the `#define` text, but `#ifndef PREIMPORT` lets a `-DPREIMPORT` override
     it. An embedder who follows the README's sentence ("`PREIMPORT` is one `-D` flag on step
     60's compile") ships an `x-preimport` line that names the default list.
   - **Fix,** either of:
     - the sentence says to edit the `#define`, which keeps the recipe hash, `x-preimport` and
       the binary in agreement;
     - or the sentence says MANIFEST then misstates the list.

9. **F9 (nit): numbers and sources.**
   - With the old check removed, the README's new row ("`import pandas`, snapshot: 4.63G") has
     no metric of its own. Cite the memo for it (criterion 7), or the nearest recorded check,
     `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]` at 4.60 G.
   - numpy appears as about 0.7 G in the CHANGELOG, about 0.8 G in the README and about +0.9 G
     in the growth reason. They measure the saving (B − A), the job's total and the `.npy` job's
     growth. Say which is which.
   - Decision 2's "no specification may pre-import a package" should say "in the default
     profile". A `full` profile, if the owner ever asks for one, brings its own check.

## Constitution and rules

- **§2 holds.** It adds no profile, and a `full` profile is out of scope and built only if
  asked.
- **§4.1 and §4.2 hold.** No patch, no pin, no change to `SHA256SUMS`.
- **§4.6 holds.** The artifact set has the same members. Their hashes and sizes are recorded.
- **§4.9 holds.** (b) is a ratio of counts. The README's times are labelled as benchmark
  facts.
- **§4.10 mostly holds.** The labels are used throughout. One INFERRED cause is contradicted by
  a cheap execution (F4).
- **§4.15 holds.** No default gets looser (see "What was verified").
- **§5.6:** this is the required pre-build review.
- **§5.7 holds for the landings it names.** The order with 046, 047, 055 and 063 is written
  down; 065 and 071 are missing (F3).
- **AGENTS.md rule 4 holds.** Each judge change is restated with its reason and goes through
  `--accept-judge`. The retirement needs `--retire` (F2).
- **Rule 3:** R1's failure mode needs a check or a gap entry (F1).
- **§7:** nothing tripped.

## Notes for 055's builder (no finding against 069)

R2 gives 055 a figure. On A, undoing the freeze adds about 28.2 M to a bare run (15.6 M to
43.8 M), against 225 M on today's snapshot. 055's Decision 8 says its closing cost falls with
069. On A it is about 44 M, not about 310 M (INFERRED from R2: a run is not a session close).

## Verdict

**Ready once F1 to F3 are written in.** Each one is a few sentences of text. F4 to F9 may be
written in or answered in writing. The design is sound:
- the list is stdlib only;
- the module check refuses any package by rule, so it holds for packages not yet added;
- the judge changes are honest restatements;
- the evidence reproduces.

One line: the stdlib-only snapshot is right and well evidenced. Before it is built, the spec must
say why the freeze stays and who owns the lost-flush defect on `run`, retire the removed check
properly, and name 065 and 071.


# Confirmation of 069's revision (addendum to the pre-build review)

- **Date:** 2026-10-18
- **Reviewer:** the fresh agent that wrote the pre-build review beside this file.
- **Reviewed:**
  - the revision, `git diff e444a74..68062f3` on `spec/069-the-snapshot-pre-imports-no-package`
    (the specification only, +231 −48);
  - the rebase: `21dd92e` onto `ef1441b` as `e444a74`.
  - Each was read against the review's findings F1 to F9 and the lane's rulings: F1 is closed
    by spec 073, with a gap entry and a check (h); F3 adds 065 and 071.
- **Re-ran:** the four checks below. Nothing was written in either git tree.
  - `git range-diff 4a94c14..21dd92e ef1441b..e444a74`, for the rebase.
  - `scan.report` on (h)'s finding string, for the digest.
  - The closer rule for gap entries in `tests/checks/test_rules.py`, read against (h)'s entry.
  - Spec 070's diff of `tests/harness/scan.py`, to see whether the digest could move under
    (h).

## Verdict

**Confirmed for build.** F1 to F9 are each written in soundly. Nothing new is wrong. N1 to N4
below are nits: the builder can take them, or the lane can check them in the landing notes. None
needs another round of review.

## The rebase

`range-diff` prints `21dd92e = e444a74` (EXECUTED), so the draft's patch is unchanged. Main moved
by one research memo, one security review and five roadmap lines. None of that touches a file 069
edits except `context/roadmap.md`. Decision 10's target sentence (line 34, "decided from M1's
measurements (question 34)") is still there.

## F1 to F9

- **F1, written in.** Decision 4 gives the freeze's reason with R2's figures. The arithmetic
  holds: 43.77 M / 15.59 M is 2.81, and 166.5 M / 43.77 M is 3.80. It names the coupling with
  (b) both ways: whoever changes one restates the other. It states the defect with R1's evidence
  and names 073 as its closer.
  - Check (h) and its gap entry are well formed:
    - **The digest is right.** `scan.report(["snapshot: a file left open kept 0 of 100 bytes"],
      "unclosed file")` gives `… 1 finding(s), digest 7da6e52329c1 …` (EXECUTED), which is the
      entry's `match`.
    - **The entry passes the closer rule.** `closes_with`, cut at the first space, is
      `context/roadmap.md`. That is a file under `context/`, as `test_rules.py` requires
      (READ).
    - **It fits the gap mechanism.** Parametrised node ids are already used by gaps. "A gap
      whose check passes fails the run" makes 073's fix visible.
  - The `[plain]` case guards CPython's own behaviour, which R1 showed (100 bytes kept).
  - The defect is the same on main's frozen snapshot (R1), so (h) behaves the same before and
    after 069. Criterion 1 can see it as written.
  - Spec 070 changes `scan.py` without touching `digest` or `report` (READ), so the digest
    stays.
  - The judge-hash note and the `--accept-judge` text both name (h), the gap entry and (i).
- **F2, written in.** `--retire <node>` is in Decision 7 and in criterion 9, with its reason.
- **F3, written in.** 065 and 071 are in Decision 11:
  - for 065, A1's reason goes away and the fixed start is restated;
  - for 071, a collision is possible in the recipe and in criterion 3's hashes, and the one that
    lands second restates them;
  - criterion 3 names 046, 047 and 071 as conditions on the hashes.
- **F4, written in.** Decision 4 now states the measured map difference and the 0.011% to 0.017%
  spread. The growth reason says the same. The INFERRED label is kept on the mechanism only.
- **F5, written in.** The message prints both counts and the ratio, and names the two causes. The
  rule is written down: a specification that changes the plain start, the freeze or the teardown
  restates the factor. It names a faster directory read, the teardown skip and 073.
- **F6, written in.** `_host` joins `REACTOR_MODULES`. `paths.CPYTHON_UNLISTED` labels CPython's
  three kinds of unlisted names. The derived set is renamed "the zip's non-stdlib names". The
  sentence on the one shared zip is added. See N3 for a wording nit.
- **F7, written in.**
  - S8 has the right expectation: (a) fails naming `six`, while (c) and (e) pass.
  - S9 sees the non-vacuity guard fail.
  - Decision 3's reader is one function, `preimport_list`, with a unit test (i) for no line,
    one line and two lines.
  - S7 has moved. See N1 for where (i) lives.
- **F8, written in.** The README's `-D` sentence is replaced: a self-builder edits the `#define`.
  Decision 3 says why that keeps MANIFEST true. `#ifndef` stays, because the stand-ins are built
  through it.
- **F9, written in.** The pandas row cites the memo and the nearest recorded check. Each numpy
  figure says what kind it is. Decision 2 says "in the default profile".

## Nits (not findings)

- **N1. (i) has a better home.** `scripts/assemble_artifacts.py` is already unit-tested in
  `tests/unit/test_build_scripts.py`, which imports it. `test_artifact_rules.py` tests the
  harness's v1.1 rules on synthetic sets instead. Putting (i) beside the other
  `assemble_artifacts` tests is more natural. Either file is a judge file, and either works.
- **N2. The roadmap edit misattributes 073.** Decision 10 adds 073 to the roadmap's "Follow-ups
  decided by the owner". But 073 is the lane's ruling, not the owner's. Put it where its
  attribution is true, or attribute it in the line. Also, main's line 88 says "pre-imports no
  package (question 34; spec 069 …)"; it could become "decision 34" in the same edit.
- **N3. `CPYTHON_UNLISTED` is not "three names".** It is two names and one prefix
  (`_sysconfigdata_*`), and the text should say so. The constant should then be a pair (names,
  prefixes) or a predicate, not a plain tuple of names.
- **N4. 065's allowances, if they move, are a judge change.** Decision 11 says that if 065 lands
  first, any moved number of 065's is restated in 069's landing notes. If 065 by then carries
  allowances or expected lists (as the upstream suites do), changing them is a judge change. It
  belongs in `--accept-judge` with its cause (rule 4), not only in the notes.

One line: every finding is written in correctly. The gap's digest and closer check out, the
rebase is a clean replay, and 069 is confirmed for build, with four nits the builder can take.
