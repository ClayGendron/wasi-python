# 136: the build reads its pins by exact name, and the release checks every inner file

- **Status:** **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, the release-workflow and build-input hardening notes). **Build-class** (it touches `scripts/steps/`, `scripts/00_download.sh`, `scripts/assemble_artifacts.py` and the release workflow), so its pre-build review is required (constitution §5.6) and it lands alone or as the wave's one build-class entry. Not for build until reviewed.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **build-class**, comments and control flow in the build scripts, the release workflow, `release/version.py`, `docs/how-to/verify-a-download.md`, `.gitignore`, `CHANGELOG.md`; one rules check and fixture rows in `tests/`. **No pin, recipe or compiler flag changes, so the artifact set's bytes should not change**; the dry run's same-bytes check is the proof (criterion 7). It tightens every check it touches and loosens none.
- **Depends on:** nothing in flight. 127's CLI follow-up (the wasmtime CLI moves, build-class) is separate and may share a wave slot's queue.
- **Research it stands on:** hunter h10's and h11's evidence (`0.1.0-security-audit-2026-10-25/agents/h10-ci/artifacts/evidence/`, in particular `same_bytes_fixture.log`; `agents/h11-build/artifacts/evidence/`, the `pinned()` fixture under `scratch/fixture/`); the roadmap's note that the repository was renamed to `wasi-python` on 2026-10-24 (`5b2689b9`).

## The problem

Seven places where the build or the release trusts a little more than it checks. None is a finding: no current input collides, and the judge or a later step catches each today. Each is a check that should hold on its own.

