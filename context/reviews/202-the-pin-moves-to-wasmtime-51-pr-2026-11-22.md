# Review of 202 — The pin moves to wasmtime 51

- **Date:** 2026-11-22
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01ThzDEVEoH7V2U4kpFD24Yy; not the author
- **Reviewed:** `git diff a85cac7..b7a5e49`, then the round's fix commit `4b56dd5` and the per-system rows of `c599881`, on `claude/zen-meitner-1f2lmx` (pull request #129; code at `af2bc0b`, `b7a5e49` adds `context/` only), with the specification, its pre-build review, the news file and `decisions.md`'s "0.1.6 is a security release"
- **Run:** 45048766529 on `af2bc0b` (READ: the gather, job 137295888630, 1272/2422 pass, 0 fail, three systems, set `c4fb24f6…` reused from run 45040897479's build; the Windows `own-hostile` judge, job 137290016880, 161 passed, gained 8). Run 45040897479's build job 137265038448 (READ: the v51.0.0 aarch64 archive fetched and verified, `ok 80_snapshot: … ad43f4214ce167fe`, `python.wasm` `ca6a8eb07d9754b2`, zip `118609fa6df71ede`). The pull request's four comments.
- **Re-ran:** with `WASI_PYTHON_ARTIFACTS` the 0.1.5 set and wasmtime-py 51.0.0 installed, logs under `build/review-202-pr/`:
  - `test_a_drive_prefixed_name_stays_in_its_folder` (8) and `test_one_large_write_arrives_whole` (2) → 10 passed, exit 0 (EXECUTED, Linux).
  - `tests/unit/test_runner_grants.py`, `test_runner_mounts.py::test_the_runner_answers_namespace_calls_it_can`, `test_runner_calls.py` → 87 passed, 1 failed (`test_the_walk_judges_links`, the root container's, as on `dev`) (EXECUTED).
  - `tests/checks/test_rules.py -n 2` → 151 passed, 4 skipped; `ruff check`, `ruff format --check` → clean; `tests/lint` → 14 passed (EXECUTED).
  - A probe of `path_remove_directory` on a writable grant against a writable mount (`build/review-202-pr/probe_rmdir.py`, the parity's own `_write_sides`), on this branch, on `dev`'s `_fs_paths.py`, and with the fix of Finding 1 (EXECUTED; `probe.log`, `probe-dev.log`, `probe-fix.log`). Finding 1.
- **Box:** 45 minutes (build-class); overrun by about 15 minutes on Finding 1's probe.

Labels: EXECUTED, I ran it or read the run's log; READ, I read the file or page cited; INFERRED, my reasoning.

## Acceptance criteria against evidence

1. Pin, `PIN`, the `ImportError` message say `>=51,<52`; `uv.lock` names 51.0.0; the seam imports; the bundled library is 51.0.0 — met (READ, the diff; EXECUTED, `uv pip list`; the library's version READ from the landing notes).
2. Command line — met but for its `x-wizer` clause. `line.conf`, the three `get` lines and `SHA256SUMS` name v51.0.0, and the three hashes in `SHA256SUMS` are the landing notes' (READ). The build verified its archive and ran step 80 on it (READ, build log). All three binaries equal 0.1.5's `SHA256SUMS` (EXECUTED, against the 0.1.5 set). The new set names 51.0.0 only in MANIFEST's three `pin` lines; `x-wizer` spells no version (READ, `assemble_artifacts.py:1652-1657`, 0.1.5's `MANIFEST:619`). Finding 4.
3. 3a passes on three systems, red on 50.0.1 on Windows — met (READ, run 45048766529; the comments on run 45037617781). The safety assertions come before the errno table, so the final check still fails first on 50 (INFERRED, the code's order).
4. No empty-write check; `SECURITY.md` and the CHANGELOG say carried, not reached, with the reason — met (READ).
5. 3c to 3f pass on three systems — met (READ, the run; `test_runner_grants.py` is in `own-guest-b`, `systems = ["macos", "linux", "windows"]`, so the grant's 27 is asserted on all three). But the slash-named `rmdir` does not follow the grant for every spelling: Finding 1.
6. GC off in both engines and the judge's three mirrored engines; no probe variable lands — met (READ, the diff; `grep environ` on it finds nothing).
7. Branch green on three systems, no growth — met (READ, the gather; the news file claims none, and the snapshot did not move).
8. `ruff`, format, rules — met (EXECUTED).

## Findings, most severe first

1. **High: a slash-dot `rmdir` on a mount removes a folder that the grant refuses** (`src/wasi_python/_fs_paths.py:478,484`). The new branch tests `last`, the text after the last `/`, which is empty for `e/./`. So `e/./` counts as a slash-named `rmdir` and goes to the provider. Failure (EXECUTED, the probe): `rmdir("e/./")` and `rmdir("e/.//")` on an empty `e` answer 28 on the grant and 0 on the mount, and the mount's `e` is gone. `rmdir("d/./")` answers 28 on the grant and 55 on the mount. On `dev`'s `_fs_paths.py` all three answer 28 on both sides. This is new in this pull request, and it breaks the docstring's own promise: "never removes a folder the plain name's rules would keep". Decision 3d says "not `.` or `..`". What to change: test the last non-empty part, `texts[0].rstrip("/").rsplit("/", 1)[-1] in (".", "..")`, in the new condition. Add write-parity rows `rmdir 'e/./'` and `rmdir 'd/./'`, and see them fail on `af2bc0b` first. With that line, all nine spellings probed answer as the grant does, and the grant and mount unit files pass (EXECUTED, `probe-fix.log`: 141 passed, plus the root failure).
2. **Low: the self-check has two empty boxes** (the pull request's description). "Every new check was seen failing" and "The Windows legs … were read" still say "Not yet". The facts now exist (run 45037617781; run 45048766529's Windows legs). Fix text: tick both. Beside the first, name run 45037617781's red Windows `own-hostile` leg and the Linux rows of 3d and 3e. Beside the second, name run 45048766529.
3. **Low: the twin allowance in 3a is wider than its comment** (`tests/checks/test_v1_2_hostile_guest.py`, the last `else` of the table). It accepts any refusal the twin gives, an ENOENT for a missing target included. So for a row whose twin is refused, the spelling table does not bind the errno. Safety is not weakened, and I checked each path (READ):
   - Every Windows colon row outside the link rows must still be an integer, so a refusal.
   - Once a link is made, every call through it must be refused.
   - The canary, `cwd`, `temp` and `tmp_path` assertions come first and have no condition.
   - An escape answers `"ok"` or `["ok", …]`, and no allowance admits either.

   The owner chose this rule. I wrote the limit into Decision 3a's text myself (context only, below). No code change is needed.
4. **Low: the specification still expects the snapshot to change** (Kind line, Decision 2, Intent, criterion 2, For the lane's claim list). wizer 51.0.0 made 0.1.5's bytes, and no `x-wizer` line names a version. Fix text: in the Kind line and Intent, say the set's bytes are unchanged and only MANIFEST's pin and recipe lines move. In Decision 2 and criterion 2, replace "`x-wizer` 51.0.0" with "MANIFEST's `pin` lines name the three v51.0.0 archives". In the claim list, drop "the snapshot's bytes changed by the new wizer".
5. **Low: the landing notes are stale in three places.** The `pread` line still waits for macOS and Windows: the run asserts 27 on both. "The built set's hashes … go here" is answered in the Green bullet. "Not landed yet" needs the review, the fix round and the merge. Fix text: say so, with run 45048766529.
6. **Low: `pyproject.toml:17` still says "The runner is tested on 50 only".** Fix text: "on 51 only". It goes in the round's fix commit.
7. **Low: the claim block's `changed` names four checks whose status does not move.** These are the two pin-text checks and the two rename checks, which are unchanged in code and pass on both sides. It is harmless, since the accept job asks for no claim for them. Fix text: optional. Keep them with the comment, or move them into the comment.

I wrote in two `context/` Lows myself, uncommitted in the working tree, for the author's round commit:
- In Decision 3a, the Windows sentence now names the twin's allowance and its limit (Finding 3).
- The advisory draft's Impact said 0.1.5 read the canary "through the runtime's own folders as well as the granted ones". The run shows a read in each call, not which folder it went through. It now says "In the call given no folders, it read through the runtime's own folders alone."

Writes outside were not run. `SECURITY.md`, the security model and the CHANGELOG say "could write", and the draft's notes say it was inferred (READ). That is honest.

## Constitution checks

- §4.1, §4.2: no patch. The three archives are pinned by URL and SHA-256 and verified before use (READ, the build log). Holds.
- §4.4: the guest's imports and exports do not change, and the binaries' bytes do not change. Holds.
- §4.9: no check measures time. Holds.
- §4.10: the documents keep reads (EXECUTED) apart from writes (INFERRED). With the draft's line written in, holds.
- §4.15: no default loosens. Finding 1 loosens what `rmdir` removes on a mount, a wrong answer, not a limit.
- Structure (4a): one condition in `_namespace` (34 lines), one config line, one string. No mutable, no lock, no private name, no platform branch in `src/`, and no new seam. Not structural holds. 4b: nothing under `.github/` or `release/` changes.
- Judge: no golden output, allowance, `known_gaps.toml` or verdict-bearing file changes. 3a's table was refitted three times, but its safety assertions were never loosened (Finding 3).
- §7: nothing tripped. The one red push was the owner's ("Yes, one red push").

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — **fixed in the round's commit.** `_namespace` takes the last component past any trailing slashes (`texts[0].rstrip("/").rsplit("/", 1)[-1]`, the review's own line). The write parity's path list gains `e/./`, `d/./` and `e/.//`, each run through `mkdir`, `unlink` and `rmdir`. They were seen failing first on `af2bc0b`'s `_namespace` (`rmdir 'e/./'`: grant 28, mount 0, `e` removed; `rmdir 'd/./'` differing), then passing with the fix. The grant and mount unit files show 134 passed, plus the known root-container failure (EXECUTED, the author).
2. Finding 2 — **fixed** in the pull request's description: both boxes ticked, naming run 45037617781 (the Windows leg red on wasmtime 50) and run 45048766529 (the Windows legs read green).
3. Finding 3 — written in by the reviewer; the author confirms it.
4. Finding 4 — **fixed in the specification**: the Kind line, Decision 2, Decision 7, Intent, criterion 2 and the claim list say the three binaries are byte-identical to 0.1.5's, and that the set names 51.0.0 only in `MANIFEST`'s `pin` lines.
5. Finding 5 — **fixed in the landing notes**: the `pread` line says macOS and Windows confirmed 27; the hashes line points at the built-set line; "Not landed yet" names the green run and this review's round.
6. Finding 6 — **fixed in the round's commit**: `pyproject.toml`'s comment says the runner is tested on 51 only.
7. Finding 7 — **taken**: the four `changed` entries are dropped from the claim block, since their status does not move.

Confirmed by the reviewer, second round, 2026-11-22. I read `git show 4b56dd5` line by line.

- **Finding 1, confirmed.** The fix differs from my text in one way. It changes `last` for the whole function, not just the `rmdir` test, so `mkdir` of `e/./` now takes the `stat` path too. The parity's path list runs each new spelling through `mkdir`, `unlink` and `rmdir`, so that is covered. I also probed 21 more spellings on both sides, across the three calls (`new/./`, `new/.//`, `missing/./`, `a.txt/./`, `e/..//`, `d/.//`, `e//./`). All 21 answer as the grant does and leave the same tree (EXECUTED, `build/review-202-pr/probe2.log`). `tests/unit/test_runner_grants.py`, `test_runner_mounts.py` and `test_runner_calls.py` give 162 passed, plus the root-container failure (EXECUTED).
- **Finding 2, confirmed** from the author's account. I did not read the description again, to save the API budget.
- **Findings 3 to 7, confirmed** (READ, the commit's diff of the specification, the news file and `pyproject.toml`). The claim block still holds `new` and `units = 2`, and it claims no growth. That is right for this round, since the new rows are unit rows inside an existing test.
- **Run 45052595788 on `4b56dd5`:** in progress when I signed (READ, one listing). Its three-system result goes in the landing notes before the merge.

Third round, 2026-11-22. I read `git show c599881`. Run 45052595788 on `4b56dd5` was red in one leg, `judge (macos-15, own-guest-b)`. The coordinator's reading: the three new rows `unlink 'e/./'`, `'d/./'` and `'e/.//'` answered 63 on macOS's grant and 31 on the mount, with identical trees (READ, the coordinator's message; I did not read that log myself).

The commit adds the three rows to `LINUX_ROWS` with 31. **This is a faithful per-system record, not a weakening.** It is the same mechanism and answer as the existing `unlink 'e/.'`, `'d/.'` and `'d/..'` rows. The test's code shows what stays checked (READ, `tests/unit/test_runner_grants.py:1467-1475`):
- On every system, the mount must answer Linux's 31.
- On Linux, the grant is still compared, and it must also answer 31.
- Off Linux, only the grant's answer is set aside: it is the host's own.
- The grant's tree after the call is still compared with the mount's on every POSIX system. So a removal on either side would still fail the check.
- The `rmdir` rows that Finding 1 fixed stay under the plain comparison.

Locally, the write parity and the write differences give 2 passed (EXECUTED, Linux). Run 45052595788's other legs were green when the coordinator read it. A run on `c599881` is still to come.

## Verdict

Lands at `c599881`: Finding 1 is fixed and its rows hold, the macOS `unlink` rows are a faithful per-system record, and every Low is fixed or written in; the merge waits on a green run on `c599881` (or this file's head after it) on three systems.

Second round, at `4b56dd5`: "Lands at `4b56dd5`", withdrawn when run 45052595788's macOS `own-guest-b` leg was red on the three new `unlink` rows.

First round, at `af2bc0b`: "Does not land yet: Finding 1, a slash-dot `rmdir` on a mount (`e/./`) removes a folder the grant refuses, new in this pull request."
