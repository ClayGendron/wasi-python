# What host memory a guest can hold

- **Status:** research, 2026-10-27. The measurement Decision 3 of `../specifications/146-the-tool-hosts-bounds-are-the-processs.md` asks for: the peak host memory of one guest that holds its linear memory near `memory_bytes` and stages a writable mount's file to the staging bound. It changes nothing: no code in `src/`, no pin. The number is a benchmark fact, never a check.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the builder of specification 146. Box: one run of each arm, one after another, in one session.
- **Evidence:** the program in §2, whole, and its two output lines in §3. No file beside this memo.
- **Stands on:** `src/wasi_python/_call.py` (`staging`, from `memory_bytes`), `src/wasi_python/_fs_table.py` (`_fits`, `_write_back`'s `bytes(entry.data)`), `src/wasi_python/_fs_descriptors.py` (`_fd_write`, `_grow`); `2026-10-27-a-code-review-of-the-runner-for-production-use.md` §3, Medium 5, which inferred the bound and did not measure it.
- **Machine:** darwin-arm64, Apple M1 Pro, 32 GiB, macOS 26.5.2; CPython 3.14.10, wasmtime-py 50.0.1; the published 0.1.1 artifact set, read only; branch `spec/146-the-tool-hosts-bounds-are-the-processs` at `0a5b5c08`, on `dev` `898bc091`, before its rebase; no file the measurement reads (`_call.py`'s staging, `_fs_table.py`, `_fs_descriptors.py`) changed after it. Two other agents ran their fast tiers on the machine at the time; the peak resident set is a count of pages, not of time, so their load moves it little.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **One guest at the default `memory_bytes` of 1 GiB held 2.80 GiB of host memory above an idle call's peak** (EXECUTED, §3): 3,010,609,152 bytes, the peak resident set of a full arm less that of a control arm.
2. **The three allocations the code names account for it** (READ, INFERRED): the linear memory the guest touched (832 MiB of ballast and the interpreter's own pages), the staging buffer grown to the bound (1,024 MiB, `_grow`), and the copy handed to the provider at the close (1,024 MiB, `bytes(entry.data)` in `_write_back`). Their sum is 2,880 MiB; the measured difference is 2,871 MiB.
3. **So an embedder budgets three times `memory_bytes` for a guest with a writable mount**: about 3 GiB at the default, where the limits page used to let it budget one. The pages now say so.

## 1. The three allocations (READ)

The call's staging bound is `memory_bytes`, or 4 GiB when it is `None` (`_call.py`, `staging`). A write at an offset past a buffer's end grows the buffer with zeros to that offset (`_fd_write`, `_grow`), judged first against the bound on the new size (`_fits`), so one `pwrite` of one byte at `memory_bytes - 1` stages `memory_bytes` bytes. At the close the whole buffer is copied once more, `bytes(entry.data)`, and the copy is the provider's to keep (`_write_back`). The guest's linear memory, up to `memory_bytes`, is a third allocation beside both.

## 2. The program (EXECUTED)

One Python program, run twice as a fresh process through `uv run python`, with `WASI_PYTHON_ARTIFACTS` at the 0.1.1 set. Each run calls `run` once with `memory_bytes=1 << 30` and one writable mount whose provider keeps every file it is handed in a dict, then prints `resource.getrusage(RUSAGE_SELF).ru_maxrss` (bytes on macOS). The control arm's guest runs `print(1)`. The full arm's guest runs:

```python
import os
ballast = b"\x01" * ((1 << 30) - (192 << 20))  # linear memory touched, near the bound
fd = os.open("/work/big", os.O_WRONLY | os.O_CREAT)
os.pwrite(fd, b"x", (1 << 30) - 1)  # staging grows to the bound
os.close(fd)  # the whole file is handed to the provider
print(len(ballast))
```

The ballast leaves 192 MiB of the guest's memory for the interpreter, so the guest neither traps nor raises `MemoryError`; a ballast closer to the bound is possible and would add at most those 192 MiB.

## 3. The result (EXECUTED)

```
control 0 None 1 b'' held 0 peak_bytes 262766592
full 0 None 872415232 b'' held 1073741824 peak_bytes 3273375744
```

Both arms exited 0 with nothing trapped. The provider held a file of 1,073,741,824 bytes, the staging bound exactly. The control arm's peak, 250.6 MiB, is the process: Python, wasmtime, the compiled module and an idle guest. The full arm's peak is 3,273,375,744 bytes, 3.05 GiB. The difference, 3,010,609,152 bytes or 2.80 GiB, is what this one guest held above an idle one: 2.80 times `memory_bytes`; with the ballast at the bound it would be about 3.0 times (INFERRED: 192 MiB more of touched linear memory).

## 4. What follows (INFERRED)

The bound is the sum of three allocations, each up to `memory_bytes`, and the measurement meets it within 9 MiB. N untrusted guests with writable mounts, run at once, need about 3N GiB of host memory at the default, not N. `docs/how-to/limits.md`, `docs/how-to/mounts.md` and `docs/reference/defaults-and-limits.md` now state the three-times budget. Counting the handed-over copy against the staging budget would bring the bound to two times; it is a change to the mounts' contract, out of specification 146's scope, waiting for an embedder who needs it. A guest with only read-only mounts has no write-back copy (INFERRED from `_write_back` being reached only for a dirty buffer); it was not measured here.

## One line

One guest at the default 1 GiB, holding its memory and staging a writable mount's file to the bound, held 2.80 GiB of host memory above an idle call (EXECUTED), the sum of its linear memory, its staging buffer and the copy handed to its provider, so an embedder budgets three times `memory_bytes` per such guest.
