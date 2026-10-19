# Build review of 081 — guest fuel does not depend on where the repository is checked out, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 081's code. I reviewed its specification before
  build, and confirmed it.
- **Under review:** `spec/081-guest-fuel-does-not-depend-on-the-checkout` at `e194f46`, rebased
  onto main `3f69654`. Main is now `59b90b6` (079 landed), and the lane rebases at landing.
  - Commits: `b760a6e` (the checks first), `fa5321e` (the guard), `767404d` (the lxml split) and
    `e194f46` (notes, evidence, the roadmap line for 083).
  - The builder's evidence: `context/research/2026-10-19-guest-fuel-and-the-checkout-path/build/`.
- **How I ran it:** a `git clone -b` of the branch into the scratch folder (`c/`), then
  `uv sync`. All runs used `build/sets/s-c50ca51fae5eb55b`, read only. The file the mutants edit
  was restored after each, and `git status` is clean. I touched no project git tree. My script is
  `probes/run_all.sh` (with the builder's `mutate.py` beside it), and its logs are in `logs/`.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

It is built as confirmed.
- The guard has every F2 form, c1 and c2 are in the code, and the six unit rows cover the forms.
- The lxml check runs the host path unrecorded, on the very string it checks on the host first.
  Its four mutants each fail.
- The fast tier is green: lost 0, grew 0.
- The matplotlib "wider across paths" spread is sampling, not the path. Six more runs at a third
  path land on the same 17-instruction lattice as the builder's runs at two other paths.

No finding. **It lands, once its merge with 063 has had a delta look** (below), as the
coordinator expected.

## The code against the confirmed spec (READ)

- **`_forms(root)`** gives each root:
  - as written and resolved, each also in forward slashes;
  - `as_uri()` only when `p.is_absolute()` (**c1**: a Windows-shaped root on POSIX is relative,
    and has no URI);
  - every form holding a backslash again, with the backslashes doubled.
- **`host_paths_in`** decodes bytes as UTF-8 (with replacement), and folds case when
  `fold_case`, which defaults to `sys.platform == "win32"`. It looks at argv, env as
  `NAME=value`, each `files=` path and its contents, and each grant's guest path.
- **`host_roots_always()`** gives the checkout, plus `tempfile.gettempdir()` unless that is
  literally `/tmp`. `run()` checks before anything runs, when `measured` and not `own`, against
  those roots and the caller's `host_roots`.
- **The fixture** passes `measured=record` and `host_roots=(getbasetemp(),)`.
- **The lxml check:**
  - **c2:** `host = str(ro / "secret.txt")` is bound once, asserted on the host (it reads
    `SECRET` and is the same file as `ro / "secret.txt"`), and that same string is passed to
    `OUTSIDE`.
  - `OUTSIDE` answers exactly two keys: the control "entity by guest path, outside run"
    (`file:///ro/secret.txt`) and "entity outside grants" (the host path).
  - The keys are asserted disjoint from `SAFETY`'s before the merge.
  - The control expects `<r>SECRET\n</r>`. "No `SECRET` outside" is asserted on every platform,
    already in the form the merged check keeps.
  - The win32 branch is 063's; it comes with the merge (below).
- **The unit rows** (six) cover:
  - every input kind;
  - the `file:` URI of a root holding a space and `é`;
  - a Windows-shaped root inside `repr` and JSON text, and in another case with `fold_case`;
  - guest paths, and paths under another folder, not named;
  - the system temp folder as a root unless it is `/tmp` (patched each way);
  - a measured run refused before its root is made, with a `measured=False` run that goes on.

  `work` lives under `build/harness/`, inside the checkout, so the refusal row holds on Linux
  too, where the system temp folder is `/tmp` and is no root (READ, `tests/unit/conftest.py`).
- **The roadmap line** reserves 083, with the steps' source and bound.

## Executed

- **The four lxml mutants** (the builder's `mutate.py`, each applied alone; `logs/run_all.log`).
  Each fails both rows; the unmutated check passes both.

  | mutant | how it fails |
  |---|---|
  | m1, `ro` granted at its host path in `OUTSIDE` only | `entity outside grants: ok '<r>SECRET\n</r>'`, **and** "the host's secret was read" |
  | m2, the control names `/ro/elsewhere.txt` | the control: `ok '<r/>'`, want `<r>SECRET\n</r>` |
  | m3, a made-up host path `/nonexistent/secret.txt` | the host-side check, at once (`FileNotFoundError` from `read_bytes`), before any guest runs |
  | m4, "entity outside grants" answered in `SAFETY` too | the disjoint-keys assertion |

  m3 fails on the first half of the host-side check, before its assertion message, but it fails.
- **The fast tier, `-n 3`** (`logs/fast-n3.log`): 474/550 pass, 1 gap, 24 blocked, 0 fail. Unit
  suite 1366/1374. 1840 passed. **Ratchet: lost 0, grew 0**, judge changed (the four files).
  The restated lxml values do not move in the ratchet, because they fall.

## The matplotlib spread (EXECUTED; the builder's `build_spread*.out` READ)

- **The builder's claim.** Across two paths with three runs each, matplotlib's plot rows spread
  wider between paths than within one: the snapshot row 221 against 187, the plain row 136
  against 102. The builder attributes the extra 34 to file timestamps, and sets 083's bound at
  187.
- **My test.** Six more runs of `test_plot_line_job_matches_native` at a third path (my clone),
  each a fresh process, so each has a fresh extraction of matplotlib's data and fresh timestamps:
  - snapshot: 8,783,535,958 to 8,783,536,060, spread 102;
  - plain: 9,107,997,797 to 9,107,997,899, spread 102.

  Every value is a multiple of 17 from the minimum.
- **All three paths share one lattice.** The builder's four snapshot values (8,783,536,077,
  …,111, …,890, …,060) differ from my minimum by −68, +102, +119 and +153: all multiples of 17.
  My range sits inside theirs. A path effect would not land on the lattice: the lxml argument
  moved fuel by about 700 instructions a character, with jumps of tens of thousands.
- **So the 34 is sampling.** With three runs a path, the largest gap within a path is
  underestimated. A difference of two 17-steps between "between" and "within" is the expected
  scatter, not a signal (INFERRED from the lattice and the overlap). Nothing else of the host's
  reaches the plot row's guest: the guard passes its inputs, and matplotlib's data is granted at
  a fixed guest path (READ).
- **The roadmap's wording.** The largest step seen is **221** (between runs in different
  sessions), of which 187 is between runs at one path. "Up to 187 at one path" is true, but 083's
  bound should say 221 is the most seen.

