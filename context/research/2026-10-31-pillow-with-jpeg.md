# Pillow with JPEG, a spike

- **Status:** research, 2026-10-31. A time-boxed spike the owner chose on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3": "two time-boxed research spikes whose product is a memo each"). It changes nothing: no code under `src/`, `recipes/`, `scripts/` or `tests/`, no pin, no specification. Times are wall-clock on one loaded machine (load average 85 to 140 on 10 cores): benchmark facts, never checks.
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), a spike sub-agent of the orchestrating session
- **Evidence:** the worktree's `build/spike-jpeg/` (git-ignored): `prog/probe.c`, `prog/pil.sh`, `link/cmd.txt`, `prog/guest_jpeg.py`, `prog/guest_pytest.py`, `prog/fuel.py`, `prog/imports.py`, and their outputs. Read only from the main tree's `build/`: wasi-sdk 34.0 and wasmtime 49.0.3, the Pillow 13.0.0 tree, CPython's cross-build objects, `link/reactor-commands.txt`, and `build/artifacts` (the build of 2026-10-21).
- **Stands on:** `2026-10-30-what-0-1-3-could-carry.md` item G; `scripts/steps/37_plot_libs.sh`, `55_matplotlib.sh`, `60_link.sh`; `recipes/wasi-plot-libs.cross`; `tests/upstream/pillow.toml`; `../constitution.md` §4.12.

Labels: EXECUTED means run here; READ means read from a page or file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **libjpeg-turbo 3.2.0 builds for wasm32-wasip1 as it is.** The pinned wasi-sdk 34, SIMD off, the build's own setjmp flags: 101 objects, no warning, no patch, 14 seconds at `-j2`. EXECUTED.
2. **The guest already does setjmp and longjmp** (FreeType, qhull). A Pillow-style error handler that longjmps out of libjpeg works under wasmtime 49.0.3 and wasmtime-py 50.0.1, metered or not. EXECUTED.
3. **Pillow's `_imaging` links libjpeg statically.** Step 55's compile with `-DHAVE_LIBJPEG` and the setjmp flags, plus the archive on the link, gives a `python.wasm` with the same imports, exports and exception tags. Pillow's own JPEG and MPO tests pass in it: 141 passed, 2 skipped. EXECUTED.
4. **The cost is small.** The binary grows by 520,798 bytes (0.52 %), about 103 KiB compressed. The zip does not grow. Fuel outside JPEG does not move. One decode costs about 280 fuel per pixel. EXECUTED. The licences are IJG and BSD-3-Clause. They need the owner's approval under §4.12. READ.
5. **Recommendation: a specification for 0.1.3.** It is a build-recipe change with no patch, no new import and nothing in `src/`. INFERRED.

## 1. The pins (READ, EXECUTED)

