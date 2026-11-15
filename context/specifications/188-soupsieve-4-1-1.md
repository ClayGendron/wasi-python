# 188: soupsieve 4.1.1

- **Status:** built 2026-11-15, in review. Pre-build review `../reviews/188-soupsieve-4-1-1-spec-2026-11-14.md` lands it at round 1 (constitution §5.6: it changes the artifact set and the build recipe). Asked for on 2026-11-14 by the owner ("Yes, bump Soup Sieve", to the question whether soupsieve moves from 3.0.4 to 4.1.1 in 0.1.5).
- **Date:** 2026-11-14
- **Owner:** Clay Gendron
- **Kind:** **build-class** and **a judge change**, not structural: nothing under `src/` changes. Recipe: `scripts/00_download.sh`, `downloads/SHA256SUMS`, `scripts/assemble_artifacts.py`, `scripts/steps/70_zip.sh`. Judge: `tests/upstream/soupsieve.toml`, the oracle (`tests/jobs/oracle/pyproject.toml` and its `uv.lock`), the markup job's golden (`tests/jobs/markup.expected`), the new class's list file and its gap in `tests/known_gaps.toml`, the release ledger's file. Documents: `docs/reference/packages.md`, the news file.
- **Depends on:** nothing unlanded. 166 (the pins move for 0.1.3) is the model: it moved soupsieve 3.0.3 to 3.0.4 the same way.
- **Research it stands on:** PyPI's JSON API for soupsieve 3.0.4 and 4.1.1, read 2026-11-14 (3.0.4's `vulnerabilities`; 4.1.1's files, digests and `requires_python`); soupsieve's changelog, 4.0 to 4.1.1, read 2026-11-14 from its repository; the advisory page for GHSA-8jvp-3x96-xpqw at wiz.io, read 2026-11-14; GitLab's advisory pages for CVE-2026-49476, -49477, -85999 and -86000, read 2026-11-14; beautifulsoup4 4.15.0's `requires_dist` on PyPI; the 4.1.1 sdist, downloaded and read in scratch.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

Every 0.1.x release ships soupsieve 3.0.4 inside the zip (READ, `scripts/assemble_artifacts.py`, `docs/reference/packages.md`). Two published advisories cover it:

- **GHSA-mmhr-3c5m-f64f** (CVE-2026-126190). Matching a selector with descendant combinators takes time polynomial in the document's nesting depth, `O(n^(k+1))` for `k` combinators. A document of nested `<div>` of about 1 KB keeps `section div div div` busy for about 40 seconds on 3.0.4. Fixed in 4.0 by caching per element and relation (READ, PyPI's JSON API for 3.0.4, its `vulnerabilities` entry, `fixed_in` 4.0.0).
- **GHSA-8jvp-3x96-xpqw.** Some `:has()` selectors take time quadratic in the document's size. Fixed in 4.0.1 (READ, wiz.io's page; soupsieve's 4.0.1 changelog, "Cache whether an element is or has a matching descendant when matching `:has()` to avoid quadratic time").

The four older soupsieve advisories of 2026 (CVE-2026-49476, -49477, -85999, -86000) were fixed in 2.8.4 and 2.9.0, before any version this project shipped (READ, GitLab's advisory pages). 4.1 and 4.1.1 fix further quadratic paths (`:lang()`, `:read-write`, nested `nth`, `:placeholder-shown`; READ, the changelog).

Reach in the sandbox. Each is a denial of service on CPU, with no memory corruption; the advisories' fixes change no selector's result. The move from 3.0.4 to 4.1.1 does change some results (Decision 2). In the guest it is bounded by the cell's own limits: a stalled `select()` runs the cell into its fuel or its time limit and the runner ends it, and no other cell and nothing in the host is touched (INFERRED from the runner's limits; no new channel). The harm is to an embedder whose agent code scrapes pages an attacker controls: the cell fails where it would have finished.

## Decisions

### 1. soupsieve moves to 4.1.1, its newest release

4.1.1 was uploaded 2026-11-14 (READ, PyPI). Its files, from PyPI's JSON API, with the SHA-256 PyPI gives, matched by the bytes downloaded (EXECUTED):

| File | SHA-256 | Source |
| --- | --- | --- |
| `soupsieve-4.1.1-py3-none-any.whl` | `8ff3422dab0b720fb667ee79864d80531a0e57994a13eb701697719ffcb751f6` | PyPI |
| `soupsieve-4.1.1.tar.gz` | `b296bd2d2f65b1a78149f3d7bf6736a147d2c9e2dfbde0e4404639d748a02e03` | PyPI |

The wheel goes into the zip as 3.0.4's did; the sdist is the test source, as before. 4.1.1 needs Python 3.11.5 or newer (READ, `requires_python`); the guest is CPython 3.15.2. beautifulsoup4 4.15.0 needs `soupsieve>=1.6.1` (READ), so bs4 stays.