## Does 083's priority rise?

A little, and not urgently.
- **The steps grow with a check's file work.** The plot rows read many files (fonts, the data
  folder), so they gather up to 13 steps (221). That is 2.5 parts in 100 million of an
  8.8 G row, far inside the tolerance of 1e-4 × accepted.
- **The risk is a small check that reads timestamps.**
  - The smallest accepted row (1,213,059, an exit-path check) allows 121 instructions, about 7
    steps, but it reads no timestamps.
  - The nearest real case is `test_a_program_sees_real_entropy_and_file_metadata[snapshot]`, at
    16,524,228 (tolerance 1,652). It reads file metadata by design, and it varied by one step.
- **No row is at risk today.** A future check under about 3 M instructions that stats a dozen
  files could flake. Suggest:
  - 083 lands before 0.1.0, or before the first such check, whichever comes first;
  - its specification records the largest step per row, so the ratchet's margin is known.

## The merge with 063: yes, a delta look before landing

The merged lxml check is the assertion of a security property, and a hand merge can drop a line.
I need to see it, and I will check:
1. the merged `test_v1_3_lxml.py` against Decision 5's six points:
   - `OUTSIDE` unrecorded and `SAFETY` measured, each exit code asserted;
   - the disjoint keys;
   - 063's win32 expectation (`XMLSyntaxError`, "failed to load", "Operation not permitted")
     beside 046's `ok <r/>` elsewhere, with "no `SECRET`" on every platform;
   - the twelve other expectations and the `out.xml` assertion;
   - both docstring sentences, and `import sys`;
