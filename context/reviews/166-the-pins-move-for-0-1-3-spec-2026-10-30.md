# Review of 166 — The pins move for 0.1.3

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/166-the-pins-move-for-0-1-3.md`, at `4849fc4e` on `docs/0.1.3-specifications`; 159 and 161 read as they stand on their open branches (`9c71bfc0`, `96c24338`)
- **Run:** none: a specification review
- **Re-ran:** `git log -S sqlite-autoconf-3540100 -- downloads/SHA256SUMS` → `5abc9721`, 2026-10-17, spec 007; `sorted()` of `wasmtime-v49.0.3-*` and `wasmtime-v50.0.1-*` → 49.0.3 first; the 0.1.2 wheel's headroom → 1,614,646 bytes (1.64%) to 100,000,000 and 6,472,246 (6.58%) to 104,857,600; with this file written, `uv run pytest -q tests/lint` → 13 passed (all EXECUTED).
- **Time box:** 45 minutes (build-class); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

READ and confirmed: SQLite 3.54.1 is pinned (`downloads/SHA256SUMS:9`); `10_tools.sh:214` (the host Python's version assert), `:227` and `:230` (f2py's `2.5.2`); `35_stdlib_libs.sh:63`; `70_zip.sh:147`; `test_v1_5_rebuild_from_pins.py:568`; `paths.wasmtime_cli()` takes the first sorted match (`tests/harness/paths.py:362-365`); `scan.py:701` reads the host names; `_wasmtime_ffi.PIN` is `wasmtime>=50,<51`; `decide()` sets `rebuild` only on a release pull request, a tag, the weekly run and a dispatch (`release/ci_plan.py:369-399`); `compare_snapshots.py` compares initial linear memory, not the file; the three carried patches' drafts are `drafted`. Not structural: nothing under `src/` changes (agreed).

## Acceptance criteria against evidence

1. Decision 9's rows fail first: two of three cannot as written (Low 7).
2. Publisher hashes, rebuild-from-pins: buildable; the tree checks run only in the build shard (Medium 1).
3. Patches at no offset: the build job's zero-patch step runs on the pull request (READ, 159's `release.yml:363-373`); the sweep's patches are not covered (Medium 5).
4. `-V` and builtin versions: sound.
5. The two-CLI comparison: sound, but the tool reads memory only (Low 12).
6. Golden and `tests/upstream/**` edits: sound for `expected/`; CPython's plan is not named (Low 9).
7. Local release-tier groups: numpy, pandas, CPython only (Medium 6).
8. Decision 11's table: no comparable fuel in the pull request's run (Medium 3); no wheel row (Medium 4).
9. macOS against arm64 Linux, x86-64 at the weekly run: the pre-merge vote is one ISA (Medium 2).
10. News file shape: the patch entry fails the patch rule (Low 8).

## Findings, most severe first

1. **Medium: the checks this change moves most run nowhere before the release** (`tests/release_shards.toml:15-26`; 159 Decision 5) — under 159 the build shard runs only in `rebuild-linux-x86-64`, on a release pull request, the weekly run or a dispatch, never on a pull request or after a merge. Failure: `test_the_guests_configure_results_are_recorded` (Decision 9's third row and `tests/cpython_configure.txt`), `test_recursion_raises_under_the_wasmtime_cli` (Decision 4's guard), `test_every_build_python_is_pinned` (the new host Python, f2py's numpy) and `test_every_compile_contracts_nothing` are not run on either pull request; a 3.15.2 configure flip or a CLI-50 recursion trap reaches `dev` green and is found at the weekly run. Fix: "On the local macOS build of each pull request's final head (Decision 12), the builder runs the build shard (`uv run pytest --shard=build`) and records its pass line and the configure diff in the landing notes; the review reads them."

2. **Medium: the pre-merge same-bytes vote compares two aarch64 hosts, once** (Decision 12) — macOS arm64 against arm64 Linux tests the OS, not the ISA, and only the first pull request's first head. Failure: wizer 50 (Cranelift on each host) or the x86-64 clang over new 3.15.2, numpy or C++20 pandas code gives other bytes on x86-64; the weekly run finds it after 165 and 167 have built on the line. If 159 has not landed (Depends calls it landed; it is built, not landed, pull request #56), the pull request's build is on macOS and the comparison is macOS with macOS. Fix: "159 lands first. The comparison is made at each pull request's final head, the second's included. 165 and 167 merge only after the first weekly run after 166's last merge shows `same-bytes` green, or the owner, asked with AskUserQuestion, dispatches one."

3. **Medium: Decision 11's fuel bounds cannot be read from the pull request's run** (154 Decisions 4 and 6; 159 Decision 2) — Linux fuel is recorded and never compared, a pull request without the `platform` flag has no macOS legs, and the upstream groups run on Linux alone. Failure: the "+1% sum", "+5% own check" and "+15% pandas group" bounds have no comparable numbers in CI, and the builder compares noisy Linux fuel or nothing. "Spec 154 does not apply" is true of its engine rule only. Fix: "Each pull request carries `ci:full`, so the gather compares darwin with darwin; the upstream groups' fuel in the table (numpy, pandas, CPython, normal and release) is measured on darwin at `dev`'s set and the head's, each labelled EXECUTED with its platform."

4. **Medium: the wheel is neither bounded nor recorded against decision 64** (Decision 11) — the 0.1.2 wheel is 98,385,354 bytes, 1.64% under 100,000,000. Failure: the second pull request's allowed +3% on `python.wasm` and the zip (the zip stored nearly unshrunk, 167's finding 5) takes the wheel past the 100 MB line decision 64 says the agent brings back before a landing crosses it, and toward PyPI's 104,857,600-byte default. Fix: "Decision 11's table has a wheel row per pull request, against 100,000,000 and 104,857,600; a pull request whose wheel crosses 100,000,000 asks the owner with AskUserQuestion before it merges (decision 64), joined with 167's PyPI request."

5. **Medium: the sweep reaches patched trees that Decision 6 does not cover** (Decisions 6, 7) — 16 other trees carry 24 patches. Failure: a swept matplotlib, scipy, lxml or OpenBLAS leaves its patch folder on the old name (`patch_errors`: "no pinned source tarball has this top folder"); OpenBLAS's three are generated by `scripts/make_openblas_void_patch.sh`, not by hand; a swept regex stops the build, since `MODIFIED` (`scripts/assemble_artifacts.py:379-386`) is keyed by the patch's path. Fix: "Decision 6 applies to every carried patch of every moved pin: re-made with the same changed lines, the draft moved with `Against` updated, `MODIFIED`'s keys moved, OpenBLAS's regenerated by its script and compared. A swept pin with a patch is listed as such among the candidates."

6. **Medium: release-tier groups of the other moved and dependent pins are first run at the release** (Decision 10) — only numpy's, pandas' and CPython's are run locally. Failure: a swept sympy, or scipy's or scikit-learn's release groups over numpy 2.5.4, lose a pass. It surfaces at the release pull request, where no claim clears a lost pass (AGENTS.md; 161 Decision 3 leaves the release pull request's rows strict). Fix: "The builder also runs the release groups of every swept pin; the release groups of scipy, scikit-learn, statsmodels, matplotlib and contourpy are read at the first weekly run after the merge (Finding 2's gate) and their claims appended to the ledger (`context/release-claims.toml` once 161 lands)."

7. **Low: two of Decision 9's rows cannot be seen failing on `dev`'s tip** — at 3.15.0 the literal `Python-3.15.0` path is right, and `sorted()` returns 49.0.3, which is today's line (EXECUTED). Fix: "The `wasmtime_cli()` row passes the line's name, `wasmtime-v50.0.1-…`, to the function, and fails today; the configure row is seen failing after commit 2 with the literal kept."

8. **Low: the news entry fails the patch rule** (Decision 13; `tests/harness/scan.py:3637`) — `patch_errors` needs each patch's full path in a news file. Failure: naming the folders gives `test_carried_patches_follow_the_rules` red three times. Fix: "The entry names each re-made patch's path, `recipes/patches/numpy-2.5.4/0001-npy-files-without-dup.patch` and so on, split into two entries if past sixty words."

9. **Low: CPython's plan and the fuel caps** (Decision 10) — `tests/upstream/python/*.txt` is a judge allowance (AGENTS.md) that 3.15.2 may change, and "rise only past the measured value" reads two ways. Fix: "The plan files take the same three kinds of edit as `expected/`. A cap rises only when a measured value exceeds it, by the file's own margin, with the run named."

10. **Low: the numpy commit's file list is short** (Decision 2 step 4; Kind) — it omits `40_numpy.sh:2,11,12`, `PACKAGES` (`assemble_artifacts.py:28`, not line 804, which is the source paths), `70_zip.sh:146`; the rename headers (`recipes/npy_rename.h`, `pandas_rename.h`) and `recipes/wasi-pandas.cross` are the recipe-first edit points (§4.1). Fix: name them.

11. **Low: the licence rule covers the sweep only** (Decision 7, §4.12) — `assemble_artifacts.py:805,815-818` read numpy's `license-files` and pandas' `LICENSES/`. Fix: "A numpy or pandas move whose licence files change waits for the owner, as a swept pin does."

12. **Low: the comparison and the security text** — `compare_snapshots.py` reads memory, so a wizer-50 change in sections shows only as a SHA-256. `SECURITY.md:24` says `x-wizer` names the CLI; it does not (READ, a built `MANIFEST`). Fix: "The landing notes record both files' SHA-256 and the tool's output; `SECURITY.md` drops the `x-wizer` clause."

13. **Low: the order with the siblings** — 167 needs `recipes/patches/pandas-3.1.0/` from 166's second pull request, or the 3.0.x folder under option A; 165 says "whichever lands second". Fix: "167's pandas patch lands after 166's second pull request, on its pandas folder; 165 builds after 166's first."

## Constitution checks

- §4.1: holds for numpy and pandas once Findings 5 and 8 are applied. §4.2 pins: Decision 5 checks each against its publisher; holds. §4.12: Finding 11. §4.15: no default moves. Artifacts stay out of git.
- §5.6: this is the pre-build review a build-class change needs.
- §7: nothing tripped; no judge edit is allowed to turn a run green (Decision 10).

## Disposition

By the specification's author, 2026-10-30. Every finding taken; each line names where.

1. Medium 1: taken. Decision 12 runs the build shard (`uv run pytest --shard build`) on the local macOS build of each pull request's final head and records its pass line and the configure diff; criterion 2 holds it.
   - Reviewer: confirmed. Decision 12 and criterion 2 say it (READ).
2. Medium 2: taken. Depends on reads "159, landing before this is built"; Decision 12 compares at each final head, the second's included, and gates 165 and 167 on the first weekly run's green `same-bytes` after 166's last merge, or an owner-dispatched run asked with AskUserQuestion; criterion 9.
   - Reviewer: confirmed. Depends on, Decision 12 and criterion 9 say it; the second pull request's head is compared too (READ).
3. Medium 3: taken. Decision 1 puts `ci:full` on each pull request; Decision 11's first paragraph reads own checks from the gather's darwin comparison and measures the upstream groups' fuel (numpy, pandas, CPython, both tiers) locally on darwin at `dev`'s set and the head's, labelled with the platform; the "154 does not apply" sentence now names its engine rule only.
   - Reviewer: confirmed. Decision 1 and Decision 11's first paragraph say it (READ).
4. Medium 4: taken. Decision 11's table has a wheel row against 100,000,000 and 104,857,600; crossing 100,000,000 asks the owner before the merge (decision 64), joined with 167's request; criterion 8.
   - Reviewer: confirmed. Decision 11's last sentence and the table's wheel row say it (READ).
5. Medium 5: taken. Decision 6 covers every carried patch of every moved pin: folders renamed, drafts moved, `MODIFIED`'s keys moved, OpenBLAS's regenerated by `make_openblas_void_patch.sh` and compared; Decision 7 marks patched candidates.
   - Reviewer: confirmed. Decisions 6 and 7 say it, regex's `MODIFIED` keys and OpenBLAS's script named (READ).
6. Medium 6: taken. Decision 10 runs the release groups of every swept pin locally, reads the numpy-dependent release groups (scipy, scikit-learn, statsmodels, matplotlib, contourpy) at Decision 12's weekly run, and names `context/release-claims.toml` once 161 lands.
   - Reviewer: confirmed. Decision 10 says it; the weekly read is the gate of Decision 12 (READ).
7. Low 7: taken. Decision 9: the `wasmtime_cli()` row passes the line's name and is red today; the configure row is seen failing after commit 2 with the literal kept.
   - Reviewer: confirmed. Decision 9 says it (READ).
8. Low 8: taken. Decision 13 adds a per-pull-request entry naming each re-made patch by full path; criterion 10 names `test_carried_patches_follow_the_rules`.
   - Reviewer: confirmed. Decision 13 and criterion 10 say it (READ).
9. Low 9: taken. Decision 10 gives `tests/upstream/python/` the three kinds of edit; a cap rises only past a measured fuel, keeping the group's former headroom, with the run named (the files state no margin of their own).
   - Reviewer: confirmed. Decision 10 says it (READ).
10. Low 10: taken. Kind and Decision 2 step 4 name `40_numpy.sh` lines 2, 11 and 12, `PACKAGES` at line 28, the source paths at 804, `70_zip.sh` line 146; Decision 8 names `wasi-pandas.cross` and `pandas_rename.h` as the recipe-first points, `npy_rename.h` for numpy.
   - Reviewer: confirmed. Kind, Decision 2 step 4 and Decision 8 say it (READ).
11. Low 11: taken. Decision 7's licence rule covers any moved pin, numpy's `license-files` and pandas' `LICENSES/` named.
   - Reviewer: confirmed. Decision 7 says it (READ).
12. Low 12: taken. Decision 4 records both snapshots' SHA-256 beside the tool's memory comparison; Decision 13 drops `SECURITY.md`'s `x-wizer` clause.
   - Reviewer: confirmed. Decisions 4 and 13 say it (READ).
13. Low 13: taken. Depends on: 165 builds after the first pull request lands; 167's pandas patch lands after the second, on its pandas folder (the 3.0.x folder under option A).
   - Reviewer: confirmed. Depends on says it (READ).

## Verdict

Fit to build: the six Mediums and seven Lows are answered in the amended specification (read whole again, 2026-10-30), and nothing ranked High or Medium stands.
