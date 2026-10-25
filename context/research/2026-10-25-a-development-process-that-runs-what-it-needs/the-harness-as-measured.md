# How the test harness works, as it stands on 2026-10-25

A reader agent's report (Claude Opus, 2026-10-25), read-only, for the memo beside this folder. Labels: EXECUTED (run here, on darwin-arm64: collect-only, the rules file alone, one small unit file, and the fast-tier goal checks once with an empty artifact folder, every record to the scratchpad), READ (a document, a log under `build/`, or the code), INFERRED (reasoning).

## 1. Tiers, markers and goals

A **goal check** is a test marked `goal("<area>")`; the plugin judges these. An unmarked test belongs to the "unit suite", counted on its own line and never ratcheted. `slow` marks the golden guest jobs, the oracle and the upstream group checks. A **release-tier check** is one of the upstream rows listed in `tests/upstream/*.toml`; a normal-tier run deselects every one of them, even when named by node id.

| Command | Collected (EXECUTED) | Goal checks | Unit tests | Left out |
|---|---|---|---|---|
| `uv run pytest -m "not slow"` (fast tier) | 3,184 of 4,345 | 715 | 2,469 | 885 release-tier, 229 upstream normal groups, 47 golden jobs |
| `uv run pytest` (normal tier) | 3,460 | 991 | 2,469 | 885 release-tier |
| `uv run pytest --tier=release` | 4,345 | 1,876 | 2,469 | nothing |

**Found (EXECUTED):** the form the documents give, `uv run pytest [-n 3] --tier release …`, fails at once with `unrecognized arguments: --tier`, exit 4: with no path argument, `release` is read as a path, so `tests/conftest.py` never loads and nothing registers the option. `--tier=release`, or adding `tests`, works. CI always uses the `=` form.

Areas on the scoreboard (READ, scoreboard.py): v1.1 artifact set 48 checks; v1.2 portable and sealed 176; v1.3 data stack 1,293, of which 1,116 upstream; v1.4 embedding 231; v1.5 rebuild from pins 53; rules 75. G1 to G7 are the CI gather's goals (gather.py): G1 every shard's record handed on, one to one, the tier right; G2 each record tied to the build's `python.wasm` and `SHA256SUMS`; G3 each shard ran exactly its share and the shares cover the judge; G4 nothing failed, unit tests included; G5 every row matches `accepted.json`, fuel within 1e-4 on darwin; G6 the probe passed on three systems; G7 the newest acceptance is on this artifact and this set, clean and not partial. The shard plan (READ): 256 shards, 229 release-only, 18 Linux-only, 5 on all three systems, `own-rest` on macOS and Linux, one each for build, macOS and Windows.

## 2. The ratchet and the acceptance flags (READ)

`accepted.json` holds, per check: status, commit, artifact hash, metrics keyed by platform, and the hash of all 597 judging files. The history is append-only and hash-chained, 97 lines in two volumes. Every stored metric is keyed `darwin-arm64`: 801 checks record fuel and passes, 261 fuel only, 3 bytes. **So the fuel ratchet only bites on a darwin host**; on Linux or Windows fuel is recorded and not compared.

