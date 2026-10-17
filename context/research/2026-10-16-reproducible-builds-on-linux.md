# Reproducible builds on Linux

- **Status:** executed, 2026-10-17 (written as a placeholder 2026-10-16, completed in place)
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5); box: 3 hours, about 2 used.
- **Blocks:** the release workflow's Linux build; the claim that the published hash can be
  rebuilt by anyone. **Feeds:** the known gap
  `test_toolchain_is_pinned_for_linux_and_macos`, which a specification closes with the pins
  below.
- **Evidence:** `2026-10-17-the-linux-build-experiment/`. `fetch.sh` and `linux-pins.txt`
  fetch and verify the Linux pins. `setup.sh` and `edit.py` clone this repository into a
  scratch directory and make the clone's recipe host-aware (nothing in the repository itself
  changed). `Dockerfile`, `run-build.sh` and `run-swap.sh` are the second host. `tools/` holds
  the comparison scripts. `outputs/` holds every run's step lines and hashes (`runs.txt`), the
  diffs, the edits as one diff, and the judge's output on Linux.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5. Docker 29.7.2, whose Linux VM
  has 10 CPUs and 8 GB.

## The question

Today the build and the judge run only on arm64 macOS. Does the pinned recipe
(`scripts/build.sh`, steps 00 to 90, the line in `scripts/line.conf`) rebuild the same artifact
bytes on a second host? The second host here is Linux aarch64, in a container. Where the bytes
differ, what is the cause?

The reference is the macOS build, which the CI dry run reproduced from a different checkout
path:

- reactor `4e2b2470314ee392acbcd53b8861d283d2ebb7c07816662e7c0c0b158463a251`
- snapshot `c6a791d3960c63982e83aeaa9daeff2b2036aa4cf218ef6731575563dfc0c6bd`
- zip `e95b35dea78981e8be867e136136a9b5d4235891c8b3483ba415494d427af8df`

## Method

1. Pin the Linux inputs by URL and SHA-256, and check each against its published digest.
2. Build a container: a base image pinned by digest, with the host tools the recipe calls.
3. In a scratch clone, make the recipe host-aware with the smallest change (`edit.py`).
4. Run the whole build in the container from an empty `build/`, and compare.
5. Where the bytes differ, hash every intermediate on both hosts and narrow it down. Test
   each cause by changing only that cause, then rebuild on both hosts.
6. Run the judge's fast tier in the container against the Linux-built artifacts.

## Findings

1. **Every Linux input exists and is pinned** (EXECUTED: `fetch.sh` fetched each file, and its
   SHA-256 matched the digest the publisher gives). The digests come from GitHub's release-asset
   digests (wasi-sdk, wasmtime, uv), python-build-standalone's `SHA256SUMS` and PyPI's JSON.
   The macOS pins already in `downloads/SHA256SUMS` match their published digests too.

   | input | aarch64 Linux | x86_64 Linux |
   |---|---|---|
   | wasi-sdk 33 | `wasi-sdk-33.0-arm64-linux.tar.gz` `4f98ee738c7abb45c81a94d1461fc53cc569d1cd01498951c8184d841a027844` | `wasi-sdk-33.0-x86_64-linux.tar.gz` `0ba8b5bfaeb2adf3f29bab5841d76cf5318ab8e1642ea195f88baba1abd47bce` |
   | wasmtime v49.0.3 | `wasmtime-v49.0.3-aarch64-linux.tar.xz` `880fcb026da88ad7fc1713d572b0d03d139758b7da96cd3cb8c9cbf847a521df` | `wasmtime-v49.0.3-x86_64-linux.tar.xz` `4001225413f208345b980525f31c4080e1873808b38d0ddc7918497340667fbb` |
   | host Python 3.15.0+20261009 | `cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz` `f02953d2c56c7eaa2fa3a21f2680a823b8748959c571ac149cd76b0fd1a1c33c` | `cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz` `95ba085863806dacf0fd7119c590154bbcd3351099e55c0808a9c61603e320a8` |
   | Cython 3.3.0 cp315 | `cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` `4a36c34d1950845b8ac148653b07cdc62421a4b0d9abfcc849e69f1c4ff9919d` | `cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` `b447f6906e0555f05dc4742ef1f99091b1e5d9aa9f16616e772fbf9ff6271616` |
   | ninja 1.13.2 | `ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` `d775a5e43e9088f507a6250d57fcf5678eb31268c545feb5064ffeee33735622` | `ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` `65a24341b5ac09fcadcc37082660be40a94174e51a937fabf6e2cae26225fa2c` |
   | uv 0.9.22 (container only) | `uv-aarch64-unknown-linux-gnu.tar.gz` `2f8716c407d5da21b8a3e8609ed358147216aaab28b96b1d6d7f48e9bcc6254e` | `uv-x86_64-unknown-linux-gnu.tar.gz` `e170aed70ac0225feee612e855d3a57ae73c61ffb22c7e52c3fd33b87c286508` |

   The URLs are in `linux-pins.txt`, and as `get` lines in `outputs/recipe-edits.diff`. Two
   host-neutral inputs come from the same wasi-sdk 33 release (finding 6):
   `wasi-sysroot-33.0+m.tar.gz` (`063bc1b56582b9923e08ac9b89e58789618d851763f01530b3ff20b9e5df0ca3`)
   and `libclang_rt-33.0+m.tar.gz`
   (`d3302760b78c8c50f2875650833b3584479131eab9ec2e6c72f7dfec26288be3`). Their URLs spell `+` as
   `%2B`. x86_64 was pinned and fetched, but not built.
