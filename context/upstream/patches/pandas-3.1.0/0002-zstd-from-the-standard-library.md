- **Project:** pandas (https://github.com/pandas-dev/pandas)
- **Against:** 3.1.0 (the pinned tarball)
- **Status:** drafted
- **Title:** ENH: read and write zstd through the standard library's compression.zstd when python-zstandard is missing
- **Files:** pandas/io/common.py
- **Why we carry it:** pandas' `compression="zstd"` (and every `.zst` path) imports the third-party `zstandard`, which the set does not carry, while the guest's CPython 3.15 has the standard library's `compression.zstd` (PEP 784) built over libzstd 1.5.7. Without the patch, `to_csv(path, compression="zstd")` raises pandas' missing-dependency `ImportError` ("`Import zstandard` failed").

**This is a facts sheet, not pull request text.** pandas lets a contributor use AI tools to write code, but not to speak for them in issues, pull requests or reviews (its contributing guide, "Automated contributions policy", and its `AGENTS.md`; the first patch's draft, `0001-styler-templates-from-a-zip.md` beside this one, gives the policy's points in full). So the owner writes any comment or pull request in their own words, from the facts below, after reviewing and changing the code as pandas asks. Nothing here has been posted, and no agent will post anything to pandas. The agent's work was done in Claude Code with Claude Opus 5.5 (`claude-opus-5-5`); its reasoning setting was not recorded, so do not guess it.

## Upstream's state

READ on 2026-10-31 with `gh`:

- pandas' `main` (d834961c, 2026-10-30) has the same zstd branch as 3.0.6 and 3.1.0: `import_optional_dependency("zstandard")`, then `zstandard.ZstdDecompressor` or `ZstdCompressor` from the options. No commit adds `compression.zstd`, so there is nothing to backport.
- Issue pandas-dev/pandas#62365, "ENH: Add support for the standard library `compression.zstd`", is open. Its author's revised proposal (comment of 2026-10-06) makes `compression.zstd` (or `backports.zstd` before 3.14) the primary implementation, chooses the implementation from the option names, keeps `python-zstandard` for its own options with a deprecation warning, and asks the maintainers about a fallback when the preferred module is missing. No maintainer has answered, and nobody holds the issue (the bot unassigned the last claimant on 2026-08-18).
- So the issue is the place to speak, not a new pull request: the route in pandas' guide is a comment there, a maintainer's answer, then `/take`.

## The change

The smallest step toward #62365 that changes nothing for an install that has `python-zstandard`: in `get_handle`'s zstd branch, `zstandard` is imported with `errors="ignore"`. When it is missing and `compression.zstd` imports, the handle is `compression.zstd.ZstdFile(handle, mode=..., **options)`. When neither imports, the old error is raised by the old call, word for word.

The options: `ZstdFile` takes `level` when writing and refuses it when reading (`TypeError: level is illegal in read mode`, CPython 3.15.2 `Lib/compression/zstd/_zstdfile.py`). The patch forwards `level` only when writing, and raises `TypeError` naming any other key (`threads`, `write_checksum`, any key on read), as `zstandard.ZstdCompressor` and `ZstdDecompressor` raise for a key they do not take. No key is dropped silently.

`ZstdFile` is an `io.BufferedIOBase`, so `_get_binary_io_classes` needs no change, and pandas' text wrapping, the `.zst` suffix inference and buffers work as they do for `bz2` and `xz`.

This differs from #62365's proposal in its order: `python-zstandard` stays first wherever it is installed, so nothing changes for today's users, and the standard library serves only where it is absent. A maintainer who prefers the proposal's order (standard library first, options deciding) would rewrite the branch; the tests below serve either.

## How it was tested

EXECUTED in the guest (CPython 3.15.2 for `wasm32-wasip1`, no `zstandard`), with pandas 3.0.6 patched on 2026-10-31 and with pandas 3.1.0 patched on 2026-11-01; the check is `test_pandas_zstd_reads_and_writes_through_the_standard_library` in this repository:

- `to_csv(path, compression="zstd")` and `to_csv("frame.csv.zst")` write frames that `compression.zstd.open(path, "rt").read()` returns as `to_csv()`'s text, and `read_csv` gives the frame back, the second with the method inferred from the suffix;
- a `BytesIO` handle works both ways;
- `to_pickle` and `read_pickle` with `compression="zstd"` round-trip;
- `{"method": "zstd", "level": 19}` writes;
- `{"method": "zstd", "threads": 2}` raises `TypeError` naming `threads`, and `level` on read raises `TypeError` naming `level`.

Before the patch, the first call raised pandas' missing-dependency `ImportError` ("`Import zstandard` failed").

pandas' own zstd tests use the `compression` and `compression_only` fixtures, whose zstd parameter is skipped without `zstandard` (`pandas/conftest.py`, `td.skip_if_no("zstandard")`). For upstream, those marks would become "skip unless `zstandard` or `compression.zstd` imports", so the existing round-trip tests run through the new branch on Python 3.14 and later. That is the test the pull request needs; the carried patch has none, since the guest's pandas suite cannot run these fixtures' zstd cases until the marks change.

## Base

Against 3.1.0; first made against 3.0.6, whose branch is the same code one indent shallower. pandas' `main` has the same branch at a different line (READ 2026-10-31). When asked, an agent rebases the change onto `main` in a scratch clone and hands the owner the branch and these facts. It never writes the comment or the description and never touches GitHub.
