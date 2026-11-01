# Review of 169 — zstd, built in

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** pull request #81 at `1ef225b0`, its fix round `0a21a40a`, and on 2026-11-01 its rebases onto `5c2bff0a` (`1987545b`) and `da830491`, head `b9e33060` (range-diff: tree count, 60's header, landing notes)
- **Run:** 41308552174 at `b9e33060`, as the orchestrator relayed it: the gather and every judge shard green, all 13 windows-2025 legs included; only `review` and `ci-status` red, the plan's sole refusal the missing review file
- **Re-ran:** at `b9e33060`, on the worktree's set rebuilt on `da830491` (MANIFEST: pandas 3.1.0, libjpeg-turbo, zstd): `tests/lint` 14 passed; the golden job, the pandas check, the builtins check, the notices check and the unit row 6; the zstd and pandas trees 2; the patch, own-suite, news and ledger rules 5; every exit 0.
- **Time box:** 45 minutes (build-class); kept. No `gh` call or run. EXECUTED: run; READ: file cited; INFERRED: reasoned.

## Acceptance criteria against evidence

1. Pin and signature — met (READ; EXECUTED: `shasum` equals `SHA256SUMS`, checked by `pinned`).
2. Header sweep — met (READ: 68 dual-notice files and divsufsort's MIT, within the approval).
3. `_zstd` builtin, seen failing first — met (EXECUTED; READ: `build/169/old-set-builtin.txt`).
4. Golden job — met (EXECUTED). Bytes equal the oracle's over libzstd 1.5.7.
5. pandas guest check — met (EXECUTED; READ: `build/169/unpatched-pandas.txt`).
6. Trees and patch rules — met (EXECUTED). MANIFEST's hashes of the patch and steps 35 and 60 equal the committed files.
7. CPython's suites — met (READ: `build/169/*.log`). `cpython-release-archives` reaches 6 passes at 248.9 G.
8. Licence — met (EXECUTED). `COPYING` precedes `LICENSE`; `LICENSES/zstd.txt` holds `LICENSE` and Yuta Mori's MIT words, no GPLv2; `TOP_LICENCE` full-matches one name for one component.
9. Bytes and fuel — met (READ). The wheel grew 250,317 bytes on the old base, under the 1.0 MB stop; it is 103,095,563 on `da830491`, a fact, not a gate (#91 raised the limit to 256 MiB).
10. `ci-status` — met but for the review file (run 41308552174, as relayed).

**Point A, the release shard's time (INFERRED from fuel).** The group is in `upstream-release-001`: 10.4 minutes for 2,167.7 G, 207 G a minute; the slowest release shard ran 145 G a minute. The extra 149 G adds 0.7 to 1.0 minutes, 11.1 to 11.4 in all: under twelve, and about 17 at the weekly x86-64 runs' 1.48 times, under the 30-minute timeout. The builder's log runs the group faster per G than its other groups, so these tests are compute the fuel counts. No split is needed; lint is quiet only because `minutes` is unchanged (Finding 2).

**Point B, `import shutil` on the snapshot (EXECUTED).** The cause is CPython's own try-import at `shutil.py:36`, which native runs too: after `bz2`, `lzma` and `os`, `import shutil` adds exactly `_zstd`, `compression.zstd`, `_zstdfile` and `shutil` (`_zstd` 0.74 M fuel, `compression.zstd`'s enum classes 12.8 M). The growth, 10.4 M, is the same on both binaries; +12.2% reflects the snapshot's smaller base. The snapshot pre-imports no package, so every embedder importing `shutil`, `tempfile` or `zipfile` pays it once a call. A lazy import would patch CPython against upstream's design (§4.1), and a snapshot pre-import changes every start, a specification of its own.

## Findings, most severe first

1. **Medium: the release ledger claims growth for CPython's release groups only** (`context/release-claims.toml`, 169's block). Every pytest-driven release group imports `shutil` through pytest's `pathlib`, `capture` and `tmpdir`. So each guest pays about 10.4 M more fuel. `FUEL_TOLERANCE` is 0.01% (`tests/harness/scoreboard.py:42`). Any release group under about 100 G therefore grows past it. 281 non-CPython release groups are under 140 G. Among them are `more-itertools-r-doc` (13.6 G, about +0.08%), `joblib-r-doc` (16.1 G) and `contourpy-slow-rest` (18.1 G). Failure: the release pull request's gather lists their growth as unclaimed, and its acceptance stops for a reason this pull request knew. Fix text: in 169's block, `grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]`, as 165's block has it, and the growth sentence gains "and every group driven by pytest imports shutil through pytest, so its fuel grows by about 10 M a guest". Evidence that closes it: that change, or a release-tier run in which those groups do not grow.
2. **Low: `upstream-release-001`'s minutes are now stale** (`tests/release_shards.toml:400-401`). The field still says 10.4, so lint cannot see the growth. Fix text, in the landing notes: "upstream-release-001 is estimated at 11.1 to 11.4 judge minutes (149 G at 145 to 207 G a minute), about 17 on the weekly x86-64 runs; the release pull request's run re-measures it, and a figure past twelve repacks it."
3. **Low: Decision 8 says the snapshot carries the import** (`context/specifications/169-zstd-built-in.md`, Decision 8). It says "the snapshot, through pandas' shutil, carries it", but the snapshot pre-imports no package. The landing notes correct this, and the specification still says both. Fix text: replace that clause with "the snapshot pre-imports no package, so a snapshot start pays the same 10.4 M fuel; only the percentage is larger".
4. **Low: the patch's path is still to move** (the news file's "For contributors" line, the draft, `upstream-stages.json`). These name `pandas-3.0.6/`, while Decision 4 and the Design section name `pandas-3.1.0/`. The landing notes already say that whichever of #71 and this lands second moves them. This is a reminder that the CHANGELOG line moves with them.
5. **Low (from the rebase): the news file's judge claim names the removed single ledger** (`context/changes/169-zstd-built-in.md:40`). The key is `"context/release-claims.toml"`, but the verdict-bearing file this pull request changes is now `context/release-claims/169-zstd-built-in.toml`, and `news.names` matches exactly or by a trailing `*`. Failure: at acceptance the key matches nothing; 177's `context/release-claims/*`, if still read, gives 177's reason, and otherwise the file is recorded unclaimed. Fix text: the key becomes `"context/release-claims/169-zstd-built-in.toml"`, its reason unchanged.