2. **The second host** (EXECUTED: `Dockerfile`, `outputs/container-host-tools.txt`) is
   `debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f`
   (the multi-arch index digest, pulled 2026-10-17). It runs Debian 13 on aarch64 and kernel
   7.0.12-linuxkit, with `/bin/sh` as dash. Its tools come from Debian's archive: gcc 14.2.0,
   GNU make 4.4.1, curl 8.14.1, xz 5.8.1, git 2.47.3, GNU tar 1.35, and perl 5.40.1 for
   `shasum`. uv 0.9.22 comes from its release tarball, checked against its digest. The apt
   packages are not pinned by hash; their versions are recorded. No locale is set.
3. **The recipe needed only host names to run on Linux** (EXECUTED: edits 1 to 5 in
   `edit.py`; run 1). Four names in `scripts/line.conf` are per host. Step 10 named the macOS
   ninja wheel literally. Nothing else assumed macOS. `shasum` exists on Linux through perl.
   No script uses `sed -i`. `tar -xf` detects compression on both hosts. dash ran every script.
   `python-wasi-cross` found the build-Python as `cross-build/aarch64-unknown-linux-gnu/python`
   with no change. The edits:
   - `line.conf`: each host-specific name gets one line per host, prefixed by a host key
     (`MACOS_ARM64_`, `LINUX_AARCH64_`, `LINUX_X86_64_`), plus a new `NINJA_WHEEL`;
   - `line.sh` and `line.py`: set the plain name for the running host (from `uname`, or from
     `platform`), so every reader of the plain name is unchanged, including the judge's oracle;
   - `00_download.sh`: a `case` on the host key fetches only that host's toolchain, host
     Python and native wheels, still as literal `get <url> <name>` lines;
   - `10_tools.sh`: `$NINJA_WHEEL` in place of the literal macOS wheel.

   The whole build passed on the first run, all ten steps, in 185 s. The macOS builds took
   307 to 347 s, but they ran beside the container, so the times do not compare.
4. **The first run differs in all three artifacts** (EXECUTED: run 1, `outputs/runs.txt`):

   | artifact | macOS reference | Linux, run 1 |
   |---|---|---|
   | reactor | 29,802,408 bytes, `4e2b2470…` | 29,802,344 bytes, `4428c35a…` |
   | zip | 11,140,659 bytes, `e95b35de…` | 11,140,674 bytes, `0780282e…` |
   | snapshot | 63,492,577 bytes, `c6a791d3…` | 63,488,735 bytes, `ba278ac7…` |

   Each build reproduces itself. Linux runs 1 and 3 printed the same hashes. The cause is the
   host, not chance.
5. **What is not a cause** (EXECUTED: `outputs/intermediates-diff.txt`, `zip-diff.txt`,
   `cython-output-diff.txt`). The two hosts' intermediates were hashed (2,577 files each).
   - The checkout path, `/Users/claygendron/…` on macOS and `/work/wasi_python` in the container.
     236 of 250 CPython objects differ, and all 236 are equal after `llvm-strip --strip-debug`:
     only their DWARF holds the path. Step 60 strips DWARF from the reactor. Every numpy and
     pandas object and archive is equal, thanks to `-ffile-prefix-map`.
   - The host C compiler that builds CPython's build-Python: Apple clang on macOS, gcc 14.2 on
     Linux. The frozen and deep-frozen modules it generates compile to equal objects, as above.
   - The host Python's bytecode: 1,749 of the zip's 1,751 members are byte-equal, and the zip's
     member order is the same.
   - Cython: its C output differs (finding 11), but it compiles to the same objects.
   - `wasmtime wizer`: given the same reactor, zip and file-system answers, Linux and macOS
     write the same snapshot (finding 8).
   - Timestamps: none differ. `SOURCE_DATE_EPOCH`, the zip's fixed dates and the reactor's
     pinned clocks hold on both hosts.
