# 094 — The removal rows name their Windows need

- **Status:** **landed 2026-10-20 in wave 03** (094, 092) on main `44540cb`: accepted on `c0d2e7e`, history line 84, 630/701 pass, 0 fail, judge changes only; the integration review `../reviews/wave-03-integration-2026-10-20.md` ("lands as merged at c0d2e7e"); the dry run 39365394797 dispatched as main moved (see "Landed in wave 03" below). Before: **built 2026-10-20** on `spec/094-the-removal-rows-name-their-windows-need`, from
  main `e8ba20a` (the Landing notes); **build review: "lands once M1"**
  (`../reviews/094-the-removal-rows-name-their-windows-need-build-2026-10-20.md`), M1 and L1 fixed,
  L2 written in by the reviewer ("Disposition of the build review"); **rebased onto main
  `e00d394`** (spec 093 landed in wave 02); rides in wave 03. Drafted the same
  day, after wave 01's dry run 39358820218 failed one job, `judge (windows-2025, own-embedding)`,
  on spec 084's two read-only rows (the lane's log `build/wave-01/dryrun-failed.log`).
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits
  `tests/harness/needs.py` (one need), `tests/harness/gather.py` (the need allowed on Windows),
  `tests/checks/test_v1_4_embedding.py` (one check's body and docstring) and
  `tests/unit/test_gather.py` (one test). No `src/`, `scripts/`, `recipes/`, pin or workflow
  file. It changes neither the guest's imports nor its exports, the artifact set nor the build
  recipe, so §5.6 asks no review before build.
- **Depends on:** 084 (the check, and its pre-build review's C2), 085 (a check may be blocked only
  by a need its own body names, on a system that lacks it), both landed in wave 01.
- **Research it stands on:** wave 01's dry run 39358820218 on main `6006fde` (READ, the job's log):
  on `windows-2025` both rows of
  `test_the_removal_never_deletes_what_the_guest_may_not` reached the guest, whose unlink of the
  read-only file **succeeded** (`unlinked`), and then called a bare `pytest.skip("a Windows guest
  deletes a read-only file itself (spec 084, C2)")`. The plugin turns a skip that names no known
  need into a failure (spec 002, Decision 5), so both rows were FAIL, and LOST against their
  accepted passes. The same run settled 084's C2: a Windows guest deletes a read-only file itself.

## The problem

Spec 084's criterion 3 checks that removing a private root or a fresh `HOME` never deletes a file
the host made read-only. That holds only where the read-only mode protects the file from the
guest. 084's pre-build review (C2) asked whether a Windows guest could delete the file itself, and
the builder wrote the Windows rows to skip if it did. The wave's dry run showed it does. But the
skip named no need, and the judge refuses a skip without a known need. The answer was right; it
was written in a form the judge cannot accept.

## Decisions