2. m1 to m4 re-run on the merged check;
3. the rebased guard and fixture unchanged from this review.

The win32 branch runs only in the release workflow. Its proof is the release dry run before the
next tag (AGENTS.md rule 6b), not the lane's darwin judge. The landing notes should say so.

## Notes

- **N1.** The builder's full judge (`-n 3`: 0 fail, lost 0, grew 0, and the lxml rows at the
  restated values six times from two paths) I READ. I did not re-run the full tier; the fast tier
  and the targeted runs above cover what 081 changes. The lane's serial full run on the exact
  commit is the final word.
- **N2.** The guard's holes are as the spec lists them: a `host=` door's answer, a file written
  into a grant outside `files=`, paths outside every root, other encodings. No current check uses
  one.
- **N3.** Constitution: a judge change only. Parallel-safe. It needs `--accept-judge`. The two
  restated rows fall, so no `--accept-growth`. §4.9 holds: counts, not time.

## Verdict

**It lands, once the merge with 063 has had a delta look:** the six points, m1 to m4 on the
merged check, and the guard and fixture unchanged. There is no finding against this build. The
roadmap's 083 line should say 221 is the largest step seen; that can ride with the merge.

## One line

The guard, the split and its four mutants are right, and the plot rows' extra spread is sampling
on one 17-step lattice. Show me the lxml check after the 063 merge, and it lands.

## Addendum: the delta look after the rebase onto 08de0c8 and the merge with 063 (2026-10-19)

- **Under review:** the -081 branch at `9a5fc3d`, rebased onto main `08de0c8` (063 landed). The
  tip I reviewed before was `e194f46`.
- **How I ran it:** a fresh `git clone -b` into the scratch folder (`d/`), then `uv sync`. Scripts
  `probes/delta_run.sh`, `lxml_fuel.sh` and `rows_fuel.sh`; logs in `logs/`. No project git tree
  was touched, and the clone is clean.

### 1. What changed besides main (EXECUTED: `git range-diff 3f69654..e194f46 08de0c8..9a5fc3d`)

- Commits 1 to 4 and 6 are identical (`=`).
- Commit 5 (the lxml split) differs only in the merge with 063's lines: the Windows docstring
  sentence, the `win32` branch, and the "no `SECRET`" line moved out of that branch.
- `1ef0a70` touches only the specification (the landing notes).
- `9a5fc3d` commits the evidence as `built/` (17 files, `merge_with_063.diff` and `mutate.py`
  among them), and the spec's three references follow the rename.
- The diffs of `tests/harness/`, `tests/unit/`, `tests/checks/conftest.py` and `src/` against each
  base are byte-identical (`diff` of the two diffs: empty). Against `08de0c8`, the branch changes
  exactly the four test files, plus the context files.

### 2. The merged check against Decision 5 (READ)

Each point holds:
1. `OUTSIDE` runs unrecorded (`record=False`) with the host path. Its exit code is asserted.
2. `SAFETY` runs measured, with guest paths only. Its exit code is asserted.
3. The keys are disjoint: `set(away) == OUTSIDE_KEYS` (two keys), and no `OUTSIDE` key is in
   `SAFETY`'s answer.
4. On `win32`, "entity outside grants" expects `XMLSyntaxError` with "failed to load" and
   "Operation not permitted". Elsewhere it expects `ok <r/>`. The "the host's secret was read"
   check runs **on every platform**, after the branch.
5. The twelve other `expect` lines and the `out.xml` assertion are unchanged. The control,
   "entity by guest path, outside run", expects `<r>SECRET\n</r>`.
6. Both docstring sentences are kept, and `import sys` is at the module's top.

The host-side check on the very string passed (c2) is unchanged.

### 3. The mutants on the merged tip (EXECUTED, `logs/delta_run.log`)