A run is red on: a lost pass; an absent check; `fewer` (an upstream group's passes fell); `GREW` (fuel up by more than 0.01% on the same platform and wasmtime version, any rise in bytes, a metric no longer recorded); unrun (an accepted pass blocked by a protected need, unless `--partial`); `moved` (a check changed tier); anything steering pytest from outside the judge; a malformed gaps file.

| Flag | What it guarantees | What it costs |
|---|---|---|
| `--accept "<r>"` | The run is recorded only when green and nothing was lost; refused in a linked worktree, on a dirty tree, or when HEAD moves during the run. | Only the lane, in the main tree, on a detached HEAD. |
| `--accept-judge "<r>"` | A change to any judging file is named in the history. The judge is everything under `tests/` plus `pyproject.toml`, `uv.lock` and every conftest. | **96 of 97 history lines carry a judge reason**: the flag is given on almost every landing. |
| `--accept-growth "<r>"` | Fuel or bytes cannot rise quietly; without it a metric only moves down. | A written reason per rise; 33 of 97 lines carry one. |
| `--accept-fewer-passes "<r>"` | A drop in upstream passes is never carried by a growth reason. | A separate flag and reason. |
| `--partial "<r>"` | A machine without artifacts can still accept, and says so. | 0 of 97 lines use it; G7 refuses a partial acceptance for a release. |
| `--accept-tier-move`, `--retire` | Moving or dropping a check is explicit. | One reason per change. |

The judge hash is the SHA-256 over the paths and hashes of every judging file plus any stray `conftest.py`; computing it costs 0.11 s (EXECUTED). Sameness compares two run records of one commit on status, need, area, closer, facts, bytes, passes, fuel beyond 1e-4 on darwin only, the deselected list, the collected files and the unit tally; `--claims` filters differences a specification's claim block explains.

## 3. Kinds of check (counts EXECUTED; times READ from `build/*.log`)

| Kind | Where | Count | Time |
|---|---|---|---|
| Product checks: guest and runner behaviour under wasmtime | `tests/checks/test_v1_*` except upstream | 800 goal checks (fast tier 639, plus 47 golden jobs and the oracle) | CI Linux own-embedding 5m58s; own-guest 12m47s on Windows |
| Runner unit tests | `tests/test_api.py`, `test_runner_*`, `test_cli`, `test_tools`, … | about 879 | CI own-runner 56 s Linux, 80 s Windows |
| Build-tooling unit tests | `test_build_*`, `test_pins`, `test_patches`, `test_set_key`, … | about 373 | inside own-rest |
| Judge-of-the-judge: tests of the harness itself | `test_plugin`, `scoreboard`, `history`, `gather`, `sameness`, `shards`, `tiers`, `upstream`, `several_cores`, `landing_lane`, `scan` (293), `wrap` (106), `regrtest`, `packages`, … | about 1,217 | own-rest (rules plus these, 1,784 tests) 4m42s Linux, 5m53s macOS |
| Rules: lint of the repository's own documents and code shape | `test_rules.py` | 74 checks from 57 functions | 33.6 s, 19.4 s of it one guest run (EXECUTED) |
| Upstream suites: the packages' own tests inside the guest | `test_v1_3_upstream_suites.py` | normal 229 slow plus 2 fast; release tier adds 885; sympy 343, scipy 174, statsmodels 52, scikit-learn 39, contourpy 25, cpython 18, … | normal minus fast about 6 min at `-n 6`; release tier about 1h27m at `-n 6` |

Whole runs (READ, logs, `-n 6`): fast tier 9m02s to 10m27s (2026-10-22 and 10-23); AGENTS.md still says 3m48s, a figure from 2026-10-18 when the fast tier had 2,009 tests; normal tier 15m26s; release tier 1h27m47s; one CI release-tier run 91 min to its last job. Of the 1,876 goal checks, 1,577 are accepted passes and 297 accepted gaps; every gap is an upstream class, trap, host or environment row, none a product or rules check.

## 4. What needs the artifact set (EXECUTED)

The fast-tier goal checks with `WASI_PYTHON_ARTIFACTS` set to an empty folder, at `-n 3`, took 4m16s. 150 of 715 passed without artifacts: rules 72; rebuild-from-pins 51 (9 of its 24 functions need build-tree records or source trees); embedding 14; public API 11; 1 artifact-set and 1 upstream check. 268 were blocked (snapshot binary 129, plain binary 104, stdlib zip 21, manifest 12). 297 failed instead of blocking, 190 of them with `ArtifactsMissing`: the `artifact dir` need is met by the variable being set at all, so a wrong path shows as red, not blocked (spec 002's "no silent fallback"). The judge-of-the-judge and build-tooling unit tests (about 1,590) are pure Python under pytester (INFERRED from the code); runner unit tests start guests. No CI job runs pytest without the build or a cached set: every judge job waits on `build` (READ).

## 5. The rules checks (READ)

| Group | Checks | Protects |
|---|---|---|
| Release and supply chain (about 21 functions, about 40 checks) | the wheel carries every component licence; carried patches hashed, drafted and in the CHANGELOG; no artifact or large file tracked; prior-art licence recorded; build scripts call Python only through uv; mypy strict; the release attests and verifies; it signs what the build made; actions pinned by commit; the release check refuses other bytes (9 cases); the id guard (4); set reuse only on a branch (7); the set key names every build input; every build host has its input table; the rename and readdir guards match the floor; native compile with fallback; the pre-import list is the stdlib bootstrap; `-V` states the platform; the version released by the book; generated doc pages current | **The product** |
| Code shape, structural (14) | no name bound twice; module ≤1,500 lines; function ≤80 lines; no module-level lock or mutable outside `_process.py`; wasmtime private API only in the seam; that debt documented; filesystem imports; platform chosen once; tests patch the runner only through the process object; the API lists every module; handlers change the table only through its methods; ruff check; ruff format | Maintainability; indirectly the product |
| The judge's own integrity (10) | no test reads a clock; known gaps well formed; history intact; the newest acceptance sits on its commit; the clean-acceptance key is in the judge; main is linear; shards cover the judge; every package names its suite; the release judges in shards; the oracle's lock | The ratchet's trustworthiness |
| Writing and process conventions (12) | code outside `src/` names no `context/` document; strings name none; `src/` names none; no embedder name in code or public pages; specification header and sections; no open question; landed specifications cite a review; a release has its structural review; built structural specifications cite a pre-build review; Markdown paragraphs one line each; README codecov badge; executed memos label their claims | **Writing conventions** ("no embedder name" is closer to a confidentiality rule) |

**Found (EXECUTED):** on `research/performance-specs-2026-10-24`, `test_markdown_paragraphs_are_one_line_each` fails on 14 findings in `context/research/2026-10-24-moving-to-wasmtime-50/wasmtime-49.0.4-notes.md`, so the fast tier is red there, and only because of a writing rule.

## 6. Known gaps and `--partial` (READ)

A gap is an allowed, named failure: a strict xfail whose message must carry `N finding(s), digest <12 hex>`; one that fails differently, passes while listed, or has no entry is red. 266 of the 297 gaps close with `docs/reference/limitations.md`. On a machine without artifacts the product checks are blocked; accepted passes blocked by a protected need are unrun, red unless `--partial`; `--accept` also refuses while any accepted upstream row did not run. In CI a block is allowed only for the needs CI lacks (`CI_NEEDS`).

## 7. Overlaps and per-run overheads (described, not judged)

- **Fuel is guarded three times**, at the same 1e-4 tolerance and on darwin only: the local ratchet; CI G5 against `accepted.json`; sameness between the lane's record and a reviewer's or the dry run's. Lost passes: the local ratchet, G4 and G5, and sameness. Same bytes: the `same-bytes` job, G2 and G7, and the `bytes` metric.
- **The rules run in every tier**: every local fast tier; every CI run on macOS and Linux inside own-rest (4 to 6 min); the lane's step 5 again.
- **The judge's own tests outnumber the runner's**: about 1,217 against about 879, including 106 for the Markdown wrapper.
- **`--accept-judge` is near-universal** (96 of 97): its reason no longer tells one landing from another.
- **Per-run costs (EXECUTED):** a 5-test file takes 1.6 to 2.8 s end to end; judge hash 0.11 s; the host-litter scan 0.85 s over 5,837 sealed folders (4.6 GB) in `build/harness`; 36 worktrees inside the repository add 36 notes to every record.
- **The fast tier has grown** from 2,009 to 3,184 tests and from 3m48s to about 9 min at `-n 6`.

One line: the judge stacks ratchet, gather and sameness to guard the same few facts (passes, darwin fuel, bytes); about 150 of 715 fast goal checks plus about 1,590 pure-Python unit tests run without artifacts; the documented `--tier release` form fails to parse; and the research branch's fast tier is red on a Markdown wrapping rule.
