# Pre-build review of 084 — a private root never outlives its call, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 084, nor the security review it closes.
- **Under review:** `context/specifications/084-a-private-root-never-outlives-its-call.md` on `spec/084-a-private-root-never-outlives-its-call`, commit `d203d78` over main `a6dfc17`. The branch changes only `context/` (`git diff --name-only`). Its evidence is in `context/research/2026-10-19-a-private-roots-removal/`. Its source is F1 of `context/reviews/0.1.0a7-security-review-2026-10-19.md`.
- **Read:**
  - the spec in full; the research's `proto_walk.py`, `proto_remove.py`, `p_deep_root.py`, `p_home.py`, `p311.py`, `matrix.sh` and every `.out`/`.log`;
  - in `src/wasi_python/runner.py`: `_Private`, `_drop`, `_abandon`, `_sweep_once`, `_sweep_entry`, `_try_lock`, `_unlock_close`, `_zip_folder`, `_zip_folder_locked`, `_remove_zips`, `_run_checked`'s `finally`, `_preopens`, `_call_deferred`, `_home_folder`, `_dir_fd_ok`, `_remove_home`, `_private` (the existing warning), and every `with _lock:`;
  - `tests/unit/test_runner_sweep.py` (the fixtures, and the check Decision 9 restates);
  - README *Safety* and *Not protected*; `.github/workflows/release.yml` (`UV_PYTHON`);
  - CPython `Modules/posixmodule.c` (`os_chmod_impl`, both the POSIX and the Windows branch) and `Lib/os.py` (`supports_follow_symlinks`), `context/prior_art/cpython` at `7c04882`;
  - wasmtime 49 `crates/wasi/src/filesystem/windows.rs` (`symlink`);
  - 078's Decision 14 (`spec/078-…` at `fb41ed4`, not built), and the in-flight branches' diffs against `a6dfc17` (073 built, 078 and 083 spec only, 085 and 087 empty).
- **How I ran things:** in the 084 worktree with `uv run`, against a `cp -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` in my scratch folder. Every probe set `tempfile.tempdir` to a folder of its own. The 3.11 run used a scratch venv (`UV_PROJECT_ENVIRONMENT`, `--frozen`). Probes are in `probes/` beside this file, logs in `logs/`. Every tree they left was deleted by name. I wrote nothing in any git tree. I did not run the judge: the branch carries no code, so its scoreboard is main's.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The diagnosis is right. I reproduced it: at a soft limit of 128, a 256-level tree leaves the private root, for `run` and for a session (EXECUTED). The two-descriptor walk is the right shape. Its prototype removed both leftovers with four free descriptors and a peak of two (EXECUTED).

**The climb's identity check works.** I attacked the prototype at exact steps: a subtree moved out of the tree after the walk opened it, a subtree renamed up, a parent moved out. In each case the walk stopped and the canary outside the tree was kept. Without the check, the same walk climbed out and emptied the canary and the folders beside it (EXECUTED). So the check carries the safety. But no check in the spec tests it.

Things to settle before building, most severe first:

- **F1 (high). Decision 4 turns the runner into the guest's deputy.** A guest that cannot delete a file in a folder the host made read-only moves that folder's writable parent into its `HOME`, or into its private root. Then the removal makes the folder writable and deletes the file. Main leaves the file (EXECUTED, both cases). Drop the repair.
- **F2 (medium). No check guards the identity check.** The spec's whole safety claim rests on it, and removing it lets the walk climb out (EXECUTED). Add a check, with that stand-in.
- **F3 (medium). The walk has no bound against a concurrent writer.** Another call on the same root can keep a `HOME`'s removal running, and so keep the first `run` from returning, for as long as it writes (EXECUTED: 20,000 files written, 20,002 unlinks). Bound it, or name it.
- **F4 to F10 (low and nits):** the chmod by name follows a link on Linux, and `os.chmod` follows links on Windows; a link swapped in is left rather than unlinked; the re-arm comes before the name is dropped, and the warning may be given under a runner lock; a session's `HOME` has no check; the 3.11 `RecursionError` happens at Linux's common limit of 1,024 and deserves its own CHANGELOG line; some wording; 073 shares a check file.