1. **`pinned()` matches by regular expression.** `scripts/steps/common.sh:52` selects the pin line with `grep "  $1\$"`, so `.` in a name matches any character. On a fixture, `pinned foo.tar.gz` accepted an unpinned `foo.tar.gz` because `fooXtar.gz` was pinned (EXECUTED, h11). `scripts/steps/10_tools.sh:207,226` and `scripts/make_openblas_void_patch.sh:38` do the same with `grep "  $wheel\$" | cut -c1-64`. No pinned pair collides today, and every literal name has an exact line.
2. **The same-bytes step compares the index, not the files.** `release.yml:448-457` unpacks the tarball and `cmp`s its inner `SHA256SUMS` with each rebuild's; it never runs the inner `SHA256SUMS` against the inner files (EXECUTED on a dummy, `same_bytes_fixture.log`). The judge legs' runner-integrity check binds `MANIFEST`, the binaries and the zip; the licence files are bound by nothing in the workflow.
3. **Meson may download a subproject.** No `meson setup` in `scripts/steps/` passes `--wrap-mode` (`37_plot_libs.sh:39`, `50_pandas.sh:21`, `55_matplotlib.sh:118,169`, `57_scipy.sh:75`, `58_sklearn.sh:55`, `59_statsmodels.sh:61`), and no cross file sets `wrap_mode`. The pinned libraqm 0.10.5 carries `subprojects/sheenbidi.wrap`, an unhashed `[wrap-git]` at `revision=master`, behind `dependency('sheenbidi', fallback: …)`. The recorded build resolved it through pkg-config to step 37's own SheenBidi; had pkg-config failed, meson would have cloned `master` over the network and built it in, and the zero-patch judge (`tests/harness/pins.py`, "files the build adds are not judged") would not have seen the added folder.
4. **Some licence inputs are read without their pin.** `scripts/assemble_artifacts.py` reads some downloads through `pinned_bytes()` (line 521; tqdm, reportlab, the MPL and MIT texts, the scikit-learn and statsmodels extras) and others with a plain `read_bytes()`: the wheels `wheel_licences()` opens, the sympy wheel's nested licence, the wasi-libc and LLVM notices, the Unicode terms. `00_download.sh` verified them in a full build; a step run alone from a named step skips that.
5. **curl may leave HTTPS on a redirect.** `scripts/00_download.sh:35` has `-fsSL --retry 3` and no `--proto '=https' --proto-redir '=https'`. Integrity holds through the in-repo SHA-256, so this matters only with a wrong pin. A present-but-mismatched file is never refetched and fails every later run until someone deletes it (fails closed; a lasting red).
6. **The signer identity users are told to verify is stale.** `release/version.py:301-303` (the release notes' verify command) and `docs/how-to/verify-a-download.md:20-21` hard-code `--repo ClayGendron/wasi_python` and the matching `--signer-workflow`. The repository is `ClayGendron/wasi-python` since 2026-10-24; the attest job itself uses `$GITHUB_REPOSITORY` (`release.yml:2484-2485`) and passes. The next release's attestation will carry the new name and the documented command will fail closed, which teaches users to drop the check. The v0.1.0 attestation carries the old name, which the docs page already says (`5b2689b9`).
7. **`.gitignore` names no secret-file pattern** (`.env`, `*.pem`, `*.key`, `.claude/settings.local.json`); none is tracked, and the untracked `test_app/`, `.agents/` and `skills-lock.json` show how a broad `git add` would carry a stray file.

## Decisions

### 1. Pins are selected by exact field, and exactly one

`pinned()` in `common.sh` becomes `awk -v n="$1" '$2 == n' "$D/SHA256SUMS"` into the check file, and dies unless the result is exactly one line ("`$1` is not pinned" for none, "`$1` is pinned twice" for more). The three `grep … | cut` lookups in `10_tools.sh` and `make_openblas_void_patch.sh` call a shared `pin_of()` in `common.sh` with the same selection and the same one-line rule. A rules check in `tests/checks/test_rules.py` greps `scripts/` for `grep "  \$` against `SHA256SUMS` and fails on any.

### 2. The same-bytes step checks every inner file

`release.yml`'s same-bytes step gains, after the `cmp` loop: `(cd set/wasi-python-* && sha256sum --strict -c SHA256SUMS)` and a listed-equals-present comparison (`sort` of the names in `SHA256SUMS` against `find . -type f ! -name SHA256SUMS | sort`), as the wheel step already does for the wheel. The build job's "Release assets" step re-runs `release/set_key.py verify build/artifacts` just before packing, so the producer's handoff is tight after the wheel copy and the zero-patch pytest step (`release.yml:176-198`).

### 3. Meson never downloads

Every `meson setup` in `scripts/steps/` passes `--wrap-mode=nodownload`, through one variable `MESON_WRAP="--wrap-mode=nodownload"` in `common.sh`, so a wrap that pkg-config does not satisfy fails the build instead of cloning. The zero-patch judge (`tests/harness/pins.py`) gains a rule: a `subprojects/*/` folder that the pinned tarball did not ship, inside any build tree, is a difference (the files the build adds are still not judged elsewhere; this one folder shape is the exception, with the reason in words).

### 4. Every download is read through its pin

`assemble_artifacts.py` routes every read of a file under `downloads/` through `pinned_bytes()`: the wheels (`wheel_licences` takes bytes, or a path it has checked), the sympy wheel, the wasi-libc and LLVM notices, the Unicode terms. A file under `build/` (an unpacked tree) is the step's own output, verified at unpacking, and stays a plain read. A unit row hands the function a fixture `downloads/` with one mismatched file and expects the failure to name it.

### 5. curl keeps HTTPS, and a mismatch is said once

`00_download.sh`'s curl gains `--proto '=https' --proto-redir '=https'`. A present file whose hash does not match is reported with the one-line fix ("delete downloads/<name> and run again") instead of a bare mismatch; it is still never refetched on its own (a poisoned cache must be seen, not silently replaced).

### 6. The verify command is built from the repository's name

`release/version.py`'s `verify_note()` takes the repository name from the workflow (`$GITHUB_REPOSITORY`, passed as an argument by the `notes` command, which `release.yml:2547` calls), with a default of `ClayGendron/wasi-python` for a local run; `tests/unit/test_release_version.py:175-184` follow. The attest job runs **the exact command the notes print** (it reads `notes.md`'s fenced block), so the documented command is the one that passed. `docs/how-to/verify-a-download.md:20-21` names `ClayGendron/wasi-python`, keeps its sentence that 0.1.0 and earlier verify under the old name, and shows the old-name command for them. `tests/harness/coverage.py:31`'s Codecov constant follows the rename if the badge does (the README's badge is the owner's, memory: no downloads badge).

### 7. `.gitignore`

Four lines under a comment that says why: `.env`, `.env.*`, `*.pem`, `*.key`, and `.claude/settings.local.json`. `test_app/`, `.agents/` and `skills-lock.json` are the owner's to ignore or commit; this specification does not touch them.

## Intent

After this specification, a pin is found by its exact name and never by a pattern; the release's same-bytes check binds every file in the tarball, not only its index; no build step can reach the network through a build system's fallback; every byte read from `downloads/` is checked against its pin in the step that reads it; the download keeps HTTPS; and the command users are told to run is the one the release itself ran, under the repository's current name.

## Design

