# Review of 094 — The removal rows name their Windows need (build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh review agent (Claude Opus 5.5); not the author. Time box: 25 minutes
  (parallel-safe).
- **Reviewed:** `e8ba20a..1d70261` on `spec/094-the-removal-rows-name-their-windows-need`
  (worktree `wasi_python-094`), one commit.
- **Run:** the builder's release run 39361856604 on `1d70261` (the caller's instruction; no second
  run dispatched, so CI is not loaded twice). At 23:22 EDT every finished job was green, among them
  `judge (windows-2025, own-embedding)` (job 118434145425), `judge (windows-2025, own-runner)`,
  `verify (windows-2025)` and the same-bytes job; three judge shards (Windows and macOS
  own-guest, macOS own-embedding) and the gather were still running.
- **Re-ran:** in the worktree, each after checking that `build/lane.lock` was gone, against a
  private copy of the main tree's `build/artifacts` (the set the lane had just built for wave 02,
  `python.wasm` `cef11d8d…`, not wave 01's `5f8d1b29…`; the change is judge-only, so the set does
  not bear on it), logs under the worktree's `build/094-review/`:
  - the two rows and `tests/unit/test_gather.py`, `-n 3 -rA` → `82 passed`, exit 0; scoreboard
    `2/2 pass · 0 blocked · 0 fail (unit suite 80/80)`, ratchet `lost 0 · grew 0`, both rows
    `PASSED` (EXECUTED);
  - `tests/checks/test_rules.py`, `tests/unit/test_plugin.py`, `tests/unit/test_scan.py`, `-n 3`
    → `289 passed, 1 skipped`, exit 0; `43/44 pass · 1 blocked` (`unrun locally 1`, the
    prior-art clones), `lost 0` (EXECUTED);
  - `ruff check src tests` → all passed; `ruff format --check src tests` → 109 files formatted
    (EXECUTED).
  - A first run without the artifact variable blocked both rows on `artifact dir` (the worktree
    has no set), as it should; not counted.

## The question this review was asked: is this a true platform limit, or a hidden broken promise?

It is a true platform limit, and 084 did not promise otherwise. The evidence:

1. **What the dry run saw (READ, `build/wave-01/dryrun-failed.log`, lines 31 to 55).** The old
   skip ran only after `out.startswith("unlinked")`. The guest prints `unlinked` only when its own
   `os.unlink("…/ro/secret")` returns without error (`test_v1_4_embedding.py:1426-1432`). So on
   `windows-2025` the guest itself deleted the file, inside wasmtime, before the call ended. The
   runner's removal never touched it. The runner has no hook on a guest's unlink: the call goes
   guest → WASI `path_unlink_file` → wasmtime 49 → Rust `std::fs` (084's C2, READ by 084's
   review in `filesystem/windows.rs`). No runner code is on that path, so there is no runner bug
   for 084 to have prevented.
2. **The two protections differ by nature.** On POSIX the host's protection is the folder's mode
   (`ro` at `0500`); a file's own mode never refuses an unlink there either. On Windows the
   check sets the read-only attribute on the file (`_read_only`, `:1449-1456`), and a folder has
   no write bit to clear. A delete-denying ACL is the only Windows analogue of a `0500` folder,
   and nothing in the runner's interface sets one. So "the read-only attribute refuses a guest's
   delete" is not a Windows fact for this guest, and the check's question has no Windows instance.
3. **What 084 promised (READ, spec 084).** Decision 4 promises that *the removal* never changes a
   mode or an attribute, "on POSIX or on Windows". It does not promise that a read-only file
   survives the guest. Criterion 3's Windows bullet (the confirmation's C2) wrote this outcome in
   advance: "If the guest's unlink succeeds on the Windows shard, the Windows rows skip with that
   reason … and the README says nothing that suggests the read-only attribute protects a file
   from a guest." Criterion 17's "criterion 3 (both rows) `PASSED`" is read with that bullet.
   084's build review (§8) says the same.
4. **The Windows half of Decision 4 stays guarded.** `tests/unit/test_runner_sweep.py::
   test_read_only_content_is_left_and_named` has a Windows branch (`:685-688`): a file with
   `S_IREAD` in a folder, `_remove_tree` leaves it with the attribute still set (084's criterion
   8). So the promise 084 did make for Windows is still checked there; only the guest-side
   question, which has no Windows answer, is blocked.

So the need does not hide a broken promise. The old answer was right; its form (a bare skip) was
one the judge refuses (spec 002, Decision 5). 094 changes the form, not the verdict.

## Acceptance criteria against evidence

1. On macOS, both rows pass through the full guest run — met, EXECUTED (both `PASSED`, need none).
2. With the predicate forced false, both rows `blocked` (`read-only files`), ratchet "unrun
   locally" — met, READ: the builder's stand-in (`build/094-standin.log`, landing notes); and
   INFERRED from `scoreboard.py:116` (`read-only files` is not in `PROTECTED_NEEDS`).
