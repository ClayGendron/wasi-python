# The release workflow: a map, with measurements

A reader agent's report (Claude Opus, 2026-10-25), read-only, for the memo beside this folder. Sources: `.github/workflows/{release,set-cache,docs}.yml`, `tests/release_shards.toml`, `release/set_key.py`, specs 101 and 102, and `gh` run data. Every number names the run it came from. Labels: EXECUTED (a `gh` read), READ (a file).

## 1. Triggers

| trigger | effect |
|---|---|
| `push` of a tag `v*` | Builds on macOS. Judges the release tier. Then attest, publish and pypi (pypi only when `vars.PYPI_PUBLISH == 'true'`). |
| `workflow_dispatch` on `main` | Builds on macOS. The release tier is forced on. Nothing is published. |
| `workflow_dispatch` on any other branch | Reuses a cached set when one exists for the key. Judges the normal tier. |
| input `from-source` (bool) | Turns reuse off on a branch. |
| input `release-tier` (bool) | Turns `judge-release` on for a branch (229 legs). |

There is no `pull_request` trigger and no `paths:` filter. `concurrency: release-${{ github.ref }}` is set with `cancel-in-progress: false`: a second dispatch on the same ref waits rather than cancelling the first.

The other two workflows: `set-cache.yml` runs on push to main and on dispatch, with cancel-in-progress true; it looks up the key and on a miss compiles the set on arm64 Linux and saves it to main's cache. `docs.yml` runs on PRs and on pushes to main and tags: `mkdocs --strict` plus two "generated page is current" checks; it deploys only from a tag or a dispatch. It is the only workflow that runs on PRs.

## 2. Jobs and wall times (EXECUTED)

Three runs: **39943021050**, a main dry run with the release tier, success, 80.6 min, 281 jobs; **39957192055**, the v0.1.0 tag run, success, 85.5 min; **39732496724**, a spec/067 branch run that reused the cached set, normal tier, 36.3 min, 52 jobs, red only at the gather (G7). No green post-101 spec run built from source exists; **39715865231** (spec/067, built from source, 46.1 min, red at two fetch legs) stands in.

| job | runner | does | needs | main | tag | reuse |
|---|---|---|---|---|---|---|
| `inputs` | ubuntu-24.04 | computes the key, cache lookup, decides reuse and tier | — | 0.2 | 0.1 | 0.2 |
| `build` | macos-15 (ubuntu on reuse) | compiles or restores the set, verifies it against the key, builds the wheel, zero-patch check, release assets | inputs | 27.8 (compile 23.4, zero-patch 1.3, assets 2.1) | 28.7 | 1.6 |
| `rebuild-linux-arm64` | ubuntu-24.04-arm | compiles from the pins, uploads SHA256SUMS and the wheel | — | 19.8 | 20.8 | 19.1 |
| `rebuild-linux-x86-64` | ubuntu-24.04 | the same | — | 21.0 | **37.0** | **35.6** |
| `build-shard` | ubuntu-24.04-arm | compiles from the pins again, zero-patch check, `--shard=build` | — | 22.1 | 22.4 | 22.0 |
| `same-bytes` | ubuntu-24.04 | `cmp` of each rebuild's SHA256SUMS and wheel against build's | build, both rebuilds | 0.5 | 0.9 | 0.2 |
| `save-set` | ubuntu-24.04 | saves the set to the cache (branch run that built) | build, same-bytes | 0.3 | skipped | skipped |
| `judge-macos` ×7 | macos-15 | one shard each | build | longest 18.9 (own-guest) | 21.4 | 19.7 |
| `judge-linux` ×24 | ubuntu-24.04 | one shard each | build | longest 10.5 | 13.0 | 7.0 |
| `judge-windows` ×6 | windows-2025 | one shard each | build | longest 12.7 | 13.5 | 13.6 |
| `judge-release` ×229 | ubuntu-24.04 | release-tier shards, `max-parallel: 18` | inputs, build | +28.1 to +78.5, 830 runner-min, longest 28.0 | +29.0 to +83.4, 903 runner-min | skipped |
| `coverage` | ubuntu-24.04 | the fast tier, serial, under coverage.py, then Codecov | build | 11.2 | 15.2 | 18.1 in 39891594258 |
| `gather` | ubuntu-24.04 | merges 38 to 267 records and gives the verdict (G1 to G7) | inputs, build, build-shard, same-bytes, the judges | 2.0 | 0.6 | 0.3 (red) |
| `verify` ×3 | ubuntu, windows, macos | installs the wheel fresh, runs pandas and the CLI | build | 0.9 to 1.5 | 0.8 to 1.7 | 1.0 to 1.4 |
| `attest`, `publish`, `pypi` | ubuntu-24.04 | provenance, the GitHub release, PyPI (tag only) | build, verify, same-bytes, gather | skipped | 0.3, 0.5, 0.4 | skipped |

