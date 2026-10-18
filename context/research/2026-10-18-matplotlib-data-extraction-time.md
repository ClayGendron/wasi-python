# What extracting matplotlib's data costs the runner

- **Date:** 2026-10-18
- **Labels:** EXECUTED unless marked. Wall-clock times are benchmark facts on one machine
  (constitution §4.9), never a check's bound.
- **Feeds:** spec 023, Decision 5 ("its time goes in the memo as a benchmark fact"), and its
  build review's F5.

## The question

The runner extracts `matplotlib/mpl-data.zip` from its private copy of the stdlib zip once per
process, at the first call, plotting or not, and compares the extracted tree with its record
before every call (spec 023, Decision 5). How long does each take?

## Method

The final set of spec 023's build (`python-stdlib.zip` `16ee747c…`, 21,948,256 bytes) on
darwin-arm64, an M-series Mac with 10 cores, shared with other sessions. The script, run from the
worktree root with `uv run python`, calls the runner's own functions five times each, in fresh
folders under `build/harness/`:

```python
for _ in range(5):
    d = Path(tempfile.mkdtemp(dir="build/harness"))
    t = time.perf_counter(); rec = runner._extract_data(d / "mpl-data", zip); ext.append(time.perf_counter() - t)
    t = time.perf_counter(); ok = runner._data_intact(d / "mpl-data", rec); chk.append(time.perf_counter() - t)
    shutil.rmtree(d)
```

`_extract_data` reads the deflated outer member whole, writes each of the inner archive's files,
reads each back and compares its CRC-32 and size, and records every path. `_data_intact` walks
the tree with `lstat` and compares names, types and stamps with the record.

## Findings

| run | load average | extraction (204 files, 9 folders, 9.7 MB) | per-call comparison |
|---|---|---|---|
| spec 023's landing notes | not recorded | 92.9, 89.6, 89.1, 101.8, 88.4 ms; median 89.6 ms | median 2.39 ms |
| for this memo | 22 (1 min), 21 (5 min) | 80.7, 77.9, 73.9, 77.8, 77.9 ms; median 77.9 ms | 2.51 to 2.73 ms; median 2.67 ms |

- **Once per process, about 80 to 90 ms.** It is paid at the process's first call, beside the
  zip's own copy and its SHA-256, and before the call's deadline starts (READ: `_run_checked`
  calls `_zip_folder` before `_call`).
- **Every call, about 2.5 ms of host time** for the comparison: about a tenth of a 20 ms snapshot
  call (the README's figure). INFERRED: a stamp kept per folder, or a check only every Nth call,
  would cut it; neither is proposed, because the comparison is what lets the runner notice a
  temporary-folder cleaner or a tampering process before it grants the folder.

## One line

Extracting matplotlib's data costs a process about 80 to 90 ms once, and checking it about 2.5 ms
per call, on this machine.