## 1. The walk's safety: the `..` race (question 1)

**The attacks** (`probes/r2_walk_attacks.py`, `logs/r2.log`, EXECUTED on darwin arm64, CPython 3.14.2). Each attack is made by a hook on `os.open`, `os.unlink` or `os.scandir`, at an exact step, so none depends on timing. Each tree is six levels, with a file at each level. `outside/keep` is the canary. The mutant is `proto_walk.py` with its one identity-check line replaced by `if False:`.

| attack | prototype: returned, canary | mutant (no identity check): canary |
|---|---|---|
| A2. Level 4 moved into `outside/` just after the walk opened it | False, **kept** | **emptied; `outside/` removed** |
| C2. Level 4 renamed up to `tree/up` just after the open | False, **kept** | **emptied** |
| D. Level 3 moved into `outside/` while the walk is in level 4 | False, **kept** | **emptied** |
| A, C. The same moves just *before* the open | True, kept (the open fails `ENOENT`; nothing escapes) | kept |
| B. Level 3 swapped for a link to `outside/` before the open | False, kept; **the link is left** (F5) | kept |

- **The mutant climbed as many levels as it had frames.** In my first run, its climb from D left the case's folder and removed the sibling cases' folders beside it. That is the shape of the real danger: in a 1,000-level tree, a move at depth *d* would let an unchecked walk climb up to *d* levels above the top, out of the temporary folder.
- **Does the check close it? Yes, for climbing.** The walk only ever holds a folder it opened by name, with `O_NOFOLLOW`, from a folder it held, or a `..` whose `(st_dev, st_ino)` matched the recorded parent. A mismatch stops the walk before any `rmdir` or listing in the new folder (A2, C2, D).
- **Does it need checking before every unlink? No (INFERRED).** An unlink acts on an entry of the folder the walk holds. If someone moved that folder, they needed write access to both its old parent and its new one. So the folder and everything in it are theirs to delete anyway. A check before each unlink would not close the window either: the move can come just after it. The one way this reasoning fails is when the walk does more than the mover could. That is F1.
- **Who can move things during the walk?** For a private root, the guest has finished (`_run_checked`'s `finally`, after the store closes, READ), and the folder is `0700`. So only a host process of the same user can. For a `HOME` in a caller's root, another call on the same root can, while it runs. The README already lists "concurrent calls on one root" under *Not protected*, with "nothing outside the grants changes". The identity check keeps that promise for climbing. F1 and F4 are where the design breaks it.
- **A bind mount** (INFERRED, not run): `st_dev` does not tell a bind mount of the same filesystem from a plain folder, so the walk would enter one. Only root can make one. And `shutil.rmtree` enters every mount today. So this is wording only (F9).

## 2. TOCTOU on the chmod (question 2)

- **Through a descriptor, it is safe (READ).** The prototype makes the folder it holds `0700` with `os.fchmod(cur, …)`, on the descriptor it opened with `O_NOFOLLOW`.
- **By name, on Linux, it follows a link (EXECUTED, the Linux branch forced on macOS, `probes/r3_chmod_toctou.py`, `logs/r3.log`).** For a folder it cannot open at all (mode `0000`), Decision 4 chmods by name. On macOS it uses `follow_symlinks=False`. On Linux, `os.chmod` is not in `os.supports_follow_symlinks` (READ, `Lib/os.py:179`, the line is commented out), so the spec falls back to a plain `fchmodat`, which follows links. I swapped the folder for a link between the refused open and the chmod. On the Linux branch, a file outside the tree went from `0644` to **`0700`**. On the macOS branch, only the link changed.
- **The spec's premise is wrong for one folder.** It says "nothing writes a dead root, so the name cannot change in between". A `HOME` in a caller's root is not dead: another call on that root can write it. A guest can make a link that points out (README *Safety*). The `0000` folder must have been made by the host, so the case is rare.
- **The same on Windows (READ).** `os.chmod(path, stat.S_IWRITE)` opens the path with `CreateFileW` *without* `FILE_FLAG_OPEN_REPARSE_POINT` when `follow_symlinks` is True, the default (`os_chmod_impl`, `MS_WINDOWS` branch). CI runs 3.14.2. So a read-only link whose delete is refused would have its *target's* attribute cleared.
- Both go away if F1 drops Decision 4. If any repair stays: on Linux, try `os.chmod(name, 0o700, dir_fd=cur, follow_symlinks=False)` and treat `NotImplementedError`, `ValueError` and `OSError` as "left". glibc 2.32 and later do this for a non-link, and refuse a link. On Windows, pass `follow_symlinks=False`, and touch only entries that `lstat` says are not links (F4).

## 3. Windows (question 3, READ and INFERRED)

- **`\\?\` paths, down by name, up by dropping a name.** No `..` is used, so the climb race of §1 does not arise. But a descent by path follows any reparse point that a concurrent actor swaps in between the listing and the next call. `shutil.rmtree` on Windows has the same exposure (`avoids_symlink_attacks` is False there). The spec's Decision 8, "the walk adds its identity checks, so … cannot lead it outside the tree", is true on POSIX only. It should say so (F9).
- **Can a Windows guest make links?** The runner's comments say it cannot (`runner.py:2467`, `:3430`). wasmtime 49 does call `symlink_dir` or `symlink_file` there (`filesystem/windows.rs:180`). That succeeds where the user holds the symbolic-link privilege, and GitHub's Windows runners run as an administrator. This matters only for a `HOME` in a caller's root shared by concurrent calls, already *Not protected*. But the README's new sentence should not repeat "cannot".
- **Junctions:** `is_dir(follow_symlinks=False)`, plus `is_junction()` or the 3.11 reparse-tag test, then `os.unlink`. That matches what `shutil` does (READ, as the spec cites).
- **Read-only attribute:** F1 (the deputy) and F4 (the chmod follows links).
- **Open handles:** windows-2025 deletes with POSIX semantics on NTFS, so a scanner's handle rarely blocks the parent's `rmdir` (INFERRED). If a Windows shard ever shows a stray `RuntimeWarning` in criterion 1's "no warning" assertion, a scanner is the first suspect, not the walk.
- **What the Windows shards will prove.** Criteria 1, 2, 3 and 6 to 11 on `windows-2025` prove four things: host paths past 260 characters are removed; the retry, the bound, the warning and the `finally` work there; the restated check holds; and (if kept) the read-only repair works. Criterion 5 will *run*, not skip, on GitHub's runners (they have the privilege). The shards cannot prove any race-freedom on Windows: nothing in the spec claims it there, and the README should not.

## 4. The retry and the lock protocol (question 4)

- **A root in use is never swept (READ).** A live call's folder is in `_held` and its lock file is locked. A sweep skips a name in `_held`, and `_try_lock` refuses a held lock: with `flock` on POSIX (per open file description), and with `LockFile` on another handle on Windows. A filesystem without locks gives `None`, and `_Private` then writes no identity, so that folder is never swept. Re-arming runs the sweep more often. That exercises the creator-versus-sweeper window more often too, but the existing checks cover it (`test_a_lock_file_swept_before_its_lock_makes_the_creator_draw_again`). The protocol holds.
- **Order of the re-arm and the drop (F6).** The Design says `_left(…)` warns and re-arms, then `_drop(self.name)` runs in a `finally`. That order is wrong. Another thread's call can run `_sweep_once` between the two. It claims the sweep, sees the name still in `_held`, and skips it. The re-arm is used up, and the folder waits for the next process. The warning sits in that window and widens it. Fix: drop the name first, then re-arm.
- **A re-arm during a running sweep** lets a second sweep start in the same process while the first is still listing. On a local filesystem, `flock` keeps their walks apart. On NFS, `flock` may be per-process, which is why `_held` exists. There, two walks could run on one folder: harmless to the data, but they produce a false failure and a false warning. Re-arm after the sweep's loop ends, not from inside `_sweep_entry` (F6).
- **The bound of three** is reasonable. It costs one listing of the temporary folder per failed name, at most three times per name per process. The dictionary and the warned set grow only with failures.
- **The review's own suggestion** was to keep the name in `_held` until the folder is gone. Decision 5 answers it in writing ("Why the sweep"). I agree with the answer.

## 5. A warning, not a `stats()` key (question 5)

- **Right against spec 049 (READ).** `tests/public_api.txt` lists no warning. `stats()` documents that "a later release may add keys", but a key is still a line in the frozen file. A warning changes nothing there, and the runner already warns for a module cache it refuses (`_private`, `runner.py:3797`).
- **Guarded against `simplefilter("error")`:** right. Nothing a guest does may make `run` raise.
- **Give it outside every runner lock (F6).** `_Private.remove` runs under `_zip_lock` on two paths (`_zip_folder`'s re-make, `_zip_folder_locked`'s failure, READ). Under 078 it may run under the home's lock, on the guest thread. `warnings.warn` calls the embedder's `showwarning` (for example `logging.captureWarnings` with a handler). If that handler calls `wasi_python.stats()` (which takes `_lock`, not re-entrant) or `run`, it deadlocks under the lock held. So: collect the message under the lock, and warn after releasing it.
- **Three:** fine.

## 6. The 3.11 `RecursionError` (question 6)

- **It happens at Linux's common default, not only at 8,192 (EXECUTED, `logs/r4_311_1024.log`).** On 3.11.14 at a soft limit of 1,024: 990 levels return exit 0 and are removed; **1,010 levels make `run` raise `RecursionError`** out of `remove:918`, leaving the root and its lock. At 1,024, recursion (about 995 frames) comes before `EMFILE` (about 1,015), so every depth past about 995 raises.
- **Yes, its own line (F8).** This breaks a different promise from F1: "nothing a guest does makes `run` raise". And the lock stays held for the process's life. The 0.1.0a7 review did not find it (it ran 3.14). Give it its own **Fixed** bullet, and propose a one-line addendum to the security review for the lane.
- **No release job will prove the fix.** CI pins `UV_PYTHON: "3.14.2"` (READ). The walk does not recurse, so the fix holds by construction, and criterion 9 is the stand-in. The builder should run criteria 1 and 3 once under 3.11, as the author's `p311.py` did, and record it in the landing notes.

## 7. The checks (question 7)

- **They count, never time.** Entries, descriptors and calls. The 120 s fail-safe decides no verdict.
- **They fail today.** Criteria 1 and 2 by behaviour. I re-ran criterion 1's parameters on main for `run` and `session`: one `EMFILE` and 119 `ENOTEMPTY`, 256 levels left (`logs/r5_criterion1_on_main.log`). Criteria 3 to 10 fail at least by `AttributeError` on `runner._remove_tree`, and the spec names a behavioural failure "in kind" for each.
- **The restated check is faithful (READ).** Today's body patches `shutil.rmtree` to do nothing and asserts both entries are kept, then that one sweep removes both. The restated body makes the same assertions through `runner._remove_tree`. Its name is kept, and the judge-hash line will show it. Two small things:
  - its explicit `claimed = False` now hides the re-arm (criterion 7 covers that);
  - `remove()` will now warn, so wrap it in `pytest.warns(RuntimeWarning)`, which adds to the check and weakens nothing.
  - `shutil` may become unused in the file (ruff F401).
  - No other check patches `shutil.rmtree` for the runner's folders (grep).
  - `test_a_private_folder_goes_before_its_lock_file` asserts exactly one `os.unlink` during `remove()`. It stays true only because its folder is empty, so the walk should not call `os.unlink` on the top of an empty folder.
- **Missing checks:**
  - the identity check (F2);
  - a folder swapped for a link mid-walk (F5);
  - a session's `HOME` (F7);
  - F1's case, the guest moving a read-only folder in;
  - the writer bound (F3), if a bound is chosen.
- **For the builder:** criterion 3's 1,000-level tree (2,000 characters) must be built through `dir_fd`, since macOS's `PATH_MAX` is 1,024. The "three free descriptors" arithmetic should count the holes below the limit. My count found four free with the parent held (`logs/r6.log`).

## 8. Coordination (question 8)

- **078 (READ, its Decision 14; not built).** It registers the teardown steps (the scratch folder, the `HOME`, the private root) with the home. They run through `home.finish()`, under the home's lock, on the guest thread if the home was abandoned. 084 is compatible:
  - the walk holds no recursion;
  - it never raises (Decision 6), which 078's steps need;
  - but its warning and its re-arm (`_lock`) must not run under the home's lock (F6). Name this in Decision 11 for whichever lands second.
- **083:** as the spec says, no dependency.
- **073 (built, waiting to land)** adds 223 lines to `tests/checks/test_v1_4_embedding.py`, where criteria 1 and 2 go. That is textual only, but Decision 11 should name it (F10).
- **072:** as stated.

## Findings, most severe first

### F1. Decision 4's permission repair deletes what the guest itself cannot. High (EXECUTED)

`probes/r1_escalation.py`, `logs/r1-*.log`. The setup: a writable root (or, for the second case, a writable grant at `/w` beside `root=True`) holds `data/ro/` at `0500`, made by the host, with a file `secret` in it.

- **What the guest does.** It tries `os.unlink` on the file and gets `PermissionError` (WASI errno 2, `EACCES`). Then it renames `data` (writable) into `$HOME`, or into its private root (`/data`). Nothing else.
- **Main:** `rmtree` meets `EACCES` and leaves the file, moved but intact, in both cases.
- **The design** (the author's `proto_walk.remove_tree`, routed in for the runner's removals): it `fchmod`s `ro` to `0700` and **deletes `secret`**, in both cases. The call returns exit 0. Nothing is warned.

What this breaks:

- **The confused deputy.** A guest runs as the host user, but WASI gives it no chmod. So host modes bind it, and an embedder may rely on that to protect a subfolder of a writable grant. The repair spends the host's power over modes on whatever the guest moved into a folder the runner removes. On Windows the same holds for the read-only attribute (INFERRED): a read-only file can be renamed but not deleted, so a guest moves it in and the removal clears the attribute and deletes it.
- **Its motivating cases are nearly empty.** The spec's own reasons are "an embedder's tool, or a umask". The runner chmods nothing read-only itself (READ: its only `chmod`s set `0o644`). A umask that removes the owner's write bit also makes the guest's own folder unwritable.

**Fix:**

- Drop Decision 4, on POSIX and on Windows. A host-made read-only folder is then left: warned about, kept with its lock file, retried, then left for the next process. That is the failure path the spec already has.
- Invert criterion 6. Read-only content is left, the removal returns False, and one warning names it.
- Add F1's case as a check: a guest moves a writable folder that holds a `0500` folder into `HOME`, and into its private root; afterwards the protected file still exists.
- If a repair is kept anyway, it needs a rule that tells the call's own folders from moved-in ones. I see none that holds.

### F2. No check guards the identity check, the design's central safety property. Medium (EXECUTED)

Removing the one line that compares `..` with the recorded parent lets the walk climb out and empty folders above the tree (§1 table, `logs/r2.log`). No criterion fails with that mutant: criteria 3 to 8 build static trees.

Add a unit check, `test_the_walk_never_climbs_out_of_a_moved_folder`, with hooks as in `probes/r2_walk_attacks.py`, on POSIX:

- **the cases:** a subtree moved into a canary's folder just after the walk opens it; a subtree renamed up; a parent moved out;
- **what it asserts:** `_remove_tree` returns False, and the canary holds `keep`;
- **its stand-in:** the identity check removed, which empties the canary.

It counts calls and times nothing.

### F3. The walk has no bound when another writer adds entries during it. Medium (EXECUTED)

A hook that adds one file after each unlink, up to N files: N = 1,000 gave 1,002 unlinks and 1,007 listings; N = 20,000 gave 20,002 unlinks and 20,007 listings (`logs/r2.log`, `E_writer_*`).

- **Why it does not stop.** Decision 2 lists a folder again whenever a listing removed something. So the work grows with the writer, without limit.
- **Who can write.** For a `HOME` in a caller's root, a concurrent call on that root can. It can be a session, or a call with `deadline_s=None`.
- **What it costs.** The removal runs in the first call's `finally`. So that `run` does not return while the other guest writes.
- **Today's `rmtree`** lists each folder once and gives up.

Fix, either way:

- **Bound the walk.** List a folder again only after a descent, or once after an unlink-only pass (that covers readdir skipping entries removed during a listing). Or give each removal a budget of operations, and return False past it.
- **Or name the hang** under *Not protected* beside "concurrent calls on one root".

A private root has no concurrent writer, so this is about the `HOME` only.

### F4. The chmod by name follows links: on Linux, and on Windows. Low (EXECUTED for Linux's branch, READ for Windows)

§2. The fix is F1's. If any repair survives, use `follow_symlinks=False` on Windows, and try `fchmodat` with `AT_SYMLINK_NOFOLLOW` on Linux, treating `NotImplementedError` and `ValueError` as "left". Decision 4's sentence "nothing writes a dead root" is wrong for a `HOME` either way.

### F5. A folder swapped for a link mid-walk is left, not unlinked. Low (EXECUTED)

Decision 2 says such a link "fails the `O_NOFOLLOW` open and is unlinked on the next listing". The prototype adds the name to its skip set on any `OSError` from the open. So the link stays, and the walk returns False (attack B). It is safe, but it is not what the spec says.

- The builder should list again after `ELOOP` or `ENOTDIR` from the open, rather than skip the name.
- Criterion 5 should add this swap by hook. It tests static links only.

### F6. Re-arm after the drop, and warn outside every runner lock. Low (READ, INFERRED)

§4 and §5:

- `_drop(name)` first, then the re-arm; otherwise a concurrent sweep uses up the re-arm and skips the held name.
- Re-arm after the sweep's loop ends, not from inside `_sweep_entry`.
- Give the warning after releasing `_zip_lock`, `_lock`, `_held_lock` and, under 078, the home's lock.

Criterion 7 could cover the first point deterministically: patch `runner._drop` to run `_sweep_once()` before it drops, then assert that the folder is still swept by the next call.

### F7. A session's `HOME` removal has no check. Low (READ)

Decision 1 changes `_remove_home` too, but criterion 2 runs `run` only. Criterion 1's `[session]` builds its tree at `/` of a private root, not under `HOME`, so `_remove_home` never meets a deep tree there. A stand-in that leaves `_remove_home` on `rmtree` fails nothing. Add `test_a_deep_fresh_home_is_removed[session]`: a `Session` with a caller's root, a turn that builds 256 levels under `HOME`, then the close.

### F8. The 3.11 `RecursionError` needs its own CHANGELOG line, and happens at 1,024. Low as written; it is a promise broken (EXECUTED)

§6:

- Correct the problem statement: it happens at the common Linux limit of 1,024, from about 995 levels, not only at 8,192.
- Give it its own **Fixed** bullet ("on 3.11 a guest could make `run` raise `RecursionError` and keep its lock for the process's life").
- Have the builder record one 3.11 run of criteria 1 and 3, since CI runs 3.14.2 only.

### F9. Wording. Nit (INFERRED, READ)

- "One filesystem": `st_dev` does not see a bind mount of the same filesystem. Say "never enters a folder of another device".
- "Needs no free disk space": true for `unlink` and `rmdir` on the common filesystems. A copy-on-write filesystem filled to the last block (btrfs) can still refuse them. Say "creates nothing".
- Decision 8's "cannot lead it outside the tree" is POSIX only (§3).
- The README should not say Windows guests cannot make links (§3).

### F10. 073 also edits `tests/checks/test_v1_4_embedding.py`. Nit (READ)

Name it in Decision 11. Whichever lands second rebases that file.

## Notes (no finding)

- The rejected alternatives are argued well. I agree with each:
  - **rename-up** fails on a full volume (`t_full.out`);
  - **`fwalk`** keeps a descriptor per level (READ);
  - **`rmtree` then a fallback** keeps two paths, and the one that matters runs least;
  - **a native `rm`** breaks §2.2 and spec 015's fork refusal.
- **Parallel-safe, not build-class:** right. Only `runner.py`, tests and docs change; no `scripts/`, `recipes/`, pins or workflow.
- **A link at the top:** `_sweep_entry` keeps refusing one, while `_Private.remove` would unlink one. The two are consistent: the sweep's check runs first, and a link there was never the runner's.
- **The walk's cost on a default call:** a handful of extra calls on a five-folder tree, as the spec says (`t_walk.out`: 3.5 counted calls per entry).

## Verdict

**Ready once F1 to F3 are written in:**

- **F1:** Decision 4 dropped (POSIX and Windows), criterion 6 inverted, and F1's moved-in case added as a check.
- **F2:** a check of the identity check, with its stand-in.
- **F3:** a bound on the walk's re-listing, or the hang named under *Not protected*.

F4 to F10 are small. Write them in at the same time; F4 goes away with F1. None needs another pre-build review if written as above. The build review should re-run F1's and F2's probes against the built code.

## One line

The two-descriptor walk is right and its climb check holds under attack. But the permission repair lets a guest delete host-protected files by moving them into its own folders, the climb check has no test, and a concurrent writer can keep the walk going forever: ready once those three are written in.

## Confirmation of the revision (`eaf584d`), 2026-10-19

- **Reviewer:** the same agent. I wrote none of the revision.
- **Under review:** the spec at `eaf584d` on the same branch, still over main `a6dfc17`; its "Disposition of the pre-build review" section; `proto_walk2.py`; and the new outputs (`p_guest_modes.out`, `r1_escalation_walk2.out`, `r2_walk2.out`, `t_writer.out`/`.py`, `t_walk2.out`). The branch still changes only `context/`.
- **How I ran things:** as before. My own probes were pointed at `proto_walk2.py` (`probes/r1_escalation_w2.py`, `probes/r2_walk_attacks_w2.py`), plus one benchmark probe (`probes/r7_entry_rate.py`). They ran against the same set copy. Every tree they left was deleted by name. I wrote nothing in any git tree.

### My probes against the revised walk (EXECUTED)

- **F1:** `logs/r1-w2-home.log` and `logs/r1-w2-private.log`. In both cases the guest's unlink is refused (`PermissionError`) and it moves `data/` in. Afterwards the revised walk has **kept `secret`**: under `tmp/.home-…/data/ro/` for `[home]`, and in the left private root, with its lock file, for `[private]`. That matches the author's `r1_escalation_walk2.out`. **Closed.**
- **F2:** `logs/r2_w2.log`. With the identity check, A2, C2 and D return False and keep the canary. Without it, all three empty it. Every case peaked at two descriptors. That matches `r2_walk2.out`. Criterion 7 runs exactly these three, with that stand-in. **Closed.**
- **F3:** in the same log, a writer adding 20,000 files against a budget of 10,000 makes the walk return False after 4,996 unlinks. The default budget lets the 20,000-file writer finish. That matches `t_writer.out`. **Closed for the writer.** But see C1.
- **F5:** attack B still returns False and leaves the link and the moved folder, and Decision 2 now says exactly that. Criterion 6 adds the swap. **Closed.**

### Each finding, read against the revision

- **F1:** Decision 4 now forbids any repair, on POSIX and Windows, and Decision 3 says the read-only attribute is never cleared. Criterion 8 is the inverted draft criterion 6. Criterion 3 is my case, both rows, and its stand-in is the drafted repair. The author's new measurement (`p_guest_modes.out`) settles what dropping the repair costs: in the guest, `mkdir`'s modes, `O_CREAT`'s modes and `chmod` change no host mode (`0755`, `0644`), and `fchmod`, `umask` and `mkfifo` are missing. So read-only content in a removed folder is always the host's. Taken. One Windows caveat: C2.
- **F2, F3, F5:** above.
- **F4:** gone. No `chmod` remains, and criterion 4 counts `os.chmod` and `os.fchmod` at 0.
- **F6:** taken, all three.
  - `_drop` comes before the re-arm (Decision 5, the Design). Criterion 10's drop-order case is the deterministic test I suggested.
  - The sweep re-arms after its loop. Criterion 10 asserts that `claimed` stays True during the loop.
  - Warnings are queued and flushed where no runner lock is held. Criterion 14 checks each lock with a non-blocking `acquire` and calls `stats()` from the handler. Its stand-in (warning inside `remove`, under `_zip_lock`) bites, since the lock is not re-entrant. The flush-at-return design also covers 078's abandoned teardown (the next flush gives it).
- **F7:** criterion 2 `[session]` reaches `_remove_home`, with its own stand-in.
- **F8:** the problem statement now gives the 1,024 row. The CHANGELOG gets its own bullet (criterion 19), and criterion 16 records a 3.11 run.
- **F9, F10:** done. That includes correcting the runner's two "cannot make links" comments, which is in scope (comments only).
- **The restated check:** `pytest.warns` with the flush inside. Its `claimed = False` is kept, so it does not depend on the re-arm. Faithful, and stronger.

### Still open

**C1. The budget applies to private folders, where no writer exists, and so a big enough tree outlives its call again. Low to medium (EXECUTED for the rate; INFERRED for the totals).**

- **What happens past the budget.** Decision 12 gives every `_remove_tree` call 2**20 counted calls, and a private root past that is "removed over several attempts". But the attempts per process are bounded: its own removal and three sweeps, about 4.2 M calls in all. A name at its bound is then skipped by this process for good.
- **How fast a guest makes entries.** A guest made **83,000 empty files in 10 s** in its private root on darwin (`logs/r7_entry_rate.log`, a benchmark fact). That is about 500,000 in a default 60 s call: within one budget. But a `Session(root=True)` keeps its root across turns, each with its own deadline, and `deadline_s=None` has none (the spec's own "How deep a call gets"). A root of more than about four million entries is therefore left by this process, call after call. In a long-running server, disk use again adds up across calls: F1's original harm, by size instead of depth.
- **The budget buys nothing there.** Its only reason is a concurrent writer. Decision 8 says no private folder has one: the guest has ended, the folder is `0700`, a dead root's process is gone, and only the runner writes the stdin, scratch and zip folders. A same-user host process is already handled by the identity check.
- **Fix (pick one, in writing):**
  - apply the budget to the `HOME` removals only (`_call_deferred`, `_remove_home`), and leave `_Private.remove` and `_sweep_entry` unbudgeted; or
  - keep it everywhere, and say in the Intent and the README that a private root of more than about four million entries can be left until a later process.

  The first keeps the Intent's promise ("gone when the call returns, whatever the guest built"). Criterion 9 then patches the budget on a `HOME`-style call, and could add a private-folder row showing that no budget applies.
- **A benchmark fact for the README sentence.** The revised walk spent 83,103 counted calls in 4.3 s of host time on that flat tree. So "about a million system calls" is roughly 50 s on an arm64 Mac, and the README could say so.

**C2. The Windows row of criterion 3 assumes a guest cannot delete a read-only file. Low (INFERRED; check at build).**

- **Why it may not hold.** wasmtime 49's Windows `remove_file_or_symlink` opens the file for `DELETE` and calls cap-primitives' `remove_file`, which goes through Rust's `std::fs` (READ, `filesystem/windows.rs:188`). As far as I know, recent Rust standard libraries can delete a read-only file on Windows, but I could not confirm this offline. If the toolchain that built the pinned wasmtime does, a Windows guest deletes `secret` itself. Then criterion 3's Windows rows fail at "the guest gets `PermissionError`", or prove nothing.
- **What the builder should do:** look at the guest's unlink result on the Windows shard (or on a Windows machine first). If the unlink succeeds, the Windows rows should skip with that reason, and the README should not suggest that the read-only attribute protects anything from a guest. Criterion 8's Windows row still guards the walk itself.

**N1 (nit).** On `EACCES` from opening a folder (an empty `0000` folder in criterion 8), the walk could try `rmdir` before recording the name as failed. `rmdir` of an empty folder needs only the parent's write permission, which the guest has as well, so it oversteps nothing. Optional.

### Verdict

**Confirmed once C1 is written in:** either the budget limited to the `HOME` removals, or the residue stated in the Intent and the README. C2 is a check for the builder on the Windows shard, and N1 is optional. Neither needs another look before build. The build review should re-run `r1_escalation.py` and `r2_walk_attacks.py` against the built `_remove_tree`.

**One line:** F1 to F10 are closed. My probes keep the protected file and the canary against the revised walk. One thing is left: the writer's budget also caps private folders, which have no writer, so a session-sized tree can outlive its call again. Exempt them, or say so.