4.0 is chosen over 3.0.x because no 3.0.x release carries the fixes (READ, PyPI's release list: 3.0.4 is the last 3.0).

### 2. Two changes users can see, named in Upgrading

4.0's changelog marks two breaks (READ):

- The contents of an HTML `template` are no longer part of the document: a selector does not match inside one.
- The contents of an `iframe` are no longer a separate document.

Both go in the news file's Upgrading entry. A second Upgrading entry names the other results that change between 3.0.4 and 4.1.1, where selectors now match as a browser does (READ, the changelog, 4.0 to 4.1.1): HTML attributes the HTML specification lists as ASCII case insensitive (`rel`, `method`, `lang`, `dir`) match that way; `[attr=value]` no longer ignores a trailing newline in the value; `:checked` matches only the last checked radio of a group and the option a browser would select; `:lang()` refuses an ill-formed language tag; `:enabled` and `:disabled` match hidden inputs; `:in-range` and `:out-of-range` change for range inputs. It links the packages page (review, Low 5).

4.1 also makes soupsieve thread safe with locks taken at import (`css_parser.py`, `threading.Lock` and `RLock`; READ, the sdist). The guest has `threading`'s locks and cannot start a thread, so the import works and only the new thread tests cannot (INFERRED; the build's smoke group imports the package from the zip and shows it).

### 3. The pins move in every file that names them

`scripts/00_download.sh` (the `get` line for the wheel and the `tests` line for the sdist, at the addresses PyPI gives), `downloads/SHA256SUMS` (both lines), `scripts/assemble_artifacts.py` (the version and the wheel's name), `scripts/steps/70_zip.sh` (the `--wheel` pin), `tests/upstream/soupsieve.toml` (`wheel`), `tests/jobs/oracle/pyproject.toml` (`soupsieve==4.1.1`) and its `uv.lock` (by `uv lock --upgrade-package soupsieve` in that folder, with the oracle's pinned uv, 0.9.22, so the lock's diff touches soupsieve's lines alone), `tests/jobs/markup.expected` (rewritten by `uv run python tests/jobs/regen.py --job markup`; its diff is the versions line, line 1), `docs/reference/packages.md`. `tests/harness/pins.py` matches soupsieve's sdist by pattern and needs no change (READ). The licence: 4.1.1's `LICENSE.md` is 3.0.4's byte for byte (EXECUTED, `diff`), so the zip's notice does not change.

### 4. soupsieve's own tests, and the two groups' fuel

4.1.1's test tree adds `tests/test_threads.py`, `tests/test_extra/test_iframe.py` and `tests/test_extra/test_template.py`, and keeps `tests/test_level1` (14 files) for the smoke group (EXECUTED, the sdist against 3.0.4's). `test_threads.py` starts `threading.Thread`s, which the guest cannot (READ). It joins `soupsieve-r` and five of its six tests fail there. One `[[expected]]` row names them: id `no-threads`, group `soupsieve-r`, outcome `failed`, `match = "can't start new thread"`, the guest's own message (`docs/how-to/troubleshooting.md`), and not `charset-normalizer.toml`'s wider alternation, `reason = "the guest cannot start a thread (README)"`, `closes_with = "docs/reference/limitations.md"`. Its list file, `tests/upstream/expected/soupsieve-r/no-threads.txt`, names the five, sorted: `test_compile_and_purge`, `test_lazy_pattern`, `test_lazy_pseudo_selectors`, `test_parse` and `test_select`, each by its node id. `test_tokens_have_no_match_state` starts no thread and is expected to pass (EXECUTED natively, with thread starts refused, by the review, Low 3). Its class check, `test_upstream_class[soupsieve-r-no-threads]`, gets a `[[gap]]` in `tests/known_gaps.toml` beside `soupsieve-r-no-alarm`'s, with the finding digest the run prints. Nothing else in the file changes, and no row is loosened (review, Medium 1).

The fuel numbers stay as they are when the pins move, and the run measures both groups. Then both groups' `measured` takes the run's figure, and a cap rises only by the rule that holds it at most 1.5 times its `measured`, within the file's 303 G `budget` (`tests/harness/packages.py`, `tests/harness/tiers.py`). The smoke group is the tight one: the test-source smoke groups record 1,183.07 G against `SMOKE_TOTAL_BOUND`'s 1,200 G, 16.9 G of headroom, and `test_level1`'s Python calls rise 36% (EXECUTED by the review; calls are not fuel), which puts the smoke near 20.5 G, under its 23 G cap (INFERRED). If the smoke would take the test-source total past 1,200 G, or itself past its 110 G bound, no bound is raised here: the heaviest new `test_level1` file moves to the release tier by path, claimed under `[claim.moved]` and `fewer`, or the owner is asked (review, Low 4). The markup job's fuel is read from the gather the same way (166 saw `import soupsieve` and a compile grow with 3.0.4).

