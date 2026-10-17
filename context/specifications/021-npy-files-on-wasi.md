# 021 — `.npy` files on WASI: the first carried patch

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** a carried patch (`recipes/patches/numpy-2.5.2/`), its pull request draft
  (`context/upstream/patches/numpy-2.5.2/`), a judge addition in `tests/checks/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 020 (carried patches: the applier, the rules, the patched zero-diff check),
  which must land first.
- **Research it stands on:** `../research/2026-10-17-numpy-npy-files-need-dup.md` and
  `../upstream/3-numpy-npy-wasi/` (`notes.md`, `fix.patch`, `pr.md`, `evidence/`): `np.save`
  to a path and `np.load` of a path fail in the guest, because numpy hands real files to
  `tofile`/`fromfile`, which call `os.dup`, and WASI cannot duplicate a descriptor
  (`OSError(58, 'Not supported')`, EXECUTED there). The owner's answers to question 8 (file
  upstream, after reading the text) and question 32 (carry fixes; do not wait).

## The problem

`np.save("a.npy", x)` writes the header and then raises; `np.load("a.npy")` raises. Code that a
model writes saves arrays this way often. The fix is upstream's to take, and its text waits for
the owner (numpy's AI policy: the owner writes the pull request description). Under the amended
§4.1 the project carries the fix now.

## Decisions

1. **The patch is the runtime half of the upstream fix.**
   `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch` changes one file,
   `numpy/lib/_format_impl.py`: `import sys`, and in `isfileobj`, before its `fileno()` probe,

   ```python
   if sys.platform == "wasi":
       # `tofile` and `fromfile` need `os.dup`, which WASI does not
       # support, so read and write real files like other file-likes.
       return False
   ```

   It is `../upstream/3-numpy-npy-wasi/fix.patch`'s first file, re-made against the pinned
   2.5.2 tarball (its hunks sit at lines 164 and 1029 there, against `ac61120`'s 165 and 1038), so
   the applier takes it with no offset. The upstream pull request also adds a test to
   `numpy/lib/tests/test_format.py`; tests are not built into the guest, so the carried patch
   leaves it out, and the draft says so.
2. **The pull request draft** is `context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md`,
   with spec 020's six header lines (`Files: numpy/lib/_format_impl.py`; `Status: drafted`). Its
   body does not write the pull request description: numpy's AI policy asks the contributor to
   write it. The body points the owner to `../upstream/3-numpy-npy-wasi/pr.md` (the facts under
   numpy's template headings), names the upstream base and the test the pull request adds, and
   notes numpy's AI disclosure.
3. **What it changes in the artifact set.** `_format_impl.py` is in the stdlib zip as bytecode,
   so the zip changes, and with it the snapshot (it holds the zip's offsets and pre-imports
   numpy). `python.wasm` does not change. `MANIFEST` gains the patch's `recipe` line. The
   `.npy` path is not on any judge program's way, so the judge's fuel should not move
   (INFERRED; any growth is accepted with its reason).
4. **The check** (v1.3, `test_npy_files_round_trip`, both binaries): in the guest, `np.save` to a
   path under `/tmp` and `np.load` of it, for a plain array, a record array, a 0-d array, a
   Fortran-ordered array and an object array (`allow_pickle=True`), and `np.savez` /
   `np.load` of an `.npz`; each loaded array equals the saved one. It is seen failing first on
   the current artifact set (`OSError` 58).
5. **Docs.** The README's data-stack facts: `np.save`/`np.load` of paths work, through a carried
   patch until numpy releases the fix. The CHANGELOG names the patch's path (spec 020's rule) and
   the README's count becomes 1.

## Intent

`np.save` and `np.load` work in the guest today, by the exact change the project asks numpy to
take, and the patch goes when numpy releases it.

## Design

```
recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch
context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md
tests/checks/test_v1_3_data_stack.py   test_npy_files_round_trip
README.md, CHANGELOG.md
```

The artifact set is rebuilt from step 40 (numpy unpacks, the patch applies, then 50 to 90).

## Scope

In: the above. Out:
- `np.memmap` and `open_memmap` of a path: they need `mmap`, which WASI does not have
  (`../upstream/3-numpy-npy-wasi/evidence/guest-memmap-probe.txt`); a known gap, not this fix.
- Sending the pull request: the owner's (§7, and numpy's policy).

## Acceptance criteria

1. The check exists and was seen failing on the current artifact set.
2. A full build from pins in a clean clone applies the patch at step 40 (the step log names it)
   and makes a set whose `python.wasm` equals today's byte for byte, and whose zip differs from
   today's only in `numpy/lib/_format_impl.pyc` (and the snapshot with it).
3. `uv run pytest` is green with `--accept-judge`; the rules check passes with the draft, the
   CHANGELOG line and the README count.
4. A release dry run passes every job, the same-bytes rebuild on arm64 Linux included.

## Landing notes

Not built.