- `scripts/steps/common.sh`: `pinned()` by exact field, `pin_of()`, `MESON_WRAP` (Decisions 1 and 3); `scripts/steps/10_tools.sh`, `scripts/make_openblas_void_patch.sh`: the lookups through `pin_of()`; every `meson setup` line in `scripts/steps/`.
- `scripts/00_download.sh`: the curl flags and the mismatch message (Decision 5). `scripts/assemble_artifacts.py`: every `downloads/` read through `pinned_bytes()` (Decision 4).
- `.github/workflows/release.yml`: the same-bytes step's inner check and the producer's re-verify (Decision 2); the attest job runs the notes' command (Decision 6).
- `release/version.py`, `tests/unit/test_release_version.py`, `docs/how-to/verify-a-download.md`: the repository name (Decision 6). `.gitignore`: Decision 7.
- `tests/checks/test_rules.py` and the fixture rows: the pin-lookup, wrap-mode and `downloads/`-read rules; `tests/harness/pins.py`: the `subprojects/` rule.
- The commits, in order: the specification with its roadmap line and the rules seen failing; the scripts; the workflow and the notes; the documents and `.gitignore`.

## Scope

In: Decisions 1 to 7, the CHANGELOG line ("The build selects pins by exact name, meson builds never download, every licence input is read through its pin, the release checks every file inside its tarball, and the verify command in the release notes follows the repository's name."). Out: release authority (rulesets, required reviewers, PyPI's publisher binding: repository and PyPI settings, the owner's); the set-cache write scope (a note; false-red is its worst case); the `hatchling` bound (the hashed release constraints hold the release).

## Acceptance criteria

1. **`pinned()` fixture:** a `SHA256SUMS` pinning only `fooXtar.gz` makes `pinned foo.tar.gz` fail, and a name pinned twice fails; the rules check finds no `grep "  $` pin lookup in `scripts/` (seen failing first on main's scripts).
2. **Same-bytes fixture:** the audit's dummy replay (`agents/h10-ci/artifacts/evidence/same_bytes_fixture.log`'s shape: an inner file changed, the index unchanged) fails the new step; recorded in the landing notes from a local run of the step's shell.
3. **Meson:** every `meson setup` line carries `$MESON_WRAP`; a rules check holds it; the zero-patch rule's row sees a planted `subprojects/x/` as a difference.
4. **`assemble_artifacts.py`:** no plain read of a path under `downloads/` (a rules check over the AST: every `read_bytes`/`read_text`/`open` on a `d / …` path is inside `pinned_bytes`); the fixture row of Decision 4.
5. **The verify command:** `verify_note("0.2.0", "ClayGendron/wasi-python")` names the new repository; the attest job's command is read from `notes.md` and passes on the dry run; the docs page carries both names with the version boundary.
6. **`.gitignore`** carries Decision 7's lines; `git check-ignore .env x.pem` says so.
7. **Same bytes:** the dry run on three systems shows the artifact set unchanged against the last accepted set (`SHA256SUMS` identical), since no pin, recipe or flag changed; if any byte differs, the specification stops and the difference is explained before anything else.
8. `ruff`, `mypy`, the rules checks green; no code file names a specification, review, finding or `context/` path; the dispatch read on three systems.

## For the lane

- **Kind:** build-class; lands alone or as the wave's build-class entry, after a dry run on three systems; shares `CHANGELOG.md`, `context/roadmap.md`, `tests/checks/test_rules.py` with others; `scripts/steps/common.sh` with 127's CLI follow-up if both are drafted.
- **Claim list** ("136:"): new rules checks and fixture rows; retired none; lost passes none; fuel none; **bytes none** (criterion 7 is the proof).
- **Flags:** `--accept "136: pins are selected by exact field and exactly one, meson builds pass --wrap-mode=nodownload, every downloads/ read goes through pinned_bytes, curl keeps HTTPS, the same-bytes step checks every inner file and the producer re-verifies the set before packing, the verify note is built from the repository's name and the attest job runs it"`, `--accept-judge "136: rules checks for pin lookups, meson wrap mode and downloads/ reads, fixture rows for pinned() and assemble_artifacts, the zero-patch rule's subprojects row; no existing expectation edited"`.
- **Dry-run needs:** a full three-system run; the same-bytes line read for every runner.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

Seven places where the build or the release trusted a little more than it checked are made to check: exact pin names, no meson downloads, every input read through its pin, HTTPS kept, every inner file bound, and a verify command that names the repository as it is.