## Constitution checks

- §4.1: one carried patch, minimal, hashed in MANIFEST, named in the news file, its draft pointing at pandas-dev/pandas#62365. Re-made against 3.1.0 (READ in full; EXECUTED: applies clean to the pinned tarball): 3.0.6's lines one indent deeper, one message split into two f-strings of the same text, none past 88 columns; the draft says "Against: 3.1.0".
- Pins and reproducibility: pinned and checked before use; 30 files enforced; `rcD`, `-ffile-prefix-map` and `LC_ALL=C` fix the archive.
- §4.12: BSD-3-Clause and divsufsort's MIT ship. GPLv2's text does not.
- 4b: `release.yml`'s tree count goes from 33 to 34 in three places (libjpeg-turbo the 33rd, zstd the last); nothing else in what runs changes. `JOBS` holds `zstd_files` and `jpeg_images`; the README's 31 equals the patch files.
- Judge: every verdict-bearing file changed is claimed, the cap's rise (150 G to 380 G) with its reason; nothing is weakened. The trailer names Claude Opus 5.5.
- Structure: nothing under `src/`.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed in `0a21a40a`, now in `context/release-claims/169-zstd-built-in.toml`: every upstream group, the cause named. Confirmed.
2. Fixed in `0a21a40a` (landing notes). Confirmed.
3. Fixed in `0a21a40a` (Decision 8). Confirmed.
4. Fixed by the rebase: patch, draft and CHANGELOG line name `pandas-3.1.0/`. Confirmed.
5. Fixed in the review commit: the key is `"context/release-claims/169-zstd-built-in.toml"`, its reason unchanged.

## Verdict

Lands at `b9e33060`: the round closed the Medium and Lows 2 and 3, the rebase closed Low 4 with the patch unchanged in substance, and Low 5 is fixed in the review commit; its run, 41308552174, is green but for the review file itself.