Each of m1 to m4 (the builder's `mutate.py`, byte-identical to before) turns both rows red; the
merged check passes unmutated:
- m1: "want ok with ('<r/>',)" and "the host's secret was read";
- m2: the control fails;
- m3: the host-side check fails (`FileNotFoundError`) before any guest runs;
- m4: the disjoint-keys assertion fails.

### 4. The judge, and an environment effect that is not 081's (EXECUTED)

- **The lane's set in place gave other numbers.** Against
  `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` read where it lies:
  - the two lxml rows gave 506,204,459 and 214,981,776, **not** the restated 506,200,859 and
    215,014,922;
  - the fast tier was 0 fail, lost 0, but **grew 21** (for example
    `test_dotted_builtins_keep_their_import_names[plain]` +923,590,
    `test_lxml_is_builtin_at_manifest_versions[plain]` +80,761) (`logs/delta-fast-n3.log`).
- **The cause is the hard-link count of the set's stdlib zip, not 081.**
  - The same merged code on `s-c50ca51fae5eb55b` gives the restated values. So does the
    pre-merge tip on that set. And the pre-merge tip on the lane's set gives the other values.
  - The two sets' `python.wasm`, snapshot and zip are byte-identical (`cmp`). A `cp -Rp` copy of
    the lane's set gives the restated values.
  - What differs is the zip's link count on the host. The driver hard-links the zip into every
    run's folder (`_place`, `os.link`), and run folders that are not removed keep their links.
    The lane's set had 2,486 links when I began, 2,459 later and 2,640 at the end.
  - The guest's `stat` reports that count (`st_nlink`), and above a threshold the guest's work
    changes.
- **I bisected it on the copy** by adding hard links: counts of 1, 256, 257, 401, 999, 1,000, 1,011
  and 1,017 give the restated lxml values; 1,023, 1,024, 1,459 and 2,459 give the other values.
  The threshold is between 1,018 and 1,023. The three grown rows I checked flip at the same point:
  at 1,017 they equal `accepted.json` (one to within two 17-steps), and at 1,027 they grow by the
  fast tier's amounts (`logs/rows-rows-nlink-*.json`). I did not find which guest code reads the
  count. The effect is two-state, so it is probably an allocation or a cache crossing a boundary
  (INFERRED).
- **Where the links are** (EXECUTED, `find -inum`): 141 in `wasi_python-065/build`, 243 in
  `wasi_python-073/build`, and more than 2,000 in spec 083's probe folders in a shared scratch
  folder (`scratchpad/083/tmp*/run-*/lib/python315.zip`, 60 to 120 each), growing while I worked.
- **On a clean copy, the judge is green.** On a `cp -Rp` copy of the lane's set (same bytes, the
  same post-079 `MANIFEST`, link count 1):
  - the fast tier, `-n 3`, is **477/554 pass, 0 fail, lost 0, grew 0**; unit suite 1503/1511;
    1980 passed (`logs/delta-fast-n3-clean.log`);
  - the two lxml rows equal the restated values (plain **506,200,859**, snapshot
    **215,014,922**);
  - the lxml rows and the six guard rows by node id: 26 passed;
  - the MANIFEST check passes on this set, as the lane said.

**This matters to the lane now, and to spec 083.** While the lane's set holds more than about
1,018 links, its serial judge in the main tree will report about 21 false "grew" lines, whatever
lands. Until fixed:
- judge on a fresh `cp -Rp` copy of the set (link count 1), or clear the leftover run folders
  first;
- spec 083's probes should remove their run folders.

The lasting fix, for 083 or its own small specification:
- the driver copies the zip instead of hard-linking it; or
- the driver answers every `filestat` field the host leaks (link count and inode, besides the
  times F1 found) from fixed values.

Either way, the judge should check that a run's fuel does not move with the zip's link count.

### Verdict

**Lands.** The merge is Decision 5's, exactly. Nothing else changed beyond main, the landing notes
and the evidence's rename. m1 to m4 each turn the merged check red. On a clean copy of the lane's
set, the fast tier is green with lost 0 and grew 0, and the lxml rows equal the restated values.
The "grew" lines on the set in place are the zip's link count, which 081 does not touch; the lane
should judge on a fresh copy of the set until that is fixed.
