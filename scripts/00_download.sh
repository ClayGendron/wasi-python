#!/bin/sh
# Fetch the pinned inputs into downloads/ and verify every one against downloads/SHA256SUMS.
#
#   scripts/00_download.sh          the build's inputs
#   scripts/00_download.sh --all    also the research input (Brett's 3.14.7 build)
#
# Each pin is one `get <url> <name>` line: a literal URL and the file's name in downloads/ (spec 003,
# Decision 1). Downloads are untrusted data: they land in downloads/ only, and nothing here runs
# them. This script reads SHA256SUMS and never writes it; a mismatch fails the build.
#
# One line per pin, `fetched <name>` or `present <name>`, then shasum's `<name>: OK` lines, then
# `downloads: <n> pins, <f> fetched, <v> verified`, which build.sh shows as the step's line (spec
# 027). curl is needed only for a pin that is not present yet, and checked there.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
D="$HERE/downloads"
ALL=0
[ "${1:-}" = "--all" ] && ALL=1

PINS=0 FETCHED=0 NAMES=" "
get() { # url name
  PINS=$((PINS + 1))
  NAMES="$NAMES$2 "
  if [ -s "$D/$2" ]; then
    echo "present $2"
    return 0
  fi
  if ! command -v curl > /dev/null 2>&1; then
    echo "ERROR: no curl on PATH; it fetches $2" >&2
    exit 1
  fi
  curl -fsSL --retry 3 -o "$D/$2.part" "$1"
  mv "$D/$2.part" "$D/$2"
  FETCHED=$((FETCHED + 1))
  echo "fetched $2"
}
research() { # url name: fetched only with --all
  if [ "$ALL" = 1 ]; then get "$1" "$2"; fi
}

# The running build host's own inputs: its toolchain, host Python and native build-tool wheels, in
# the branch of its key (scripts/line.sh; spec 012, Decision 1). The line's versions are named in
# scripts/line.conf; the URLs here stay literal, one pin per line (spec 003, Decision 1).
. "$HERE/scripts/line.sh"
case "$HOST_KEY" in
  MACOS_ARM64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-macos.tar.gz wasi-sdk-33.0-arm64-macos.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-macos.tar.xz wasmtime-v49.0.3-aarch64-macos.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-apple-darwin-install_only.tar.gz cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz
    get https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl
    get https://files.pythonhosted.org/packages/b5/b8/90a9518f2264637084d6199bc20c2f3fb97fefc4c474d277720150c3bd6d/ninja-1.13.2-py3-none-macosx_10_9_universal2.whl ninja-1.13.2-py3-none-macosx_10_9_universal2.whl
    get https://files.pythonhosted.org/packages/bf/67/fcd20a9e78fd6bba952e982a86e98e0240a95a216143eab389cbef045d43/pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl
    ;;
  LINUX_AARCH64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-linux.tar.gz wasi-sdk-33.0-arm64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-linux.tar.xz wasmtime-v49.0.3-aarch64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/6e/5d/afb6866ab10236bb208dff0f172ea4b397c9693c5250280c4d9d26057218/cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
    get https://files.pythonhosted.org/packages/35/54/7368ce188625e39acc03ee362bb86cc9bfa6ad15e25c50889ae36e2889b3/ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl
    get https://files.pythonhosted.org/packages/42/b9/6c5293a5c65de1152db827cffaaede42a001c5913927e1ef2e8e8aae139f/pkgconf-3.0.7.post0-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl pkgconf-3.0.7.post0-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
    ;;
  LINUX_X86_64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz wasi-sdk-33.0-x86_64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-x86_64-linux.tar.xz wasmtime-v49.0.3-x86_64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-x86_64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/c9/aa/4c0b6773ecf6bc1ec6cda7db8312a566611b330fb6dae87d740e44a47822/cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    get https://files.pythonhosted.org/packages/6e/53/ebfed7b689c338dd8ebeec9c0730c8d56821292f14e2536e5f3ef1a05744/ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
    get https://files.pythonhosted.org/packages/6c/eb/4a4fe6c178d4447f3a3189b5fb740a76dc7ef8846a57886270315f22f7ee/pkgconf-3.0.7.post0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl pkgconf-3.0.7.post0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    # The compiler this host runs (spec 040, Decisions 3 and 4): the arm64 Linux SDK's clang, under
    # Debian's qemu-aarch64 (a static binary) with the four aarch64 libraries that clang loads. Each
    # is a snapshot.debian.org URL, which does not change when Debian moves on.
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-linux.tar.gz wasi-sdk-33.0-arm64-linux.tar.gz
    get https://snapshot.debian.org/archive/debian/20260905T205002Z/pool/main/q/qemu/qemu-user_10.0.13%2Bds-0%2Bdeb13u1_amd64.deb qemu-user_10.0.13+ds-0+deb13u1_amd64.deb
    get https://snapshot.debian.org/archive/debian/20260711T202405Z/pool/main/g/glibc/libc6_2.41-12%2Bdeb13u4_arm64.deb libc6_2.41-12+deb13u4_arm64.deb
    get https://snapshot.debian.org/archive/debian/20250317T031857Z/pool/main/g/gcc-14/libstdc%2B%2B6_14.2.0-19_arm64.deb libstdc++6_14.2.0-19_arm64.deb
    get https://snapshot.debian.org/archive/debian/20250317T031857Z/pool/main/g/gcc-14/libgcc-s1_14.2.0-19_arm64.deb libgcc-s1_14.2.0-19_arm64.deb
    get https://snapshot.debian.org/archive/debian/20250306T211336Z/pool/main/n/ncurses/libtinfo6_6.5%2B20250216-2_arm64.deb libtinfo6_6.5+20250216-2_arm64.deb
    ;;
