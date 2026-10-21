# Review of 114 — HOME is never the root

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (pre-build reviewer; wrote none of 114, none of the 0.1.0 security
  review, none of 025, 032, 042, 084 or 111)
- **Reviewed:** the specification as drafted,
  `context/specifications/114-home-is-never-the-root.md`, and its three new check functions in
  `tests/checks/test_v1_2_hostile_guest.py`, at `aa427420` on `spec/114-home-is-never-the-root`
  (`git diff 1875d4cd aa427420`: the specification, the roadmap line, 175 lines of checks); read
  on `review/114-spec` at that commit
- **Run:** none (pre-build review of the draft; no build, no dispatch)
- **Re-ran:** the three new functions by node id, against the main tree's frozen set
  (`WASI_PYTHON_ARTIFACTS=…/build/artifacts`, `SHA256SUMS` sha256 `d0d91cef…`), on main's code →
  **12 failed, 2 passed**, exit 1 (`build/114review/checks-on-main.log` in this worktree): the six
  plant rows fail on `b'PLANTED RAN\nimported\n' != b'imported\n'`, the stand-in row on exit 1
  (`ModuleNotFoundError`), the five HOME rows on `"home": false` (with a root also
  `"planted": true`); the two fresh-HOME rows pass. Two guest probes of my own over the same set
  (scratch scripts, nothing kept): `sys.path` and the shadowing routes, and the default profile's
  packages under a read-only HOME. reportlab 5.0.1's wheel from `downloads/` (hash in
  `SHA256SUMS`), unzipped into a scratch folder and read; matplotlib 3.11.2's source in the main
  tree's `build/matplotlib-3.11.2/` read. No fast tier, no full judge.
- **Time box:** 45 minutes (build-class and runner code); kept.

Precedent form: `111-the-filesystem-along-the-wasi-seams-spec-2026-10-21.md`.

## Verified, not trusted

1. **reportlab's hooks look on the import path first** (READ, the pinned wheel).
   `reportlab/__init__.py:39-45`: `import reportlab_mods`; only on `ImportError` does it
   `_fake_import(os.path.expanduser('~/.reportlab_mods'))`. `reportlab/rl_config.py:26-41`:
   `rl_exec('from reportlab_settings import *')`; only on `ImportError` does it read and
   `rl_exec` `~/.reportlab_settings`. The two earlier lookups, `reportlab.local_rl_mods` (35) and
   `reportlab.local_rl_settings` (21), are inside the `reportlab` package; the wheel ships
   neither (`unzip -l | grep -c local_rl` → 0), and the package lives in the zip, which no guest
   can write. A scan of the whole wheel for `expanduser` and `'~'` finds those two and the font
   search paths (`rl_config.py:110-112`), data. `RL_*` variables set options (`_setOpt`,
   `rl_config.py:63-67`). The specification's reading holds.
2. **The zip's top level wins over anything a guest can plant** (EXECUTED, my probe). On the
   default binary: `sys.path` is `['/usr/local/lib/python315.zip']` for `-c`, for a script run
   from the root (`run(["/main.py"], root=…)`: no script folder is added) and in a session;
   `sys.flags.safe_path` is `True`, `sys.flags.ignore_environment` is 1, so an `env=`
   `PYTHONPATH=/pp` is in `os.environ` but not on `sys.path`; `site` does not run, so no `.pth`
   (README *Safety*). `import_path` is appended after the zip (`_call.py:319-336`;
   EXECUTED: `['…python315.zip', '/ip']`) and must be a read-only grant (`run` refused my
   writable-root entry with `ValueError`). A planted `/reportlab_mods.py` beside a script in a
   reused root did not run on main (the root is not on `sys.path`). An embedder's
   `reportlab_mods` on `import_path` **does** run today (EXECUTED: `IMPORT_PATH reportlab_mods
   RAN`), so Decision 2's shadowing is real and correctly described.
