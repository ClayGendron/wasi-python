#!/bin/sh
# Fetch the pinned inputs into downloads/ and verify every one against downloads/SHA256SUMS.
#
#   scripts/00_download.sh          the build's inputs
#   scripts/00_download.sh --all    also the research input (Brett's 3.14.7 build)
#
# Each pin is one `get <url> <name>` line: a literal URL and the file's name in downloads/ (spec 003,
# Decision 1). Downloads are untrusted data: they land in downloads/ only, and nothing here runs
# them. This script reads SHA256SUMS and never writes it; a mismatch fails the build.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
D="$HERE/downloads"
ALL=0
[ "${1:-}" = "--all" ] && ALL=1

get() { # url name
  if [ ! -s "$D/$2" ]; then
    curl -fsSL --retry 3 -o "$D/$2.part" "$1"
    mv "$D/$2.part" "$D/$2"
  fi
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
    ;;
  LINUX_AARCH64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-linux.tar.gz wasi-sdk-33.0-arm64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-linux.tar.xz wasmtime-v49.0.3-aarch64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/6e/5d/afb6866ab10236bb208dff0f172ea4b397c9693c5250280c4d9d26057218/cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
    get https://files.pythonhosted.org/packages/35/54/7368ce188625e39acc03ee362bb86cc9bfa6ad15e25c50889ae36e2889b3/ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl
    ;;
  LINUX_X86_64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz wasi-sdk-33.0-x86_64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-x86_64-linux.tar.xz wasmtime-v49.0.3-x86_64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-x86_64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/c9/aa/4c0b6773ecf6bc1ec6cda7db8312a566611b330fb6dae87d740e44a47822/cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    get https://files.pythonhosted.org/packages/6e/53/ebfed7b689c338dd8ebeec9c0730c8d56821292f14e2536e5f3ef1a05744/ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
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

# Host-neutral build tools (wheels, installed offline with their hashes)
get https://files.pythonhosted.org/packages/57/99/36cd25f9598eef70db97577440a70a360af505f6f01c2338a18d1556079c/meson-1.12.1-py3-none-any.whl meson-1.12.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/b0/79/f0f1ca286b78f6f33c521a36b5cbd5bd697c0d66217d8856f443aeb9dd77/versioneer-0.29-py3-none-any.whl versioneer-0.29-py3-none-any.whl

# Pure-Python packages for the stdlib zip
get https://files.pythonhosted.org/packages/ec/57/56b9bcc3c9c6a792fcbaf139543cee77261f3651ca9da0c93f5c1221264b/python_dateutil-2.9.0.post0-py2.py3-none-any.whl python_dateutil-2.9.0.post0-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/94/21/1e5995a1c920cce14e4bffae20c665ec10e7ed03ab25e006cd741092b718/tzdata-2026.5-py2.py3-none-any.whl tzdata-2026.5-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl six-1.17.0-py2.py3-none-any.whl

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

# Research inputs: the reference build the harness self-tests use
research https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.14.7/python-3.14.7-wasi_sdk-24.zip python-3.14.7-wasi_sdk-24.zip

cd "$D"
shasum -a 256 --ignore-missing -c SHA256SUMS