esac
# The wasm runtime every host links, the same bytes for each: wasi-sdk's host-neutral sysroot and
# compiler-rt builtins, laid in place of the host tarball's own by step 10 (spec 012, Decision 2).
get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sysroot-33.0%2Bm.tar.gz wasi-sysroot-33.0+m.tar.gz
get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/libclang_rt-33.0%2Bm.tar.gz libclang_rt-33.0+m.tar.gz

# Sources
get https://www.python.org/ftp/python/3.15.0/Python-3.15.0.tar.xz Python-3.15.0.tar.xz
get https://files.pythonhosted.org/packages/9a/80/db0b4559e57ec36362bedbb05530a87fafbcb6067708c946967a41d449e7/numpy-2.5.2.tar.gz numpy-2.5.2.tar.gz
get https://files.pythonhosted.org/packages/e2/17/d7b106e05bfa642e8694451e7d3d759c6a241c5386a5d962e4f66c047e06/pandas-3.0.6.tar.gz pandas-3.0.6.tar.gz
get https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz zlib-1.3.1.tar.gz
# The C libraries of _bz2, _lzma and _sqlite3 (spec 007): host-neutral sources, like zlib's
get https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz bzip2-1.0.8.tar.gz
get https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz xz-5.8.4.tar.gz
get https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz sqlite-autoconf-3540100.tar.gz
# matplotlib (spec 023): the five C libraries at matplotlib 3.11.2's own wrap versions, which give
# native pixel parity; qhull and SheenBidi saved under names that are their top folders (the
# release workflow's tree check names a tree by its file)
get https://download.savannah.nongnu.org/releases/freetype/freetype-2.14.3.tar.xz freetype-2.14.3.tar.xz
get https://github.com/harfbuzz/harfbuzz/releases/download/14.1.0/harfbuzz-14.1.0.tar.xz harfbuzz-14.1.0.tar.xz
get https://github.com/Tehreer/SheenBidi/archive/refs/tags/v3.0.0/sheenbidi-3.0.0.tar.gz SheenBidi-3.0.0.tar.gz
get https://github.com/HOST-Oman/libraqm/archive/v0.10.5/libraqm-0.10.5.tar.gz libraqm-0.10.5.tar.gz
get https://github.com/qhull/qhull/archive/v8.0.2/qhull-8.0.2.tar.gz qhull-8.0.2.tar.gz
get https://files.pythonhosted.org/packages/e7/c8/9aa712a0afb882649424dd8de8ad9aa6235e796e84c6052e8f6dc1598d0d/matplotlib-3.11.2.tar.gz matplotlib-3.11.2.tar.gz
get https://files.pythonhosted.org/packages/ba/07/bd78e6a8fae171ea041ef5bba3ed21a003522fa088834b069b1909981f30/kiwisolver-1.5.1.tar.gz kiwisolver-1.5.1.tar.gz
get https://files.pythonhosted.org/packages/ce/a4/9cc30690a394a8305e8be4c9036aa16d0dfddadd09079860b582f562496d/pillow-13.0.0.tar.gz pillow-13.0.0.tar.gz
# Header-only C++ that is compiled in (matplotlib's and kiwisolver's bindings), so its notices ship
get https://files.pythonhosted.org/packages/33/fd/8762f7ee3e4e4be6d1d846cffb4916dd9bb02b2f800d3603718a0efe494c/pybind11-3.1.0-py3-none-any.whl pybind11-3.1.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/8b/3c/823fda3f226d84f983e48005527a6dd2dc365220ac4f098b770779d9f4a1/cppy-1.3.1-py3-none-any.whl cppy-1.3.1-py3-none-any.whl

# Host-neutral build tools (wheels, installed offline with their hashes)
get https://files.pythonhosted.org/packages/57/99/36cd25f9598eef70db97577440a70a360af505f6f01c2338a18d1556079c/meson-1.12.1-py3-none-any.whl meson-1.12.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/b0/79/f0f1ca286b78f6f33c521a36b5cbd5bd697c0d66217d8856f443aeb9dd77/versioneer-0.29-py3-none-any.whl versioneer-0.29-py3-none-any.whl