Critical paths: main and tag, build (+28) then the release tier, throughput-bound (168 of 229 legs start after +40; the last at +73.8), then the gather (+80.6); the normal-tier judges had all ended by +47.0, so **the release tier adds about 33 min**. A source branch run: build 26.2, then the macOS judges (+26.4 to +46.1). A reuse branch run: the judges finish at +25.4 (macOS own-guest); **the x86-64 rebuild (35.6) is the critical path**, because the gather needs `same-bytes`.

The dominant costs: the compile, 19 to 23 min each, done three or four times per run; the macOS own-guest, own-hostile and own-embedding legs, 16 to 21 min each; the release-tier fan-out, 830 to 903 runner-min throttled to 18 at a time. Runner minutes per run: 1,153 (main), 1,280 (tag), 321 (source branch), 301 (reuse branch). The x86-64 compile varies on the same runner label: 20.3 min in 39943021050, 34.8 in 39732496724.

## 3. The graph, rebuilds and the cache (READ)

```
inputs -> build -+-> judge-{macos,linux,windows}, judge-release(if tier) -+
                 +-> verify x3 ------------------------------------------+
                 +-> coverage   (nothing needs it)                       |
rebuild-arm64 ---+-> same-bytes -+-> save-set (branch, built)            |
rebuild-x86-64 --+               +---------------------------------------+
build-shard ------------------------------------------------------------+-> gather -> attest -> publish -> pypi
```

The judges run on macOS (7 legs), Linux (24) and Windows (6); `verify` on all three; the release tier on Linux only. The compiles run on macOS arm64 (`build`), Linux arm64 (`rebuild-linux-arm64` and `build-shard`) and Linux x86-64. A source run compiles 4 times, a reuse run 3 (the cached set skips only the macOS build): the two rebuilds give same-bytes votes from separate toolchains; `build-shard` needs a build tree, which a reused set has none of, and the owner chose on 2026-10-20 to run it on Linux always; `set-cache` adds a fifth compile on every push to main whose key misses. `build-shard` and `rebuild-linux-arm64` compile the same pins on the same runner type, side by side.

The cache key is `wasi-python-set-v1-<sha256>` over the five env values, `downloads/SHA256SUMS`, every tracked file under `scripts/` and `recipes/`, `release/set_key.py`, `release/build-constraints.txt`, and `tests/harness/constructors` with its local imports. It does not cover `src/`, the rest of `tests/`, or `context/`. Reuse needs a dispatch on a branch that is not main, `from-source` false, and a cache hit (the branch's own or main's). Tags and main never reuse. A reused set must still match both rebuilds in `same-bytes` before the gather.

## 4. What runs on every dispatch (READ)

Nothing selects jobs by changed paths. A change to `context/` alone, dispatched on a branch, still runs 3 full compiles, 37 judge legs, verify ×3, coverage, same-bytes and gather: about 52 jobs and 36 min. On main the same change also builds on macOS and runs 229 release legs: 281 jobs, about 80 min. The only conditional cuts are reuse (skips the macOS compile), `tier` (skips `judge-release`) and the tag-only publish jobs.

## 5. Which pieces stand alone (READ)

Pieces that depend only on `build`, and so could run on their own: the judge legs, `verify`, `coverage`. In a reuse run `build` takes 1.6 to 2.1 min, the Linux judge legs finish by +9.0, and `verify` on ubuntu takes about 1 min. Pieces that cannot: `same-bytes` needs both rebuilds (20 to 37 min); `gather` needs `build-shard`, `same-bytes` and every judge job, so no verdict exists without the compiles. The fast tier already runs as one job, `coverage`, 10.8 to 18.1 min serial.

## 6. Redundancies and oddities (READ)