6. **Cause 1: the per-host wasi-sdk tarballs carry different wasm runtimes** (EXECUTED:
   `outputs/sdk-runtime-diff.txt`). In both tarballs, the `libc.a` the build links and every
   header are equal (only the `llvm-lto/` variants of libc differ, and the build does not use
   them). For
   `wasm32-wasip1`, `eh/libc++.a`, `eh/libc++abi.a` and `libclang_rt.builtins.a` differ. Each
   was compiled at its builder's path: `/Users/runner/work/wasi-sdk/wasi-sdk` for the macOS
   tarball, `/src` for the Linux one. Most of that is DWARF. But `__FILE__` strings in assert
   messages survive the strip. The reactor links two of them, from libc++abi's
   `private_typeinfo.cpp` and `fallback_malloc.cpp`. Each path is 32 bytes longer on macOS:
   64 bytes, exactly the reactor's DATA difference. wasi-sdk also publishes a host-neutral
   `wasi-sysroot-33.0+m` and `libclang_rt-33.0+m`. Its libc++ and libc++abi equal the Linux
   tarball's, its libc.a equals both, and its builtins differ from both.
7. **Cause 2: step 60's link order follows the builder's locale** (EXECUTED:
   `outputs/link-order.txt`). With the macOS runtime archives swapped in (run 2), the Linux
   reactor had macOS's size but not its bytes. The first difference is in the FUNCTION
   section: the functions come in a different order. Step 60 orders the extension archives with
   `find | sort` and `sort -u`. Under macOS's `en_US.UTF-8`, `pandas_ops_dispatch.a` sorts
   before `pandas_ops.a`; under C or POSIX, after it. Run 3 added `export LC_ALL=C` to
   `build.sh` (edit 6). The macOS build then wrote reactor `35bfa758…`, and the Linux build
   with the macOS runtime archives wrote the same bytes. This changes the macOS reactor's hash
   but not its size, and the zip stays `e95b35de…`.
8. **Cause 3: the snapshot captures the host file system's directory size** (EXECUTED:
   `outputs/snapshot-diff.txt`). With the same reactor (`35bfa758…`) and the same zip, the
   snapshots still differed: `989317297a…` on macOS, `5ba00077…` on Linux. 21.1 million of
   their 59.1 million memory bytes differ, almost all in the heap. Tracing every WASI call of
   step 80 (`WASMTIME_LOG=wasmtime_wasi=trace`), with inode and times masked (the reactor pins
   those), leaves five differing answers. All five are `path_filestat_get` on `usr`,
   `usr/local` and `usr/local/lib` in the wizer root. APFS answers a directory's size as 96;
   ext4 and overlayfs answer 4096. One `nlink` is 3 against 2. CPython shares the int objects
   up to 256 and allocates larger ones. So 96 costs no allocation and 4096 costs one, and every
   later heap address shifts. Edit 7 makes `pin_filestat` in `recipes/reactor_main.c` also
   answer a directory's size as 0 and its `nlink` as 1 while pinned. That is our recipe file,
   not upstream. With it, the snapshots matched: `59faf331…` on macOS (run 5), and the same
   bytes on Linux from the same reactor and zip (run 6).
9. **With causes 1 to 3 fixed in the recipe, the reactor is byte-identical across hosts**
   (EXECUTED: run 7, a full build from an empty `build/` on both hosts). Edit 8 pins
   `wasi-sysroot-33.0+m` and `libclang_rt-33.0+m`, and step 10 lays them over the host SDK's
   own sysroot and builtins. Both hosts then wrote reactor
   `2df569f2f59397d59b175eec7553d6a0ec7dff99b5e819659f9ce0758fdba3ad` (29,802,418 bytes). Given
   macOS's zip, Linux's step 80 wrote macOS's snapshot,
   `ba44932bc1d34f0b05c413f36daeb5b40a8b68629c59259b874b3793c95bdbfb`. The zip, and therefore
   the snapshot, still differ: cause 4.
10. **Cause 4 (open): two zip members record the build host** (EXECUTED:
    `outputs/zip-diff.txt`). `_sysconfigdata__wasi_wasm32-wasi.py` records the build triple
    (`aarch64-apple-darwin` vs `aarch64-unknown-linux-gnu`) and the SDK and wasmtime directory
    names. It also records the build-Python's name (`python.exe` vs `python`), `GNULD` (`no` vs
    `yes`) and `MKDIR_P` (`mkdir -p` vs `/usr/bin/mkdir -p`). numpy's `__config__.py` records
    the build machine's `"system"` (`darwin` vs `linux`). Step 70 already replaces the
    repository path in both files; nothing replaces these values. None of them means anything
    inside the guest. The snapshot follows the zip: zipimport's offsets and the modules it
    loads are in its heap. No fix for these two members was tried.