# Pure-Python packages for the stdlib zip
get https://files.pythonhosted.org/packages/ec/57/56b9bcc3c9c6a792fcbaf139543cee77261f3651ca9da0c93f5c1221264b/python_dateutil-2.9.0.post0-py2.py3-none-any.whl python_dateutil-2.9.0.post0-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/94/21/1e5995a1c920cce14e4bffae20c665ec10e7ed03ab25e006cd741092b718/tzdata-2026.5-py2.py3-none-any.whl tzdata-2026.5-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl six-1.17.0-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/e7/05/c19819d5e3d95294a6f5947fb9b9629efb316b96de511b418c53d245aae6/cycler-0.12.1-py3-none-any.whl cycler-0.12.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/38/bb/d215ee7c73b61497b28a5503f9f53523f294fcc936762b7caf90e0c1c2b5/pyparsing-3.3.3-py3-none-any.whl pyparsing-3.3.3-py3-none-any.whl
get https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl packaging-26.3-py3-none-any.whl
get https://files.pythonhosted.org/packages/3d/61/4161946319472aaa9b897bd18ad5108a5b10f5ebaa503d921a001ac4fff9/fonttools-4.67.0-py3-none-any.whl fonttools-4.67.0-py3-none-any.whl

# Licence notices of what wasi-sdk 33 links in (its tarball carries none), at the commits its VERSION
# names (wasi-libc 161b3195, LLVM 4434dabb, 22.1.0)
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/LICENSE wasi-libc-161b3195-LICENSE
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/LICENSE-APACHE wasi-libc-161b3195-LICENSE-APACHE
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/LICENSE-APACHE-LLVM wasi-libc-161b3195-LICENSE-APACHE-LLVM
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/LICENSE-MIT wasi-libc-161b3195-LICENSE-MIT
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/libc-top-half/musl/COPYRIGHT wasi-libc-161b3195-musl-COPYRIGHT
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/161b3195fc2558d2b1ba3eb9ffae3b2b47407623/libc-bottom-half/cloudlibc/LICENSE wasi-libc-161b3195-cloudlibc-LICENSE
get https://raw.githubusercontent.com/llvm/llvm-project/4434dabb69916856b824f68a64b029c67175e532/libcxx/LICENSE.TXT llvm-4434dabb-libcxx-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/4434dabb69916856b824f68a64b029c67175e532/libcxxabi/LICENSE.TXT llvm-4434dabb-libcxxabi-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/4434dabb69916856b824f68a64b029c67175e532/libunwind/LICENSE.TXT llvm-4434dabb-libunwind-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/4434dabb69916856b824f68a64b029c67175e532/compiler-rt/LICENSE.TXT llvm-4434dabb-compiler-rt-LICENSE.TXT
# The Unicode data terms of HarfBuzz's tables, whose tree carries no copy (spec 023, Decision 9): the
# Unicode License V3 from Unicode's own repository at a commit, so the bytes cannot change
get https://raw.githubusercontent.com/unicode-org/unicodetools/4fd8eca90b30aa4c72543ccddb4c15d05becdf8d/LICENSE unicodetools-4fd8eca9-LICENSE

# Research inputs: the reference build the harness self-tests use
research https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.14.7/python-3.14.7-wasi_sdk-24.zip python-3.14.7-wasi_sdk-24.zip

# shasum's lines go to a file, never through a pipe: sh has no pipefail, so a pipe would hide a
# mismatch. The file is shown whole, then its OK lines are counted.
mkdir -p "$HERE/build"
checked="$HERE/build/downloads-verified.txt"
cd "$D"
if shasum -a 256 --ignore-missing -c SHA256SUMS > "$checked" 2>&1; then
  cat "$checked"
else
  cat "$checked"
  echo "ERROR: a download does not match its pin in downloads/SHA256SUMS" >&2
  exit 1
fi
# Verified counts this run's pins; a file that is no pin of this run (the research input, say) and
# still verifies is named apart, so no count exceeds the pins.
VERIFIED=0 OTHER=0
while IFS= read -r line; do
  case "$line" in
    *": OK")
      case "$NAMES" in
        *" ${line%: OK} "*) VERIFIED=$((VERIFIED + 1));;
        *) OTHER=$((OTHER + 1));;
      esac;;
  esac
done < "$checked"
summary="downloads: $PINS pins, $FETCHED fetched, $VERIFIED verified"
case "$OTHER" in
  0) ;;
  1) summary="$summary; 1 other file in downloads/ verified too";;
  *) summary="$summary; $OTHER other files in downloads/ verified too";;
esac
echo "$summary"