1. **A need, not a gap.** The need is `read-only files`: "a file's read-only mode refuses a
   guest's unlink". It is met on POSIX, where the host's folder without write permission refuses
   it, and unmet on Windows. This is the shape of `descriptor limit` (a host capability one system
   lacks by nature, spec 063). A known gap would be wrong. A gap says "this should pass and does
   not yet". Here there is nothing on Windows for the removal to protect, because the guest can
   already delete the file. The check's question has no Windows instance. Observed on wasmtime 49
   (wave 01's dry run); a wasmtime upgrade that changes how Windows deletes a read-only file
   revisits this need (the build review, L2).
2. **The body names the need first.** The check calls `needs.need("read-only files")` before
   building anything, so on Windows the row is `blocked` with that need, as `descriptor limit`'s
   row is. The bare skip after the guest's run is removed. On POSIX nothing changes: the need is
   met, and every assertion runs as before.
3. **The gather allows it on Windows alone.** `CI_NEEDS["read-only files"]` is
   `frozenset({"windows"})`, like `descriptor limit`. A record claiming the block on macOS or
   Linux is red (G4), and so is a check claiming it without naming it in its body (085).
4. **The ratchet does not move.** A pass blocked by a need outside `PROTECTED_NEEDS` is "unrun
   locally", not lost. The accepted rows stay passes, measured on darwin, and they stay protected
   there and on Linux.
5. **The root skip stays.** The check's other skip, `modes refuse nothing to root`, is unchanged.
   It names no need either, but no judge runs as root (CI's runners do not), and changing it is
   outside this fix.

## Intent

On Windows, 084's read-only rows report `blocked by: read-only files`, a reason the judge and the
gather accept. On POSIX, they assert what they always asserted.

## Design

- `tests/harness/needs.py`: `_read_only_files()`, returning `os.name != "nt"`, with a docstring
  citing 084's C2 and the dry run; `Need("read-only files", _read_only_files, SPEC_094)`.
- `tests/harness/gather.py`: `CI_NEEDS["read-only files"] = frozenset({"windows"})`; the comment
  above the map names it beside `descriptor limit`.
- `tests/checks/test_v1_4_embedding.py`: `needs.need("read-only files")` first in
  `test_the_removal_never_deletes_what_the_guest_may_not`; the `os.name == "nt"` skip removed; one
  docstring sentence.
- `tests/unit/test_gather.py`: `test_the_removal_rows_may_be_blocked_on_windows_alone`. The check's
  body names exactly `{"read-only files"}`. The gather allows the block for both rows on Windows
  and on no other system. The predicate is false on Windows only.

## Scope

In: the need, its gather entry, the check's body, one unit test, the CHANGELOG line. Out: the
root skip (Decision 5); any change to what the check asserts; the runner.

## Acceptance criteria

1. On macOS, both rows pass as before, through the full guest run.
2. With the need's predicate forced false (a stand-in, as on Windows), both rows are `blocked`
   with `need` `read-only files`, and the ratchet counts them "unrun locally", not lost.
3. The new unit test passes; `test_no_ci_need_is_hidden_in_the_repository` passes (the literal is
   in the check's body).
4. `tests/checks/test_rules.py`, `tests/unit/test_gather.py`, `tests/unit/test_plugin.py` and
   `tests/unit/test_scan.py` pass; `ruff check` and `ruff format --check` are green.
5. The branch dry run: the `judge (windows-2025, own-embedding)` job shows both rows blocked, not
   FAIL, and the gather has no G4 line for them. Any red line there is a GREW line or G7.

## For the lane

- **Wave kind: parallel-safe** (a judge change only). It enters wave 02 if ready in time, else
  wave 03 with 086.
- **The claim list:**
  - **No row grows, no pass moves, no node is gained, lost or retired.** On macOS and Linux both
    rows of `tests/checks/test_v1_4_embedding.py::test_the_removal_never_deletes_what_the_guest_may_not`
    stay `pass` (no metrics). On Windows they become `blocked` (`read-only files`), which the
    gather now allows there; before this spec they were FAIL there.
  - **The unit suite** gains one test, in `tests/unit/test_gather.py`.
  - **The judge hash changes**, in four files: `tests/harness/needs.py`, `tests/harness/gather.py`,
    `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_gather.py`.
- **The flags** (paste-safe):
  - `--accept-judge "094: spec 084 read-only removal rows name the need read-only files, unmet on Windows alone, where a guest deletes a read-only file itself (084 C2, settled by wave 01 dry run 39358820218); the gather allows that need on Windows only; the bare skip is gone; one unit test in test_gather"`
  - no `--accept-growth`, no `--accept-fewer-passes`, no `--retire`.
- **Dry-run needs:** the Windows own-embedding shard is the evidence (criterion 5); the branch
  dry run's id is in the Landing notes.

## Disposition of the build review

The review, `../reviews/094-the-removal-rows-name-their-windows-need-build-2026-10-20.md`
(written in the lane's scratchpad, copied here by its builder): "lands once M1 is closed and run
39361856604 finishes with no G4 line for the two rows".

- **M1 (Medium), fixed.** The README said content the host made read-only is left by a removal,
  without saying that on Windows the attribute does not stop the guest, which 084's criterion 3
  asked the README never to suggest. Two sentences now say so: beside the removal bullet ("On
  Windows that keeps it from the removal only, not from the guest: a guest with a writable grant
  or a private root deletes a file the host gave the read-only attribute itself (seen on wasmtime
  49; spec 094)"), and as a *Not protected* item ("on Windows, a file the host gave the read-only
  attribute in a writable grant or a root: the guest can delete it itself").
- **L1 (Low), fixed.** `_read_only_files`' docstring now names the folder's mode on POSIX and the
  attribute on Windows, in the review's words.
- **L2 (Low), written in by the reviewer** (`137c0a2`): Decision 1 names wasmtime 49, where the
  Windows behaviour was observed, and says an upgrade revisits the need.

## Landing notes

### What was built

On `spec/094-the-removal-rows-name-their-windows-need`, from main `e8ba20a`: the four file edits of
the Design, and the CHANGELOG line under `## 0.1.0a8 — unreleased`.

### The checks (EXECUTED, darwin arm64, against a private copy of main's set, wave 01's acceptance: `python.wasm` `5f8d1b29…`)

- **Criteria 1, 3 and 4.** The two node ids, `tests/checks/test_rules.py`, `tests/unit/test_gather.py`,
  `tests/unit/test_plugin.py` and `tests/unit/test_scan.py`, `-n 3`, log `build/094-nodes.log`:
  `45/46 pass · 1 blocked (prior-art clones) · 0 fail (unit suite 326/326)`; `371 passed, 1
  skipped`; both rows `pass`, `need` none. `ruff check` and `ruff format --check` green.
- **Criterion 2, the stand-in.** A plugin setting the need's predicate to false, log
  `build/094-standin.log`. Result: `0/2 pass · 2 blocked`, `blocked by: read-only files 2`,
  ratchet `lost 0 · unrun locally 2`. The run is red only for "steered from outside the judge",
  the plugin itself, as it should be.
- **Seen failing first:** wave 01's dry run, on 084's code (the Research line).
- No fast tier: the lane was rebuilding for wave 02 under `build/lane.lock`.

### The branch dry run (READ, run 39361856604 on `1d70261`)

**Green: 26 jobs passed, 3 skipped (the release-only jobs), none failed** (criterion 5).
- `judge (windows-2025, own-embedding)`: `165/669 pass · 1 gap · 2 blocked · 0 fail`,
  `blocked by: read-only files 2`, `ratchet vs 47b3695c2d: lost 0 · unrun locally 2 · grew 0`.
- The gather printed no G line at all, so none for the two rows. It reports `593/669 pass · 69 gap
  · 7 blocked · 0 fail (unit suite 4121/4149, 28 skipped)`, `blocked by: descriptor limit 2 ·
  read-only files 2 · oracle 1 · prior-art clones 1 · three systems 1`, and three systems on
  `python.wasm` `5f8d1b29…`, set `89b14f67…`.
- Everything after `1d70261` (L2, M1, L1 and the rebase onto `e00d394`) changes only `context/`,
  `README.md` and one docstring in `tests/harness/needs.py`, so the run's verdict stands for the
  tip.

### Rebased onto main `e00d394` (spec 093 landed in wave 02)

`git rebase e00d394` replayed both commits with no conflict hunk and no semantic change. The
CHANGELOG line stays under `## 0.1.0a8 — unreleased`. After the rebase I ran the two node ids and
`tests/checks/test_rules.py` against a private copy of main's wave 02 set (`python.wasm`
`cef11d8d…`, set `2b0480af…`), with `tests/unit/test_gather.py`, `-n 3`, log
`build/094-rebased.log`: `45/46 pass · 1 blocked (prior-art clones) · 0 fail (unit suite
80/80)`, `125 passed, 1 skipped`, `ratchet vs 2bb98c8421: lost 0 · grew 0`; both rows pass.
`ruff check` and `ruff format --check` green.

### Landed in wave 03

- On Windows the two removal rows now read blocked by the need read-only files instead of FAIL. They were the only red lines in wave 01's dry run 39358820218 and wave 02's dry run 39363060501; wave 02's run was green on every other job on all three systems, Windows own-guest included (093's fix) and 073's rows included (its first release-workflow read, the integration review's M2).
- Reviews: `../reviews/094-*` and the wave's integration review.
