# Review of 169 — zstd, built in

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/169-zstd-built-in.md`, uncommitted on `docs/specifications-169-and-170` from `dev` at `d64f8146`
- **Run:** none: a specification review
- **Re-ran:** no test run. Read CPython 3.15.2's and pandas 3.1.0's pinned tarballs in the 166 worktrees' `downloads/`, wasi-sdk 34's sysroot `time.h`, and the 0.1.2 build's stdlib zip in the main tree's `build/artifacts/`. The zstd 1.5.7 tarball is not on this machine, so every claim about its files is INFERRED.
- **Time box:** 45 minutes (build-class); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

**The claims checked.** All READ unless marked.

- Step 35 compiles bzip2 file by file with `clean $CC` (`35_stdlib_libs.sh:26-38`): **verified**.
- Step 60's archive check, weak-duplicate list and dropped-module check are at `:21-23`, `:100` and `:139`: **verified**.
- 3.15.2's `Setup.stdlib.in:69` names the four `_zstd` files: **verified**.
- `shutil.py:36` and `zipfile/__init__.py:35` import `compression.zstd` at module top: **verified**. `tarfile` imports it only when a zst mode opens (`tarfile.py:426`). `zipimport` imports it only for a zstd member (`zipimport.py:591-603`).
- `compression/zstd/__init__.pyc` and `_zstdfile.pyc` are already in the 0.1.2 zip, so the zip does not grow: **verified** (EXECUTED).
- pandas 3.1.0's zstd branch is `io/common.py:914-924`, and its fixtures skip without `zstandard` at `conftest.py:320` and `:337`: **verified**. pandas requires `zstandard>=0.23.0` (`compat/_optional.py:55`).
- `test_zstd.py:68` sets `SUPPORT_MULTITHREADING` from `nb_workers.bounds()`: **verified**.
- `cpython-b` is 490 G (`tests/upstream/python.toml:48-50`), `test_zstd` is on `cpython-b.txt:140`, and `stdlib_modules` is `packages.toml:13`: **verified**. `shards.py:388-395` accepts a `via` that names a listed stdlib module: **verified**.
- The tree count "^28 passed" is at `release.yml:383`, `:489` and `:588`: **verified**.
- No wheel-size gate is on `dev` yet (no `PYPI_FILE_LIMIT` under `tests/`, `release/`, `scripts/` or `.github/`): **verified**.

## Acceptance criteria against evidence

1. Pin checked against `.sha256` and the signature — testable. The signing key is not named (Finding 9).
2. The header sweep before the pull request — sound.
3. `_zstd` builtin, seen failing first — testable.
4. `zstd_files` against the oracle — sound (Finding 6).
5. The pandas guest check — testable. Its read side is not specified (Finding 4).
6. Tree check and patch rules — sound.
7. `test_zstd` and the expected classes — the groups named are incomplete (Finding 7).
8. The artifact-set checks with `LICENSES/zstd.txt` — not reachable if `COPYING` is zstd's first top-level file (Finding 1).
9. Bytes, fuel and the wheel's line — recorded, but with no stop line of its own (Finding 2).
10. Fast tier, lint, `ci-status`, same-bytes — sound.

## Findings, most severe first

1. **Medium: the fallback for a `COPYING` that comes first cannot work** (Decision 6; `tests/harness/paths.py:656-673`, `:681`, `:777-790`). `_top_level_licence` returns the first top-level `LICENSE*` or `COPYING` in the tarball's member order. `licence_errors` requires that text in the notice. `MORE_LICENCE` only adds texts: it never replaces the first one. zstd's release tarball is made with `git archive` (INFERRED). That puts `COPYING` (GPLv2) before `LICENSE`, because C sorts before L. Failure: the builder writes `LICENSES/zstd.txt` with `LICENSE` and divsufsort's MIT words, as Decision 6 says. `licence_errors` then reports "LICENSES/zstd.txt does not contain the licence of zstd-1.5.7.tar.gz", because it wants GPLv2's text. Naming `LICENSE` in `MORE_LICENCE` leaves that demand in place. Fix text for Decision 6: "The builder first lists the tarball's top level (`tar -tzf zstd-1.5.7.tar.gz | awk -F/ 'NF==2'`) and records the order. If `COPYING` comes first, the judge change is a per-component choice of the top-level file. `paths.py` gains `TOP_LICENCE = {"zstd": "LICENSE"}`, which `_top_level_licence` reads in place of the first match. Its reason: zstd is BSD-3-Clause or GPLv2 at the user's choice, and the set takes BSD-3-Clause. Shipping GPLv2's text in the notice as well is refused: it would suggest the set is under GPLv2." `_more_licence` reads top-level members only (`:701`), so divsufsort's notice stays the assembler's (`head_notice`). The judge checks only that the notice file is present for it, and the review says so.
2. **Low: no stop line of its own, and no gate if this lands before 167's Part A** (Decision 8, criterion 9). The 0.5 MB estimate is INFERRED: no spike built libzstd. The headroom is about 4.5 MB (104,857,600 bytes less about 100.3 MB). 167 Part A takes about 2 MB of it, and 170 about 0.2 MB. Fix text: "The builder records `python.wasm`'s and the snapshot's growth and the wheel's bytes before the pull request opens. If the wheel grows by more than 1.0 MB, the builder stops and asks the owner before merging, since landing it would crowd out 167's Part A. If 167's `PYPI_FILE_LIMIT` row is not on `dev` when this merges, criterion 9's recorded bytes are the line's only evidence. The landing notes say so."
3. **Low: `clock()` and the import list** (Decision 2). zstd's `dictBuilder` files include `<time.h>` and call `clock()` in their progress displays (INFERRED). Without `-D_WASI_EMULATED_PROCESS_CLOCKS`, wasi-sdk 34 declares `clock` deprecated (sysroot `include/wasm32-wasip1/time.h:63-71`, READ). qhull already compiles with that define (`37_plot_libs.sh:74`), so the emulated clock and its constructor are already linked and reviewed. Fix text: "The flags gain `-D_WASI_EMULATED_PROCESS_CLOCKS`, as qhull's do. The guest's imports, exports and constructors do not change. `test_imports_are_wasi_and_the_door_only` and step 60's constructor check hold that."
4. **Low: the patch's read side, and the weighing in words** (Decision 4). (a) On read, `ZstdFile` raises `TypeError: level is illegal in read mode` (3.15.2 `_zstdfile.py:63-65`, READ). Say: "`level` is forwarded only when writing. On read, any key, `level` included, raises `TypeError` naming it, as `zstandard.ZstdDecompressor` would." (b) §4.1: the stand-in is rightly refused, and Decision 4 should give the facts. pandas needs `zstandard>=0.23.0`, so a stand-in must claim a version of a package it is not. `pd.show_versions()` would report that version. A user's `import zstandard` would meet a partial API. The stand-in's one advantage is that pandas' `compression` fixtures would run through it. The patch is about fifteen lines with an upstream path, so it is the smaller departure. (c) Before drafting, the builder reads pandas' main branch and its issue tracker. If upstream already has a fallback, the patch backports that commit, with its hash in the draft. Then deleting the patch at upstream's release changes nothing a user sees.
5. **Low: the guest check is the path's only test, so widen it a little** (Decision 5). Add a `BytesIO` handle in both directions, `read_csv("frame.csv.zst")` inferring the method, and `to_pickle`/`read_pickle` with `compression="zstd"`. These are the shapes pandas' own skipped fixtures cover.
6. **Low: the oracle comparison** (Decision 5). It is sound as drafted. Levels 1, 3 and 19 use the fast, dfast and btultra2 strategies, not the row match finder. `train_dict` calls `ZDICT_trainFromBuffer` (`_zstdmodule.c:306`, READ), which trains fastCover on one thread. Its dictionary ID is a hash of the content (INFERRED). Fix text: "The job prints `compression.zstd.zstd_version_info` first, so a libzstd version difference shows as one line, not as every hash."
7. **Low: the zstd cases run in more groups than `cpython-b`** (Decision 5). `test_tarfile`, `test_zipfile` and `test_zipfile64` are in `cpython-archives` (250 G). `test_shutil` is in `cpython-fs` (100 G). `test_zipimport` gains zstd cases (`test_zipimport.py:1101`, READ). The release tier's `cpython-release-archives` is 150 G, with 99.7 G measured. Name each group. A cap that rises is a judge change with this specification's reason.
8. **Low: the file list and object names** (Decision 2). Say the count: about 30 `.c` files in 1.5.7 (INFERRED). The step stops on any other count, as 170's does with 101. Objects are named by basename, and the step stops if two share one. Give the include folders zstd's own build uses.
9. **Low: the signing key** (Decision 1, criterion 1). Record the key's fingerprint and where it was read, beside the `.sha256` match.
10. **Low: the comments.** These say "the four C libraries" or "three stdlib modules" and need the new count: `60_link.sh:2-4` and `:96`, and `35_stdlib_libs.sh:2-5`. Also say where the cost lands. `compression.zstd` builds three enum classes and loads `_zstdfile` and `compression._common._streams`. Every program that imports `shutil`, `tempfile` or `zipfile` without the snapshot pays that cost. The builder names the fuel checks that move.

## Constitution checks

- §4.1: one carried patch with its draft. A stand-in is weighed and refused for good reasons (Finding 4). The tree check covers zstd's tree and the patched pandas tree.
- §4.12: libzstd 1.5.7 approved on 2026-10-31, divsufsort's MIT included (167's review, Finding 2). The header sweep (criterion 2) catches anything else. The notice needs Finding 1 to pass the judge.
- §4.11 and the documents: the `-V` line and both reference pages change. Planned.
- §5.6: the build recipe and the artifact set, reviewed before building. The guest's imports should not change (Finding 3).
- Pins: URL and SHA-256 checked against the release's asset. Planned.
- Structure: nothing under `src/`. Agreed.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-31. Every finding is taken.

1. **Taken.** Decision 6: the builder lists the tarball's top level and records the order. If `COPYING` comes first, `paths.py` gains `TOP_LICENCE = {"zstd": "LICENSE"}`, with its reason, and GPLv2's text is not shipped. divsufsort's notice stays the assembler's `head_notice`, and the judge checks presence only. Criterion 8 names it.
2. **Taken.** Decision 8: the headroom, a stop at 1.0 MB of wheel growth before merging, and the recorded bytes as the line's only evidence while `PYPI_FILE_LIMIT` is not on `dev`. Criterion 9 names it.
3. **Taken.** Decision 2: `-D_WASI_EMULATED_PROCESS_CLOCKS`, as qhull's. The imports and constructors hold.
4. **Taken.** Decision 4: (a) `level` only when writing, and any key on read raises `TypeError`; (b) the §4.1 weighing in words; (c) the builder reads pandas' main branch first and backports an upstream fix if there is one.
5. **Taken.** Decision 5's guest check: `BytesIO` both ways, `read_csv` inferring `.zst`, and pickle round trips.
6. **Taken.** Decision 5: the job prints `zstd_version_info` first.
7. **Taken.** Decision 5 names `cpython-archives`, `cpython-release-archives` and `cpython-fs`, and `test_zipimport` too. Criterion 7 follows it.
8. **Taken.** Decision 2: the count is recorded and enforced, objects are named by basename and duplicates stop the step, and the include folders are `lib/` and `lib/common/`.
9. **Taken.** Decision 1 and criterion 1: the key's fingerprint and its source.
10. **Taken.** Decision 3 names the comments to recount. Decision 8 names the import cost and the fuel checks that move. `tempfile` reaches it through `shutil`.

## Verdict

Fit to build after amendments: Finding 1 (the zstd notice's top-level file) must be fixed in Decision 6; the nine Lows are write-ins.

Confirmed after amendments, 2026-10-31 (READ, the amended specification): all ten findings are taken as written. Finding 1 is in Decision 6 and criterion 8. Finding 2 is in Decision 8 and criterion 9. Findings 3 and 8 are in Decision 2, 4 to 7 in Decisions 4 and 5, 9 in Decision 1 and criterion 1, and 10 in Decisions 3 and 8. Nothing stands open. The verdict is now Fit to build.
