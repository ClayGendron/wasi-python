# 188: soupsieve 4.1.1

- **Status:** written 2026-11-14, waiting on its pre-build review (constitution §5.6: it changes the artifact set and the build recipe). Asked for on 2026-11-14 by the owner ("Yes, bump Soup Sieve", to the question whether soupsieve moves from 3.0.4 to 4.1.1 in 0.1.5).
- **Date:** 2026-11-14
- **Owner:** Clay Gendron
- **Kind:** **build-class** and **a judge change**, not structural: nothing under `src/` changes. Recipe: `scripts/00_download.sh`, `downloads/SHA256SUMS`, `scripts/assemble_artifacts.py`, `scripts/steps/70_zip.sh`. Judge: `tests/upstream/soupsieve.toml`, the oracle (`tests/jobs/oracle/pyproject.toml` and its `uv.lock`), the markup job's golden (`tests/jobs/markup.expected`). Documents: `docs/reference/packages.md`, the news file.
- **Depends on:** nothing unlanded. 166 (the pins move for 0.1.3) is the model: it moved soupsieve 3.0.3 to 3.0.4 the same way.
- **Research it stands on:** PyPI's JSON API for soupsieve 3.0.4 and 4.1.1, read 2026-11-14 (3.0.4's `vulnerabilities`; 4.1.1's files, digests and `requires_python`); soupsieve's changelog, 4.0 to 4.1.1, read 2026-11-14 from its repository; the advisory page for GHSA-8jvp-3x96-xpqw at wiz.io, read 2026-11-14; GitLab's advisory pages for CVE-2026-49476, -49477, -85999 and -86000, read 2026-11-14; beautifulsoup4 4.15.0's `requires_dist` on PyPI; the 4.1.1 sdist, downloaded and read in scratch.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

Every 0.1.x release ships soupsieve 3.0.4 inside the zip (READ, `scripts/assemble_artifacts.py`, `docs/reference/packages.md`). Two published advisories cover it:

- **GHSA-mmhr-3c5m-f64f** (CVE-2026-126190). Matching a selector with descendant combinators takes time polynomial in the document's nesting depth, `O(n^(k+1))` for `k` combinators. A document of nested `<div>` of about 1 KB keeps `section div div div` busy for about 40 seconds on 3.0.4. Fixed in 4.0 by caching per element and relation (READ, PyPI's JSON API for 3.0.4, its `vulnerabilities` entry, `fixed_in` 4.0.0).
- **GHSA-8jvp-3x96-xpqw.** Some `:has()` selectors take time quadratic in the document's size. Fixed in 4.0.1 (READ, wiz.io's page; soupsieve's 4.0.1 changelog, "Cache whether an element is or has a matching descendant when matching `:has()` to avoid quadratic time").

The four older soupsieve advisories of 2026 (CVE-2026-49476, -49477, -85999, -86000) were fixed in 2.8.4 and 2.9.0, before any version this project shipped (READ, GitLab's advisory pages). 4.1 and 4.1.1 fix further quadratic paths (`:lang()`, `:read-write`, nested `nth`, `:placeholder-shown`; READ, the changelog).

Reach in the sandbox. Each is a denial of service on CPU, with no memory corruption and no change to what a selector returns. In the guest it is bounded by the cell's own limits: a stalled `select()` runs the cell into its fuel or its time limit and the runner ends it, and no other cell and nothing in the host is touched (INFERRED from the runner's limits; no new channel). The harm is to an embedder whose agent code scrapes pages an attacker controls: the cell fails where it would have finished.

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

Both go in the news file's Upgrading entry. 4.1 also makes soupsieve thread safe with locks taken at import (`css_parser.py`, `threading.Lock` and `RLock`; READ, the sdist). The guest has `threading`'s locks and cannot start a thread, so the import works and only the new thread tests cannot (INFERRED; the build's smoke group imports the package from the zip and shows it).

### 3. The pins move in every file that names them

`scripts/00_download.sh` (the `get` line for the wheel and the `tests` line for the sdist, at the addresses PyPI gives), `downloads/SHA256SUMS` (both lines), `scripts/assemble_artifacts.py` (the version and the wheel's name), `scripts/steps/70_zip.sh` (the `--wheel` pin), `tests/upstream/soupsieve.toml` (`wheel`), `tests/jobs/oracle/pyproject.toml` (`soupsieve==4.1.1`) and its `uv.lock` (by `uv lock` in that folder), `tests/jobs/markup.expected` (its versions line), `docs/reference/packages.md`. `tests/harness/pins.py` matches soupsieve's sdist by pattern and needs no change (READ). The licence: 4.1.1's `LICENSE.md` is 3.0.4's byte for byte (EXECUTED, `diff`), so the zip's notice does not change.

### 4. soupsieve's own tests, and the two groups' fuel

4.1.1's test tree adds `tests/test_threads.py`, `tests/test_extra/test_iframe.py` and `tests/test_extra/test_template.py`, and keeps `tests/test_level1` (14 files) for the smoke group (EXECUTED, the sdist against 3.0.4's). `test_threads.py` starts `threading.Thread`s, which the guest cannot (READ). It joins `soupsieve-r` and fails there; one `[[expected]]` row names it, as `charset-normalizer.toml`'s `no-threads` row does: id `no-threads`, group `soupsieve-r`, outcome `failed`, matched on the guest's error for a thread it cannot start, `closes_with = "docs/reference/limitations.md"`. Nothing else in the file changes, and no row is loosened.

The fuel numbers stay as they are when the pins move. The run measures both groups. If a group needs more fuel, the change is a measured budget raise in the landing notes, with the run's figure and the cause, as 166 recorded soupsieve 3.0.4's (166's landing notes). The markup job's fuel is read from the gather the same way (166 saw `import soupsieve` and a compile grow with 3.0.4).

### 5. The markup job's golden

`tests/jobs/markup.expected` carries the versions line, and the job compares the guest with the oracle's native run (READ). Its selectors (`a.x, a[href='/a']`, `p.note`) use neither `template` nor `iframe`, so only the versions line is expected to change (INFERRED; the job shows it).

## Design

The decisions are the design. One commit moves the pins and the judge's rows together, so no run sees the zip and the judge disagree.

## Intent

The zip ships a soupsieve with no known advisory, and the change users can see is named.

## Scope

The files in Decision 3, `tests/upstream/soupsieve.toml`'s one new row, the news file `../changes/188-soupsieve-4-1-1.md`. Nothing else.

## Acceptance criteria

1. Every pin names 4.1.1 with PyPI's digest; `git grep soupsieve-3.0.4` and `soupsieve==3.0.4` find nothing outside `context/`.
2. The run is green: the build, `verify`, every judge leg, the gather with no pass count lost, and `test_markup_job_matches_native`.
3. soupsieve-smoke passes in the normal tier; `soupsieve-r`'s new `no-threads` row matches only `test_threads.py`'s failures (read at 0.1.5's release pull request, where the release tier runs).
4. The news file's Upgrading entry names both of 4.0's breaks.

## Landing notes

Not built yet.
