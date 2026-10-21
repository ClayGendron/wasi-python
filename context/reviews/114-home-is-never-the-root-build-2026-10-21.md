# Review of 114 — HOME is never the root (the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude). It wrote none of 114. It did not review 114 before the
  build. It wrote none of the 0.1.0 security review, and none of 025, 032, 042, 084 or 111.
- **Reviewed:** `spec/114-home-is-never-the-root` at `59dafd6d`, checked out as
  `review/114-build`. The last code commit is `2147b335`; `59dafd6d` adds context only. The base
  is main `1875d4cd`, which is still main's tip. The diff is `git diff 1875d4cd 59dafd6d`: 14
  files, +1,332 −125.
- **Box:** 60 minutes (the lane's; build-class and runner code). Kept: 13:27 to 13:50.
- **Run:** the builder's run **39633291201** on `2147b335`, the exact code commit. I dispatched
  no run of my own, as the lane asked. Read back with `gh run view --json jobs`, each red job's
  `--log`, and eleven shard records (`gh run download`) (EXECUTED):
  - 37 jobs green: the build and judge, both rebuilds from the pins, the same bytes from every
    host, the three verify jobs, and every Linux and Windows judge shard.
  - `judge (macos-15, own-guest)`: `448/904 pass · 0 fail`. Its ratchet reads `lost 0 · absent 0 ·
    unrun 0 · gained 16 · grew 72`. Its only RED line is `RED: 72 metric(s) grew`.
  - `judge (macos-15, own-embedding)`: `180/904 pass · 0 fail`. Its ratchet reads `lost 0 · absent
    0 · unrun 0 · grew 19`. Its only RED line is `RED: 19 metric(s) grew`.
  - The gather was skipped behind those two jobs, so the run has no G line.
  - Every one of the 24 claimed rows (15 new, 9 changed) shows `pass` in the macOS, Linux
    and Windows records of its shard (`rows.py`).
- **Re-ran (EXECUTED, in this worktree; logs and scripts under `build/114-review/`):**
  - The fast tier, `uv run pytest -m "not slow" -n 3`, against the builder's set, in the lane's
    fast slot (`build/slots/fast` taken; `build/lane.lock` absent; the slot was removed after).
    Result: `658/904 pass · 0 gap · 42 blocked · 0 fail`. The ratchet reads `lost 0 · absent 0 ·
    unrun 0 · gained 15 · grew 81`. `rules 61/62` (1 blocked), `v1.4 231/231`. 2679 passed, 51
    skipped; exit 1, red by growth only (`fast.log`). The 42 blocked rows are this worktree's
    missing source trees and compile records.
  - Nine rules and unit node ids: the function-length, module-size, mutable, lock, private-API,
    platform and both citation checks, and `test_a_writer_cannot_keep_a_home_removal_going`.
    Result: 9 passed. Also `test_the_judge_patches_the_runner_only_through_the_process_object`:
    1 passed.
  - `uv run ruff check src tests`: clean. `uv run ruff format --check src tests`: 159 files
    already formatted.
  - The security review's three probes, copied unchanged into `build/114-review/probes/` and run
    with `WASI_PYTHON_ARTIFACTS` at the builder's set and `TMPDIR` at a scratch folder.
  - Five probes of my own: `r01_routes.py`, `r02_placeholder.py`, `r03_chmod.py`, `r04_fuel.py`
    and `r05_runner_fuel.py`.
  - A data-only diff of the two sets' zips (`zipdiff.py`, `uv run --no-project python -I`).

## The builder's self-check

The self-check list is present, and every item is checked. Two items are true only in part:

- "every number from a measured run". The claim block's count of new rows is wrong (L1).
- "the growth list is this build's". The reason it gives for the largest rows is not the cause
  I measured (L2).

The build's grep for other HOME readers, which Decision 5 asks the builder to list, is not
listed (L5).

## Acceptance criteria against evidence

1. **The new checks pass** — met. All 15 new rows pass in the macOS, Linux and Windows records
   of run 39633291201 (READ, `rows.py`), and in my fast tier (EXECUTED). That is 8 plant rows,
   2 stand-in rows and 5 HOME rows. On main's code they failed first: 12 failed and 2 passed
   (pre-build review, EXECUTED there), then 16 failed and 11 passed (`checks-on-main-2.log`,
   the builder's).
2. **The guest always has a HOME** — met. I checked six configurations: no root; no root with a
   writable grant; a root with a read-only grant at `/tmp`; a root with a mount at `/tmp`; a
   writable mount at `/`; a root with a writable mount at `/tmp`. In every one, `HOME` is
   `/tmp/.home-<32 hex>`. The folder is empty, and every write under it is refused (EXECUTED,
   `r02_placeholder.log`). Two sessions get two different HOMEs, and a session keeps its HOME
   across turns (EXECUTED). An `env=` HOME still wins: `/home`, `''` and `home` all reach the
   guest unchanged (EXECUTED, `r01.log`, `r02_placeholder.log`).
3. **Nothing becomes writable** — met. `test_nothing_is_writable_by_default[plain|snapshot]`
   keeps all four refusals (`/x`, `/tmp/x`, `/usr/local/lib/x`, `x`) and `no root`. It replaces
   the bare `no HOME` token with `HOME-refused`, a write it now attempts (READ, the diff; pass in
   all three systems' records).
4. **The placeholder leaves nothing** — met on macOS (EXECUTED), and read for Windows (READ).
   - macOS: some 50 calls and 6 sessions ran over the placeholder with `TMPDIR` at a scratch
     folder. Afterwards the folder held no `wasi-python-*` entry, only uv's own lock. While two
     sessions were open, their folders and locks were present, as expected. The read-only
     grant's folder stayed empty.
   - Windows: the logs of the Windows `own-guest` and `own-embedding` shards have no pytest
     warnings summary. So `_Private.remove` raised no left-folder `RuntimeWarning` there, while
     the new rows made and removed placeholders. No check holds this yet (L4).
5. **reportlab reads no start-up file** — met (EXECUTED, `zipdiff.py`).
   - Main's zip has 6,260 members. The branch's has 6,262. The two added members are
     `reportlab_mods.pyc` and `reportlab_settings.pyc`, at index 2890 and 2891. No member was
     removed. No member's bytes, CRC, size, date, compression or attributes changed, and the
     order is the same.
   - Each added member's code object names only `__doc__`, and its only constant is the
     docstring.
   - `python.wasm` is `d4192605…` in both sets, byte for byte.
   - The `MANIFEST` diff is exactly: the recipe's new line, `70_zip.sh`'s new hash, the zip's
     hash, and the snapshot's hash. The recipe's hash (`33a8c62f…`) and `70_zip.sh`'s hash
     (`44738584…`) equal the branch's files.
   - The diff touches nothing under `recipes/patches/` and nothing in `downloads/`.
6. **The judge changes are exactly those listed** — met. There are nine check rows, plus one
   unit test, which is claimed (Rule 4 below). `test_a_mount_at_tmp_means_no_home` keeps its node
   id: its first claim is reversed, and both loops and the last assertion stay (READ). My grep of
   `tests/` found no other check that encodes "no HOME" (L5).
7. **Not structural** — met.
   - Function lengths, measured with `ast` (EXECUTED): `_instance` 159 → 158, `_open_session`
     150 → 136, `_call_deferred` 43 → 24. The new functions are `_guest_home` 33, `_release_home`
     10 and `_remove_home` 7.
   - Module sizes: `_call.py` 1,337 lines, `_sessions.py` 1,096.
   - `LONG_FUNCTIONS` and `SEAM_ALLOWED` are unchanged: `test_rules.py` is not in the diff.
   - The rules checks are green (above).
8. **README and CHANGELOG** — met (READ).
   - Every README line in the Design is made, with the errors the build measured.
   - The CHANGELOG entry is under the one unreleased section.
   - `test_the_readme_reference_matches_the_api` passes in the fast tier (v1.4 231/231).
9. **Growth is named** — met for the bytes and for `-c pass`. The largest rows' cause is
   misnamed (L2). Lost 0, absent 0, fail 0.
10. **Code speaks for itself** — met. Both citation checks pass. The new comments and
    docstrings name no specification or review (READ).
11. **The run** — met. ruff is clean. The fast tier is red by growth only. Run 39633291201 was
    read: red by growth only, and the Windows legs are green.

## H2, read as an attacker (EXECUTED, against `SHA256SUMS` `60706eed`)

- **The security review's probes, re-run unchanged:**
  - `p05c_reportlab_mods.py`: all three configurations now print `PWNED_MODS False`. Those are
    a read-only grant at `/tmp` with no HOME, an `env=` HOME of `/home`, and the default. Before,
    the first two printed `PLANTED reportlab_mods RAN`.
  - `p05_planting.py`: `reportlab: planted code ran? OK False` in all three configurations
    (A, B and C), and no `/PWNED` in any root. In B (a read-only grant at `/tmp`), HOME is now
    `/tmp/.home-…`. scikit-learn's data home there is `PermissionError` on
    `<HOME>/scikit_learn_data`; before, it listed the planted `marker`, which closes L3.
  - `p05b_no_home.py`: `PWNED False` in all four `/tmp` swaps. `figure.hooks` still exits, which
    is L1, now documented and not fixed (Decision 3).
- **Every configuration the brief names** (`r01_routes.py`). Call 1 plants both dot-files at `/~`,
  `/home`, `/`, `/out`, `/out/~` and its own HOME. It also plants `reportlab_mods` and
  `reportlab_settings`, as `.py` files and as packages, in `/`, `/out`, the working folder and
  every `sys.path` entry. Call 2 imports `reportlab`, `reportlab.rl_config` and
  `reportlab.pdfgen.canvas`. In each configuration below, call 1 planted (24 to 26 files), and
  call 2 ran none of it: both hooks resolved to `/usr/local/lib/python315.zip/reportlab_*.pyc`.
  - a root with a read-only grant at `/tmp`;
  - a root with a mount at `/tmp`;
  - a writable mount at `/` (the provider kept every plant);
  - a root with `env={"HOME": "/home"}`;
  - no root, a writable grant at `/out`, and `os.chdir("/out")` before the import;
  - a root, a read-only `/tmp` and a writable `/out`, with the same `chdir`;
  - a session with a root and a read-only `/tmp`, planted in one session and imported in a
    later one;
  - a session with a root and a mount at `/tmp`.
  In every one, `sys.path` is `['/usr/local/lib/python315.zip']`.
- **My own routes** (none of the checks covers them). Each was planted, and none ran:
  - **An empty `env=` HOME on a reused root** (`r01`). `~` expands to `/.reportlab_mods`, in the
    root, and the plant is there. Only the stand-ins stop it: Decision 1 cannot help, because
    the embedder chose that HOME.
  - **A relative `env=` HOME** (`HOME="home"`, `r02`). `~` expands to `home/.reportlab_mods`,
    against the working folder, the root. The stand-ins stop it.
  - **One folder written by one call and imported by a later one** (`r02`). Call 1 granted the
    folder writable at `/out` and wrote `reportlab_mods.py` and `reportlab_settings.py` there.
    Call 2 granted the same folder read-only at `/ip`, with `import_path=["/ip"]`. reportlab
    imported the zip's stand-in. On main, the pre-build review saw this route run the plant.
  - **Spelled paths around the placeholder** (`r02`). These were `<HOME>/./x`, `/tmp/./<name>/x`,
    `/tmp//<name>/x` and `<HOME>/../<name>/x`. Each is refused (`EPERM`), or is `ENOENT` where
    nothing serves `/tmp`. None lands in a root or provider: the roots hold only `src` and `usr`
    afterwards, and the writable `/tmp` mount's provider holds nothing.

## The placeholder HOME

- **Can a guest write under it?** No (EXECUTED, `r02`, in all six configurations above). Each of
  these is `PermissionError` (63): `open` with `w`, `a` and `x`; `os.open` with `O_CREAT`;
  `mkdir`; `symlink`; `link`; `rename` into it; `rmdir` of HOME; `utime`; and `O_WRONLY` on the
  folder.
  - Renaming HOME away is `EPERM`, or `ENOENT` where nothing serves the target.
  - `os.chmod` "succeeds", but it is a no-op in the guest. preview1 has no call that sets a mode,
    and a host folder's mode was `0o700` before and after (`r03_chmod.log`).
- **Does it leak across calls or sessions?** No. Each call and session draws a fresh 128-bit
  name and a fresh `_Private` folder. A session keeps one HOME for its life, and a second session
  gets another (EXECUTED). Nothing is left in the temp folder after the process ends (EXECUTED).
- **Is its handle closed before its folder is removed?** Yes, by the code (READ).
  - The release callbacks run innermost first: `_instance` closes the store, then
    `_call_deferred` calls `_release_home`, which closes the walk and then removes the folder.
    Last, `_run_checked` closes every preopen's walk again, a no-op for this one.
  - In a session, `_release_session` closes the store, then the walks and the scratch folder,
    and then calls `_release_home`.
  - Windows' logs show no left-folder warning (criterion 4). No check holds this (L4).
- **Mount numbering, nested preopens, identity.** Right (READ and EXECUTED).
  - `_guest_home` appends to `preopens` before `_instance` and before the session's `every`. So
    `others`, `first = 3 + len(preopens)` and `_check_preopens(…, every)` all count it.
  - The HOME check's mount rows read the provider's file through the mount, so a mount
    numbered onto the placeholder would fail them. They pass on three systems.
  - My writable-mount rows served `/src` from the provider while the placeholder answered
    `EPERM`.
- **Does `test_nothing_is_writable_by_default` still hold every refusal?** Yes (criterion 3).

## The growth (EXECUTED unless marked)

- **Bytes.** The zip grows +1,289 (53,913,865 → 53,915,154). The snapshot grows +6,371
  (104,511,377 → 104,517,748), the macOS shard's GREW line. Both are measured.
- **`-c pass` through the branch's runner on both sets** (`r05`, the snapshot, metered; the code
  is held fixed, so only the set differs). Main's set gives 53,430,745 in both the default
  profile and with `root=True`. The branch's set gives 53,438,780 in both.
  - So the builder's default-profile growth of +15,468 is +7,433 from the code (the placeholder's
    preopen and `HOME` variable; 53,423,312 → 53,430,745) plus +8,035 from the rebuilt set.
  - `root=True` grows +8,035, the set alone.
  - That confirms the builder's sentence "the two profiles cost the same".
- **The largest rows are not start-up and not the runner** (`r04`, the judge's own driver, which
  makes no HOME).
  - `test_recursion_through_python_raises[min-key-snapshot]`: 56,821,847 on main's set and
    56,996,102 on the branch's, **+174,255**. That is exactly CI's line, and +0.31%.
  - `-c pass` on the same driver *falls* by 4,468.
  - My comparison of the macOS `own-guest` record with the accepted darwin-arm64 values: 120
    metrics grew and 110 shrank; the largest growth is that recursion row.
  - So the large rows are the rebuilt snapshot's changed heap and dict layout, in the program's
    own work. They are neither its start-up nor the HOME (L2).
- **Fair under rule 5?** Yes. The fix needs the zip changed, so the snapshot has to be rebuilt.
  The growth runs both ways, and its peak is 0.31% on one recursion row. Every red line in both
  macOS shards is a GREW line: lost 0, absent 0, unrun 0, fail 0 (READ, their ratchet lines). The
  earlier run's ABSENT (39626982133) is gone, because `2147b335` restored the old node id.

## Rule 4: the changed rows

Each change reverses one documented "no HOME" behaviour, and none is weakened:

- `test_nothing_is_writable_by_default[plain|snapshot]` is stronger: it now attempts a write
  under HOME and needs `HOME-refused`, and a `no-HOME` or `HOME-wrote` fails it.
- `test_no_root_and_no_grants_runs`, `test_a_mount_at_the_root[plain|snapshot]` and
  `test_a_mount_at_tmp_means_no_home` now assert the HOME's 11-character prefix in place of
  `None`. That is a check of form only. Read-only-ness is held by the new HOME rows for the same
  configurations. The mount-at-root row's provider-call bound is unchanged.
- `test_seaborn_takes_its_scipy_paths[plain|snapshot]` and `test_scikit_learn_says_what_it_lacks`
  read the measured `PermissionError` on `<HOME>/.cache` and on `<HOME>/scikit_learn_data`. They
  keep "no `~` folder in the grant" and the `images` row.
- The unit test `test_a_writer_cannot_keep_a_home_removal_going` calls `_call._remove_home`,
  whose body equals the removed `_sessions._remove_home`, line for line.
- **The stand-in check's defaults comparison** (`rl_config._DEFAULTS` against `rl_settings`) is
  right, and it is not a tautology. I read it in the pinned wheel, `rl_config.py:4-41`.
  `_DEFAULTS` starts as `rl_settings`, and then the names from `from reportlab_settings import *`
  are laid over it. So a stand-in that set a known option makes the comparison `False`. A
  stand-in that set an unknown option makes `getattr(rl_settings, k)` raise, so the guest exits
  non-zero. Comparing `rl_config.<name>` instead would be wrong, because `_startUp` converts
  `"A4"` to a tuple. That was the builder's fix.

## Findings, most severe first

No High. No Medium.

1. **L1. The claim block's count of new rows is wrong** (spec, "For the lane, as built", and
   "The checks on that set"). The block says "the 18 rows of the three new functions". There are
   15: 8 plant rows, 2 stand-in rows and 5 HOME rows. My fast tier says `gained 15`, and the
   records list exactly those 15. "All 27 rows of the new and changed checks" is 24.
   Fix text: "**new:** the 15 rows of the three new functions: the 14 of Decision 4 plus the
   stand-in check's second binary", and "All 24 rows of the new and changed checks pass".