- **Size.** 1,066 of 2,602 lines (41%) wire per-shard ids and sha256s by hand: 532 matrix-output lines and 534 gather env lines. The matrix lists repeat `tests/release_shards.toml`'s 256 `[shard.*]` tables; rules in `tests/harness/scan.py` hold the two equal. No generator.
- **The same verification block, copied** 11 times, about 23 lines each, after a copied "artifact id" guard.
- **Duplicate compiles:** `build-shard` and `rebuild-linux-arm64` on arm64 Linux in every run; the zero-patch check runs twice on source runs; the wheel is built three times (by design, for the comparison).
- **`coverage` re-runs the fast tier** the judge shards already cover; nothing needs it; its failure turns the run red. In 39904389018 one rule failure surfaced three times.
- **No early stop.** With `fail-fast: false`, a red own-rest at about +50 did not stop the 229 release legs; they ran to +82.3 and the gather was skipped (39904389018).
- **One absent check reds every shard.** In 39891594258 (wave/13) all 38 shards printed "RED: 1 accepted check(s) absent".
- **On reuse runs the gather waits on `same-bytes`**: the x86-64 rebuild sets the wall time even when the judges finished at +25.4.
- **Throttling.** `max-parallel: 18` turns about 850 runner-min into about 50 min of wall time; upstream-pure-r-001 alone takes 28.0 to 28.7 min against a 30-min timeout.
- **No retry** on the upstream fetch step; an SSL EOF killed 39708064741.
- **Publishing-only work on branch runs:** the macOS publish build and the lzma `.tar.xz` assets (2.1 min).

## 7. Failure rate (EXECUTED)

177 runs, the workflow's whole history (2026-10-16 22:51 to 2026-10-23 12:56).

| kind | success | failure | cancelled |
|---|---|---|---|
| spec/* | 20 | 67 | 7 |
| main | 35 | 17 | 2 |
| wave/* | 10 | 6 | 1 |
| tags | 7 | 1 | 1 |
| claude/* | 0 | 2 | 1 |
| **all** | **72 (41%)** | **93 (53%)** | **12 (7%)** |

By failing job across the 93 failures: macOS legs only 28; Windows legs only 25 (9 on main); several systems 15; the old macOS "build and judge" job 10; gather only (G7) 8; fetch 2; release tier 2; pinned download 1; verify 1; one Linux upstream leg 1.

| run | branch | job | reason | class |
|---|---|---|---|---|
| 39626982133 | spec/114 | macOS build shard | "1 accepted check(s) absent" | red by design (judge change not yet accepted) |
| 39633291201 | spec/114 | macOS own-guest, own-embedding | "72 metric(s) grew" / "19 grew" | red by design (growth) |
| 39636646869 | spec/102 | macOS upstream-macos | "1 metric(s) grew" | red by design |
| 39589394200, 39720564953, 39732496724 | spec/112, spec/067 | gather | G7, the newest acceptance is not on the release's set | red by design |
| 39705963592 | spec/095 | own-rest (macOS and Linux) | lxml's group JSON changed | real bug in the branch |
| 39715865231 | spec/067 | two fetch legs | `openpyxl-3.1.5-tag.tar.gz` missing from downloads/ | real (wiring) |
| 39708064741 | spec/095 | upstream-plot-g fetch | `SSLEOFError` during the kit download | flaky download |
| 39891594258 | wave/13 | all 38 shards | one accepted check absent | red by design, fanned out to every shard |
| 39904389018 | main | own-rest ×2 and coverage | the acceptance commit carried release-tier-claims files | real (process) |
| 39741960669 | main | release pure-r-040 | networkx approximation group out of fuel | real; release tier only |
| 39764234616 | main | release pure-r-112 | joblib mmap test failed | real; release tier only |

Not determined: whether any cancellation came from the concurrency group; the duration of a green post-101 source spec run (none exists); why one absent check reds every shard; why the x86-64 compile time varies; how often reuse hit.

One line: every dispatch runs three or four full compiles and every judge leg, with no path filter; branch runs take 36 to 46 min, bound by the x86-64 rebuild or the macOS judges; main and tag runs take 80 to 85 min, bound by the 229 release-tier legs throttled to 18 at a time; 53% of all runs failed, and in the sample most spec-branch failures are red by design.
