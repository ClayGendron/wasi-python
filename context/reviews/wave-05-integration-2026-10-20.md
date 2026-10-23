# Review of wave 05: integration of 090 and 082

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent. I wrote and reviewed neither entry.
- **Reviewed:** `wave/05` at `f70c666`, on main `ebd0449` (086, wasi-sdk 34). First 090 (rebased from `125b063`, on `e00d394`, to `70a8e07`), then 082 (rebased from `b673782`, on `f7511b7`, to `f70c666`).
- **Time box:** 25 minutes. 090 is build-class. 082 changes only the judge.
- **Run:** in a `git archive f70c666` export in my scratchpad, with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. I checked for `build/lane.lock` before each command, and it never existed. I wrote nothing to the main tree. Each item is labelled EXECUTED, READ or INFERRED.
  - The eight unit files 090 changes, plus `tests/unit/test_inline_sessions.py`: **332 passed, 1 failed, 1 skipped**, 334 rows (EXECUTED). The one failure is `test_build_scripts.py::test_the_repository_ignores_litter_itself`. It runs `git check-ignore` against the repo, and an archive export is not a git repo. After a `git init` in the export, it **passes** (EXECUTED). So the failure comes from my setup, not the branch. The skip is `test_pins.py:122`: "zlib-1.3.1.tar.gz is not downloaded".
  - The ratchet line names the judge as changed in 17 files ("tests/conftest.py, tests/harness/artifacts.py, tests/harness/litter.py and 14 more"). That matches `git diff --name-only ebd0449 f70c666 -- tests` exactly: 090's fifteen plus 082's two (EXECUTED).
  - `ruff check src tests` passes, and `ruff format --check src tests` passes (120 files) (EXECUTED). `scripts/make_stdlib_zip.py` has two ruff findings (E501 on line 12, I001 on line 52). Both are already at `ebd0449`, and `scripts/` is outside the rule.

## Acceptance criteria against evidence

### 1. 090's `git range-diff` (EXECUTED)

`git range-diff e00d394..125b063 ebd0449..70a8e07` (saved beside this file as `rd090.txt`):

- Commits 1–3 and 5–7 are `=`. They are patch-identical to the reviewed ones (`125b063` is the build review's tip; `a4ab975` is commit 6).
- Commit 4 (`fa34179` to `a07d8ed`) is `!`. It changes only context lines:
  - In `CHANGELOG.md`, 090's bullet now sits under the existing `## 0.1.0a8 — unreleased` heading, after 094's bullet. It no longer opens a new heading.
  - In `scripts/steps/20_cpython.sh`, the hunk's context is now 086's two-line driver command.
  - No `+` or `-` line of 090's own changed.
- Two new commits:
  - `7bbfb91` copies in the build review and makes its L3 change to `README.md`.
  - `70a8e07` adds 11 lines to the specification ("For the lane", rebase notes).
- `git diff 125b063 70a8e07 -- . ':!context'` holds only main's changes (086 and 094) plus the README's L3 change. No script or judge line of 090 moved.

### 2. 090's `20_cpython.sh` merge with 086 (READ)

The merged step:

1. Unpacks, patches and enters `$CP`.
2. Runs the driver with 086's `--disable-test-modules --with-hash-algorithm=siphash13`, under 086's comment.
3. Tests for `$W/python.wasm`.
4. Then 090's block: a comment, and `find "$CP/Lib" -name __pycache__ -type d -prune | while read -r d; do remove "$d"; done`.
5. Echoes the size and hash.

The two changes touch different lines. 086 changes the driver's arguments. 090 acts only after the build finishes. So neither changes what the other does.

- `remove` comes from `scripts/steps/remove.sh`, which `common.sh` sources.
- `$CP` is `$B/Python-$PYTHON_VERSION` (`common.sh:17`).
- The `find … -prune | while read` form is the one `host_from_source` already uses in `common.sh:34`.
- `diff 125b063:20_cpython.sh 70a8e07:20_cpython.sh` shows only 086's hunk.

The step removes only bytecode from the source tree after the build. It does not change `python.wasm`. A cache file reaches nothing shipped, because steps 60 and 70 marshal with the tools' Python (INFERRED from the comment and 090's build review). The lane's criterion-2 comparison is what proves this.