3. **The routes** (EXECUTED on main unless marked). The four H2 rows reproduce as the checks
   show. The `chdir` route is real by construction: with no HOME, `expanduser('~/x')` is `'~/x'`
   (EXECUTED, the HOME probe's `"expands": false`), relative to whatever folder the program
   entered. `Path.home()` raises `RuntimeError` without a HOME (EXECUTED). An `env=`
   `{"HOME": ""}` expands `~/.x` to `'/.x'`, the root (EXECUTED): an embedder's choice, in the
   `env=` class Decision 2 already closes for reportlab (note N1).
4. **A read-only preopen answers `PermissionError`** (EXECUTED, a stand-in: `env={"HOME":
   "/usr/local/lib"}`, the read-only stdlib folder): scikit-learn's fetch raised
   `PermissionError [Errno 63] … '/usr/local/lib/scikit_learn_data'`. So the HOME check's
   `"write": "PermissionError"` is the answer the placeholder will give (INFERRED from the
   stand-in; the build sees the real one).
5. **The placeholder cannot be written through another preopen** (READ). A `_Private` folder
   lies in the temporary folder, and no grant may be at or above it (`_places.py:516-521`), so a
   read-only preopen of a folder there is the only route to it. Its name is random per call, and
   a session keeps one empty, read-only folder for its life: nothing a turn or a call does can
   leave content in it for a later call.
6. **`test_nothing_is_writable_by_default` keeps every refusal** (INFERRED from wasi-libc's
   component-wise longest-prefix match): `/tmp/.home-<hex>` is not a prefix of `/tmp/x`, so
   `/tmp/x` still finds no preopen; `/x` and `x` likewise. `tempfile` never reads `HOME`.
7. **Not structural by the letter** (READ, `tests/checks/test_rules.py:1043-1055`):
   `_call.py:_instance` is at its recorded 159, `_sessions.py:_open_session` at 150; the plan adds
   no module-level mutable, lock, private wasmtime-py name, platform branch or seam. Whether
   `_instance` can stay at 159 is M1 below.

## Acceptance criteria against evidence

1. The new checks pass — not yet testable (no fix); the 14 rows fail and pass on main for the
   reasons Decision 4 gives (EXECUTED, above). Each row fails for the right reason: the plant
   rows assert the plant reached the root first, so they cannot pass on a call that wrote
   nothing.
2. The guest always has a HOME — testable, held by the HOME check's five rows. Met in plan.
3. Nothing becomes writable — testable; see L4 for making the check cover the new folder.
4. The placeholder leaves nothing — the first half is held by the litter checks; the second
   half ("a read-only grant at `/tmp` leaves that grant's folder unchanged") has no check (L3).
5. reportlab reads no start-up file; two members; no reportlab byte changes — testable (the
   stand-in check; spec 020's sameness; a member-list diff of the two zips, which the landing
   notes should carry). A stand-in module is a recipe by §4.1's own list. Met in plan.
6. The judge changes are those listed — the list is honest and each carries its reason; the one
   retirement drops an assertion worth keeping (L2).
7. Not structural — depends on M1.
8. README and CHANGELOG — mostly accurate; one wrong path (L1).
9. Growth named — testable at build; the snapshot grows too (L5).
10. Code speaks for itself — met in the new checks (READ: no specification, review, finding or
    `context/` name in their comments or docstrings).
11. The run — at build.

## Findings, most severe first

### M1. Where the placeholder sits, and who makes and removes its folder, is not pinned, and Decision 6's "neither grows" is not evidenced for `_instance`. Medium

(`context/specifications/114-home-is-never-the-root.md:114-117`, `:251-261`;
`src/wasi_python/_call.py:262-282`, `:403-433`, `:467-485`; `_sessions.py:991-1050`)

- **What the plan says.** The placeholder is "an empty folder in the call's private folder
  (`_Private`), beside the mounts' placeholder, made before the preopens" and "one more
  read-only `_Preopen` in the call's list". One helper in `_call.py` chooses HOME and does the
  fresh folder's `mkdir`; "neither `_instance` nor `_open_session` grows, and both should shrink"
  because "today both bodies carry their own copy of the fresh HOME's `mkdir` block".
- **Why that does not yet add up.**
  - The two bodies with the `mkdir` block are `_call_deferred` (`_call.py:262-277`) and
    `_open_session` (`_sessions.py:1000-1013`). `_instance` has none, so moving the block out
    shrinks `_call_deferred`, not `_instance`, which is at its recorded 159.
  - "The call's private folder beside the mounts' placeholder" is `scratch`, made **inside**
    `_instance` (`_call.py:409`), after `preopens` is final. Making the placeholder there means
    new lines in `_instance`.
  - Its place in the list is load-bearing in three ways:
    - the mounts' descriptors are numbered `first = 3 + len(preopens)` (`_call.py:432`,
      `_sessions.py:1048`). A placeholder put in `every` between `preopens` and `mounted`
      without counting it shifts every mount by one: the table would serve the placeholder's
      descriptor as the first mount and forward the last mount's to wasmtime's empty folder;
    - the mount table refuses paths a nested preopen owns and keeps `rmdir` off a folder above
      one only for the guests in `others = [p.guest for p in preopens]` (`_call.py:429`,
      `_fs_table.py:99-105`, `_fs_paths.py:88-90`, `:395-397`). A placeholder outside
      `preopens` is not "forwarded as a grant nested in a mount is", as Decision 6 says it is;
    - the identity check (`_places.py:387-411`) covers `every`, by position.
  - The release order differs by path. In a call, the walked handles of `preopens` are closed
    by the outermost release (`_call.py:166-173`), after `_instance`'s release has removed
    `scratch` (`:482-483`). A placeholder whose handle is in `preopens` but whose folder is in
    `scratch` is removed while still held on any ending before the identity check closes the
    walks (`_places.py:409-411`). On Windows, which holds every walked folder, that removal
    fails and is litter with a `RuntimeWarning`; the release workflow is the only place
    Windows runs. In a session the order is right (`_sessions.py:604-607`: walks, then
    `scratch`), if the handle joins `state.walked`.