3. The new unit test and `test_no_ci_need_is_hidden_in_the_repository` pass — met, EXECUTED (in the 82 passed).
4. `test_rules.py`, `test_gather.py`, `test_plugin.py`, `test_scan.py`, ruff — met, EXECUTED (above).
5. The branch dry run: `judge (windows-2025, own-embedding)` shows both rows blocked, not FAIL,
   no G4 line — the first half met, EXECUTED (read from job 118434145425's log through the API):
   `wasi_python v1: 165/669 pass · 1 gap · 2 blocked · 0 fail · 501 deselected`, `blocked by:
   read-only files 2`, ratchet `lost 0 · unrun locally 2 · grew 0`. Before this spec the same
   shard had the two rows FAIL (wave 01's dry run). The gather's verdict (no G4 line for the
   rows) was not yet out when this review closed: the run was still in progress.

## The diff, point by point

- **The predicate matches only what it says, with one wording slip.** `_read_only_files()` is
  `os.name != "nt"`: unmet on Windows alone, which is exactly the system the dry run showed. It is
  a platform proxy, not a probe, like `descriptor limit` (`find_spec("resource")`). A probe would
  need a guest run inside the need, which the needs module never does. Its docstring says "a
  file's read-only mode refuses a guest's unlink: POSIX (a folder without write permission)": the
  parenthesis is right and the first clause is not (on POSIX the file's mode refuses nothing; the
  folder's does). See L1. The predicate is also met on POSIX as root, where modes refuse
  nothing; the check's own root skip covers that, and Decision 5 keeps it out of scope.
- **The POSIX assertions are unchanged (READ, the diff).** The only lines removed are the two of
  the `os.name == "nt"` skip; `needs.need("read-only files")` is added before the root skip and
  the setup. Every assertion after the guest's run (`exit_code == 0`, `refused PermissionError`,
  the file's bytes in both cases, exactly one `RuntimeWarning`) and the `finally` cleanup are
  byte-for-byte as on main.
- **The gather entry is tight.** `CI_NEEDS["read-only files"] = frozenset({"windows"})`, the shape
  of `descriptor limit`. `allowed()` (`gather.py:95-99`) needs both the node's own body to name
  the need (085, Decision 1) and the system to lack it. The new unit test proves the set of
  systems allowed is exactly `{"windows"}` for both rows, and that `needs_called` on the check's
  body is exactly `{"read-only files"}`. No other check names the literal (`hidden_ci_needs`
  passes), so no other node can borrow the block.
- **The flags are paste-safe and complete.** `--accept-judge "094: …"`: one double-quoted string,
  starting `094:`, with no `"`, `$`, backtick, `!` or backslash inside; semicolons and parentheses
  are inert in double quotes in zsh and bash. No growth, fewer-passes or retire flag is owed: the
  rows stay `pass` on darwin and Linux, and on Windows go FAIL → blocked. The claim list names the
  four judge files and the one unit test, which is the diff.

## Findings, most severe first

1. **M1. The README still reads as if the read-only attribute protects a file from a guest on
   Windows** (`README.md:3035-3043`, and *Not protected* `:3134-3136`). Medium (a guarantee 084's
   C2 asked for, not evidenced). 084's criterion 3 made the Windows skip conditional on three
   things: the rows skip, the landing notes record it, "and the README says nothing that
   suggests the read-only attribute protects a file from a guest". The README says "content the
   host made read-only is left, even when the guest moved it into its folder". True of the
   removal; but on Windows a guest with a writable grant or root deletes a file the host gave the
   read-only attribute, before any removal (wave 01's dry run). An embedder on Windows who reads
   that sentence may mark files read-only and expect them kept.
   Failure: Windows host, `Grant(folder, "/w", writable=True)`, a file in it with `S_IREAD` →
   the guest's `os.unlink` succeeds and the file is gone.
   Closing evidence: one README sentence, in *Not protected* or beside the removal bullet, e.g.
   "On Windows the read-only attribute does not stop a guest from deleting a file in a writable
   grant or root (wasmtime deletes it); only a POSIX folder without write permission refuses a
   guest's unlink." Or the owner's written answer that the current wording suffices. It is not a
   judge change and not in 094's four files, so it may ride on 094's branch as a README-only
   commit (not build-class) or go to a follow-up with a roadmap line; either closes M1.
2. **L1. The predicate's docstring names the wrong mode on POSIX** (`tests/harness/needs.py`,
   `_read_only_files`). Fix text: "Read-only content refuses a guest's unlink: on POSIX the host's
   folder without write permission does; on Windows the read-only attribute does not, and the
   guest deletes the file itself (spec 084's C2, …)." Code, so the builder's; no further round.
3. **L2. The block is unconditional, so a change in wasmtime would go unseen.** Before, a Windows
   guest that *refused* the unlink would have run the full check; now the Windows rows never run.
   That is the right trade for the judge (a need is decided before the check, spec 085), but the
   observation is wasmtime 49's. Fix text, for the spec's Decision 1: "Observed on wasmtime 49
   (wave 01's dry run). A wasmtime upgrade that changes how Windows deletes a read-only file
   revisits this need." Written in by this review (context only), see Disposition.

## Constitution checks

- §4: judge-only; no `src/`, `scripts/`, `recipes/`, pin or workflow file; no artifact in git;
  uv only. AGENTS rule 4: the judge is changed as its own change with a reason (the spec, the
  `--accept-judge` text); no check is weakened on POSIX, and the Windows block is allowed only
  where the platform lacks the property, through 085's own mechanism. Rule 5: no pass is lost;
  on darwin and Linux the rows stay passes and protected.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — open.
2. L1 — open (builder).
3. L2 — written in by the reviewer on the branch, `137c0a2` (context only; CI ran on `1d70261`, and a context-only commit needs no new run).

## Verdict

Lands once M1 is closed (a README sentence saying a Windows guest deletes a file the host gave the
read-only attribute, or the owner's written answer that the present wording suffices) and run
39361856604 finishes with no G4 line for the two rows and no red line other than GREW or G7; L1
needs no further round.
