# Review of 004 — Alpha releases: the version, the tag and the release workflow

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read
  the constitution (§4 and §7 closely), `AGENTS.md`, specification 004
  with its landing notes, 002's Decisions 6, 7, 14 and 17, and 001's
  Decision 3 with its amendment. Then I read the change itself. I did
  not rely on the landing notes. Each claim below is labelled EXECUTED,
  READ or INFERRED.
- **Reviewed:** three commits on `main`, and the working tree on top:
  - `a786321` (the spec 004 draft), `dcebe74` (the wiring self-test),
    `af0e6b9` (verify judges pass and fail only; the Windows zip race).
    `e385d32..HEAD` also holds `9aea66c` and `eb19228`. Those are spec
    001's landing and a research memo, and are not part of this review.
  - The uncommitted spec 004 landing notes and the spec 001 amendment
    (`git diff`).
  - Files: `release/version.py`, `.github/workflows/release.yml`,
    `CHANGELOG.md`, `pyproject.toml`, `uv.lock`,
    `src/wasi_python/__init__.py`, `src/wasi_python/runner.py`,
    `tests/unit/test_release_version.py`, `tests/checks/test_rules.py`,
    `tests/checks/test_v1_4_embedding.py`,
    `tests/unit/test_checks_wiring.py`, `tests/known_gaps.toml`, and the
    README's "Releasing" section.
  - `.idea/` and `context/research/2026-10-16-what-matplotlib-needs.md`
    are untracked and not part of the change.
- **Re-ran (EXECUTED, darwin-arm64, uv 0.9.22):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 90/93 pass
    · 1 gap · 2 blocked · 0 fail (unit suite 154/154)`. Blocked: three
    systems 1, wheel 1 (no `dist/` here). `244 passed, 2 skipped, 1
    xfailed`. **Exit 0.** Ratchet: `ratchet vs e385d322f7: lost 0 · absent
    0 · unrun 0 · gained 2 · grew 0 · judge changed: pyproject.toml,
    tests/checks/test_rules.py, tests/checks/test_v1_4_embedding.py and 4
    more`. The other four are `known_gaps.toml`, `test_checks_wiring.py`,
    `test_release_version.py` and `uv.lock` (READ, `git diff --stat`).
    Landing needs `--accept-judge` (002 Decision 7).
  - `uv run ruff check src tests release` → `All checks passed!`, exit 0.
  - `uv run ruff format --check src tests release` → `38 files already
    formatted`, exit 0.
  - `uv lock --check` → exit 0.
  - `gh run view` and `gh run view --log` on the three runs. I downloaded
    run 38980695810's `release-assets` artifact.
  - `release/version.py` in a scratch clone whose `origin` is a bare
    scratch repository. That includes `release --push` into the bare
    repository.
  - I did not run `--accept`, commit, tag or push in the real repository.
    Scratch work is under the session scratchpad, `review-004/`.

## Acceptance criteria against evidence

1. *`bump` takes the tree from `0.0.0` to `0.1.0a1`; `uv build --wheel`
   names the wheel `wasi_python-0.1.0a1-py3-none-any.whl`, and it carries
   the set (the judge's wheel check passes with it in `dist/`).* —
   **Met.**
   - EXECUTED, in the clone: I set `__version__ = "0.0.0"` and removed
     the changelog section. `check` → `ok 0.0.0`. `bump` → `0.0.0 ->
     0.1.0a1`, with a new `## 0.1.0a1 — unreleased` section.
   - EXECUTED: `SOURCE_DATE_EPOCH=1767225600 uv build --wheel` at
     `af0e6b9`, with the local set copied in → that wheel name,
     36,182,921 bytes, SHA-256 `02f83128…`.
   - EXECUTED: with that wheel in the clone's `dist/`,
     `test_wheel_carries_the_artifact_set` plus the whole
     `tests/unit/test_checks_wiring.py` → `7 passed`.
   - The landing notes give 36,182,466 bytes and `435f0f81…`. Those are
     from an earlier commit (finding 13).