- **Fix (text for Decision 6).** Pin one design. A design that meets every constraint above:
  - The helper runs where the fresh HOME's block runs today, in `_call_deferred` and in
    `_open_session` after `_preopens`. It returns the guest's HOME and either the fresh folder or
    the placeholder.
  - The placeholder is an empty folder in a `_Private` of its own. It is made by the helper and
    walked. It is **appended to `preopens`**, so `others`, `first` and the identity check count
    it, and it sorts before the mounts.
  - Use the prefix `wasi-python-`. `_private_dirs._LOCK_NAME` (`_private_dirs.py:23`) knows only
    `wasi-python-`, `-root-` and `-zip-`, so the sweep will find a stale one.
  - Release order: in a call, its walk is closed by the outermost release with the other
    preopens. The folder is removed after that, in the same step as the private root. In a
    session, the walk joins `state.walked` and the `_Private` is removed after the walks.
  - `_instance` then changes by one line at most (`fresh` loses its `None` case), and
    `_open_session` shrinks.

  Whatever design the builder picks, the specification should name it before build. The build
  should show `_instance` ≤ 159 and `_open_session` ≤ 150 with the rules check's output.
- **Evidence that closes it:**
  - the revised Decision 6;
  - at build, the long-function check green;
  - the HOME check's `mount at /tmp` and `mount at /` rows green, with a mount row that also reads
    a provider file, so a shifted mount number fails. `test_a_mount_at_the_root` already does
    this for `/`; for `/tmp`, add `"listed": sorted(os.listdir('/tmp'))` or a read of a
    provider file to the mount row;
  - a Windows leg of the release workflow green on the litter checks.

### L1. matplotlib's HOME folder on this target is `~/.matplotlib`, not `~/.config/matplotlib`; and a read-only HOME adds a stderr warning. Low

(`context/specifications/114-home-is-never-the-root.md:95`, `:137`, `:185-186`, `:311-312`, and
the CHANGELOG and README text drafted from them)

- READ `build/matplotlib-3.11.2/lib/matplotlib/__init__.py:528-563`: the XDG path is used only
  when `sys.platform` starts with `linux` or `freebsd`. The guest's is `wasi`, so the folder is
  `Path.home() / ".matplotlib"`. That is what README:387 already says.
- EXECUTED (stand-in read-only HOME, no writable `/tmp`, no `MPLCONFIGDIR`): matplotlib's
  `OSError` changes from "…an issue with resolving the home directory…" to "…an issue with the
  default path (`<HOME>/.matplotlib`)…". When the program goes on (seaborn's import), matplotlib
  also logs `mkdir -p failed for path <HOME>/.matplotlib: [Errno 63] Operation not permitted` to
  stderr.
