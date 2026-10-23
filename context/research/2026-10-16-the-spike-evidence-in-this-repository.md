# The spike's evidence, brought into this repository

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: one hour.
- **Supersedes:** every path in `2026-10-16-the-spike-that-proved-the-build.md` that points into the vfs repository. That memo is not edited; this one maps its paths.
- **Feeds:** the build specification that scripts the recipe end to end; `README.md`'s *Evidence* section.

## Why

The owner asked that this repository stand alone: nothing needed to build, verify or understand wasi_python may live only in the vfs repository. The spike that proved the build ran there, and its outputs, its link lines and its hand-made steps were there alone.

## What came in, and where it is (EXECUTED)

Copied 2026-10-16 from the vfs repository's `context/research/studies/2026-10-15-agent-shell/experiments/s12/`:

| spike path | here | what |
|---|---|---|
| `outputs/*` (78 files, less `pyodide-recipes/`) | `2026-10-16-the-spike-that-proved-the-build/outputs/` | every command output, log and JSON record the spike memo cites |
| `cross/Setup.local.generated`, `cross/Setup.local.pandas.generated` | the same `outputs/` directory | the exact `Modules/Setup.local` link lines the build generated (absolute paths of the spike's machine) |
| `build/numpy-host-shim/numpy/__init__.py` | `2026-10-16-the-spike-that-proved-the-build/numpy-host-shim/__init__.py` | the host-side numpy stand-in the pandas build imported; never scripted |
| `build/` (2.9 GB) | `2026-10-16-the-spike-that-proved-the-build/build-tree-inventory.txt` | an inventory of what each unscripted step produced, not the bytes |
| `cross/*` (the other ten files) | `recipes/` | byte-identical (EXECUTED: `cmp` on each) |
| `scripts/*` | `scripts/` | identical except `cross/` → `recipes/` in three paths (EXECUTED: `diff`) |
| `fixtures/*` | `fixtures/` | byte-identical (EXECUTED: `cmp`) |

Total: 75 files, 1.6 MB, none over 500 KB (EXECUTED: `du -sh`, `find -size +500k`). A scan for keys, tokens and passwords found only compiler file names (`token.c`, `tokenizer`). The four `.txt` copies that sat at the top of `context/research/` were identical to files in `outputs/` (EXECUTED: `cmp`) and were removed.

**How to read the spike memo now:** `experiments/s12/outputs/X` is `2026-10-16-the-spike-that-proved-the-build/outputs/X`; `experiments/s12/cross/X` is `recipes/X`; `experiments/s12/scripts/X` is `scripts/X`.

## What did not come in, and why

- **`outputs/pyodide-recipes/`**: seven `meta.yaml` files copied from Pyodide's recipes (MPL-2.0). They are other people's work; this project studies them through the `context/prior_art/pyodide-recipes` clone (indexed in `context/prior_art/README.md`), never as copies (constitution §4.7).
- **`shim/run_vfs.py`**: the embedder's preview1 shim, which imports the vfs repository's own `experiments/s4/shim.py`. It is embedder code (§4.5). Its job here, running the guest and counting work, is done by the harness's driver (`tests/harness/guest.py`). The counts it produced are in `outputs/`.
- **`build/` and `downloads/`**: regenerated from the pins in `downloads/SHA256SUMS`; artifacts never live in git (§4.6).
- **The vfs project's studies 04, 05, 11 and 12, its specifications 172 and 173, and its ADR 086**, which the spike memo cites as background. They are the vfs project's design history. Every fact this project relies on from them is restated in the spike memo itself, with its output now here. INFERRED: nothing in this repository's work needs them.

## What the inventory shows about the unscripted steps (READ)

The spike's scripts stop short of a build anyone can re-run. Read from `build-tree-inventory.txt` and the spike memo's executed log, these steps were done by hand:

1. **`host-pylib/`**: Cython 3.3.0 and versioneer 0.29, installed with `uv pip install --target` for the native build-Python (READ: spike memo finding 6.2; EXECUTED: `INSTALLER` reads `uv`), with no hashes. Needed by pandas' `generate_pxi.py` and its Cython build.
2. **`numpy-host-shim/`**: `__init__.py` (the file brought in), numpy's `__init__.pxd` and `__init__.cython-30.pxd`, and `_core/include/` (numpy's sdist headers plus the three the WASI build generates: `_numpyconfig.h`, `__multiarray_api.h`, `__ufunc_api.h`).
3. **`pandas-install/`**: a `meson install --destdir` of the pandas build into `usr/local/lib/python3.14/site-packages/pandas/` (536 KB, part of the Python tree), and **`pandas-py/`**: pandas' whole pure-Python tree from its sdist (8.8 MB, `conftest.py` and `meson.build` included), which is what went into the zip.
4. **`pandas-deps/`**: python-dateutil 2.9.0.post0, tzdata 2026.5 and six 1.17.0, installed with `uv pip install --target` (EXECUTED: each `dist-info/INSTALLER` reads `uv`), with no hashes.
5. **`pandas-shims/`**: `ctypes.py` and `mmap.py`, which are `recipes/ctypes_stub.py` and `recipes/mmap_stub.py` under the module names pandas imports.
6. **`wizer-root/` then `wizer-root2/`**: the two Wizer `--mapdir` roots. The first (`lib/python314.zip`) was the wrong shape; the second (`usr/local/lib/python314.zip`) is the one the spike memo's finding 7 settles on.
7. **The final zip**: `python314-pandas-deflated.zip` holds **sources** (`1033 python files (py)`, `outputs/zip_pandas_deflated.txt`), while the README records the decision that the shipped zip is bytecode-only. INFERRED: a scripted build must compile with the 3.14 build-Python (`make_stdlib_zip.py --pyc`), and the zip's size will differ from the spike's 6,050,752 bytes.

Two inputs were never pinned by hash: the pure-Python packages of step 4 and the build tools of step 1 (the spike's `.venv-build` held Cython, meson, ninja and versioneer from an unlocked install). Their wheels' URLs and SHA-256s, read from PyPI's JSON API on 2026-10-16, are recorded for the build specification:

```
a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427  python_dateutil-2.9.0.post0-py2.py3-none-any.whl
b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac  tzdata-2026.5-py2.py3-none-any.whl
4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274  six-1.17.0-py2.py3-none-any.whl
0deedc2e9a5a664e1adfa4c2d310aa7b54903e1a647c274b6c9213f77a02d637  cython-3.3.0-cp314-cp314-macosx_11_0_arm64.whl
9b24b5c8cd536946b62086fcafee6d5509d3f549f72d553d2336af87ffbe0da1  cython-3.3.0-py3-none-any.whl
930bc7542cbd9f57009e182fd014eba48cf1a0180a7b9006d2d32d8f168d8b02  meson-1.12.1-py3-none-any.whl
0f1a137bb5d6811e96a79bb0486798aeae9b9c6efc24b389659cebb0ee396cb9  versioneer-0.29-py3-none-any.whl
66b07ef7315a31bfe1089cd3d71a7de781c9dca986762d0b4fe7c0ef17465d10  pandas-3.0.6.tar.gz
```

(the pandas sdist's hash equals the existing pin, so its literal URL can replace the download script's lookup at fetch time). The ninja 1.13.2 query returned no macOS arm64 wheel under the filter used; the build specification resolves it.

## One line

The repository now holds every output, link line and hand-made file the spike left behind, and says what it left out and why, so nothing here needs the vfs repository.