2. **L2. The growth reason misnames the largest rows** (spec, "The fast tier": "Each is start-up
   on the rebuilt snapshot, or a no-root call's HOME preopen and variable"). Measured above, the
   top rows are neither: the recursion row grows +174,255 on the judge's driver, which has no
   HOME, while `-c pass` there falls by 4,468.
   Fix text: "Each grown row is the rebuilt snapshot (its heap and zip index moved, so a
   program's own work costs a little more or less: 120 rows grew and 110 shrank in the macOS
   guest shard), plus, in a call where the runner makes no fresh HOME, the placeholder's preopen
   and variable (+7,433 on `-c pass`)." The `--accept-growth` flag text may stay as it is.
3. **L3. The empty HOME outlives a failed `wt.Store`** (`src/wasi_python/_call.py`,
   `_call_deferred`). `_guest_home` runs, and appends to `preopens`, before
   `store = wt.Store(engine)`, which is outside the `try`. If `wt.Store` raises,
   `_release_home` never runs. Then the `_Private` folder and its lock stay until the process
   ends, and a later sweep removes them. The fresh HOME had the same shape before. It would
   take an out-of-memory error to trigger.
   Fix: wrap the store's creation, as in
   `try: store = wt.Store(engine)` / `except BaseException: _release_home(home); raise`. Or
   answer it in writing as accepted. The session path already releases `state.home` on any
   failure.