- **Fix:**
  - Write `~/.matplotlib/matplotlibrc` (and `stylelib/`) in the survey, in Decision 1's list, in
    Decision 3 and in the README's `env=` item.
  - Add one sentence to README:394-397 ("No writable `/tmp`, no matplotlib"): with the read-only
    HOME, matplotlib also logs one `mkdir -p failed` warning naming it.
  - Have the build's grep cover checks that compare a matplotlib or seaborn call's stderr where
    `/tmp` is not writable and `MPLCONFIGDIR` is unset.

### L2. Retiring `test_a_mount_at_tmp_means_no_home` drops a claim that still holds. Low

(`tests/checks/test_v1_4_embedding.py:2779-2795`;
`context/specifications/114-home-is-never-the-root.md:234-235`, `:365`, `:386`)

- Only the check's first assertion is reversed: `HOME` is `None`. Two other claims still hold
  after the fix, and nothing else holds them:
  - the root's own `tmp` gets nothing when a mount is at `/tmp`
    (`assert not (root / "tmp").exists() or … == []`);
  - the same is true for the private root (`given=True`).
- The new HOME check's `mount at /tmp` row looks only at `root/~`.
- **Fix:** change the check rather than retire it. Rename it
  `test_a_mount_at_tmp_makes_nothing_in_the_roots_tmp`. Its `None` becomes the runner's form,
  and both of its loops and its last assertion stay. In "For the lane" it moves from "retired" to
  "changed". Or move both claims into the new check's mount row, and say so.

### L3. AC4's "the grant's folder unchanged" has no check. Low

(`tests/checks/test_v1_2_hostile_guest.py`, the HOME check, `read-only grant at /tmp` and
`mount at /tmp` rows; specification AC4, `:358-360`)

- **Fix:**
  - In the HOME check, after the probe, assert that the read-only grant's host folder is empty:
    `assert list((base / "read-only-tmp").iterdir()) == []`.
  - For the mount row, assert that the provider holds nothing new. Keep the `MemoryProvider` in a
    name and compare its contents, or its `paths`, before and after.
  - Then AC4 has evidence on both paths that place the HOME inside a grant or a mount.

### L4. The "nothing writable" check should cover the new folder, not only change a word. Low

(`tests/checks/test_v1_2_hostile_guest.py:976-1018`; specification `:228-229`)

- Decision 5 turns `no HOME` into `HOME` and keeps the refusals. The check's own claim is that
  nothing is writable by default. From now on the default profile has one more folder the guest
  can name.
- **Fix:** add `os.path.join(os.environ['HOME'], 'x')` to `NOTHING_WRITABLE`'s write loop, with
  the word `refused` before it. That gives one more `refused <HOME>/x` pair. Assert it by its
  prefix, since the name is random: for example, change the `HOME` token to `HOME-refused`. The
  change is then honest and also guards Decision 1's read-only property on both binaries (this
  check is `@parametrize`d over them; the new HOME check runs only on the default binary).

### L5. Decision 2 does depend on the binary: the snapshot freezes zipimport's index. Low

(specification `:159-160`, `:219-220`; `scripts/steps/80_snapshot.sh:5`)

- READ: "zipimport's offsets [are frozen], so the snapshot runs only beside this exact zip". So
  the snapshot is necessarily rebuilt with the zip (READ, not INFERRED). The two stand-ins are
  found on the snapshot only through that rebuilt index.
- **Fix:**
  - Label the snapshot's rebuild READ, citing `80_snapshot.sh:5`.
  - List the snapshot's bytes as a certain GREW line, not an "if".
  - Parametrize `test_reportlab_start_up_hooks_are_the_zips_empty_modules` over both binaries
    (`snapshot=` True and False). It is one call each, and it shows both readers of the zip find
    the stand-ins.
  - Strike "Neither decision depends on the binary" (`:219`), or limit it to Decision 1.

### N1. Notes, no change asked

- **An empty `env=` HOME.** `env={"HOME": ""}` sends `~` to `/` (EXECUTED). It is the embedder's
  choice and inside the `env=` item Decision 3 writes. The item could say "an `env=` `HOME`
  (empty included)". It is the builder's call.
- **A writable mount at `/` reused across calls** is a reused root in all but name, for
  `./matplotlibrc` and `./.pdbrc` in the working folder. If the README's *Not protected* item
  says only "a reused root", it could add "or a writable mount at `/`".
- **Shadowing an embedder's own `reportlab_mods`** is acceptable. It is documented in the README
  and the CHANGELOG, and reportlab's options stay reachable through `RL_*` and through
  `reportlab.rl_config`. It is a deliberate trade for an import-time code hook that no other
  package in the set has.
