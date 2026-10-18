# Review of 057 — The release ties what it signs to what it built (build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude). It wrote none of the specification, its pre-build review
  or its build.
- **Reviewed:** `git diff c6cdd86 8290c20` on `spec/057-the-release-ties-what-it-signs-to-what-it-built`
  (`e579da3` the build, `8290c20` the rebase onto 059): 38 files, +3,344 −221. Read against the
  specification as confirmed (`bab6b79`), its pre-build review (F1 to F7) and Confirmation (N1;
  M1, M2, M5, M6), its landing notes with "Rebased onto 059", the 0.1.0a4 security review's F4,
  N1 and N3 with the 0.1.0a5 addendum, spec 059, and main's `release.yml`.
- **Re-ran** (in the worktree, against the builder's own rebuilt set in `build/artifacts`,
  `SHA256SUMS` `c353b1d9e59304c9…`; it differs from main's frozen set `s-4eb5418a2b1bb553`
  (`25a101ac…`) only in `MANIFEST`'s line for `scripts/00_download.sh`, EXECUTED by `diff`):
  - `uv run pytest -m "not slow" -n 3` → **1584 passed, 10 skipped in 244.57s**, exit 0.
    Scoreboard `367/416 pass · 0 gap · 3 blocked · 0 fail · 46 deselected`; v1.5 31/31, rules
    40/41. Ratchet vs `fdb06c26f1`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 19 ·
    grew 0 · … · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_5_rebuild_from_pins.py,
    tests/harness/scan.py and 1 more` (`judge-fast-reviewer.txt`). It equals the builder's line.
  - `uv run pytest` (full, serial) → **1596 passed, 42 skipped, 2 xfailed in 367.93s**, exit 0.
    Scoreboard `379/416 pass · 2 gap · 35 blocked · 0 fail` (upstream kit 31, oracle 1, prior-art
    clones 1, three systems 1, wheel 1). Ratchet vs `fdb06c26f1`: `lost 0 · absent 0 · unrun 0 ·
    unrun locally 21 · gained 19 · grew 0 · upstream unrun 31 · judge changed: …`
    (`judge-full-reviewer.txt`). It equals the builder's `judge-full-059.txt`.
  - `uv run ruff check src tests` and `uv run ruff format --check src tests` → "All checks passed!", "90 files already formatted".
  - The mutations: the real `scan` functions and the judge's own behaviour cases, on in-memory
    copies of the workflow (`mutate_review.py`, `mutations-review.log`).
  - The download fix: the real script on the real pinned files, symlinked into a scratch
    repository, with zlib's pin removed, on the branch's script and on main's (`n1_probe.sh`,
    `n1_probe.log`).
  - The workflow parsed with PyYAML 6.0.3 in a throwaway environment (`yaml_facts.py`,
    `yaml_facts.log`), and every copy of the check step run under two hash tools
    (`check_tools_probe.py`, `check_tools_probe.log`).
  - No workflow was dispatched. The git tree is untouched (`git status` clean).

## Acceptance criteria against evidence

1. **Seen failing first** — met, with one justified departure. READ: `seen-failing-checks.txt`
   and `seen-failing-binding-rules.txt` (42 findings, rules 1, 2, 3, 4×9, 5×9, 7×3, 10×9, 12,
   13×4, 14×4). The 13 behaviour cases raise `LookupError`; the 3 download cases exit 0 with
   zlib's pin gone; the rebuild gate names both missing jobs. EXECUTED here: main's own script
   with zlib's pin removed exits 0 on the real pinned files (`n1_probe.log`, `[main]`). The
   departures (rule 8 not among the 42; the run on main's tree rather than `d70690a`'s) are
   judged below.
2. **19 new checks pass** — met. EXECUTED: the fast tier's ratchet says `gained 19`, and v1.5 is
   31/31. The rewritten `test_release_workflow_rebuilds_on_two_more_hosts` and the unchanged
   `test_releases_attest_and_verify_their_assets` pass.
3. **The unit tests** — met. 141 in `test_scan.py`, all green in the fast tier. M1, M2, M5 and M6
   are there by name (`test_scan.py:739`, `:751`, `:761`, `:914`), as are the seven refused
   `with:` keys, `gh run download`, `actions/github-script`, the display-name variant, the pin
   variants and the fetched-pin variant.
4. **The workflow parses** — met. EXECUTED: PyYAML 6.0.3 loads it; `on:` is the tag push and
   `workflow_dispatch`; top-level `permissions: {}` (`yaml_facts.log`).
5. **The judge** — met in the worktree (lines above). The lane accepts with `--accept-judge`.
   No fuel or byte growth. But see finding 3: the lane cannot judge this commit against main's
   frozen set.
6. **The dry run after landing** — not yet run, rightly (the lane's, after landing; rule 6b).
   The workflow can be dry-run as is (below).
7. **The first tag run after landing** — 0.1.0a6's record, not this landing's.

## What I re-applied (EXECUTED)

Each mutation goes to all four release scans (`release_binding_errors`, `rebuild_gate_errors`,
`release_attestation_errors`, `action_pin_errors`). Mutations of the check or guard step also go
to the judge's own behaviour cases (`test_rules.CHECK_CASES`, `GUARD_CASES`), run on the mutated
`attest` scripts. The real workflow: every scan `[]`, every case right.

**The builder's six, and two more of the same kind — all caught:**

- M1 (`X86_64_WHEEL_ID` bound, not looped) → rule 10.
- M2 (`continue-on-error` on the rebuild guard) → rule 15.
- M5 (the x86_64 `sums-id` into `rebuilds/ubuntu-24.04-arm`) → the rebuild gate.
- M6 (`continue-on-error` on `publish`'s check) → rules 9 and 15.
- The guard removed from `attest` → rule 10, and every guard case raises `LookupError`. From
  `publish` → rule 10.
- A download by name in `pypi` → rules 4, 10 and 7. In `attest`, guard kept → rules 4, 10 and 7.

**My own, aimed at the property "no job signs, attests or publishes bytes other than those the
build job made and the verify jobs checked":**

| | mutation | result |
|---|---|---|
| R1 | `attest`: after its check, a guarded by-id download of `rebuild-linux-arm64`'s `sums-id` into `release-assets` (with that job added to `needs`) | **missed** (finding 1) |
| R1b | `publish`: the same, before `gh release create` | **missed** (finding 1) |
| R1c | `attest`: a `run:` step after the check writes `release-assets/NOTICE` | missed (note N2) |
| R2 | `pypi` `needs: [build]` (drops `publish`) | **missed** (finding 2) |
| R3 | `pypi` `if: always() && …` | **missed** (finding 2) |
| R3b | `pypi` `if: vars.PYPI_PUBLISH == 'true'` (no tag condition) | **missed** (finding 2) |
| R4 | `verify` job-level `continue-on-error: true` | **missed** (finding 2) |
| R5 | `build`: `continue-on-error: true` on "The judge" | **missed** (finding 2) |
| R6 | both rebuild jobs upload as `release-assets`, `overwrite: true` (a name collision) | caught by the rebuild gate; at run time it fails closed (N3) |
| R7 | `verify` re-uploads `release-assets` with `overwrite: true` | missed by the scans; fails closed at run time (N3) |
| R8 | `attest` `if: always() && …` | caught (spec 009's exact `if:`) |
| R9 | `publish` `needs: [build, attest]` | caught (`publish does not need same-bytes`) |
| R10 | `same-bytes` job-level `continue-on-error` | caught (the rebuild gate) |
| R11 | every check drops `-c ../SHA256SUMS.sha256` alike (rule 9 still holds) | caught by two behaviour cases |
| R12 | every check drops the no-other-file `exit 1` alike | caught by three behaviour cases |
| R13 | every guard defaults its id to `1` before its `case` | caught by the guard's empty case |
| R14 | `build` hashes `SHA256SUMS` after the upload | caught (rule 2) |
| R15 | `build` hashes `build/artifacts/SHA256SUMS` instead | caught (rule 2) |

So the binding itself is well defended. The scans and the behaviour cases together catch every
weakening of the guard, the check, the hand-off and the downloads. What gets through is (a) more
bytes fetched into `release-assets` after the check, and (b) the gate around `pypi` and the
`continue-on-error` keys outside the rebuild and attest jobs.

**The download fix** (`n1_probe.log`; the real script, the real 45 pinned files, a `curl` that
exits 99):

- branch, every pin → exit 0, `downloads: 45 pins, 0 fetched, 45 verified; 1 other file …`;
- branch, zlib's pin removed → **exit 1**, `ERROR: no pin in downloads/SHA256SUMS for: zlib-1.3.1.tar.gz`;
- main, zlib's pin removed → exit 0, `44 verified`, no error. That is N1, as the a4 review saw it.

**The check step's tools** (`check_tools_probe.log`): all five copies (`same-bytes`, `verify`,
`attest`, `publish`, `pypi`), each under `/sbin/sha256sum` and under perl's `shasum` only →
9 of 9 cases right in all ten runs.

**The action's own source** (`build/reviews-evidence/057-review/src/dl-download-artifact.ts`, the
pinned v8.0.2 as the pre-build review saved it, READ): one id → `artifacts.length === 1` → the
files land in `path` itself (lines 190-194), so `release-assets/` holds the files directly, as the
check expects. A by-id download lists `latest: true` and filters by id (lines 126-137), so a
deleted or replaced artifact gives "None of the provided artifact IDs were found". `parseInt`
reads `12x` as 12 (line 118), which is why the guard matters.

## Per-job permissions, environments, cache (EXECUTED, `yaml_facts.log`)

| job | `needs` | `if:` | permissions | environment |
|---|---|---|---|---|
| `build` | — | — | `contents: read` | — |
| `rebuild-linux-arm64` | — | — | `contents: read` | — |
| `rebuild-linux-x86-64` | — | — | `contents: read` | — |
| `same-bytes` | build, both rebuilds | — | `{}` | — |
| `verify` | build | — | `contents: read` | — |
| `attest` | build, verify, same-bytes | pushed tag | `id-token`, `attestations: write`; `contents: read` | — |
| `publish` | build, verify, same-bytes, attest | pushed tag | `contents: write` | `release` |
| `pypi` | build, publish | pushed tag and `PYPI_PUBLISH` | `id-token: write` | `pypi` |

Top-level `permissions: {}`. All five `setup-uv` steps carry `enable-cache: false`. No `${{` in
any `run:`. Every `uses:` is a 40-hex commit (`action_pin_errors` → `[]`). No step anywhere in
the workflow carries `continue-on-error:`, and the only step `if:`s are the three
`failure()` log uploads. Each matches Decision 6's table and rule 14.

## 059's guarantees

- 059's checks are green in both runs: `test_every_compile_contracts_nothing`,
  `test_every_host_compiles_natively_with_the_fallback_kept`, and the rebuild gate.
- `REBUILD_JOBS` keeps what `REBUILD_TIMEOUTS` held, and is stricter. Main's rule read the
  minutes from the matrix's `include:` rows (`given.get(r) != str(minutes)`). The new rule
  requires each job's own `runs-on` and `timeout-minutes` exactly: 120 and 120. `_rebuild_shape`
  sets the time limit aside only for the same-text comparison; the table still pins it.
  `REBUILD_TIMEOUTS` had no other reader (EXECUTED: `grep` over `tests/` on main finds it only
  in `scan.py`).
- The job steps are byte-identical but for the runner (the rebuild gate's shape rule). Neither
  carries the emulated compiler. Which SDK a host uses is `line.conf`'s, checked by 059's
  `compiler_table_errors`, which this change does not touch. So "each vote rests on its own
  host's compiler" (Decision 4) holds as 059 left it.
- Main's README line "the x86_64 rebuild compiles under emulation …, up to six hours" was stale
  after 059. The rebase replaces it with "each job compiles with its own host's pinned clang …
  two hours". Right.

## Can the workflow be dry-run as is?

**Yes.** A `workflow_dispatch` run never signs or publishes:

- `attest` and `publish` have `if: github.event_name == 'push' && github.ref_type == 'tag'`, and
  spec 009's scan pins that text exactly (R8 caught). `pypi` adds `vars.PYPI_PUBLISH == 'true'`,
  and it also needs `publish`, so a skipped `publish` skips it.
- No `if:` contains `always()`, `failure()` or `cancelled()` at job level. So the implicit
  `success()` holds, and a skipped or failed need skips the job (INFERRED, GitHub's documented
  default).
- `environment: release` is on `publish` only. A dry run never reaches it, so it never creates
  that environment.
- The jobs a dry run runs are `build`, both rebuilds, `same-bytes` and the three `verify` legs.
  They exercise the guard, the by-id download and the check, word for word as the publish path
  runs them (rules 9 and 10).
- Two things only a run can show: that `same-bytes`' downloads work under `permissions: {}`
  (the runtime token; the source path above uses no `GITHUB_TOKEN`), and the check step under Git
  for Windows' bash on `windows-2025` (its `find`, `sort`, `awk` and `sha256sum`). Both fail
  closed if wrong, before any signing job.

## Findings, most severe first

1. **A signing or publishing job may fetch more bytes into `release-assets` after its check,
   and the judge does not see it** (low, but in the same class as the Confirmation's M6, which
   was made a must-fix; `tests/harness/scan.py`, `release_binding_errors`, rules 7 and 8).
   - Rule 8 checks only the step after the *first* `release-assets` download. A second download
     after the check passes every scan, as long as it is by id, guarded, digest-checked, and its
     job is in `needs` (R1, R1b; EXECUTED, all four scans `[]`).
   - Concretely: `attest` adds `rebuild-linux-arm64` to `needs` and, after its check, downloads
     that job's `sums-id` into `release-assets`. That overwrites `release-assets/SHA256SUMS` with
     the rebuild's, which is a different file (it lists the set, not the wheel and `.tar.xz`).
     `attest` then signs it, and `publish` would publish it. A rebuild host's output is exactly
     what F4 distrusts. The same move in `same-bytes`, with a rebuild's `wheel-id`, would make
     spec 016's wheel comparison compare a rebuild with itself.
   - It needs an edit to the workflow, which is reviewed. But catching such an edit is what this
     judge is for. Its own docstring says each reader "acts on nothing else", and Decision 3 says
     the check runs "right after the download", before the job acts.
   - **Fix (a few lines, two unit variants):** a rule 16: every `actions/download-artifact` step
     whose `path:` is `release-assets` (or lies under it) has `artifact-ids:` equal to
     `needs.build.outputs.assets-id`; and in every job of rule 7 except `same-bytes`, that
     download is the job's only `actions/download-artifact` step. Add R1 (`attest`) and the
     `same-bytes` wheel variant as unit cases.

2. **The judge does not hold `pypi` behind the gate, and allows `continue-on-error:` in `build`
   and `verify`** (low; pre-existing on main, outside the letter of the specification, but on
   the property it serves; `release_attestation_errors`, `release_binding_errors`).
   - R2: `pypi` with `needs: [build]` passes every scan. On a tag, it would upload the wheel to
     PyPI as soon as `build` ends, before `verify`, `same-bytes` and `attest`, or after they
     failed. Its check still ties the wheel to the build job, so this bypasses the gate, not the
     binding.
   - R3, R3b: `pypi`'s `if:` is not checked. With `always()` it runs after a failed `publish`.
     Without the tag condition, joined with R2, a `workflow_dispatch` dry run would reach PyPI.
     Spec 009 pins `attest`'s and `publish`'s `if:` exactly, but not `pypi`'s.
   - R4: a job-level `continue-on-error: true` on `verify` passes every scan. Then a failing leg
     would no longer stop `attest` (INFERRED, GitHub's documented job behaviour). R5: the same on
     `build`'s "The judge" step would upload and sign bytes the judge failed.
   - This specification already touched `pypi`'s `needs` (Decision 2) and checks its
     `environment` (rule 12), so the cheap closure fits here.
   - **Fix:** `release.yml` holds no `continue-on-error:` anywhere (it holds none today; this
     covers R4, R5, M2 and M6 in one line). `pypi`'s `if:` is `TAG_ONLY + " && vars.PYPI_PUBLISH
     == 'true'"` exactly, and its `needs` holds `publish`. One unit variant each. Or name it as a
     follow-up in the landing notes and the CHANGELOG, with its reason.

3. **The specification and the CHANGELOG say no artifact changes; `MANIFEST` does, and so does
   the wheel** (low, documentation and a lane hazard; spec header *Kind*, Decision 11,
   `CHANGELOG.md`).
   - *Kind* says "It changes no artifact". Decision 11 says "no artifact rebuild; the frozen set
     judges it". The CHANGELOG says "Nothing in the artifact set or the wheel changes".
   - But `MANIFEST` is one of the set's four artifacts (AGENTS.md: "the artifact set
     (`python.wasm`, the snapshot, the stdlib zip, the manifest)"). It records the recipe hash
     of `scripts/00_download.sh`, which changed: `d4627461…` → `4ca18e92…` (EXECUTED, `diff`). So
     the set's `SHA256SUMS` changes (`25a101ac…` → `c353b1d9…`), and the wheel carries both
     files.
   - Against main's frozen set, `test_manifest_recipes_match_the_tree` fails on this commit
     (EXECUTED: `WASI_PYTHON_ARTIFACTS=<main's build/artifacts>` → 1 failed, "stale artifact:
     scripts/00_download.sh changed since the build"; `manifest-vs-main-set.txt`). The landing notes already say the set was rebuilt. But the frozen
     set's name, `s-4eb5418a2b1bb553`, comes from the snapshot's hash, which did not change. So
     after landing, two different sets carry the same name.
   - **Fix:** amend *Kind* and Decision 11 to say `MANIFEST` (and so `SHA256SUMS` and the
     wheel) changes in one line, and `python.wasm`, the snapshot and the zip do not. Reword the
     CHANGELOG line the same way. Say in the landing notes that the lane rebuilds in the main
     tree (§5.7) and records `SHA256SUMS` `c353b1d9…` beside the set's name.

## Notes

- **N1. A dry run before landing is possible, and cheap.** The workflow is safe to dispatch on
  any ref: no signing or publishing job can run outside a pushed tag. A dispatch on the branch
  (`gh workflow run release.yml --ref spec/057-…`) would prove the Windows leg and
  `same-bytes`' `permissions: {}` before main carries them. It needs the branch pushed, which
  §4.14 leaves to the owner. Otherwise, criterion 6's dry run after landing does the same, and
  rule 6b keeps the tag behind it.
- **N2. What a text scan cannot reach.** A `run:` step between the check and the act can still
  change `release-assets` (R1c). In `publish`, "Create the release" runs `uv run --no-project`,
  which fetches uv's managed Python, between the check and `gh release create`. Both run in the
  same job and under its own token, so they are not F4's cross-job path, and both predate this
  change. An optional tightening: in `attest`, the step after the check is `actions/attest`.
- **N3. Collisions and re-uploads fail closed** (R6, R7; READ, the action's source). Any job
  holding the runtime token can delete the build's artifact, or replace it under the same name
  with `overwrite: true`. Either way the id the build job handed on is gone, and every later
  download throws "None of the provided artifact IDs were found". The worst a compromised host
  can do is stop the release. Decision 4 says so.
- **N4. One output-shaped gap stays by design.** A compromised rebuild host can read the build's
  artifact in its own run and upload a copy of the set's `SHA256SUMS` as its own vote. That is
  one vote. The other job's vote is its own (Decision 4), and since 059 no compiler input runs in
  both.

## The departures

- **Departure 1: `REBUILD_TIMEOUTS` removed, `REBUILD_JOBS` in its place.** Accepted. Same limits
  (120 and 120), stricter form (exact `runs-on` and `timeout-minutes` per job), no other reader,
  no 059 check edited.
- **Departure 2: main's stale README line removed.** Accepted. It contradicted 059.
- **Rule 8 not among criterion 1's 42.** Accepted. Rule 8 cannot fire until some job downloads by
  id; rule 7 names those jobs first, and rule 8 is seen failing on its unit variant.
- **Criterion 1 run on main's workflow, not `d70690a`'s.** Accepted. The rebase moved the base;
  the release path's files did not change between the two in any way that touches the rules
  (the 42 findings are the ones the specification expects, plus rule 8's explained absence).
- **The check step's behaviour cases use a fixed `PATH`.** Accepted, and widened here: all five
  copies pass under both tools.

## Constitution checks

- §4.1: holds; no source tree, no patch. §4.2: holds; no pin changes, and the download step now
  refuses an unpinned name early (N1 closed). §4.6: the set's members are unchanged; only
  `MANIFEST`'s recipe line moves (finding 3). §4.8: holds; nothing new runs outside the build.
  §4.9: no time figure in a check. §4.10: claims are labelled; the run-time ones (the runtime
  token under `{}`, Windows) are marked for the dry run. §4.13: ruff clean (above). §4.14: the
  branch is local; this review wrote nothing in git and dispatched nothing.
- §5.6: I re-ran the counted tests (fast, then full, serial) against the builder's set, checked
  each criterion and its evidence, and checked against §4 and §7.
- §5.7: build-class (`scripts/`, the release workflow). It lands alone. The lane rebuilds the set
  in the main tree and compares it with the builder's: only `MANIFEST` should differ from main's
  frozen set.
- AGENTS.md rule 6b: the first tag after landing waits on a dry run of main's exact commit
  passing on all three systems (criterion 6). Rule 9: the branch carries one specification; the
  diff touches 057's files and the three one-line amendments only.
- §7: nothing tripped. Question 97 leaves the owner's settings to the owner.

## Verdict

**Lands once finding 1 is fixed** (rule 16 and two unit variants, a few lines in
`release_binding_errors`). Finding 2 should ride along, since it is two short rules; otherwise it
is named as a follow-up, with its reason. Finding 3 is a text fix and a line in the landing notes
for the lane. The workflow, the guard, the check, the two rebuild jobs and the download fix are
sound as built, and the workflow can be dry-run as is.

## One line

The release now signs and publishes only bytes tied by id and hash to its build job, and every
weakening of that tie I tried was caught; one rule is missing, so a post-check fetch into
`release-assets` would pass the judge, and that rule should land with it.

## Confirmation (2026-10-18, against `97e562a`)

- **Reviewed:** `git diff 8290c20 97e562a`: `scan.py` (+40: rules 16, 17 and 18), `test_scan.py`
  (+7 unit variants), the specification (*Kind*, Decision 11, rules 16 to 18 in the Design,
  criterion 5, the Disposition), the CHANGELOG, and the revision's evidence. The workflow, the
  download script and the set did not change.
- **Re-ran** (in the worktree, against the builder's set, `SHA256SUMS` `c353b1d9e59304c9…`):
  `uv run pytest -m "not slow" -n 3` → **1591 passed, 10 skipped in 172.98s**, exit 0. Scoreboard
  `367/416 pass · 0 gap · 3 blocked · 0 fail · 46 deselected`, unit suite 1224/1231. Ratchet vs
  `fdb06c26f1`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 19 · grew 0 · … · judge
  changed` (`judge-fast-confirm.txt`). ruff check and ruff format --check are clean. I did not
  re-run the full judge. Only judge files changed since my full run, the fast tier runs every
  scan and unit test they touch, and nothing below raised a doubt.
- **My mutations, re-run** on a `git archive` copy of `97e562a` (`mutations-review-97e562a.log`):
  - the real workflow: every scan `[]`, every behaviour case right;
  - **R1 and R1b → rule 16. R2, R3 and R3b → rule 18. R4 and R5 → rule 17.**
  - Every earlier catch still holds (M1, M2, M5, M6, the two guard removals, the two downloads by
    name, R6, R8 to R15).
  - R1c and R7 still pass the scans, as the review expected (N2, N3).
- **Is it too broad?** (`confirm_probe.py`, `confirm_probe.log`)
  - The real workflow passes all four scans. The workflow is unchanged since the review, so a
    `workflow_dispatch` dry run runs the same jobs as before, and none of them signs or publishes.
    Rule 17 matches only a real key: a comment that says `continue-on-error:` is stripped first
    and passes. A legitimate `if: failure()` log upload added to `verify` passes too. Rule 18
    matches the real `pypi` `if:` exactly.
  - Rule 16's second clause spares `same-bytes`, whose four rebuild downloads are legitimate and
    pass.
- **What rule 16 still lets through** (nit, not blocking): its first clause compares the
  `path:` text. In `same-bytes`, an extra download spelled `./release-assets`,
  `rebuilds/../release-assets` or `${{ github.workspace }}/release-assets` passes. The plain
  spelling is caught. In `verify`, `attest`, `publish` and `pypi`, the one-download clause catches
  any spelling, so no signing or publishing job is affected. The worst case is spec 016's wheel
  comparison in `same-bytes` being weakened by a reviewed edit. Optional fix, one line: normalise
  with `posixpath.normpath` after dropping a leading `${{ github.workspace }}/`.
- **F3, fixed.** *Kind*, Decision 11, criterion 5 and the CHANGELOG now say the three binaries
  do not change, and that `MANIFEST` changes in one line, so `SHA256SUMS` and the wheel change
  too. The landing notes tell the lane to rebuild in the main tree, and to record `SHA256SUMS`
  `c353b1d9…` beside the reused name `s-4eb5418a2b1bb553`.
- **The departure in the R1 unit variant** (it reports rules 6 and 16, because the fixture leaves
  the rebuild out of `attest`'s `needs`): accepted. My exact R1, with `needs` added, is caught by
  rule 16 alone.
- **N1 to N4, answered without change:** accepted. N1's dry run waits for the lane's run on
  main's exact commit, and rule 6b keeps the tag behind that run.
- The git tree is untouched (`git status` clean). Nothing was dispatched.

**Confirmed: lands.** F1 to F3 are fixed. The rule-16 path nit may be fixed in passing or left as
it is. The lane accepts with `--accept` and `--accept-judge`, against a set rebuilt in the main
tree whose `SHA256SUMS` should be `c353b1d9…`.