### 3. 082's `git range-diff` (EXECUTED)

`git range-diff f7511b7..b673782 70a8e07..f70c666` (saved as `rd082.txt`):

- Commits 2–5 are `=`. This includes `d114e17` to `273b0ad`, the commit that adds L1's check.
- Commit 1 (`2889d75` to `a7e4fbb`) is `!` in `CHANGELOG.md` only:
  - its bullet now follows 086's `_tkinter` bullet;
  - one blank line before the spec 065 bullet is gone.
  - `tests/conftest.py` and `tests/unit/test_inline_sessions.py` are unchanged.
- One new commit, `f70c666`, adds 15 lines to the specification (rebase notes). No code changes.

### 4. 082's L1 check, which no reviewer had seen (READ; mutants EXECUTED)

The new check is `test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler`. It works like this:

- It uses the same `_handler_after` stand-in as the `inline_run` check. That helper sets SIGABRT to `SIG_IGN` with `sigaction`, after faulthandler is already on. Then it runs the session and reads the handler back. In a `finally`, it puts back the whole saved `struct sigaction`.
- The session calls `pytester.parseconfigure()`, then `config._ensure_unconfigure()`.
- In the installed pytest 9.1.1, `Pytester.parseconfigure` calls `self.parseconfig(*args)`, then `config._do_configure()`. The fixture patches the instance attribute, so the wrapped `parseconfig` is the one called (READ).
- Without the flag, the inner session's faulthandler plugin runs `pytest_configure` and `pytest_unconfigure`. The unconfigure calls `faulthandler.disable()`, which puts back the pre-faulthandler handler, so `SIG_IGN` is lost. It then calls `enable()` again, which installs faulthandler's handler.
- `_ensure_unconfigure` is guarded by `_configured`, so pytester's own finalizer calling it a second time does nothing.

Mutants, each run on the three checks in `test_inline_sessions.py`, darwin-arm64, with `PYTHONDONTWRITEBYTECODE=1` (EXECUTED):

| Mutant in `tests/conftest.py` | Result |
|---|---|
| `parseconfig(*NO_FAULTHANDLER, *args)` → `parseconfig(*args)` | **1 failed, 2 passed**. Only the parseconfigure check fails: "the configured session replaced the handler: 0x10662e7d8" |
| `inline_run(*NO_FAULTHANDLER, *args, **kwargs)` → `inline_run(*args, **kwargs)` | **1 failed, 2 passed**. Only the inline-run check fails: "the inline session replaced the handler: 0x1041527d8". The end-to-end check passes on darwin by design, because only Linux has the guard |
| Restored | 3 passed |

Each half of the fixture is held by its own check, and neither check depends on the other. That is spec 082's L1 claim ("fails with the flag dropped from the parseconfig wrapper alone"). It holds.

### 5. The claim lists (READ; unit counts EXECUTED)

**090.** Its claims:

- No goal check is new, retired or changed in verdict.
- The unit suite gains six rows: `test_build_scripts.py` 1, `test_release_version.py` 2, `test_artifact_rules.py` 2, `test_pins.py` 1.
- The judge hash changes in fifteen files.
- No growth, no `--accept-fewer-passes`, no `--retire`.

Evidence:

- Collected rows in the eight files, `ebd0449` against `f70c666`:
  - `test_artifact_rules.py`: 28 → 30
  - `test_build_scripts.py`: 28 → 29
  - `test_pins.py`: 9 → 10
  - `test_release_version.py`: 20 → 22
  - `test_patches.py`, `test_regrtest.py`, `test_scoreboard.py`, `test_upstream.py`: unchanged (39, 67, 50, 84)
  - So the six new rows are exactly as claimed (EXECUTED).
- The fifteen judge files are exactly the 17 changed files under `tests/`, less 082's two (EXECUTED).
- **The MANIFEST `recipe` lines.** `assemble_artifacts.py:472–482` hashes every `git ls-files recipes scripts` file except `bench_*`. `git diff --name-only ebd0449 f70c666` over `scripts recipes downloads src .github` lists exactly:
  - `scripts/assemble_artifacts.py`
  - `scripts/litter.py`
  - `scripts/make_stdlib_zip.py`
  - `scripts/steps/20_cpython.sh`

  So exactly four recipe lines can move, as criterion 2 says (EXECUTED).