Pillow 13.0.0 pins libjpeg-turbo 3.2.0. Its `.github/dependencies.json` at tag 13.0.0 says `"jpegturbo": "3.2.0"` (READ: https://raw.githubusercontent.com/python-pillow/Pillow/13.0.0/.github/dependencies.json, fetched once). The sdist does not carry that file; its `winbuild/build_prepare.py` reads it (READ). libjpeg-turbo's release page names 3.2.0's source tarball. It shows the date as "30 Jun" and gives no hash (READ: https://github.com/libjpeg-turbo/libjpeg-turbo/releases/tag/3.2.0). The tarball was fetched once: 2,537,858 bytes, SHA-256 `6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e` (EXECUTED). It unpacked only under the worktree's `build/spike-jpeg/src/`.

## 2. libjpeg-turbo builds (EXECUTED)

The spike configured it with CMake and wasi-sdk's own `share/cmake/wasi-sdk-p1.cmake`. The C flags were the cross file's setjmp flags (`-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`) and `-O2 -DNDEBUG`. The options were `WITH_SIMD=0`, `ENABLE_SHARED=0`, `WITH_TURBOJPEG=0`, `WITH_TOOLS=0`, `WITH_TESTS=0` and `WITH_JPEG8=1`, the last as Pillow's own Windows build sets it.

- `make -j2` built `libjpeg.a` in 14 s. Zero warnings. No source change.
- The archive is 632,412 bytes and has 101 members. Its code and data total 437,627 bytes (`llvm-size`).
- Its undefined symbols are libc's alone: `malloc`, `free`, `fread`, `fwrite`, `fprintf`, `getenv`, `sscanf`, `exit` and a few more. The library itself never calls setjmp. Only its caller does.
- Version 3 compiles most files again for 12- and 16-bit samples. The link kept 91 of 101 members; dropping the 12- and 16-bit copies would take a patch, not worth one.

The product's build has no CMake. A specification would compile the sources directly, as step 37 compiles qhull: the list is one `set(JPEG_SOURCES …)` in `CMakeLists.txt` plus the three arithmetic-coding files, and its 88 wrapper files ship in the tarball. The three configured headers (`jconfig.h`, `jconfigint.h`, `jversion.h`) would be recipe files. INFERRED.

## 3. setjmp and longjmp under the runner's wasmtime (EXECUTED, READ)

The product already depends on this. FreeType's validators and qhull's `qh_errexit` longjmp, `-lsetjmp` is on the `_host` link line, and `test_a_flat_convex_hull_raises_qhullerror` holds it. READ.

The probe, `prog/probe.c`, links the spike's `libjpeg.a`. It installs an `error_exit` that formats the message and longjmps, as Pillow's `JpegDecode.c` and `JpegEncode.c` do. Under `wasmtime run -W exceptions=y` (49.0.3) it printed:

```
plain: longjmp returned 7
testorig: 227x149 x3 fnv=f29cc190 warnings=0
truncated: 227x149 x3 fnv=7276a837 warnings=2
not-a-jpeg: caught longjmp: Not a JPEG file: starts with 0x42 0x42
bad-sof: caught longjmp: Unsupported JPEG data precision 3
loop: 1000 longjmps caught
encode: 991 bytes fnv=6ea06435
roundtrip: 64x48 x3 fnv=df0afe64 warnings=0
```

wasmtime-py 50.0.1 printed the same lines, fuel metering off and on (`prog/run_py.py`). A native arm64 build of the same tarball, SIMD off, printed the same lines byte for byte. So decode and encode match native when SIMD is off. Native SIMD on was not tried. Pillow's wheels use SIMD, so a golden is recorded from the guest or from a SIMD-off build. INFERRED.

## 4. Pillow's `_imaging` links libjpeg (EXECUTED)

Pillow's JPEG sources are already in step 55's list; `HAVE_LIBJPEG` turns them on. Without the setjmp flags, `JpegDecode.c` stops at wasi-libc's `setjmp.h`: "#error Setjmp/longjmp support requires Exception handling support". With them, the object imports `__wasm_setjmp`, `__wasm_setjmp_test`, `__wasm_longjmp` and `__c_longjmp`. `-lsetjmp` provides them.

`prog/pil.sh` compiles step 55's own source list as step 55 does, plus `-DHAVE_LIBJPEG`, libjpeg's two include folders and the setjmp flags. It gave one warning, the `_XOPEN_SOURCE` redefinition `pyconfig.h` causes. The archive grew from 451,696 to 463,532 bytes.

The relink reran step 60's recorded reactor link (`reactor-commands.txt`, line 5) with the output paths, the JPEG `_imaging.a` and `libjpeg.a` substituted. No `signature mismatch`, no `duplicate symbol`. The unchanged link, run the same way, is the baseline; both were stripped as step 60 strips.

| | baseline relink | with JPEG |
|---|---|---|
| `python.wasm`, stripped | 99,421,511 | 99,942,309 (+520,798) |
| gzip -6 | 21,316,047 | 21,421,271 (+105,224) |
| code section | 0x46e6a6a | 0x474e56a (+424,704) |
| data section | 0xa3fd82 | 0xa52ac2 (+77,120) |
| imports / exports | 43 / 7 | 43 / 7, the same names |
| tag section | 5 bytes | 5 bytes |

The baseline relink is 2 bytes shorter than the 0.1.2 build's `python.wasm`, and its hash differs. So the growth is measured against the relink.

That binary ran through the product's own `run()`, with the zip and MANIFEST of `build/artifacts`, `snapshot=False` (`prog/guest_jpeg.py`):

- `PIL.features.check("jpg")` and `check_feature("libjpeg_turbo")` are true, and the API version is "8.0".
- `Image.open` of `testorig.jpg` decodes to 227×149 RGB, FNV `f29cc190`, the native SIMD-off value.
- `save(…, "JPEG")` works with the defaults, `quality=95`, `progressive`, `optimize`, and `quality=50, subsampling=0`. Each file opens again.
- A broken Huffman table or a bad SOS component raises `OSError: broken data stream when reading image file`. That is Pillow's longjmp path. It does so 300 times in a loop, and the next good decode works.
- matplotlib's `savefig(…, format="jpg")` writes a 400×300 JPEG of 9,428 bytes.

Pillow's whole `Tests/` folder ran in the guest on both binaries (`prog/guest_pytest.py`). The run used the judge's pytest options (`-p no:faulthandler --capture=sys`, a log file under `/tmp`) but not its driver. So these are the spike's numbers, not the judge's.

| | failed | passed | skipped | xfailed |
|---|---|---|---|---|
| zlib only | 81 | 4,587 | 1,054 | 3 |
| with JPEG | 30 | 4,782 | 910 | 3 |

No test fails only with JPEG. 51 failures clear. `test_file_jpeg.py` and `test_file_mpo.py` alone give 141 passed and 2 skipped ("djpeg not available", "Windows only"). None of the 55 node ids in the judge's `pillow-zlib-only` allowance fails with JPEG. The 30 that remain fail on the zlib-only binary too. 27 are in the judge's existing allowances (no mmap, the DDS timeouts, the empty path and others). The other 3, in `test_main.py`, fail on an `os.dup` in the spike's harness. They are in no allowance, so the judge's driver must not meet it. INFERRED.

## 5. What it would cost

- **Binary.** +520,798 bytes stripped, about +103 KiB gzipped. EXECUTED. The wheel carries the binary compressed, so it grows by roughly that. The snapshot grows by about the binary's growth. INFERRED: the snapshot was not rebuilt.
- **Zip.** None. `PIL/JpegImagePlugin.pyc`, `JpegPresets.pyc` and `MpoImagePlugin.pyc` are already in it. EXECUTED.
- **Fuel outside JPEG.** `import PIL.Image` cost 543.0 M to 543.9 M on both binaries, run to run. That spread is noise, not growth. EXECUTED. Existing checks should not move. INFERRED.
- **Fuel of a decode.** The C probe spends 9.33 M per decode of the 227×149 test image. Through Pillow it is 9.43 M, so about 280 fuel per pixel. The first `Image.open` in a process also pays 287 M, mostly importing the plugin. EXECUTED. A 12-megapixel photo would cost about 3.3 G fuel, and its 36 MB RGB buffer fits the 1 GiB default memory. INFERRED by scaling.
- **Licences** (READ: the tarball's `LICENSE.md` and `README.ijg`). The libjpeg API library, the only part linked, is under the IJG License. Its condition (2) is the one that binds a binary-only distribution. The documentation must say "this software is based in part on the work of the Independent JPEG Group". BSD-3-Clause covers TurboJPEG, the tools and the build system, whose templates give the three configured headers. The zlib licence covers the SIMD code, not compiled. So the owner is asked to approve **IJG and BSD-3-Clause** for libjpeg-turbo. zlib is approved already. The notice goes into the wheel's licence set (spec 125) and the acknowledgement into the package page.

## 6. What a specification would carry (INFERRED)

- **Kind:** build-class and a judge change. No patch, since the tarball built as it is. Not structural, since `src/` does not change. Reviewed before it is built (§5.6: the build recipe and the artifact set). The guest's imports do not change (EXECUTED above).
- **Pin:** `libjpeg-turbo-3.2.0.tar.gz` in `downloads/SHA256SUMS` and `scripts/00_download.sh`.
- **Build:** libjpeg compiled directly from `JPEG_SOURCES`, read from `CMakeLists.txt` by the host Python as step 55 reads Pillow's `setup.py`. The three headers are recipe files. `pil_cc` gains `-DHAVE_LIBJPEG`, the includes and the setjmp flags. `_imaging`'s `.deps` names `libjpeg.a`. Step 60 needs nothing new: `-lsetjmp` is there, and the weak-duplicate gate reads `.deps` archives already.
- **Checks:**
  - a golden decode of a pinned JPEG, its pixel hash equal to a SIMD-off native decode;
  - a golden encode, its bytes;
  - a broken JPEG raises `OSError` and the next decode in the same guest works (the longjmp path);
  - `features.check("jpg")`;
  - `savefig(format="jpg")` writes a JPEG;
  - the existing import-list and tag-count checks unchanged.
- **Spec 063:** Pillow's own JPEG tests join the `pillow` group as they are. The `pillow-zlib-only` allowance and its 55 ids are removed, a judge change with its reason. The news file claims about 195 new passes and the binary's growth. `docs/reference/packages.md`'s Pillow row changes from "zlib only" to "zlib and JPEG".
- **Order:** none forced; spec 167's libzstd touches other steps. INFERRED.

## 7. Recommendation (INFERRED)

Write it as a specification for 0.1.3. One specification, small. The risk the scope memo named was the untested setjmp route. It is tested now, in the product's own runner, with Pillow's own suite. It adds no import, no host function, no patch and nothing in `src/`. It closes the commonest gap a user meets: opening a photo, or saving a figure as JPEG. It waits on two things only. The first is the owner's licence approval (§4.12, IJG and BSD-3-Clause). The second is its pre-build review. If 0.1.3's lane is full, it moves to 0.1.4 unchanged. Nothing in it decays.

## What the spike did not do

- It did not rebuild the snapshot or run the judge's driver.
- It did not build on Linux or x86_64, so the same-bytes gate (spec 012) is untried. Plain C with no SIMD should give the same bytes. INFERRED.
- It did not write the CMake-free recipe or compare native SIMD-on output. No hypothesis failed twice.

**One line:** libjpeg-turbo 3.2.0 builds for the guest unchanged, Pillow's JPEG path works over the guest's existing setjmp support with its own tests passing, the binary grows by half a megabyte, and it is ready to be a 0.1.3 specification once the owner approves IJG and BSD-3-Clause.
