# Review of 107 — the digest cache's fix (`2a878f0`)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent started by the lane; wrote none of the chain 103-109 or this fix
- **Reviewed:** `2a878f0` on `727bd4c` (three files: `src/wasi_python/_artifacts.py` +9 -6, `tests/unit/test_runner_sets.py` +42, the landing-notes bullet in `context/specifications/107-mounts-behind-a-protocol-and-one-platform-module.md`)
- **Run:** none dispatched (the lane's brief: single node ids, the unit files, ruff and mypy; the Windows leg is the wave's dry run). Time box: 25 minutes.
- **Re-ran:** `uv run pytest tests/unit/test_runner_sets.py` → 14 passed; `ruff check src tests` → all checks passed; `ruff format --check src tests` → 151 files already formatted; `mypy src/wasi_python/_artifacts.py` → no issues (all darwin, EXECUTED). A scratch test ran the three digest rows against two bodies, with `_artifacts._digest` replaced by a copy (no file in the tree changed): 727bd4c's body and the fix without its `samestat` guard (EXECUTED, below).

## What was read

- `git show 2a878f0`; `git show ecbdf53` (the chain's "one stamp", which moved the key to `os.fstat(fd)`); `git show dda6075:src/wasi_python/runner.py:4678-4687` (main's `_digest`).
- The pinned 3.15.0 source under `build/Python-3.15.0`: `Modules/posixmodule.c:2306-2350` (`win32_xstat_impl`, its fast path `_Py_stat_basic_info_to_stat`, and `win32_xstat`'s copy of birthtime into st_ctime), `:2783` (st_ino is the 128-bit id as one int, for both routes); `Python/fileutils.c:1104-1205` (`_Py_attribute_data_to_stat`, `_Py_stat_basic_info_to_stat`), `:1231-1287` (`_Py_fstat_noraise`); `Lib/genericpath.py:133-136` (`samestat` is st_ino and st_dev).
- Every other stamp user: `_artifacts.py:136` (`_version_tag`), `:156` (`_has_guest_package`), `_zip.py:62, 226, 245, 277`; the (dev, ino) comparisons at `_platform.py:123, 363`, `_private_dirs.py:176`.

## Acceptance against evidence

1. The cause — met (READ): by name, `win32_xstat` sets st_ctime from st_birthtime after either path; by descriptor, `_Py_fstat_noraise` keeps ChangeTime. 727bd4c looked up by `os.stat(path)` and stored under `os.fstat(fd)`, so on Windows the two keys differ unless creation and change time fall in one tick. The intermittent line 176 is that.
2. POSIX unchanged in effect — met (READ): `os.stat` and `os.fstat` of one open file give the same five fields, so the stored key equals the old one; `samestat` is true unless the name was replaced after the open.
3. Windows hits now — met (READ, EXECUTED by simulation): lookup and key both come from `os.stat(path)`. Row 1 simulates the ctime difference.
4. `samestat` on Windows is enough — met (READ). st_dev is the 64-bit volume serial and st_ino the 128-bit file id on both routes: by name from `FILE_STAT_BASIC_INFORMATION` (fast path) or `FileIdInfo` (slow path); by descriptor from `FileIdInfo`. On NTFS the 128-bit id is the 64-bit reference zero-padded, so the routes agree. A file id on one volume names one file, so "what was hashed and what is keyed are one file" holds.
5. Races — met (INFERRED from the code order: open, `fstat(fd)`, `stat(path)`, hash, store). A replacement between the open and the stat: `samestat` is false, nothing is stored, the digest returned is the hashed file's (as before). A replacement after the stat (during the hash, or before the store): the key is the old file's stamp, which a later lookup of the new file (another id) never matches. An in-place write during the hash: the stamp was taken before it, so on POSIX the new ctime misses later; on Windows the new mtime does, unless the writer sets mtime back (the residual limit, item 8).
6. The existing check is unchanged (rule 4) — met (EXECUTED): `git diff 727bd4c 2a878f0 -- tests/unit/test_runner_sets.py` removes no line; the two new rows are additions. No golden, `known_gaps.toml` or `tests/upstream/` file is touched.
7. The new rows against the old code — met, as claimed (EXECUTED). Against 727bd4c's body, row 1 (`..._still_hits_the_cache`) fails and row 2 (`..._is_not_cached`) passes; against the fix without `samestat`, row 2 fails and row 1 passes; the existing row passes on both. So row 1 is the one seen failing first, and row 2 guards the `samestat` condition. The landing notes say "the first seen failing first", which is exact.
8. No other cache mixes routes — met (READ): `_version_tag` and `_has_guest_package` use `os.stat` on both sides; `_zip.py`'s copy stamp and data record use `os.lstat` on both. The fstat-against-name comparisons elsewhere use only (dev, ino), which agree across routes.
9. The residual Windows limit is not a regression — met (READ). Main `dda6075` keyed `_digest` on `(resolved path, st_size, st_mtime_ns)` from `path.stat()` alone: a same-size, same-mtime replacement or in-place rewrite was not seen on any system. After the fix, on Windows a replacement (another file id) is seen and only an in-place rewrite that keeps size and mtime is not; on POSIX both are seen. Strictly no worse than main anywhere.

Structure (4a): no concern, flag, module-level mutable, seam, platform branch or private API added; `_digest` stays at 21 lines. The docstring names Windows to say why the key is taken by name, not to branch on it.

## Findings, most severe first

1. **Note — a file system without `FileIdInfo` is never cached on Windows** (`_artifacts.py:240`). If `GetFileInformationByHandleEx(FileIdInfo)` fails on the descriptor, `_Py_attribute_data_to_stat` falls back to the 32-bit `dwVolumeSerialNumber`, while the by-name fast path reports the 64-bit serial; `samestat` may then be false and each call hashes again. Failure: performance only, in the safe direction (no stale digest). No fix needed; NTFS and ReFS give `FileIdInfo`.
2. **Note — the in-place limit on Windows is the same as main's or better** (item 9). No fix needed; the landing notes already state it.

No High, Medium or Low finding.

## Constitution checks

- §4 constraints touched: none of the artifact set, the guest's imports or exports, or the build recipe. uv only (held). Tests count operations, never time (held: `os.open` is counted).

## Verdict

Lands: the key and the lookup now take the same route on every system, `samestat` keeps the hashed file and the keyed file one file, and the existing check is unchanged.