4. **L4. No check holds criterion 4 for the placeholder.** `test_a_call_without_a_root_shares_nothing`
   and `test_a_trapped_call_without_a_root_is_removed` watch a redirected temp folder, but only
   with `root=True`, so with a fresh HOME. The new HOME check watches the grant's folder, not
   the temp folder. A Windows regression in the release order would only queue a
   `RuntimeWarning`, and nothing would fail.
   Fix: one row beside the HOME check. Run `run(["-c","pass"])` first, then redirect
   `tempfile.tempdir` to a scratch folder. Make a call with a read-only grant at `/tmp`, and
   open and close a session. Assert the scratch folder is empty and that
   `_private_dirs._flush_warnings` gave nothing. It runs on every system. It can land later,
   with a gap entry naming its closer.
5. **L5. The build's grep is not listed.** Decision 5 asks the builder to list what its grep of
   `tests/` finds. I found no other check that encodes "no HOME":
   - the `.pdbrc` row, the deep-tree rows (`test_v1_4_embedding.py:1611-1720`) and
     `test_v1_4_embedding.py:1817` read a fresh HOME and are unchanged;
   - `tests/unit/test_guest.py:238` and `test_build_progress.py` set their own HOME.
   Fix text, in "As built": "The grep of `tests/` for `HOME`, `expanduser` and `'~'` finds no
   other check that encodes no HOME. The `.pdbrc` and deep-tree rows read a fresh HOME, and the
   unit tests that name HOME set their own. No stderr comparison of matplotlib or seaborn
   without a writable `/tmp` was found."