`soupsieve-r` is judged before the merge (review, Medium 2). A pull request into `dev` runs the normal tier alone (`release/ci_plan.py`, `decide()`, READ), and this container cannot build a set: it cannot reach `www.python.org`, where CPython's source is pinned (EXECUTED, the proxy refuses it). Nor can it fetch a run's set: the tools this session has list a run's artifacts but download none, and `gh` is used here for search alone. So the route is the workflow's own dispatch: `release.yml` dispatched on `spec/188-soupsieve-4-1-1` with `release-tier: true`. `decide()` gives a dispatch the whole workflow and both rebuilds, and the release tier when that input is set; it sets neither `accept` nor `publish`, so on a branch the run signs, publishes and pushes nothing (READ, `decide()`'s last branch; `publish` is a tag's alone). The builder asks the owner's yes before it dispatches, since the run is the workflow's longest and uses CI time the pull request alone would not. The run's `soupsieve-r` fuel, pass count, `no-threads` members and the gap's digest go in the landing notes; if the gap's digest is first known from that run, the builder adds it and the pull request's own run, or one more dispatch if a release-tier row moved, confirms it. Without the owner's yes, criterion 3 falls back to 0.1.5's release pull request, where a release-tier failure stops the tag before anything is signed (`../../docs/contributing/release-process.md`), and the weekly run on `dev` after the merge reads it first.

### 5. The markup job's golden

`tests/jobs/markup.expected` carries the versions line, and the job compares the guest with the oracle's native run (READ). Its selectors (`a.x, a[href='/a']`, `p.note`) use neither `template` nor `iframe`, so only the versions line is expected to change (INFERRED; the job shows it).

## Design

The decisions are the design. One commit moves the pins and the judge's rows together, so no run sees the zip and the judge disagree.

## Intent

The zip ships a soupsieve with no known advisory, and the change users can see is named.

## Scope

The files in Decision 3; `tests/upstream/soupsieve.toml`'s one new row and its measured fuel; `tests/upstream/expected/soupsieve-r/no-threads.txt` (the five node ids, sorted); the `[[gap]]` for `test_upstream_class[soupsieve-r-no-threads]` in `tests/known_gaps.toml`, with the digest the run prints; `../release-claims/188-soupsieve-4-1-1.toml`, since release-tier rows move; the news file `../changes/188-soupsieve-4-1-1.md`, whose claim block names `new` (the class check), `passes` (both groups), `grows` with its `growth` (the smoke group, the artifacts' sizes, the markup job), and under `[claim.judge]` each verdict-bearing file changed. Nothing else.

## Acceptance criteria

1. Every pin names 4.1.1 with PyPI's digest; `git grep soupsieve-3.0.4` and `soupsieve==3.0.4` find nothing outside `context/`.
2. The run is green: the build, `verify`, every judge leg, the gather with no pass count lost, and `test_markup_job_matches_native`.
3. soupsieve-smoke passes in the normal tier; `soupsieve-r` passes in the release tier with its new `no-threads` row matching exactly its five members and `test_tokens_have_no_match_state` passing, read on the dispatched run of Decision 4 (or, without the owner's yes to it, at 0.1.5's release pull request).
4. The news file's Upgrading entries name both of 4.0's breaks and the other selector results that change.

## Landing notes

Built 2026-11-15 on `spec/188-soupsieve-4-1-1`, rebased onto `dev` at `338ed06d` (after #105, #106 and #107 merged), by the session https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC.

- **The pins** (criterion 1). The wheel and the sdist were downloaded from the addresses PyPI's JSON API gives and match its SHA-256 (EXECUTED). `git grep` finds no `soupsieve-3.0.4` or `soupsieve==3.0.4` outside `context/` (EXECUTED); `soupsieve.toml`'s smoke note keeps its history line about 3.0.4's `test_api.py`, which is not a pin.
- **The oracle** (Decision 3, the review's Low 6). `uv lock --upgrade-package soupsieve` with uv 0.9.22 and the line's pinned Python 3.15.2: "Updated soupsieve v3.0.4 -> v4.1.1", and the lock's diff is soupsieve's four lines (EXECUTED). `regen.py --online --job markup` rewrote the golden; its diff is line 1, the versions line, and `regen.py --check --job markup` reproduces (EXECUTED).
- **The class** (Decision 4, the review's Medium 1, Lows 3 and 7). `tests/upstream/expected/soupsieve-r/no-threads.txt` names the five node ids, sorted; `scan.report` of them gives `5 finding(s), digest 61cf3b317d0f`, the gap's `match`, as the review computed (EXECUTED).
- **The fuel.** `fuel` and `measured` are as they were; the guest's figures come from the run (this container cannot build a set: no `www.python.org`). The smoke group, the markup job and the artifacts' sizes are read from the pull request's run; `soupsieve-r` waits on the owner's yes to the dispatch of Decision 4, or 0.1.5's release pull request.
- **Local runs.** `ruff check` and `ruff format --check`: clean. `tests/lint` and `tests/checks/test_rules.py`: 157 passed, 5 skipped for this container's needs (git history, artifact dir, prior-art clones), as on `dev`'s tip. `tests/unit`: 3,631 passed, 104 skipped, 1 failed, `test_the_walk_judges_links`, from running as root, as on `dev` (EXECUTED).
