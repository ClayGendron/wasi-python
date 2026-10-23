# Upstream 6: networkx's graph atlas from a zip archive

Status: **patch and test drafted; `pr.md` is a facts sheet, and anything filed upstream is the owner's, in the owner's words** (networkx's automated contributions policy, see `pr.md`). Nothing was posted. Carried by spec 041 (`recipes/patches/networkx-3.7/`).

## How it was found

Spec 039's drafting ran `nx.graph_atlas(100)` in the guest and saw the `TypeError`; spec 039 made it a known gap with a check; spec 041 closes it with this patch.

## The fix

Carried since spec 041 was built (2026-10-19): `fix.patch` was copied byte for byte (`cmp`) to `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch` and removed from this folder, and `pr.md` (a facts sheet, question 80) moved unchanged to `context/upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md`. This folder keeps these notes and `evidence/`; the `fix.patch` named below is now that carried file.

`fix.patch` (2 files, +16 −1): `_generate_graphs` opens `ATLAS_FILE` with its own `open("rb")` and hands the file object to `gzip.open`; `test_atlas_file_in_a_zip` reads the atlas through a `zipfile.Path`. SHA-256 `3b8b6d2d6c7dff34e6cdd727be84a66f283aaaa555c12503995f4cb46d9b5384`; it applies to the `networkx-3.7.tar.gz` sdist (SHA-256 `fd77a511…e96a`, equal to PyPI's) with `git apply` and no offset (EXECUTED).

## Evidence

All under `evidence/`, run 2026-10-17 while drafting spec 041.

| file | what | label |
|---|---|---|
| `files.py` | the probe (see upstream 5) | ours |
| `guest-run.txt` | the guest before (`TypeError`) and after (equal to native) | EXECUTED |
| `networkx-native.txt` | the new test failing without the fix and passing with it; the generators' tests (598 passed, 34 skipped on uv's CPython 3.15.0a3 without numpy or pandas; the pre-build review got 614 passed, 18 skipped on the line's 3.15.0 with them); the one-line reproducer with the stock wheel on `PYTHONPATH`, and the patched package zipped | EXECUTED |