- **The builder's self-check list** (`context/reviews/README.md`) is for the build review. At
  drafting it has nothing to check: there is no CI run and no fix. Write it at build.

## Constitution checks

- **§4.1:** Decision 2 is a stand-in module under `recipes/`, which §4.1 lists first among
  recipes. No byte of reportlab changes, and nothing goes under `recipes/patches/`. It holds.
- **§4.2:** no new input. reportlab's wheel is already pinned. It holds.
- **§4.15 (safe by default):**
  - Decision 1 makes nothing writable.
  - The default profile gains one read-only, empty preopen. With L4, the check proves the
    preopen is read-only.
  - It holds.
- **§5.6:** this is the pre-build review that the build recipe, the artifact set and the runner
  require. The build needs its own review and run.
- **AGENTS.md rule 4:**
  - Every judge change in Decision 5 is a documented behaviour reversed. Each has its reason
    and is in the claim list, under `--accept-judge` with a reason.
  - None loosens a refusal.
  - The one retirement is the exception (L2).
- **"Structure is reviewed" (4a), one line.** R6 and R7 are unmoved if M1 is answered as
  proposed: no new state, seam or platform branch, and no long function grows. If `_instance` has
  to grow, the change takes a function on `LONG_FUNCTIONS` further past 80 lines. The rules check
  refuses that, so the design must change. It is not a reason to mark the specification
  **structural**.
- **"Code speaks for itself":** the new checks name no specification, review or finding. It
  holds.
- **§7:** nothing tripped.

## Does the plan close H2?

Yes, with two independent closers. Each one alone covers the no-HOME rows.

| H2 row or route | Decision 1 (the placeholder) | Decision 2 (the stand-ins) |
|---|---|---|
| a read-only grant at `/tmp`, both files | closes (HOME is an empty, read-only folder) | closes |
| a mount at `/tmp`, both files | closes | closes |
| `env={"HOME": "/home"}` in the root, both files | does not (the embedder's HOME) | closes |
| a mount at `/` | closes | closes |
| `os.chdir` into a writable grant | closes (HOME is always absolute) | closes |
| a planted `reportlab_mods.py` on any `sys.path` entry | n/a | the zip is first, and `sys.path` holds only the zip and read-only `import_path` entries (EXECUTED) |
| L3's class (scikit-learn's pickles, seaborn, statsmodels, fonts, pdb's `~/.pdbrc`) where the runner chooses HOME | closes | n/a |

I found no route the plan misses for reportlab:

- `PYTHONPATH` is ignored (`-E`).
- `site` and `.pth` files do not run.
- A script's folder is not added to `sys.path` (`safe_path`).
- `import_path` comes after the zip.
- reportlab's two package-local hooks live inside the zip.

The routes that stay open are data, or an embedder's `env=` choice. They are named in Decision
3, and L1 corrects one path there.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — answered by the author in the specification's Decision 6 ("The design, pinned"): a
   `_Private` of its own (`wasi-python-`), appended to `preopens`, made by `_guest_home` in
   `_call_deferred` and `_open_session`, removed by `_release_home` with its walk closed first;
   the HOME check's mount rows read a provider file. Awaiting the reviewer's confirmation.
2. L1 — written in: `~/.matplotlib`, the `mkdir -p failed` sentence, the build's grep widened.
3. L2 — the check is renamed `test_a_mount_at_tmp_makes_nothing_in_the_roots_tmp`, its claims
   kept but the first; the old id is retired for the rename.
4. L3 — the HOME check asserts the read-only grant's folder empty and the provider unchanged.
5. L4 — `test_nothing_is_writable_by_default` writes `$HOME/x` and asserts `HOME-refused`.
6. L5 — the snapshot's rebuild READ and certain; the stand-in check on both binaries.

## Verdict

**Fit to build once M1 is answered:** Decision 6 must name where the placeholder sits in the
preopen list and who makes and removes its folder, so the mounts' numbering, the nested-preopen
rule, the identity check and the Windows release order hold, and `_instance` does not grow. The
Lows are write-ins the builder may fold into the same revision.

One line: the plan closes H2 twice over and the checks fail on main for the right reasons; pin
the placeholder's place in the preopen list before building.
