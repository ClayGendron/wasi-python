# Review of 018 — Finder litter never breaks a build (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read `AGENTS.md`, the constitution (§4, §4.9, §4.10, §5.2, §7), `context/reviews/README.md` and the 017 pre-build review (for the format). I read the specification, its memo `2026-10-17-finder-litter-breaks-a-desktop-build.md`, every file under `scripts/steps/`, `scripts/build.sh`, `scripts/line.sh`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`, `release/version.py` (`write_assets`), `.github/workflows/release.yml`, spec 016's Decision 1 (the wheel rules), and in the judge `tests/harness/paths.py`, `tests/harness/scan.py`, `tests/harness/artifacts.py` and `tests/unit/test_scan.py`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/018-finder-litter-never-breaks-a-build.md` as committed in `1f2170d` (unchanged at `7dc59fd`). The scripts and the judge files it changes are unchanged from `9419f36` to `7dc59fd` (`git diff --stat`, EXECUTED).
- **Ran (EXECUTED, darwin-arm64, macOS 25.5, APFS; and `debian:trixie-slim` in Docker with no network, dash and GNU coreutils 9.7 `rm`, on a bind mount).**
  - The repo was not edited, except to write this file. I did not run `scripts/build.sh`. Under `build/` I only listed files and read two (`MANIFEST`, `LICENSES/pandas.txt`).
  - I did not run `uv run pytest`. Nothing is built yet.
  - Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev018/`:
    - `remove.sh`: the Design's `remove`, copied exactly, with a `die` like `common.sh`'s;
    - `semantics.sh`: `remove` under `set -eu` with `rm` replaced by a counting shell function (never fails / fails once / always fails), run by `/bin/sh` (bash 3.2 in POSIX mode), `/bin/dash`, `/bin/bash` and `/bin/zsh`, and by dash in Debian (`linux/linux.sh`);
    - `mktree.sh`, `writer.py`, `writer2.py`, `race.sh`, `race2.sh`: a tree of 341 folders and 5,115 files, removed while a background writer adds `.DS_Store` files; the writer only writes into folders that exist, as Finder does;
    - `findt/t.sh`: `common.sh`'s `find … -exec rm -rf {} +` under `set -eu` when one `rm` fails;
    - `import_probe.py`: imports `make_stdlib_zip` and runs today's `walk` on two littered trees;
    - `licences_probe.py`: `assemble_artifacts`' pandas `LICENSES` listing, with and without a `.DS_Store` in that folder.

## What holds

- **`remove` keeps the step alive and dies cleanly.** EXECUTED (`semantics.sh`), the same in all five shells:
  - `rm` never fails: exit 0, 2 calls for 2 paths, folder gone.
  - `rm` fails its first call: exit 0, 3 calls, folder gone.
  - `rm` always fails: exit 1, one line `ERROR: cannot remove …/a`.
  - A dangling link is removed and passes `[ ! -L ]`.
  - READ: a failure inside an `&&` list other than its last command does not trip `set -e`. The `for` loop's non-zero status that follows is exempt too (POSIX `set -e` rule). The `[ ! -e ] && [ ! -L ] || die` list runs `die` only when the path is still there.
- **The retry beats an occasional writer.** EXECUTED. With a writer that writes one `.DS_Store` and pauses (`writer2.py`, 1 ms and 0.2 ms pauses), plain `rm -rf` failed 20 of 20 times with "Directory not empty"; `remove` succeeded 20 of 20. In Debian (dash, GNU `rm`), plain `rm -rf` failed 10 of 10 and `remove` succeeded 10 of 10, for both a shell writer in a tight loop and a slower one.
- **The shell `rm -rf` sites are the ones listed.** READ (`grep -rn '\brm\b' scripts`): steps 10 (lines 16, 30, 35), 20, 30, 35 (a two-line command), 40, 50, 60 (line 14), 80, and `build.sh:37`. Steps 70 and 90 have none. The other `rm` calls remove single files (`60_link.sh:75`, `common.sh:42`, `wasi-cc:30`); a file removal cannot fail with "Directory not empty".
- **`build.sh` does not source `common.sh`.** READ: it sets its own `HERE` and runs each step as `sh "$script"`.
- **Decision 2 covers every input tree.** READ: `walk` serves both `--lib` and every `--tree`, and it tests `SKIP_NAMES` on file names at every depth. `wheel_members` does not test `SKIP_NAMES`, but a wheel is a pinned zip and cannot gain litter. A `--file` is named explicitly.
- **Skipping the three names drops no real file.** EXECUTED: no member of the CPython, numpy or pandas tarballs, nor of any pinned wheel, is named `.DS_Store`, `Thumbs.db` or `desktop.ini` (`tar -tf` and `unzip -l` over `downloads/`). So the zip loses nothing today.
- **The walk check can fail first.** EXECUTED (`import_probe.py`): today's `walk` yields `.DS_Store`, `pkg/.DS_Store`, `pkg/Thumbs.db` and `pkg/desktop.ini` from each tree. `make_stdlib_zip` imports in the project venv (CPython 3.14.2) with `scripts/` on `sys.path`.
- **Litter is live in this tree now.** EXECUTED (read-only `find build -name .DS_Store`): 32 folders hold one, including `build/pandas-install/`, `build/numpy-2.5.2/`, `build/pandas-3.0.6/` and many folders of the wasi-sysroot. With one input tree littered, step 70 would pack `.DS_Store` into the zip today (READ, `add`), as the spec says.
- **The binaries and the zip stay the same.** INFERRED from READ: with no litter, Decision 2 changes no member list, and Decisions 1 and 3 delete nothing. `python.wasm`, the snapshot and the zip do not depend on the four scripts' own bytes. (But see finding 2 for `MANIFEST`.)

## Acceptance criteria against evidence

1. The checks exist and were seen failing — not yet built. The walk check can fail first (EXECUTED above). The `remove` check needs the redesign in finding 6.
2. `uv run pytest` green with `--accept-judge` — not yet built.
3. Steps 70 to 90 give the reviewed set byte for byte — cannot be met as written. `MANIFEST` and `SHA256SUMS` must change (finding 2).
4. A release dry run passes — not yet built.

## Findings, most severe first

1. **High. A `.DS_Store` in pandas' `LICENSES/` folder is packed into an artifact.** (`scripts/assemble_artifacts.py:143-146`)
   - The defect. `assemble_artifacts.py` lists `build/pandas-3.0.6/LICENSES/` with `iterdir()` and joins every file into `LICENSES/pandas.txt`. Decision 4 says no step reads a source tree's litter. This step does.
   - Failure. EXECUTED (`licences_probe.py`): with the tarball's 13 names, `pandas.txt` hashes to `e87c6abce0e57f22…`. Add a `.DS_Store` and it hashes to `136731e7db602b4e…`, with a new first section `==== pandas LICENSES/.DS_Store ====` holding Finder's binary bytes.
   - Why it matters. The build succeeds. `SHA256SUMS` lists the changed file, so the judge's sums rule passes. A desktop build silently makes a different artifact set. Only CI's same-bytes gate would see it, and CI has no Finder. A person who opens pandas' licences in Finder is a likely way to make this happen.
   - Fix. Skip `OS_LITTER` names in that listing, or list the folder's names from the pinned tarball. Add a check: a temporary `LICENSES/` with a `.DS_Store` gives the same notice as without. Correct Decision 4: say which steps list a source-tree folder (this one, and `make_stdlib_zip`'s `walk` over `Lib/`) and how each is covered. Add a `.DS_Store` in `build/pandas-3.0.6/LICENSES/` to criterion 3's littered run.

2. **High. Decision 5 and criterion 3 are false: `MANIFEST` and `SHA256SUMS` will change.** (`scripts/assemble_artifacts.py:168-179`)
   - The defect. `MANIFEST` has a `recipe <sha256> <path>` line for every tracked file under `recipes/` and `scripts/`. READ, and EXECUTED in `build/artifacts/MANIFEST`: it has 35 recipe lines, including `scripts/steps/common.sh`, `scripts/build.sh`, `scripts/make_stdlib_zip.py` and `scripts/assemble_artifacts.py`.
   - Failure. This change edits those four files (and every step). Their hashes change, so `MANIFEST` changes, so `SHA256SUMS` changes. Criterion 3's `cmp` of `MANIFEST` and `SHA256SUMS` against the reviewed set must fail.
   - Fix. Decision 5 says: `python.wasm`, the snapshot, the zip and `LICENSES/*` stay byte for byte; `MANIFEST` differs only in the recipe lines of the files this change touches; `SHA256SUMS` differs only in `MANIFEST`'s line. Criterion 3 checks exactly that, with a `diff` whose expected output is named. The littered run must then equal the clean run with this change, byte for byte, `MANIFEST` and `SHA256SUMS` included.

3. **Medium. Keeping `common.sh`'s cache clean-up rests on a wrong reason.** (`scripts/steps/common.sh:26-28`)
   - The defect. Decision 1 says `find … -exec rm -rf {} +` stays because "`find` goes on past an entry it cannot remove". `find` does go on. But with `+`, `find` then exits non-zero when any `rm` failed. Steps 60 and 70 call `host_from_source` under `set -eu`.
   - Failure. EXECUTED (`findt/t.sh`): one `rm` in the batch fails, and the step exits 1 under both `/bin/sh` and dash. It is the same "Directory not empty" failure, through another door.
   - Fix. Pick one and write it down. Either route it through `remove` (`find … -prune -print` and `remove` each path; no path holds a newline under `build/tools/python/lib`). Or keep it and give the true reason: the caches exist only after an outside run of the host Python, and nobody browses them. The first is one line and leaves no exception for the scan rule to carve out.

4. **Medium. The most likely litter of all is left unstated: Finder in `build/artifacts/` after the build.**
   - The defect. The Intent is a person with a Finder window on `build/`. After a build that person opens `build/artifacts/`. Finder writes `.DS_Store` there. Decision 3 cleans only before the listing.
   - Failure. READ: the judge's `test_sha256sums_match_the_files` (`sums_errors`) then reports `.DS_Store is not listed in SHA256SUMS`, and the scoreboard goes red. A wheel made locally with `cp -R build/artifacts` would carry it and fail spec 016's rule 3.
   - Fix. Decide it in the spec (§5.2). My suggestion: keep the judge strict (the set must be exact, and the wheel copies the folder), and say so in Decision 3, with the one-line remedy `find build/artifacts -name .DS_Store -delete`. If the owner prefers the other way, the judge's sums rule and wheel rule skip `OS_LITTER`, and the wheel step must not copy it. Either way, the spec names the choice and why.

5. **Medium. Decision 3 names the wrong downstream catch, and leaves where its set comes from undecided.** (`release/version.py:155-182`)
   - The defect. Decision 3 says `write_assets` "would see an unlisted file". READ: it does not check. It packs every file under the folder into the release tarball.
   - What really catches it. READ: the build job runs the judge (`uv run pytest`) before "Release assets", and `sums_errors` fails on an unlisted file. Spec 016's rule 3 in `same-bytes` fails too, since the wheel copies the folder. So the conclusion holds; the citation is wrong.
   - Undecided. The Design gives `make_stdlib_zip.py` its own `OS_LITTER`. It does not say where `assemble_artifacts.py` gets its set: a third copy, or an import of `make_stdlib_zip` (which reads `line.conf` at import). The equality check covers only one script's copy.
   - Fix. Cite the judge's sums rule and rule 3, not `write_assets`. Optionally make `write_assets` refuse a file the set's `SHA256SUMS` does not list (cheap, and it fails closed where the bytes leave the machine). Name where `assemble_artifacts.py`'s set comes from; the equality check covers every copy.

6. **Medium. The `remove` check, as designed, is timing-dependent and hard to wire.**
   - The defects.
     - "A folder that a background writer refills" plus a fake `rm` mixes two mechanisms. With a real writer, whether the second (real) `rm` wins is a race. §4.9 wants a count, not an interleaving.
     - The check must source `common.sh` to reach `remove`. `common.sh` finds the repo from `$0` (`$(dirname "$0")/../..`), so the check must pass a `$0` inside `scripts/steps/`. It sources `line.sh`, which exits on a host outside the three build hosts. And it prepends `build/tools/pylib/bin` and the wasmtime folder to `PATH`, so a fake `rm` on `PATH` must come after the source. (EXECUTED: `build/tools/pylib/bin` holds no `rm` today, so the order would work, but only by luck.)
     - The check does not count calls. A `remove` that retried forever would pass the "fails once" case and hang the "always fails" case.
   - Fix (simpler, and closes the copy in `build.sh` too).
     - Put `remove` in its own file, `scripts/steps/remove.sh`, which prints its own `ERROR: cannot remove …` and exits 1. `common.sh` and `build.sh` both source it. No copy, no drift.
     - The check runs `sh -c '. remove.sh; rm() { …count…; }; remove …'`. A shell function named `rm` takes precedence over `PATH`. EXECUTED: that works in `/bin/sh`, dash, bash and zsh.
     - Assert counts: fail once → exit 0, exactly 2 `rm` calls, path gone; always fail → exit 1, exactly 3 calls, stderr `cannot remove`. No writer, no `PATH`, no `line.sh`.
     - The check needs a POSIX `sh`; on a host without one it is blocked, not passed.
     - The scan rule then exempts `remove.sh` by name, not by parsing function bodies.

7. **Low. Two Python removals are not mentioned.** (`scripts/assemble_artifacts.py:126`, `:195`)
   - The defect. `shutil.rmtree(new, ignore_errors=True)` and `shutil.rmtree(final, ignore_errors=True)` hide a "Directory not empty" and carry on.
   - Failure. INFERRED from READ: when step 90 runs on its own (`sh scripts/steps/90_artifacts.sh`, which `pinned()`'s comment allows), a `.DS_Store` written during the first rmtree can leave `artifacts.new/LICENSES/`, and `(new / "LICENSES").mkdir(parents=True)` raises `FileExistsError`. During the second, a non-empty `build/artifacts/` makes `new.rename(final)` raise "Directory not empty". Both fail closed with a traceback. Under `build.sh`, its `remove` runs first and both are no-ops.
   - Fix. Name both in the spec. Either say `build.sh`'s `remove` covers them and why, or give them the same three tries without `ignore_errors`.

8. **Low. "Only a retry closes the window" overstates it.**
   - The defect. A retry narrows the window; it does not close it. The top folder exists until the last `rmdir`, so a writer can refill it on every pass.
   - EXECUTED (`race.sh`, macOS): against a writer that loops over every folder without pausing, plain `rm -rf` failed 20 of 20 and `remove` failed 20 of 20. Moving the folder aside first (`mv` into a fresh folder under the same parent, then a best-effort `rm -rf`) freed the path 20 of 20. In Debian the same tight shell writer lost to `remove` 10 of 10, so the result depends on the writer's speed.
   - Fix. Finder is an occasional writer, and against one the retry won every time. So keeping the retry is fine. Say the residual in one sentence: a writer faster than one `rm` pass still fails the step, with one line. Drop "only a retry closes the window". (Moving aside is the stronger design if the owner wants it; its cost is a leftover folder when the writer wins the clean-up.)

9. **Low. `remove` throws away the reason.** (Design, `rm -rf "$p" 2>/dev/null`)
   - Failure. INFERRED: a permission error and a race both end as `cannot remove X`. The log no longer says which.
   - Fix. Silence only the first two tries, or keep the last `rm`'s stderr for the one line.

10. **Low. The scan rule's pattern, scope and file are undecided.** (§5.2)
    - The defect. The rule names `rm -rf` in `scripts/steps/*.sh` and `scripts/build.sh` only. It does not say whether `rm -fr`, `rm -Rf` or `rm -r -f` count. The check's home is "`test_scan.py` or a new `test_build_scripts.py`", which is a choice left open.
    - Fix. Match an `rm` with any recursive flag, e.g. `\brm\s+(?:-\w+\s+)*-\w*[rR]`. Scan every shell file under `scripts/` (`scan.is_shell`), as `bare_python_hits` does. Name one file for the checks.

11. **Low. Criterion 3 never runs the changed steps 10 to 60 locally, and a clone has no `build/`.**
    - The defect. Nine of the eleven changed `rm` lines are in steps 10 to 60. Steps 70 to 90 need those steps' outputs, which a fresh clone lacks.
    - Fix. Criterion 3 is one full `scripts/build.sh` in a clean clone (as spec 012's landings did), then the littered re-run of 70 to 90. Criterion 4's dry run still covers CI.

## Constitution checks

- §4.1 zero patches: holds. Nothing in a source tree is changed; Decision 4 leaves litter there. The memo's manual deletion of `.DS_Store` files removed no tarball file.
- §4.2 pins: holds; no new input.
- §4.6 the artifact set is the product: at risk until finding 1 is fixed (litter enters `LICENSES/pandas.txt`). Finding 2 changes what "the same set" means.
- §4.9 tests count: the `remove` check as designed depends on a background writer's timing (finding 6). The redesign counts `rm` calls.
- §4.10 claims carry evidence: Decision 4's "not read by any … script" and Decision 1's `find` claim are contradicted by EXECUTED probes (findings 1, 3).
- §5.2 no open questions: findings 4, 5 and 10 name choices left open.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is taken; the specification is revised in place.

1. **pandas' `LICENSES/`:** fixed. Decision 4: the listing skips `OS_LITTER`; a check covers it, and criterion 3 plants a `.DS_Store` there.
2. **`MANIFEST` changes:** fixed. Decision 8 says which files stay byte for byte and which lines change; criterion 3 compares exactly that; the main tree's set is rebuilt on landing.
3. **The cache clean-up:** fixed. It goes through `remove` in a `while read` loop; the wrong reason is gone.
4. **Litter in `build/artifacts/` after a build:** decided. Decision 6: the judge stays strict, and the memo and README name the one-line remedy.
5. **The downstream catch, and the litter set's home:** fixed. Decision 5 names `sums_errors` and wheel rule 3, not `write_assets`; Decision 2 puts the set in `scripts/litter.py`, imported by both scripts, with one equality check.
6. **The `remove` check:** taken as you suggested. `remove.sh` stands alone, sourced by `common.sh` and `build.sh`; the check counts `rm` calls through a shell function, with no writer and no timing.
7. **The two `rmtree(ignore_errors=True)` calls:** fixed. Decision 5's `_remove` retries and fails with one line.
8. **"Only a retry closes the window":** fixed. Decision 1 states the residual (a continuous writer) and that it fails closed; moving aside is named in the Out list, with why.
9. **The cause is lost:** fixed. The third attempt shows its error.
10. **The scan rule:** pinned down. Every shell file under `scripts/` but `remove.sh`; any spelling of recursive plus force; its unit cases in `test_scan.py`.
11. **Criterion 3:** fixed. One full build from pins in a clean clone, then the litter re-run of steps 70 to 90.

## Verdict

Revise first: the retry itself is sound in every shell tried, but a `.DS_Store` in pandas' `LICENSES/` still changes an artifact silently, and criterion 3 cannot pass while the changed scripts' hashes sit in `MANIFEST`.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `58e645e`, and the Disposition above.
- **Ran (EXECUTED, darwin-arm64, and `debian:trixie-slim` in Docker with no network: dash and GNU `rm` 9.7).** The repo was not edited, except to append this section. Nothing under `build/` was changed. Scripts are in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev018/confirm/`: `remove.sh` (Decision 1's function, copied exactly), `sem.sh` (it under `set -eu` with `rm` replaced by a counting shell function) and `loop.sh` (the `find … | while read -r d; do remove "$d"; done` clean-up under `set -eu`).

### The revised `remove` (Decision 1)

EXECUTED in `/bin/sh` (bash 3.2, POSIX mode), `/bin/dash`, `/bin/bash`, `/bin/zsh` and Debian's dash. Two paths each run: a folder and a dangling link. Calls are totals for both paths.

| `rm` fails | exit | `rm` calls | result |
|---|---|---|---|
| never | 0 | 2 | both gone |
| first call | 0 | 3 | both gone |
| first two calls | 0 | 4 | both gone |
| always | 1 | 3 | `rm: fake failure 3` then `ERROR: cannot remove …/a` |

- The `||` chain never trips `set -e`: only its last command could, and that is `true`.
- Only the third attempt's error reaches standard error, so the cause is the line before `cannot remove` (finding 9 closed).
- `exit 1` ends the step from a plain call. `build.sh`'s last-`ERROR`-line grep picks `ERROR: cannot remove …`.

### The cache clean-up loop (finding 3)

EXECUTED in sh, dash and bash, and in Debian's dash:
- Caches present, including in a folder whose name has a space: exit 0, none left.
- No caches: exit 0 (a `while` that never runs returns 0).
- A cache `rm` cannot empty (a read-only subfolder): the subshell's `exit 1` becomes the pipeline's status, and `set -e` stops the step with `ERROR: cannot remove …/__pycache__`. The step stops with one line naming the path, as Decision 1 intends.
- One behaviour changes, and it is harmless: if `build/tools/python/lib` is missing, `find` fails but the pipeline returns the loop's 0, so the step goes on. Before, the same `find` stopped the step. The next line runs `$HOSTPY`, which is then missing too, so the step still stops (INFERRED from READ of steps 60 and 70). No condition.

### Decision 8 and criterion 3

- EXECUTED: every one of the 35 `recipe` lines in the main tree's `build/artifacts/MANIFEST` equals the hash of that file at `HEAD` today. `git ls-files recipes scripts`, without `bench_*`, also gives 35 files. So "differs only in the `recipe` lines of the changed and added scripts" is a well-defined, checkable rule against that set: the changed lines, plus two new lines for `scripts/steps/remove.sh` and `scripts/litter.py`.
- READ: the ratchet records `bytes` only for the two binaries and the zip (`test_binary_is_a_core_wasm_module`, `test_stdlib_zip_is_bytecode_only_and_deflated`). The new `MANIFEST` is therefore not "growth" to accept.
- The littered re-run now plants a `.DS_Store` in pandas' `LICENSES/`, which exercises finding 1.

### Each disposition against its finding

1. pandas' `LICENSES/` — closed: Decision 4, a check, and criterion 3's planted file.
2. `MANIFEST` — closed: Decision 8 and criterion 3 say exactly what changes. Checked above.
3. Cache clean-up — closed: EXECUTED above.
4. Litter in `build/artifacts/` — closed by a decision (Decision 6), with its reason.
5. The downstream catch and the set's home — closed: Decision 5 cites `sums_errors` and rule 3, and `scripts/litter.py` is the one copy the scripts share. READ: no module named `line` or `litter` exists under `tests/` or `src/`, so importing the scripts in a unit check shadows nothing. `frozenset == set` compares equal in Python, so the equality check works as written.
6. The `remove` check — closed: `remove.sh` stands alone, and the check counts calls.
7. The two `rmtree` calls — closed by Decision 5's `_remove`. Condition A below.
8. The residual — closed: stated in Decision 1, and moving aside is out of scope with its reason.
9. The lost cause — closed: EXECUTED above.
10. The scan rule — closed: scope, spellings, exemption and file are all named.
11. Criterion 3 — closed: one full build in a clean clone, then the littered re-run.

### Conditions left (each a sentence in the spec, or the build review checks them)

A. **`_remove` treats "already gone" as success.** `shutil.rmtree` on a missing path raises `FileNotFoundError`. `artifacts.new` is normally missing, because `build.sh` just removed it. Each attempt must catch `OSError` (or test `os.path.lexists` first), and the verdict must come from the existence test, as in `remove.sh`. Otherwise step 90 fails on every normal build. B. **The `sh` check needs a POSIX `sh`.** The revision dropped finding 6's last point. Say that on a host without `sh` the check is blocked (a named need), not passed and not failed. READ: the release workflow's Windows `verify` runs no file under `tests/unit/` except `test_runner_sweep.py`. So CI is unaffected, but a Windows desktop run must not go red.

No new gap at the level of the first review's findings.

### Verdict

Ready to build, with conditions A and B written into the specification (one sentence each) or checked by the build review.

## Disposition of the confirmation (filled in by the author)

- **A:** made. Decision 5's `_remove` catches `OSError` on each attempt and decides by existence, so a path already gone is success.
- **B:** made. The `sh`-based case is blocked, naming its need, on a host without a POSIX `sh`.

Your verdict made the spec ready to build with these two sentences.
