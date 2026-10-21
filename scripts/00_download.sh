#!/bin/sh
# Fetch the pinned inputs into downloads/ and verify every one against downloads/SHA256SUMS.
#
#   scripts/00_download.sh          the build's inputs
#   scripts/00_download.sh --all    also the research input (Brett's 3.14.7 build)
#
# Each pin is one `get <url> <name>` line: a literal URL and the file's name in downloads/.
# Downloads are untrusted data: they land in downloads/ only, and nothing here runs
# them. This script reads SHA256SUMS and never writes it; a mismatch fails the build.
#
# One line per pin, `fetched <name>` or `present <name>`, then shasum's `<name>: OK` lines, then
# `downloads: <n> pins, <f> fetched, <v> verified`, which build.sh shows as the step's line.
# curl is needed only for a pin that is not present yet, and checked there. A fetched name
# with no pin fails the step, named.
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
# the branch of its key (scripts/line.sh). The line's versions are named in
# scripts/line.conf; the URLs here stay literal, one pin per line.
. "$HERE/scripts/line.sh"
case "$HOST_KEY" in
  MACOS_ARM64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/wasi-sdk-34.0-arm64-macos.tar.gz wasi-sdk-34.0-arm64-macos.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-macos.tar.xz wasmtime-v49.0.3-aarch64-macos.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-apple-darwin-install_only.tar.gz cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz
    get https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl
    get https://files.pythonhosted.org/packages/b5/b8/90a9518f2264637084d6199bc20c2f3fb97fefc4c474d277720150c3bd6d/ninja-1.13.2-py3-none-macosx_10_9_universal2.whl ninja-1.13.2-py3-none-macosx_10_9_universal2.whl
    get https://files.pythonhosted.org/packages/bf/67/fcd20a9e78fd6bba952e982a86e98e0240a95a216143eab389cbef045d43/pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl
    # numpy for the build host, whose f2py writes scipy's Fortran-wrapper C
    get https://files.pythonhosted.org/packages/78/d9/8c4b3937ef204cb2fd88d389ccd0f265a2ffb11f35a01d2064cf46714bd6/numpy-2.5.2-cp315-cp315-macosx_14_0_arm64.whl numpy-2.5.2-cp315-cp315-macosx_14_0_arm64.whl
    ;;
  LINUX_AARCH64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/wasi-sdk-34.0-arm64-linux.tar.gz wasi-sdk-34.0-arm64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-linux.tar.xz wasmtime-v49.0.3-aarch64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/6e/5d/afb6866ab10236bb208dff0f172ea4b397c9693c5250280c4d9d26057218/cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
    get https://files.pythonhosted.org/packages/35/54/7368ce188625e39acc03ee362bb86cc9bfa6ad15e25c50889ae36e2889b3/ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl
    get https://files.pythonhosted.org/packages/42/b9/6c5293a5c65de1152db827cffaaede42a001c5913927e1ef2e8e8aae139f/pkgconf-3.0.7.post0-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl pkgconf-3.0.7.post0-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
    get https://files.pythonhosted.org/packages/43/f3/acb18d8b137a393c8e7803a8c994c9e64bde3930692a69d826993113a159/numpy-2.5.2-cp315-cp315-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl numpy-2.5.2-cp315-cp315-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl
    ;;
  LINUX_X86_64)
    get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/wasi-sdk-34.0-x86_64-linux.tar.gz wasi-sdk-34.0-x86_64-linux.tar.gz
    get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-x86_64-linux.tar.xz wasmtime-v49.0.3-x86_64-linux.tar.xz
    get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-x86_64-unknown-linux-gnu-install_only.tar.gz cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz
    get https://files.pythonhosted.org/packages/c9/aa/4c0b6773ecf6bc1ec6cda7db8312a566611b330fb6dae87d740e44a47822/cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    get https://files.pythonhosted.org/packages/6e/53/ebfed7b689c338dd8ebeec9c0730c8d56821292f14e2536e5f3ef1a05744/ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
    get https://files.pythonhosted.org/packages/6c/eb/4a4fe6c178d4447f3a3189b5fb740a76dc7ef8846a57886270315f22f7ee/pkgconf-3.0.7.post0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl pkgconf-3.0.7.post0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    get https://files.pythonhosted.org/packages/a9/bf/a8e9bb0db815a0e265b5744ebedd3af0bd5faad8604e5b50a1cd012f3c91/numpy-2.5.2-cp315-cp315-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl numpy-2.5.2-cp315-cp315-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
    # The fallback's compiler: the arm64 Linux
    # SDK's clang, under Debian's qemu-aarch64 (a static binary) with the four aarch64 libraries
    # that clang loads, each a snapshot.debian.org URL, which does not change when Debian moves on.
    # Fetched only when scripts/line.conf's switch names that SDK; a native build never asks for them.
    if [ "$COMPILER_SDK_DIR" != "$WASI_SDK_DIR" ]; then
      get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/wasi-sdk-34.0-arm64-linux.tar.gz wasi-sdk-34.0-arm64-linux.tar.gz
      get https://snapshot.debian.org/archive/debian/20260905T205002Z/pool/main/q/qemu/qemu-user_10.0.13%2Bds-0%2Bdeb13u1_amd64.deb qemu-user_10.0.13+ds-0+deb13u1_amd64.deb
      get https://snapshot.debian.org/archive/debian/20260711T202405Z/pool/main/g/glibc/libc6_2.41-12%2Bdeb13u4_arm64.deb libc6_2.41-12+deb13u4_arm64.deb
      get https://snapshot.debian.org/archive/debian/20250317T031857Z/pool/main/g/gcc-14/libstdc%2B%2B6_14.2.0-19_arm64.deb libstdc++6_14.2.0-19_arm64.deb
      get https://snapshot.debian.org/archive/debian/20250317T031857Z/pool/main/g/gcc-14/libgcc-s1_14.2.0-19_arm64.deb libgcc-s1_14.2.0-19_arm64.deb
      get https://snapshot.debian.org/archive/debian/20250306T211336Z/pool/main/n/ncurses/libtinfo6_6.5%2B20250216-2_arm64.deb libtinfo6_6.5+20250216-2_arm64.deb
    fi
    ;;