2. *`check` passes on the tree, and fails with one line naming why on a
   wrong tag, a missing changelog section and a static version.* —
   **Met.**
   - READ: `test_check_passes_a_good_tree_and_names_each_fault` covers
     all three. The static-version case gives two lines, and both name
     the fault.
   - EXECUTED, CLI in the clone:
     - `check` → `ok 0.1.0a1`, exit 0.
     - `check --tag v0.1.0a1` on the unreleased tree → `CHANGELOG.md's
       section for 0.1.0a1 is still unreleased`, exit 1.
     - `--tag v0.1.0a2` → `the tag v0.1.0a2 is not v0.1.0a1…`, exit 1.
     - `--tag 0.1.0a1` → the same message, exit 1.
     - With the section dated: `--tag v0.1.0a1` → `ok 0.1.0a1 (tag
       v0.1.0a1)`, exit 0. `--tag v0.1.0a2` → exit 1.
3. *A `workflow_dispatch` run on `main` passes every job it runs.* —
   **Met.**
   - EXECUTED, `gh run view 38980695810`: `workflow_dispatch` on `main`,
     head `af0e6b9` (today's HEAD), conclusion `success`. The jobs are
     build, verify on windows-2025, macos-15 and ubuntu-24.04 (all ✓),
     publish and pypi (skipped).
   - From its log (EXECUTED):
     - The version step printed `ok 0.1.0a1`.
     - Every build step printed `ok`. Step 60 gave the reactor
       `d77dc946962d2154`. Step 80 gave the snapshot `b450c7a6892bf9e3`.
       Both equal the local `build/artifacts/SHA256SUMS` and
       `context/progress/accepted.json`.
     - Step 20 gave CPython `28610556 bytes, 64f94066…`. The local
       `build/logs/20_cpython.log` has `28610092 bytes, 307b29e2…`. So
       the notes are right that the unshipped interpreter differs.
     - Zero-patch step: `4 passed, 8 deselected`.
     - The judge: `89/93 pass · 1 gap · 3 blocked · 0 fail (unit suite
       149/154, 5 skipped)`. Blocked by oracle, prior-art clones and
       three systems. `ratchet vs e385d322f7: lost 0 … unrun locally 2 …
       grew 0`. `238 passed, 8 skipped, 1 xfailed`.
     - Assets: a 36,182,921-byte wheel, a 26,032,696-byte `.tar.xz`, and
       a 210-byte `SHA256SUMS`.
     - Each verify job downloaded the same artifact (digest `dfca09b9…`)
       and scored `63/66 pass · 0 gap · 3 blocked · 0 fail`, blocked by
       oracle, three systems and wheel. The scoreboard said `JUDGE INPUTS
       OVERRIDDEN: --progress-dir` and `ratchet vs no baseline`. The
       wheel printed `Completed(exit_code=0, stdout=b'6\n', …)` on all
       three.
   - EXECUTED: the downloaded assets match their `SHA256SUMS`. I rebuilt
     the wheel and ran `version.py assets` locally on the local set. Both
     files came out **byte for byte the same as CI's**: `02f83128…` and
     `bc51b406…`.
   - Runs 1 and 2 (EXECUTED, `--log-failed`):
     - Run 1, head `a786321`, failed on
       `test_checks_wiring.py::test_a_good_set_passes_the_rules_it_owns
       - assert None == 'wheel'`, as the notes say.
     - Run 2, head `dcebe74`: Windows lost
       `test_runner_serves_concurrent_calls_on_one_root` to `PermissionError
       [WinError 5]` on the rename, as the notes say.
     - On macOS in run 2, **two** checks grew, not one:
       `test_gzip_round_trips` 500,664,834 → 500,823,401 (+0.032%), and
       `test_uncaught_errors_print_as_native[plain]` 578,371,225 →
       578,429,550 (+0.0101%). See finding 7.
4. *`uv run pytest` is green; the gap is removed; ruff is clean on
   `src`, `tests` and `release`.* — **Met** (EXECUTED, above). v1.5 is
   `11/12, gap 1`. The one gap left is the toolchain gap.

Release tooling, beyond the criteria (EXECUTED in the clone):

- **`bump`** → `0.1.0a1 -> 0.1.0a2`. `bump --to 0.1.0b1` → done.
  `--to 0.1.0-a3` and `--to v0.2.0` → `not a version of the form…`, exit
  1. `--to 0.1.0a2` from `0.1.0b1` → `not greater`, exit 1. So does the
  same version. Each new section goes above the newest one.
- **`release` refusals, without `--push`:**
  - A dirty tree → `the working tree has uncommitted changes`, exit 1.
    So does a tree whose **only** change is an untracked file (finding
    10).
  - A branch other than main → `releases are cut from main`.
  - A commit ahead of origin → `main is not level with origin/main`.
  - A tag that exists only on the remote → `the tag v0.1.0a1 exists
    already` (`fetch --tags` brings it in).
- **`release` on a clean tree level with origin** → `tagged v0.1.0a1. To
  cut the release: git push origin main v0.1.0a1`.
  - The commit `Release 0.1.0a1` changes only `CHANGELOG.md`, one line:
    the section is dated `2026-10-16`.
  - `git cat-file -t v0.1.0a1` → `tag`, so the tag is annotated. Its
    message is `wasi-python 0.1.0a1` followed by the notes.
  - Nothing reached the bare origin.
  - `check --tag v0.1.0a1` on the release commit → ok.
- **`release --push`** into the bare origin → main and the annotated tag
  arrive (`refs/tags/v0.1.0a1^{}` is the release commit).
- **`notes 0.1.0a1`** prints the section's body. `notes 9.9.9` → `no
  section`, exit 1.

## Findings, most severe first

1. **The release would ship HACL\* code without its MIT notice**
   (`build/artifacts/LICENSES/`, constitution §4.12).
   - The defect: CPython 3.14's hash modules are built from HACL\*
     (`Modules/_hacl/`). It is MIT-licensed (*"Copyright (c) 2016-2022
     INRIA, CMU and Microsoft Corporation"*). No notice for it is in the
     artifact set.
   - Evidence (EXECUTED):
     - `grep -ao 'Hacl_[A-Za-z0-9_]*' python.wasm` finds
       `Hacl_Hacl_Hash_Blake2b_digest` and others.
     - `Modules/_hacl/Hacl_Hash_Blake2b.c` opens with the MIT header.
     - `grep -i 'hacl\|INRIA'` over all nine `LICENSES/*.txt`, and over
       CPython's `LICENSE` and `Doc/license.rst`, finds nothing.
     - The other bundled sub-licences I probed are present: libmpdec,
       expat and mimalloc in `cpython.txt`; lapack, pocketfft and
       highway in `numpy.txt`; ujson, klib and musl in `pandas.txt`.
   - Failure: pushing `v0.1.0a1` publishes a public release, and a
     wheel, that carry MIT code without the notice MIT requires. §4.12
     says the notices are inside the release.
   - Why here: the set comes from spec 003, but this change is the one
     that publishes it. 002 Decision 17 gives "bundled sub-licences
     inside a component … CPython's libmpdec and expat" to "the release
     specification", and 004 does not take them up. The scoreboard
     still lists "bundled sub-licences" as not machine-checked.
   - Fix: before cutting, add the HACL\* notice to the set's licences.
     That is a recipe change (003's licence step), a rebuild and new
     hashes. Then audit CPython's other vendored directories for
     notices that `Doc/license.rst` does not carry. Record in 004 that
     it owns bundled sub-licences, or move that duty to 003. This
     blocks cutting the release. It does not block landing the
     machinery.
2. **A manual run on a tag publishes** (`release.yml:121`, `:150`).
   - The defect: publish runs `if: github.ref_type == 'tag'`. A
     `workflow_dispatch` started on a tag ref (`gh workflow run
     release.yml --ref v0.1.0a1`) also has `ref_type == 'tag'` (INFERRED,
     from GitHub's documented `github.ref_type`; not run here, since it
     would publish).
   - Failure: that "dry run" passes `check --tag` (the section is
     dated), builds, verifies, and calls `gh release create`. If the tag
     push's own run failed, this publishes. With `PYPI_PUBLISH=true` it
     also uploads to PyPI. Decision 5 and the README promise that a
     manual run never publishes.
   - Fix: `if: github.event_name == 'push' && github.ref_type == 'tag'`
     on `publish`, and the same, plus the variable, on `pypi`. A failed
     release run is retried with "Re-run failed jobs", which keeps the
     `push` event. Or, if dispatch-on-a-tag is meant as the retry path,
     say so in Decision 5 and the README.
3. **The published wheel is built by an unpinned build backend, and
   that backend runs beside a write token** (`pyproject.toml:31`;
   `release.yml` "The wheel" and publish steps).
   - The defect: `requires = ["hatchling"]` has no version or hash.
     `uv build --wheel` fetches the newest hatchling from PyPI.
     EXECUTED: the release wheel's `WHEEL` says `Generator: hatchling
     1.32.4`, today's latest.
   - Every `uv run` in the workflow also builds the editable project
     with that backend. The log shows `Building wasi-python @ file://…`
     in the version step and in each verify job (EXECUTED).
   - That includes the publish job's `uv run python release/version.py
     notes` (INFERRED, the same mechanism). That job holds `contents:
     write`. Every checkout runs with `persist-credentials: true`
     (EXECUTED, log), so the token also sits in `.git/config`.
   - Failure:
     - §4.2: "A build that fetches anything unpinned is not a build."
       A new hatchling can change the wheel's bytes, and the wheel is a
       release asset.
     - A compromised hatchling release would run with a token that can
       rewrite releases and tags.
   - Fix:
     - Pin `hatchling==1.32.4` in `[build-system]`, and supply its hash.
       Either use a hashed build constraint, or add its wheel to
       `downloads/SHA256SUMS` and build offline without isolation.
     - In publish, run `release/version.py notes` with `uv run
       --no-project` (it needs only the standard library).
     - Set `persist-credentials: false` on every checkout.
4. **The link check no longer has to plant a link on POSIX**
   (`tests/checks/test_v1_4_embedding.py:260-280`).
   - The defect: the guest's `os.symlink` is now inside
     `try/except OSError: pass` on every OS. Nothing asserts that the
     link was made.
   - Failure: if a future wasmtime, or a host, refuses guest symlinks
     on POSIX, the check still passes. It would then test only "repair
     a removed zip". Its name says it tests "never follows a link".
   - Today the links are made. EXECUTED, my probe on macOS:
     `is_symlink after first: True` for both `the zip` and `its
     directory`. So nothing is lost yet, but the judge has been loosened
     on the hosts where it could hold.
   - Fix: after the first call, on POSIX,
     `assert (root / link.lstrip("/")).is_symlink()`. Or swallow the
     `OSError` only when `os.name == "nt"`.
5. **The verify jobs cannot see a pass turn into a block**
   (`release.yml:98-104`).
   - The defect: with an empty baseline, verify fails only on `fail`.
     A check that is blocked on one system (a need missing there) leaves
     the job green.
   - Is it a weakening? Not of an existing check: verify is new, and the
     three-systems check stays blocked (004 Scope). The ratchet is still
     enforced for a release, in the build job, against
     `context/progress/accepted.json`. Run 3 shows `ratchet vs
     e385d322f7 … lost 0 … grew 0` (EXECUTED).
   - What it does catch: a missing set fails loudly. EXECUTED: with
     `WASI_PYTHON_ARTIFACTS` pointing at a missing directory and an
     empty `--progress-dir`, `17 failed`, exit 1.
   - Failure: a release whose Windows run silently blocks, for example,
     the v1.4 runner checks would still publish, with "checked on three
     systems" in its notes.
   - Fix: after the pytest step, read `build/progress/latest.json`
     (`--progress-latest`) and require that the only blocked needs are
     `oracle`, `three systems` and `wheel`. Read the JSON, not the
     scoreboard text: Windows prints `�` for `·` (EXECUTED, run 3's log).
6. **A tag on a commit that is not on main can publish**
   (`release.yml` build, first step).
   - The defect: Decision 2 says the tag sits on a pushed commit of
     `main`. The workflow checks only that the tag is `v{version}` and
     that the section is dated.
   - Failure: someone with push rights tags a side-branch commit with a
     matching version and a dated section. That commit is built, judged
     and published as the release. INFERRED.
   - Fix: on a tag, `git fetch origin main` and then
     `git merge-base --is-ancestor "$GITHUB_SHA" origin/main`.
7. **Fuel differs between macOS runners on the same bytes, and the build
   job's ratchet is exposed to it too** (landing notes; `release.yml`
   "The judge").
   - EXECUTED: three local runs of the two checks gave identical fuel,
     equal to the accepted figures (500,664,834 and 578,371,225). The
     macOS verify runner in run 2 gave more. Ubuntu and Windows did not.
   - Failure: the build job runs on the same `macos-15` label and keeps
     the ratchet. A release build can go red with no change in the
     product. It fails closed, so it cannot publish something wrong. It
     can stop a release for a reason nobody has explained.
   - The notes say "one check spent 0.0101% more". Two did, and gzip
     grew 0.032%.
   - Fix: correct the notes. Name the open cause in the
     reproducible-builds memo, since a host input reaching guest fuel is
     a determinism question. Say in Decision 5 what to do when the build
     job's ratchet goes red only on fuel.
8. **The published `run` extra is wider than what verify tests**
   (`pyproject.toml:20`, `release.yml:110`).
   - The defect: the wheel declares `wasmtime>=49`, with no upper bound
     (EXECUTED, `METADATA`). Verify installs the wheel *without* the
     extra and adds `wasmtime>=49,<50`. Decision 5 says "with the `run`
     extra".
   - Failure: once wasmtime 50 ships (49.0.0 is the newest today,
     EXECUTED), `pip install "wasi-python[run]"` gets a version no
     release run has seen.
   - Fix: give the extra `<50`, or record why it is open. Have verify
     install `"$wheel[run]"`, as the spec says.
9. **`bump` can write the version and then fail on the changelog**
   (`release/version.py:225-226`).
   - EXECUTED: with a `## 0.1.0a2` section already in the changelog,
     `bump` → `ERROR: CHANGELOG.md already has a section for 0.1.0a2`,
     exit 1, but `__init__.py` now says `0.1.0a2`.
   - Fix: build both new texts first, then write both.
10. **`release` refuses any untracked file, and the real tree has two**
    (`release/version.py:243`).
    - EXECUTED: a tree whose only change is an untracked file →
      `the working tree has uncommitted changes`.
    - The real tree today has `?? .idea/` and an untracked research memo
      (`git status`). So `release` will refuse there, with a message
      that does not name the cause.
    - Fix: add `.idea/` to `.gitignore`, and say "uncommitted or
      untracked" in the message. Keep the refusal itself: a release
      should come from a known tree.
11. **The README tells the public to `pip install` a name no one holds
    yet** (`README.md:130`).
    - EXECUTED: `https://pypi.org/pypi/wasi-python/json` → 404.
    - Failure: once the repository is public with a GitHub release, and
      PyPI deferred, anyone can register `wasi-python`. Readers who
      follow the README would then install their package. INFERRED risk.
    - Fix (the owner's call): upload soon, or until then point the
      README at the GitHub release's wheel.
12. **The Windows fallback records a file it did not place, from a stat
    taken after the hash** (`src/wasi_python/runner.py:225-235`).
    - The defect: after keeping the file in place, the code falls
      through to `_placed[str(dest)] = _stamp(os.lstat(dest))`. That
      `lstat` runs after `_hash_file`. On POSIX a write landing between
      the hash and that `lstat` would be trusted by the next call's fast
      path. The existing path (`:214-216`) stamps the `st` taken before
      hashing, which is safe.
    - INFERRED: hard to reach. Windows does not use the fast path. On
      POSIX, `os.replace` rarely raises `PermissionError` in a directory
      where `mkstemp` has just succeeded.
    - Also, spec 001's amendment says "where Windows refuses", but the
      code catches `PermissionError` on every OS.
    - Fix: in the fallback, stamp the `st` from before the hash and
      return. Gate the fallback on `os.name == "nt"`, or reword the
      amendment.
13. **Landing notes: stale local numbers.**
    - The notes' local wheel (36,182,466 bytes, `435f0f81…`) predates
      `af0e6b9`'s runner change.
    - At HEAD the local wheel is 36,182,921 bytes, `02f83128…`, the
      same bytes as CI's (EXECUTED). That is a stronger claim: the wheel
      and the `.tar.xz` rebuild byte for byte on a second host. The notes
      should say so.
14. **Workflow hardening, small:**
    - `uv run` without `--locked` (or `UV_LOCKED=1`). A stale lock would
      be re-resolved on the runner, not refused. The lock is in sync
      today (EXECUTED).
    - The Python that runs the judge, `version.py` and hatchling is
      whatever the runner image has: Homebrew 3.14.7 on macOS, 3.12.3 on
      Ubuntu, 3.12.10 on Windows (EXECUTED, logs). Pinning it (for
      example `UV_PYTHON`) keeps the judge's host steady across image
      updates.
    - uv itself is pinned well enough. setup-uv at `1c37ad07` carries a
      SHA-256 for `uv-aarch64-apple-darwin-0.9.22` and throws on a
      mismatch (EXECUTED, read `known-checksums.json` and `checksum.ts`
      at that commit).
15. **The zero-patch guard is right today, and brittle**
    (`release.yml:52-56`).
    - The step's shell is `/bin/bash -e {0}`, with no `pipefail`
      (EXECUTED, log). So `pytest … | tee` hides pytest's exit code,
      and `grep -q "^4 passed"` is the only guard.
    - It does guard against a vacuous pass. Trees that were never
      unpacked give `4 skipped`, and the grep fails.
    - But a fifth tree, if one is ever added and skipped, would print
      `4 passed, 1 skipped` and pass.
    - Fix: `set -o pipefail`, and require that nothing was skipped (or
      read `latest.json`).
    - The gap-closing check itself
      (`test_release_workflow_runs_the_zero_patch_check`) is a text
      search. It would pass if the test's name appeared only in a
      comment. It is older than this change, so it is noted here, not
      counted.
16. **The Windows branch of the cache check pins down more than spec 001
    says** (`test_v1_4_embedding.py:226-239`).
    - The docstring says "the cache under the user's own profile is
      trusted". The check uses a temporary directory, not the profile,
      and asserts it is written. So it fixes "on Windows any
      caller-given `cache_dir` is trusted". Spec 001 speaks only of the
      default cache.
    - On POSIX the check is unchanged and still tests the refusal (READ;
      it passes, EXECUTED).
    - Fix: state the Windows rule in spec 001 (a caller-given cache is
      the caller's to secure), or make the docstring match.

On the judge edits as a whole (002 Decision 7):

- **The gap removal is right.** The workflow closes the gap, and v1.5
  shows one gap, not two (EXECUTED).
- **The wiring self-test edit is right.** It still asserts something in
  both states: with a wheel in `dist/` the check must fail against the
  synthetic set; without one it must be blocked on `wheel`. Both states
  pass (EXECUTED: the local run without `dist/`, and the clone with it).
- **The new rules check and the unit tests are sound** (READ). The rules
  check imports `release/version.py`, which is not a judging file
  (Decision 14 hashes only `tests/` and the few root files). So an edit
  there can change that check's outcome without a "judge changed" line.
  That is the same as any check that reads product code, and is noted
  only.
- **The Windows-tolerant checks:** the cache check still tests its name
  on POSIX. The link check does not have to (finding 4).
- **The empty baseline in verify** weakens nothing that existed before.
  The ratchet for a release lives in the build job, and it held in run 3
  (finding 5).

## Constitution checks

- **§4.1 (zero patches).** Holds.
  - The zero-patch check is its own build step, with a guard against a
    vacuous pass. Run 3: `4 passed` (EXECUTED).
  - The release tooling sits outside `scripts/`, so it is not a recipe
    line (READ, Decision 4). No upstream tree is touched.
- **§4.2 (every input pinned).** Partly.
  - Every action is pinned by commit, and each SHA is the release named
    beside it (EXECUTED, `gh api repos/<r>/commits/<tag> --jq .sha`):
    - `actions/checkout` v7.0.1 → `3d3c42e5…`
    - `astral-sh/setup-uv` v10.3.0 → `1c37ad07…`
    - `actions/upload-artifact` v7.0.2 → `cf430e03…`
    - `actions/download-artifact` v8.0.2 → `9000827c…`
    - `pypa/gh-action-pypi-publish` v1.14.2 → `dc37677b…`

    Each is its repository's latest release.
  - uv is pinned by version and checked by hash through the pinned
    action (finding 14).
  - The build's own downloads are verified (`…: OK` lines, EXECUTED).
  - **hatchling is not pinned** (finding 3).
  - The judge's Python, and the verify step's `wasmtime>=49,<50`, float.
    They are test-time inputs, not shipped ones (finding 14).
- **§4.6 (no `.cwasm`; nothing large in git).** Holds.
  - EXECUTED: the `.tar.xz` lists exactly the set: the two binaries, the
    zip, `MANIFEST`, `SHA256SUMS` and nine licences, all mode 0644, owner
    0. The wheel holds the package, the same set and its metadata. Zero
    `.cwasm` in either.
  - `git ls-files` shows no `.wasm`, `.cwasm`, `.zip`, `.whl` or
    `.tar.xz`. `.gitignore` covers `src/wasi_python/artifacts/`,
    `dist/` and `*.tar.xz` (EXECUTED).
- **Nothing in a release that the pinned build did not make.** Holds,
  with finding 3's backend as the exception.
  - The set is built, judged and packed in one job.
  - Verify's `test_sha256sums_match_the_files` rejects any file not in
    the set's `SHA256SUMS` (READ, `tests/harness/artifacts.py:26-44`).
  - `wheel_errors` checks only one way, set ⊆ wheel. Extras in the wheel
    would not be caught. The run-3 wheel has none (EXECUTED).
- **§4.10 (claims carry evidence).** Mostly holds.
  - Findings 7 and 13 correct two figures in the notes.
  - The changelog's "1.3 to 2.3 times slower" traces to
    `context/research/2026-10-16-the-spike-that-proved-the-build.md`
    (READ). That measured the spike, not this pinned build.
- **§4.12 (licences ship with the artifact).** Does not fully hold for
  the release (finding 1).
  - Licences are in both assets (EXECUTED): nine files under `LICENSES/`
    in the `.tar.xz` and in the wheel, plus the project's own `LICENSE`
    in the wheel's metadata.
- **§4.13 (tooling).** Holds: ruff and pytest are green (EXECUTED). No
  dependency was added.
- **§4.14 and §7 (git, release, PyPI).** Nothing tripped.
  - The three draft commits were pushed on the owner's instruction (the
    spec's header).
  - No tag was pushed, and no release exists. Runs 1 to 3 are
    `workflow_dispatch` on main, with publish and pypi skipped
    (EXECUTED).
  - `release` prints the push command, and pushes only with `--push`.
  - pypi is gated on a variable the owner sets. But see finding 2: a
    dispatch on a tag would publish without a new instruction.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-16. A fourth dry run checks the workflow edits (its URL is in
the landing notes).

1. **Fixed.** HACL\*'s MIT notice, the header comment of
   `Modules/_hacl/Hacl_Hash_SHA2.h` as CPython ships it, is now a part of
   `LICENSES/cpython.txt`. `assemble_artifacts.py` fails if that header stops carrying the
   notice. New check: `test_cpython_notice_covers_hacl`. I also looked for other bundled code
   that `Doc/license.rst` leaves out: expat, libmpdec and mimalloc each have a section there
   (READ); HACL\* was the one gap.
2. **Fixed.** `publish` and `pypi` now require `github.event_name == 'push'`.
3. **Fixed.** `uv build` takes `--build-constraints release/build-constraints.txt
   --require-hashes`, where hatchling 1.32.4 and its five dependencies are pinned with hashes
   by `uv pip compile`. The source is `release/build-backend.in`. Every checkout sets
   `persist-credentials: false`, and publish runs `uv run --no-project`.
4. **Fixed.** On POSIX the check requires the guest to print `linked`. Elsewhere the escape is
   still attempted wherever the host allows it.
5. **Fixed.** A verify step reads `latest.json` and fails unless the needs that blocked any
   check are within {oracle, three systems, wheel}.
6. **Fixed.** On a tag, the build job runs `git merge-base --is-ancestor "$GITHUB_SHA"
   origin/main` after a full-history checkout.
7. **Answered, and the notes are corrected.** The build job's ratchet passed on runs 2 and 3,
   so fuel on the build runner has matched the accepted figures twice. Should it ever go red
   on runner variance alone, the fix belongs in the judge: compare fuel only between runs
   with the same `host` hash, which history already records (spec 002). That is a judge
   change of its own. The landing notes now give both of run 2's figures.
8. **Fixed.** The `run` extra is `wasmtime>=49,<50`, and verify installs
   `wasi-python[run] @ <wheel>`, so the published extra is what gets tested.
9. **Fixed.** `bump` computes both edits before writing either. Unit test:
   `test_bump_writes_both_files_or_neither`.
10. **Fixed.** `release` ignores untracked files and names the tracked files with
    uncommitted changes.
11. **For the owner.** Registering the name on PyPI is the owner's step; the author raises it
    with the owner.
12. **Fixed.** The fallback re-raises unless `os.name == "nt"`. Every non-Windows platform
    keeps the original error.
13. **Fixed in the notes.** They now cite the reviewer's byte-for-byte rebuild of run 3's
    assets, and the new wheel hash after the HACL\* change.
14. **Fixed.** `UV_LOCKED=1` and `UV_PYTHON=3.14.2` are set for the whole workflow. `uv.lock`
    is refreshed for the extra's new bound.
15. **Fixed.** The step uses `set -o pipefail` and matches `^4 passed, N deselected in`. A
    fifth tree would print 5 and fail the step, so the step must then be updated.
16. **Fixed.** The docstring now says what spec 001 says: the runner makes no ownership check
    on Windows, and the default cache is under the user's profile.

## Verdict

The machinery does not land yet. Fix findings 2, 3, 4 and 9 first (each
a few lines), and answer the rest in writing. Do not cut v0.1.0a1 until
finding 1 is settled and the HACL\* notice ships in the set's licences.
Everything else checks out: the build reproduced on a second host,
three systems ran green, and the assets rebuilt byte for byte here.