Notes (no action needed):

- **N1.** A program that calls `os.makedirs(os.environ["HOME"], exist_ok=True)` under a
  writable mount at `/` makes `/tmp` in the embedder's provider. The guest sees
  `/tmp/.home-…` exist, but not `/tmp` itself, so `makedirs` creates the parent (EXECUTED,
  `r01`: the provider held `/tmp` afterwards). The guest could write `/tmp` there anyway, so
  nothing is exposed. A `makedirs` under `~` does not do this, since HOME exists.
- **N2.** `_GuestHome` carries one value of two kinds as two optional fields, and exactly one
  is set. A small union, or one `release` callable, would say that in the type. That is
  cosmetic, and inside the rubric's tolerance.

## Constitution checks

- **§4.1 (recipes before patches)** holds. The fix is a recipe: one stand-in packed twice by
  `70_zip.sh`. There is no patch file and no reportlab byte change (criterion 5).
- **Every input is pinned.** `downloads/SHA256SUMS` is untouched.
- **uv only.** Every command above ran under `uv run`.
- **Tests count operations.** The new checks assert outputs and files, never time.
- **Artifacts never in git.** The diff has no `*.wasm` or `*.zip`.
- **Code speaks for itself.** Both citation checks pass.
- **Rule 4.** No check, golden output, gap or allowance is weakened. `tests/known_gaps.toml`,
  `tests/upstream/` and `context/progress/` are untouched.
- **§7 never-do list:** nothing tripped.

## Structure (one line, the reviewer's checklist 4a)

The diff moves one concern, choosing and releasing HOME, out of two places and into one helper
pair in `_call.py`. It adds no module-level mutable, lock, platform branch, private-API use or
test seam. No function grows past 80 lines, and the two on `LONG_FUNCTIONS` shrink. **Not
structural**, as the Kind line says.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — 
2. L2 — 
3. L3 — 
4. L4 — 
5. L5 — 

## Verdict

**Lands.** H2 is closed in every configuration I could reach, three of them my own, with no
High or Medium finding. The five Lows are written-in or answer-in-writing fixes; the lane reads
L1's count (15 new rows, 9 changed rows plus 1 unit test, none retired) and L2's growth reason
in place of the block's.

One line: the placeholder HOME and the zip's two empty hooks close H2 on every route tried. The
set's claims hold byte for byte. The growth is fair, but the largest rows come from the rebuilt
snapshot, not from start-up, and the new-row count is 15, not 18.