esac
# The wasm runtime every host links, the same bytes for each: wasi-sdk's host-neutral sysroot and
# compiler-rt builtins, laid in place of the host tarball's own by step 10.
get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/wasi-sysroot-34.0.tar.gz wasi-sysroot-34.0.tar.gz
get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/libclang_rt-34.0.tar.gz libclang_rt-34.0.tar.gz

# Sources
get https://www.python.org/ftp/python/3.15.0/Python-3.15.0.tar.xz Python-3.15.0.tar.xz
get https://files.pythonhosted.org/packages/9a/80/db0b4559e57ec36362bedbb05530a87fafbcb6067708c946967a41d449e7/numpy-2.5.2.tar.gz numpy-2.5.2.tar.gz
get https://files.pythonhosted.org/packages/e2/17/d7b106e05bfa642e8694451e7d3d759c6a241c5386a5d962e4f66c047e06/pandas-3.0.6.tar.gz pandas-3.0.6.tar.gz
get https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz zlib-1.3.1.tar.gz
# The C libraries of _bz2, _lzma and _sqlite3: host-neutral sources, like zlib's
get https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz bzip2-1.0.8.tar.gz
get https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz xz-5.8.4.tar.gz
get https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz sqlite-autoconf-3540100.tar.gz
# regex: its sdist, whose two C files are compiled and whose package goes in the zip
get https://files.pythonhosted.org/packages/fc/f2/af1da9d3ceed77bfcdce40427d49ba0be94e4fe84245e3bfef68c10e75b6/regex-2026.9.29.tar.gz regex-2026.9.29.tar.gz
# matplotlib: the five C libraries at matplotlib 3.11.2's own wrap versions, which give
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
# matplotlib's second milestone: contourpy's sdist, whose C++ is compiled
get https://files.pythonhosted.org/packages/83/5a/a55177dd22553a277388e8a1b3220e92de91bacb28356cdc73caa240121d/contourpy-1.4.0.tar.gz contourpy-1.4.0.tar.gz
# lxml: libxml2 and libxslt, the newest release of each, and lxml's sdist, whose
# Cython-generated C is compiled
get https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.4.tar.xz libxml2-2.15.4.tar.xz
get https://download.gnome.org/sources/libxslt/1.1/libxslt-1.1.45.tar.xz libxslt-1.1.45.tar.xz
get https://files.pythonhosted.org/packages/23/ad/28ecd7cb894d172f3c9c80a075eeeb2017ac62e3632cee05a5f9493547eb/lxml-6.1.3.tar.gz lxml-6.1.3.tar.gz
# scipy: its sdist, built with meson against OpenBLAS 0.3.34, whose C LAPACK is the
# LAPACK (no Fortran compiler targets wasm32-wasip1)
get https://files.pythonhosted.org/packages/7e/74/66de6258867beb2ef08f35f9f2ac017a52cacd5081714d239ff1a442d458/scipy-1.18.1.tar.gz scipy-1.18.1.tar.gz
get https://github.com/OpenMathLib/OpenBLAS/releases/download/v0.3.34/OpenBLAS-0.3.34.tar.gz OpenBLAS-0.3.34.tar.gz
# scikit-learn: its sdist, Cython, C and C++ built with meson against step 57's scipy
get https://files.pythonhosted.org/packages/d2/eb/eaf5e07fcc0da7149b0e084f24e54edd7441b9a89ce7e034032ae97fe3a0/scikit_learn-1.9.1.tar.gz scikit_learn-1.9.1.tar.gz
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
# Tier A: thirty pure-Python distributions, each its py3-none-any wheel, but pyyaml
# and markupsafe, which publish no pure wheel: their sdists, whose pure package folders step 70 takes
get https://files.pythonhosted.org/packages/c0/da/977ded879c29cbd04de313843e76868e6e13408a94ed6b987245dc7c8506/openpyxl-3.1.5-py2.py3-none-any.whl openpyxl-3.1.5-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/c1/8b/5fe2cc11fee489817272089c4203e679c63b570a5aaeb18d852ae3cbba6a/et_xmlfile-2.0.0-py3-none-any.whl et_xmlfile-2.0.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/3a/0c/3662f4a66880196a590b202f0db82d919dd2f89e99a27fadef91c4a33d41/xlsxwriter-3.2.9-py3-none-any.whl xlsxwriter-3.2.9-py3-none-any.whl
get https://files.pythonhosted.org/packages/1a/62/c8d562e7766786ba6587d09c5a8ba9f718ed3fa8af7f4553e8f91c36f302/xlrd-2.0.2-py2.py3-none-any.whl xlrd-2.0.2-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/85/e6/24c944e473c34e818cf1b98085796fcd780465ecfe17663f2bf8fee1958b/pypdf-6.21.1-py3-none-any.whl pypdf-6.21.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/07/6c/aa3f2f849e01cb6a001cd8554a88d4c77c5c1a31c95bdf1cf9301e6d9ef4/defusedxml-0.7.1-py2.py3-none-any.whl defusedxml-0.7.1-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/88/c6/92fcd42f1ba33e1184263f25bfabf3d27c383410470f169e4b8163bf9c17/beautifulsoup4-4.15.0-py3-none-any.whl beautifulsoup4-4.15.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/49/ca/f639c80449997b88aba7bc9705d25dd76cc0844f45f187862fd8f8bb18fa/soupsieve-3.0.3-py3-none-any.whl soupsieve-3.0.3-py3-none-any.whl
get https://files.pythonhosted.org/packages/6c/dd/a834df6482147d48e225a49515aabc28974ad5a4ca3215c18a882565b028/html5lib-1.1-py2.py3-none-any.whl html5lib-1.1-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/77/c6/040cbc72480d789a5f40d63fb484d3106554c4dfa2d2b70ad5022057750f/webencodings-0.6.1-py3-none-any.whl webencodings-0.6.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz pyyaml-6.0.3.tar.gz
get https://files.pythonhosted.org/packages/c7/18/c86eb8e0202e32dd3df50d43d7ff9854f8e0603945ff398974c1d91ac1ef/tomli_w-1.2.0-py3-none-any.whl tomli_w-1.2.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl jinja2-3.1.6-py3-none-any.whl
get https://files.pythonhosted.org/packages/38/9b/e422a865e1d5d57d0e509b4e0bf1c1a70a7f6382c29a5aa428df994c8bc8/markupsafe-3.0.4.tar.gz markupsafe-3.0.4.tar.gz
get https://files.pythonhosted.org/packages/99/55/db07de81b5c630da5cbf5c7df646580ca26dfaefa593667fc6f2fe016d2e/tabulate-0.10.0-py3-none-any.whl tabulate-0.10.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/fc/ad/d07d7862a62ffa6d79d68074d14823243dd235a77c45262acbf6adeb28bf/charset_normalizer-3.5.2-py3-none-any.whl charset_normalizer-3.5.2-py3-none-any.whl
get https://files.pythonhosted.org/packages/38/34/98a2f52245f4d47be93b580dae5f9861ef58977d73a79eb47c58f1ad1f3a/xmltodict-1.0.4-py3-none-any.whl xmltodict-1.0.4-py3-none-any.whl
get https://files.pythonhosted.org/packages/dc/76/3af777226b63a5e64a6b36b1ec5855c14e2b94a37096d4760e595fc43511/networkx-3.7.tar.gz networkx-3.7.tar.gz
get https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl sympy-1.14.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl mpmath-1.3.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/20/70/cd3cf5cff538323076a879edef02cce6f13f7d75e03d12f211b0a0dbd178/patsy-1.0.3-py2.py3-none-any.whl patsy-1.0.3-py2.py3-none-any.whl
get https://files.pythonhosted.org/packages/64/b4/17d4b0b2a2dc85a6df63d1157e028ed19f90d4cd97c36717afef2bc2f395/attrs-26.1.0-py3-none-any.whl attrs-26.1.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/5d/57/3c4b1c6f2e0cc29ba023802458ea3d2a996f87085559e4a5f2192d549532/more_itertools-11.2.1-py3-none-any.whl more_itertools-11.2.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/db/17/4c8beb6c8c4176c6bf143bfd7e1e4dd6719b00ced90738c7ac471b71c1df/toolz-1.2.0-py3-none-any.whl toolz-1.2.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/a7/03/921a3d3c75785aca9ebfbfcabfbc3a1be12e2ab5265deb026d55a5a3f83e/tqdm-4.70.1-py3-none-any.whl tqdm-4.70.1-py3-none-any.whl
get https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl typing_extensions-4.16.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/18/53/84099323c2ec4be98d935f63c033ac4151ee83836ca1050ede3b3aadf155/joblib-1.6.0-py3-none-any.whl joblib-1.6.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/88/39/799be3f2f0f38cc727ee3b4f1445fe6d5e4133064ec2e4115069418a5bb6/cloudpickle-3.1.2-py3-none-any.whl cloudpickle-3.1.2-py3-none-any.whl
get https://files.pythonhosted.org/packages/43/3f/f88a53f60a472b46f4023f56d204dd7de33d34c5d2acbfa0d70a674e639e/threadpoolctl-3.7.0-py3-none-any.whl threadpoolctl-3.7.0-py3-none-any.whl
get https://files.pythonhosted.org/packages/d1/89/5d4c86da1130d9059681e5b6cd7645df5c10279a6a079c5c37dcb2cc6f3f/narwhals-2.27.1-py3-none-any.whl narwhals-2.27.1-py3-none-any.whl
# seaborn and reportlab: seaborn's sdist, which holds the licences of the five
# pieces of code it vendors (its wheel holds one licence), and reportlab's wheel; both pure Python
get https://files.pythonhosted.org/packages/86/59/a451d7420a77ab0b98f7affa3a1d78a313d2f7281a57afb1a34bae8ab412/seaborn-0.13.2.tar.gz seaborn-0.13.2.tar.gz
get https://files.pythonhosted.org/packages/db/cb/dacbc268cb68d0428ea2cbd85266195a9ab3e677449589ddae59bd7542ac/reportlab-5.0.1-py3-none-any.whl reportlab-5.0.1-py3-none-any.whl

