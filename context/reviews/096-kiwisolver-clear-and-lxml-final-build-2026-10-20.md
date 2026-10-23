# Review of 096 — kiwisolver's `tp_clear` returns `int`, `lxml.html.diff` imports, and the scan reads type slots (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5); it wrote none of 096 and did not review its specification.
- **Reviewed:** `git diff c091f3d..4222951` on `spec/096-kiwisolver-clear-and-lxml-final` (worktree `wasi_python-096`), against the specification as confirmed, its pre-build review and confirmation, and its evidence (`context/research/2026-10-20-the-slot-scan/`, the `build_*` files). `0054f5b..4222951` touches only the specification. The reviewer's write-in of findings 3 to 5 is `5c720ef` on the branch (the specification's landing notes only). Time box: 40 minutes (build-class). `build/lane.lock` absent at every run.
- **Run:** the builder's release dry run **39386471189** on `0054f5b`, read (the brief named it; no run of my own was dispatched, see note N4).
- **Re-ran (EXECUTED, macOS arm64):**
  - the five new nodes by node id on the worktree's set (`SHA256SUMS` `72858ced…`, `python.wasm` `02baa6cb…`) → **5 passed**, exit 0;
  - the same five nodes on a private `cp -c -Rp` copy of the main tree's set (`SHA256SUMS` `4eaf1c3d…`, `python.wasm` `b6953170…`, wave 05's) → **5 failed**, exit 1: check 1 traps on both binaries (`indirect call type mismatch`, stdout `Term Expression Constraint`), check 2 exits 1 with `TypeError: 'str' object is not callable` on both, check 3 reports exactly the four `spec kiwisolver.*.tp_clear` findings (table indices 16969, 16979, 17034, 17048);
  - `uv run pytest -m "not slow" -n 3` in the worktree → `589/713 pass · 0 gap · 3 blocked · 0 fail`, unit suite 1,802/1,809, ratchet `lost 0 · gained 5 · grew 3`, its only red the three `GREW` byte rows; exit 1 for those alone (identical to the builder's `build/096/fast.log`);
  - `ruff check src tests` → all passed; `ruff format --check src tests` → 120 files formatted;
  - nine mutants of my own of `tests/harness/callbacks.py` against the unit rows (finding 1).

## Acceptance criteria against evidence

1. **Checks exist and were seen failing first** — met. EXECUTED: my own runs above, on main's set and on 096's, match `build_seen_failing_first.out` line for line. The tree check's failing side (lxml patch moved aside) is READ from the landing notes.
2. **The build** — met, with one part answered by another route (finding 3). READ: the landing notes (empty `build/`, 16 steps, patches through `patch_tree` with no offset). EXECUTED: the worktree's `MANIFEST` differs from main's in exactly the two new `recipe` lines (hashes `138e3cbe…643e`, `0291f7c0…9334`) and the `x-snapshot-zip` line; `LICENSES/` unchanged in `SHA256SUMS`. "Steps 54 to 90 run twice" was not run on one host.
3. **The same bytes everywhere** — met. READ: 39386471189, both "rebuild from the pins" jobs (ubuntu-24.04, ubuntu-24.04-arm) and "the same bytes from every host" succeeded.
4. **The patches are what their drafts say** — met. EXECUTED: each `recipes/patches/…` file and its `context/upstream/2N-…/fix.patch` hash the same (`138e3cbe…643e`, `0291f7c0…9334`); each draft at `context/upstream/patches/…` hashes the same as its `pr.md` at `a56e884` (`04347bb3…`, `06bb774a…`), so it moved unchanged; the 28 and 29 folders keep only `fix.patch`. READ: the kiwisolver patch is four hunks, 9 lines in and 4 out, each `X_clear` returning `int` and ending `return 0;`; the lxml patch is the one line `def final(self, func): return func` after `cclass`, as Decisions 2 and 4 say. 12 patch files under `recipes/patches/`, the README's count.
5. **The scan on the rebuilt set** — met. EXECUTED: check 3 passes on 096's set; READ `build/096/scan-after.txt`: kiwisolver's four `X_clear` are `(i32) -> (i32)`, coverage 481 types, 454 specs, 149 modules, 5,360 functions, 0 unreferenced candidates, 1 named at run time; spec 051's coverage (3,607 / 2,313 / 1,325 / 451) the same on both sets. `scan()` is untouched (the only removed lines in `callbacks.py` are the docstring's old out-of-scope sentence).
6. **The numbers recorded** — met. EXECUTED: the set's bytes (41,169,355 / 45,444,037 / 38,723,169), each +8, +1, +29 against main's, well under the 1 KB line. Fuel (EXECUTED, my fast tier's record): check 1 228,133,887 (plain) and 48,249,988 (snapshot), check 2 701,579,788 and 398,909,529, the claimed numbers exactly; no other fuel row moved.
7. **The judge** — met in substance (finding 2). The landing notes record the fast tier (`-n 3`, 589/713, 0 fail, only the three byte rows red), not a local `-n 6` full run; the dry run's judge shards ran the rest on three systems with 0 fail.
8. **The release** — met. READ: 39386471189, 24 jobs succeeded and 4 were skipped (the landing notes said 25; finding 5); the one failure, `judge (macos-15, own-guest)`, prints `351/713 pass · 0 fail`, ratchet `lost 0 · gained 6 · grew 3`, and its only red lines are the three `GREW` byte rows claimed; no G7 line. Every Windows shard and every `verify` job succeeded; the Windows and Linux own-guest shards show `gained 6 · grew 0 · 0 fail` (the five 096 nodes and `test_wheel_carries_the_artifact_set`, INFERRED from the counts). Gather and the publish jobs were skipped, as a red judge makes them.

## Decision 3 against `scan_slots` (READ, and mutated)

Each rule of Decision 3 as confirmed is in the code:

- **C string:** `STRING = rb"[\x20-\x7e]{1,256}\0"` matched at the address; a space is allowed.
- **Classification and drop counts:** exactly one self-typed record, else a finding; metatypes to a fixed point (C-string name, `ob_type` 0 or a metatype, `tp_basicsize` ≥ 212 or `tp_base` a metatype); module-shaped records to Part 3; static instances, names not pointers and unreferenced candidates each counted under its own key; a referenced candidate with an in-image `tp_name` that is no C string is a finding; `tp_name` 0 is read as `<tp_name NULL at …>` and counted; a dropped static instance whose `ob_type` is such a type is a finding (the confirmation's Low, option 1).
- **Bounds:** `SLOT_MAXIMUMS` holds unreferenced candidates at 0 and types named at run time at 1; `SLOT_MINIMUMS` 400 / 380 / 120 / 4,500.
- **Named records:** `SLOT_NAMED` lists exactly the records check 3 names (four kiwisolver specs and their `tp_clear` as "spec slot" records, `pandas._libs.tslibs.timestamps._Timestamp`, `type`, `numpy.ndarray`, `ImagingCore`, `lxml.etree._Element`, `_regex`, `ft2font`); `unread_named` reports each one not read.
- The `PyTypeObject` offsets (24 to 208, size 212) and the `PyModuleDef` offsets (`m_methods` 32, `m_slots` 36, `m_traverse`/`m_clear`/`m_free` 40/44/48) agree with CPython 3.15's wasm32 layout (READ); the slot ids, the four renumbered ids in both forms, and the function types agree with Decision 3's table.

The fifteen unit rows cover every row check 4 lists. The builder's thirteen daggers (`build_unit_mutants.out`) each fail their row. **My own nine mutants** (`my_mutants.py`, in the reviewer's scratchpad, same method: a copy of `tests/`, one textual change, the slot rows run):

| mutant | rows failed |
|---|---|
| A: the "names not pointers" drop removed | 1 (`…drops_are_counted_by_reason`) |
| B: a static instance counted under "names not pointers" | 1 (`…drops_are_counted_by_reason`) |
| E: `m_clear` called as ternary | 1 (`…module_definitions_functions_are_read`) |
| K: `nb_bool` called as binary | 1 (`…a_suite_is_read…`) |
| C: a type's pointer fields need not be in static memory | **0, survives** |
| D: the `tp_basicsize` / `tp_itemsize` bound removed | **0, survives** |
| F: "does not read as a PyModuleDef" never reported | **0, survives** |
| G: the C string's 256-byte bound removed | **0, survives** |
| J: a module slot with an unknown id accepted | **0, survives** |

## Findings, most severe first

1. **Five rules of Decision 3 have no unit row** (Low; `tests/unit/test_callbacks.py`). Mutants C, D, F, G and J above pass the whole unit suite, and main's binary has no record that exercises them, so check 3 would not notice either. Check 4's list does not ask for these rows, so the specification is met; but each is a rule the Decision states ("a pointer field that is neither 0 nor in static memory", "a `tp_basicsize` of 1 MiB or more", "a module definition that does not read as one, or a slot entry with an unknown id, is a finding", "1 to 256 bytes"), and a regression in any of them would be silent. Failure: delete the `TYPE_POINTERS` test in `_types` → the judge stays green. Fix text (the builder's, being code; or a reserved follow-up if the lane prefers not to move the judge hash again before landing): five rows, one per rule, each seen failing under its mutant — a type whose `tp_methods` lies below the image's base is "does not read as a type (tp_methods)"; a type with `tp_basicsize` `1 << 20` is "does not read as a type (tp_basicsize or tp_itemsize)"; a `PyModuleDef` whose `m_clear` is no table index is "does not read as a PyModuleDef (m_clear)"; one whose `m_slots` holds id 200 is "slot entry 0 unreadable"; a type named by 257 printable bytes is "does not read as a type (tp_name)".
2. **Check 3's coverage line is cut in `latest.json`** (Low; `tests/harness/callbacks.py` `SlotReport.summary`, `tests/harness/plugin.py:347`). The `note` fixture keeps the first 240 characters; the slot summary is about 330, so the recorded reason stops at "24 specs with slots past the image, " and loses "0 suites past the image, 7 module slots past the image, 0 NULL function slots". Check 3 says its coverage, with the drops by reason, is the pass's reason (EXECUTED: my record shows the cut). Nothing is compared on it, so no verdict changes. Fix text (the builder's, or a follow-up): a shorter summary (`481 types · 454 specs · …` with short keys), or the full counts as a `fact`.
3. **The builder's local full judge (criterion 7, AGENTS rule 3a) is not recorded** (Low, `context/` only). The landing notes give the fast tier; the full set ran in the dry run's shards. Written in (the reviewer's commit on the branch): the landing notes now say so.
4. **"Steps 54 to 90 run twice" (criterion 2) was not run on one host** (Low, `context/` only). The landing notes already say "not yet run"; three independent builds (macOS arm64, Linux x86_64, Linux arm64) gave the same `SHA256SUMS` in 39386471189, which answers the determinism the criterion asks about. Written in: the landing notes now say that is the answer.
5. **The landing notes counted 25 jobs passed; the run has 24** (Low, `context/` only). EXECUTED: `gh run view 39386471189 --json jobs` → 24 success, 1 failure, 4 skipped. Written in ("24 jobs passed (4 skipped)"). The tip commit's subject `4222951` keeps "25"; history is not rewritten.

### Notes (no change asked)

- **N1. My node-id runs rewrote the worktree's `build/progress/latest.json`** (03:54, the main-set run last). I then ran the fast tier `-n 3` on 096's set, which rewrote it again as a fast-tier record on 096's set, the same kind the builder's 03:25 record was. The lane judges in the main tree and is unaffected; a builder who wants its own record back re-runs the fast tier.
- **N2. `findings()` and `EXCLUDED` are shared by both scans**, as Decision 3 says: an exclusion added for one scan would turn the other's check red as "matches nothing". With the rule "never an exclusion" that is a feature; a future exclusion would need a per-scan list.
- **N3.** The unit row for a metatype's instance uses a `tp_repr` of type `(i32) -> ()`, a missing result, where check 4 says "one parameter too few". Still a mismatch; the wording differs only.
- **N4.** The reviews README asks the reviewer to dispatch its own release run. The brief gave 39386471189 to read instead, and `0054f5b..4222951` changes only the specification, so that run stands for the reviewed tree. The lane's dry run before a tag is unaffected.
- **N5.** At landing, Decision 8 asks the lane to add the slot-scan sentence to each unlanded build-class specification's status (037, 038, 043, 044); that is the lane's step, not the build's.

## The claim list and the flags (For the lane)

- **Complete against the run.** The dry run's and the fast tier's only red lines are the three `GREW` byte rows, each in the claim list with its numbers and in `--accept-growth`. "Gained 5" locally (6 in CI, the sixth the wheel check, not 096's) are the five nodes claimed. No fuel row grew; no pass lost; no check retired. The judge hash changes in the five files named, the same five the ratchet's "judge changed" line lists. The unit suite count (1,802/1,809) and the fifteen new rows match my run.
- **AGENTS rule 4: no existing expectation edited** (EXECUTED: `git diff --numstat` on `tests/` and `context/progress/` shows additions only, but for the two docstring lines in `callbacks.py`; no golden, gap, allowance, upstream plan or progress file is touched). So `--accept-judge`'s closing words "no existing expectation edited" are true, and 066 has not landed, so Decision 8's conditional edits do not apply.
- **Paste-safe** (EXECUTED: the three flag lines contain no `!`, `$`, backtick or backslash; the apostrophes sit inside double quotes; each reason begins `096:`).

## Constitution checks

- §4.1: two carried patches, each upstream's own merged change, hashed in `MANIFEST`, named in the CHANGELOG, each with its draft under `context/upstream/patches/` (status "merged", nothing to send) and a deletion condition; the recipe-first alternatives for lxml are argued and refused in Decision 4. Holds.
- Pins: no new input, `downloads/SHA256SUMS` and `scripts/` untouched. Holds.
- Artifacts not in git; tests count operations (fuel and bytes), not time. Holds.
- The judge: a new scan and three checks, all additive; nothing weakened. Holds.
- §7: nothing tripped.

## Verdict

**Lands**: both patches are upstream's own fixes byte for byte, the slot scan implements Decision 3 as confirmed, the five nodes fail on main's set and pass on 096's, and the dry run's only red lines are the three claimed byte rows; findings 1 and 2 are code Lows the builder or a follow-up adds, and findings 3 to 5 are written into the landing notes (`context/` only).