11. **Cython's output is not deterministic, and today that is harmless** (EXECUTED:
    `outputs/cython-output-diff.txt`). pandas' `_cyutility.c` lists prototypes in a different
    order on each host. `strptime.pyx.c` declares one variable as `npy_datetime` or
    `__pyx_t_5numpy_int64_t`; this varies between two macOS runs. Both forms compile to the same
    objects, so no artifact moves. It is a latent risk, not a cause.
12. **The judge passes on Linux** (EXECUTED: `outputs/judge-fast-linux.txt`). It ran
    `uv run pytest -m "not slow" --progress-dir <empty>` in the container against run 7's Linux
    artifacts: `120/128 pass · 0 gap · 3 blocked · 1 fail`, `308 passed, 8 skipped`. The one
    fail is the known gap, which now passes: with the x86_64 pins in `SHA256SUMS`,
    `test_toolchain_is_pinned_for_linux_and_macos` passes, and the judge asks for its entry in
    `tests/known_gaps.toml` to be removed. The guest's numpy and pandas jobs match their goldens
    when built on Linux.

## What it decides

The question was whether the published `SHA256SUMS` is a reproducibility claim or only an
integrity claim. **Today it is an integrity claim.** The recipe runs on Linux with small edits,
and it reproduces itself there. But no artifact matches macOS until four host leaks are closed.
Three of them close in the recipe, and those were run (edits 6 to 8). The fourth, the zip's two
host-fact members, is not yet closed. With all four closed, the claim can be "byte-identical
from any supported host". A specification that takes this up must decide:

1. **How the recipe names per-host inputs.** Edits 1 to 5 are one design that works: per-host
   keys in `line.conf` resolved by `line.sh` and `line.py`, and a `case` in `00_download.sh`.
   `downloads/SHA256SUMS` lists every host's pins. `MANIFEST` then lists every host's pins too,
   which keeps it host-neutral.
2. **One wasm runtime for every host** (edit 8, or `--sysroot` and `-resource-dir` flags in
   place of the overlay). The host tarball then supplies only the compiler.
3. **`LC_ALL=C` for the whole build** (edit 6), or a sort in Python. Either one changes the
   macOS reactor's hash once.
4. **A directory's size and link count are pinned while initializing** (edit 7). This changes
   the snapshot's hash once. A program never sees it, because the pin ends before `run`.
5. **What the zip says about its build host.** One way: step 70 rewrites the build-host values
   of `_sysconfigdata` and numpy's `__config__.py` to fixed text, as it already rewrites the
   path. Another: the zip and snapshot are declared per-build-OS, published from one host, and a
   rebuild elsewhere is checked as "equal except these two named members". Only the first gives
   a cross-host hash.
6. **The new hashes, accepted once.** Edits 6 to 8 change the reactor and snapshot hashes
   (run 7 on macOS: reactor `2df569f2…`, snapshot `ba44932b…`). Under the judge's rules this is
   a judged change, accepted with a reason.
7. **A second-host check.** The scoreboard lists "second-host rebuild" as not machine-checked.
   A CI job that builds on Linux and compares hashes would make the claim checked rather than
   asserted. The known gap's entry comes out of `tests/known_gaps.toml` in the same change.
8. **The host tools.** The Debian packages and the build-Python's C compiler stay unpinned host
   inputs, as the README already says. This run shows that gcc 14.2 against Apple clang changes
   no artifact byte.

## Where it stopped

- No fix for the zip's two members was tried (cause 4). So a full Linux build does not yet give
  macOS's zip or snapshot.
- x86_64 Linux was pinned and its downloads verified, but not built. INFERRED: the same four
  causes apply there. With edit 8 its runtime is the neutral one, so cause 1 does not return.
- The GitHub `ubuntu-24.04` runner was not used; the second host was a local container.
- The Debian packages were not pinned by `snapshot.debian.org`; their versions are recorded.
- Cython's nondeterminism was not traced to its source.

## One line

The recipe runs on Linux with only host names changed. With three small recipe fixes (one
wasm runtime for every host, `LC_ALL=C`, and pinned directory stats) the reactor is
byte-identical across hosts and Wizer is host-independent. The zip and snapshot still differ
by two host-fact members of the zip.