# Licence notices of what wasi-sdk 34 links in (its tarball carries none), at the commits its VERSION
# names (wasi-libc 2e6fb9d8, LLVM 895aa2c8, 23.1.0)
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/LICENSE wasi-libc-2e6fb9d8-LICENSE
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/LICENSE-APACHE wasi-libc-2e6fb9d8-LICENSE-APACHE
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/LICENSE-APACHE-LLVM wasi-libc-2e6fb9d8-LICENSE-APACHE-LLVM
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/LICENSE-MIT wasi-libc-2e6fb9d8-LICENSE-MIT
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/libc-top-half/musl/COPYRIGHT wasi-libc-2e6fb9d8-musl-COPYRIGHT
get https://raw.githubusercontent.com/WebAssembly/wasi-libc/2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13/libc-bottom-half/cloudlibc/LICENSE wasi-libc-2e6fb9d8-cloudlibc-LICENSE
get https://raw.githubusercontent.com/llvm/llvm-project/895aa2c896ada719451be2e3673c83da8ddf1141/libcxx/LICENSE.TXT llvm-895aa2c8-libcxx-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/895aa2c896ada719451be2e3673c83da8ddf1141/libcxxabi/LICENSE.TXT llvm-895aa2c8-libcxxabi-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/895aa2c896ada719451be2e3673c83da8ddf1141/libunwind/LICENSE.TXT llvm-895aa2c8-libunwind-LICENSE.TXT
get https://raw.githubusercontent.com/llvm/llvm-project/895aa2c896ada719451be2e3673c83da8ddf1141/compiler-rt/LICENSE.TXT llvm-895aa2c8-compiler-rt-LICENSE.TXT
# The Unicode data terms of HarfBuzz's tables, whose tree carries no copy: the
# Unicode License V3 from Unicode's own repository at a commit, so the bytes cannot change
get https://raw.githubusercontent.com/unicode-org/unicodetools/4fd8eca90b30aa4c72543ccddb4c15d05becdf8d/LICENSE unicodetools-4fd8eca9-LICENSE
# The full MPL-2.0 text tqdm's notice needs: its wheel carries only Exhibit A;
# SPDX's license-list-data at a commit, so the bytes cannot change
get https://raw.githubusercontent.com/spdx/license-list-data/31ba1a50e5397e00a304dbadc76531740e89ee48/text/MPL-2.0.txt spdx-31ba1a50-MPL-2.0.txt
# The notices of three projects scikit-learn adapts code from with no full notice of their own:
# numpydoc's docscrape, django's slugify and pytest's lines in
# sklearn/utils/_testing.py, each at the last commit that touched the file
get https://raw.githubusercontent.com/numpy/numpydoc/894c8c47646fcbb4eae4fca068c229ae761f7a62/LICENSE.txt numpydoc-894c8c47-LICENSE.txt
get https://raw.githubusercontent.com/django/django/1dae4ac1778f04805c0ed62c8debb13b281ba02b/LICENSE django-1dae4ac1-LICENSE
get https://raw.githubusercontent.com/pytest-dev/pytest/0d90a31d4a647fa7ba0d53a05b9266c2d4aaa05a/LICENSE pytest-0d90a31d-LICENSE

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
# Every pin this run fetched or found must have verified: a name with no line in SHA256SUMS is
# skipped by --ignore-missing, so it is named here and fails the step.
# set -f: the names are split on spaces, never expanded as patterns.
UNPINNED=""
set -f
for name in $NAMES; do
  grep -Fqx "$name: OK" "$checked" || UNPINNED="$UNPINNED $name"
done
set +f
if [ -n "$UNPINNED" ]; then
  echo "ERROR: no pin in downloads/SHA256SUMS for:$UNPINNED" >&2
  exit 1
fi