- `release/version.py` also changes. It is not a recipe line. No file under `recipes/`, `downloads/`, `src/` or `.github/` changes.

**082.** Its claims:

- Judge only. The diff is `tests/conftest.py`, the new `tests/unit/test_inline_sessions.py`, `CHANGELOG.md` and its specification and review.
- Three unit checks.
- Lost 0, grew 0, gained 0.

Evidence: `git diff --stat 70a8e07 f70c666` shows exactly those five paths, with no `src/`, `scripts/` or `recipes/` change. The new file has three test functions and no parametrize, and all three pass (EXECUTED). 082 adds nothing to MANIFEST.

**The wave's unit suite should grow by 9 = 6 + 3.** The two lists name no row and no file in common. Neither list grows a row, moves a pass or retires a node.

### 6. Reviews on record (READ)

- `context/reviews/090-the-build-ignores-host-litter-spec-2026-10-20.md`: "Ready once F1, F2 and F3". The confirmation in the same file says "Ready to build".
- `context/reviews/090-the-build-ignores-host-litter-build-2026-10-20.md`: **Lands.**
- `context/reviews/082-inline-sessions-keep-the-handlers-build-2026-10-20.md`, on the branch: **Lands.** Its L1 says "the `parseconfig` half has no check". The author fixed it at `d114e17` (`273b0ad` after the rebase). Item 4 above is the review of that fix.

## Findings, most severe first

There are no Critical, High or Medium findings.

### N1 (note, rule 6b): L1's check has run only on darwin

082's release run, 39364504472, predates the third check: its own-rest shard shows `test_inline_sessions.py ..`, two rows. The new check uses the same `_handler_after` helper and the same first-word read of `struct sigaction`, and the first check already passes with that read on Linux. So I expect it to pass on Linux too (INFERRED). The wave's dry run before a tag covers this. No further round is needed.

### N2 (note, lane): criterion 2 is pending

090 was not rebuilt after the rebase. The verdict below holds only if the lane's comparison shows all of these:

- `python.wasm`, the snapshot, the stdlib zip and every `LICENSES/*` file `cmp`-identical to 086's set (SHA256SUMS `4e0dc0cf`);
- `MANIFEST` different in exactly the four `recipe` lines in item 5;
- `SHA256SUMS` different only in `MANIFEST`'s line.

Any other difference is a reason to eject 090. 082 would then land alone on `ebd0449`; it does not depend on 090.

### N3 (note): the CHANGELOG's blank lines

Both rebases changed blank lines in the 0.1.0a8 list. The list was already loose on main, so this changes nothing when rendered. Nothing to do.

## Constitution checks

- **§4.1 patches and §4.2 pins:** no file under `recipes/` or `downloads/` changed. 090's script changes are declared, and each is a MANIFEST recipe line.
- **Rule 4, the judge is not weakened:**
  - 090's judge changes forgive litter names only. Its build review checked that nothing a check counted is hidden.
  - 082 adds checks and changes no verdict.
  - No golden output, `known_gaps.toml`, upstream allowance or `context/progress/` file changed.
- **Operations, not wall-clock:** no new timing assertion.
- **Rule 8, nothing unreviewed:** both build reviews are on the branch. 082's post-review check is reviewed here, in item 4.

## Accept log: pending

The lane sends its comparison and its accept summary. I check them for:

- criterion 2 as in N2;
- lost 0, gained 0, grew 0, and no node retired;
- `judge changed` in exactly the 17 files of the run above;
- the unit suite up by 9.

## Verdict

**Lands as merged at `f70c666`, once the lane's comparison meets 090's criterion 2 (N2).**

- 090's reviewed commits are patch-identical, apart from the context lines of one commit.
- `20_cpython.sh` combines 086's siphash flag and 090's bytecode removal, on separate lines.
- 082's reviewed commits are patch-identical too, apart from CHANGELOG placement.
- Its unreviewed L1 check fails when the parseconfig flag alone is dropped, and passes when it is restored.
- Both claim lists match the diff, and they share no file.

One line: both entries merged cleanly with their meaning unchanged, and 082's new check catches its mutant; they land at `f70c666` if the rebuilt set matches 086's but for MANIFEST's four recipe lines.
