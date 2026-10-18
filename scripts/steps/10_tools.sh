#!/bin/sh
# Step 10: unpack the toolchain and the host Python under build/tools/, replace the toolchain's wasm
# runtime with the host-neutral one (spec 012), and install the build tools (Cython, meson, ninja,
# versioneer, pkgconf) from their pinned wheels: offline, with their hashes (spec 003; pkgconf,
# spec 023). On x86_64 Linux, put
# the arm64 Linux SDK's clang, under the pinned qemu-aarch64, behind the native SDK's clang, and
# stop unless it is in place (spec 040, Decision 5).
set -eu
. "$(dirname "$0")/common.sh"

SDK_TGZ=$(pinned "$WASI_SDK_DIR.tar.gz")
WASMTIME_TXZ=$(pinned "$WASMTIME_DIR.tar.xz")
PYTHON_TGZ=$(pinned "$HOST_PYTHON_ARCHIVE")
SYSROOT_TGZ=$(pinned "wasi-sysroot-$WASI_SDK_VERSION.0+m.tar.gz")
RT_TGZ=$(pinned "libclang_rt-$WASI_SDK_VERSION.0+m.tar.gz")
WHEELS="$CYTHON_WHEEL meson-1.12.1-py3-none-any.whl
$NINJA_WHEEL versioneer-0.29-py3-none-any.whl $PKGCONF_WHEEL"

remove "$T" "$B/wheelhouse"
mkdir -p "$T" "$B/wheelhouse"
for archive in "$SDK_TGZ" "$WASMTIME_TXZ" "$PYTHON_TGZ"; do
  tar -xf "$archive" -C "$T"
done
[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"

# The wasm runtime every host links (spec 012, Decision 2): a host tarball keeps only its compiler.
# Its own sysroot and its wasm32-wasip1 builtins are removed and replaced by wasi-sdk's host-neutral
# ones, the same bytes on every host. The SDK is a downloaded binary toolchain, not a source tree.
neutral_runtime() { # an SDK tree under build/tools/
  set -- "$1" "$1"/lib/clang/*
  [ "$#" -eq 2 ] && [ -d "$2" ] || die "$1 has $(($# - 1)) lib/clang/* directories, not exactly one"
  builtins="$2/lib/wasm32-unknown-wasip1"
  [ -d "$builtins" ] || die "the SDK has no $builtins"
  remove "$1/share/wasi-sysroot" "$builtins" "$B/neutral-rt"
  mkdir -p "$1/share/wasi-sysroot" "$builtins" "$B/neutral-rt"
  tar -xzf "$SYSROOT_TGZ" -C "$1/share/wasi-sysroot" --strip-components=1
  tar -xzf "$RT_TGZ" -C "$B/neutral-rt" --strip-components=1
  cp "$B/neutral-rt/wasm32-unknown-wasip1/"* "$builtins/"
  remove "$B/neutral-rt"
}
neutral_runtime "$SDK"

# x86_64 Linux compiles with the arm64 Linux SDK's clang under the pinned qemu-aarch64 (spec 040):
# wasi-sdk's x86_64 clang orders two stack slots of one numpy function differently, so every host
# compiles with an arm64 build of the pinned clang. Only the compiler is emulated; every other tool
# stays native. Nothing is installed into the system and nothing is registered with the kernel.
if [ "$CSDK" != "$SDK" ]; then
  CSDK_TGZ=$(pinned "$COMPILER_SDK_DIR.tar.gz")
  tar -xf "$CSDK_TGZ" -C "$T"
  [ -d "$CSDK/bin" ] || die "$COMPILER_SDK_DIR.tar.gz did not unpack to $CSDK"
  neutral_runtime "$CSDK"

  # A .deb is an ar archive whose data.tar.* holds its files: read with the native SDK's llvm-ar and
  # the host's tar (dpkg is not assumed). The emulator is one member of qemu-user, stored with ./;
  # the four runtime packages unpack whole into the guest's root.
  unpack_deb() { # the .deb, the folder, and optionally the one member to take
    remove "$B/deb"
    mkdir -p "$B/deb" "$2"
    (cd "$B/deb" && "$SDK/bin/llvm-ar" x "$1") || die "$(basename "$1") is not an ar archive"
    set -- "$1" "$2" "${3:-}" "$B/deb"/data.tar.*
    [ "$#" -eq 4 ] && [ -f "$4" ] || die "$(basename "$1") has no single data.tar.* member"
    if [ -n "$3" ]; then
      tar -xf "$4" -C "$2" "$3"
    else
      tar -xf "$4" -C "$2"
    fi
    remove "$B/deb"
  }
  deb=$(pinned "$EMULATOR_DEB")
  unpack_deb "$deb" "$B/emulator-deb" ./usr/bin/qemu-aarch64
  mkdir -p "$T/emulator"
  mv "$B/emulator-deb/usr/bin/qemu-aarch64" "$T/emulator/qemu-aarch64"
  remove "$B/emulator-deb"
  for name in "$AARCH64_LIBC_DEB" "$AARCH64_LIBSTDCXX_DEB" "$AARCH64_LIBGCC_DEB" "$AARCH64_LIBTINFO_DEB"; do
    deb=$(pinned "$name")
    unpack_deb "$deb" "$T/aarch64-root"
  done
  # A merged-/usr system's link: the guest's loader is /lib/ld-linux-aarch64.so.1.
  [ -e "$T/aarch64-root/lib" ] || ln -s usr/lib "$T/aarch64-root/lib"
  [ -e "$T/aarch64-root/lib/ld-linux-aarch64.so.1" ] || die "the aarch64 root has no lib/ld-linux-aarch64.so.1"
  # Without a cache in the root, qemu's -L falls through to the host's /etc/ld.so.cache and the
  # guest's loader reads it. An empty file is no cache: the loader maps nothing and searches the
  # root's own folders. The gate's last probe holds this.
  mkdir -p "$T/aarch64-root/etc"
  : > "$T/aarch64-root/etc/ld.so.cache"

  # The launcher sits beside the real aarch64 clang (its InstalledDir, and its RPATH $ORIGIN/../lib).
  # The native tree's real clang is replaced by a link to it, so CPython's driver, scripts/wasi-cc and
  # wasi-cxx, and steps 30 and 35, which all run $SDK/bin/clang, clang++ or clang-cpp, are unchanged,
  # and no step can reach the native compiler by accident.
  cp "$HERE/scripts/clang-emulated" "$CSDK/bin/clang-emulated"
  chmod 755 "$CSDK/bin/clang-emulated"
  REAL=$(readlink -f "$CSDK/bin/clang")
  NATIVE=$(readlink -f "$SDK/bin/clang")
  rm -f "$NATIVE"
  ln -s "$CSDK/bin/clang-emulated" "$NATIVE"
  # The emulated driver runs wasm-ld from its own tree, an aarch64 ELF this host cannot run: it
  # becomes the native linker, with the same arguments.
  rm -f "$CSDK/bin/wasm-ld"
  printf '#!/bin/sh\nexec "%s/bin/wasm-ld" "$@"\n' "$SDK" > "$CSDK/bin/wasm-ld"
  chmod 755 "$CSDK/bin/wasm-ld"

  # The gate (spec 040, Decision 5): the build stops here, in one line, unless each probe holds.
  G="$B/compiler-gate"
  remove "$G"
  mkdir -p "$G"
  [ "$(readlink "$NATIVE")" = "$CSDK/bin/clang-emulated" ] \
    || die "compiler gate: $SDK/bin/clang does not lead to $CSDK/bin/clang-emulated"
  echo "compiler gate: $SDK/bin/clang leads to $CSDK/bin/clang-emulated"
  "$SDK/bin/clang" -v > "$G/clang-v.txt" 2>&1 || die "compiler gate: clang -v failed (build/compiler-gate/clang-v.txt)"
  grep -qxF "InstalledDir: $CSDK/bin" "$G/clang-v.txt" \
    || die "compiler gate: clang -v does not name $CSDK/bin as its InstalledDir"
  echo "compiler gate: clang's InstalledDir is $CSDK/bin"
  printf '__clang__\n__cplusplus\n' > "$G/probe.c"
  "$SDK/bin/clang-cpp" "$G/probe.c" > "$G/clang-cpp.txt" 2>&1 \
    || die "compiler gate: clang-cpp failed (build/compiler-gate/clang-cpp.txt)"
  [ "$(grep -v '^#' "$G/clang-cpp.txt" | grep -v '^ *$' | tr '\n' ' ')" = "1 __cplusplus " ] \
    || die "compiler gate: clang-cpp does not preprocess C (build/compiler-gate/clang-cpp.txt)"
  echo "compiler gate: clang-cpp preprocesses C (__clang__ 1, __cplusplus not defined)"
  "$SDK/bin/clang++" -v > "$G/clang++-v.txt" 2>&1 || die "compiler gate: clang++ -v failed (build/compiler-gate/clang++-v.txt)"
  grep -qxF "Configuration file: $CSDK/bin/clang++.cfg" "$G/clang++-v.txt" \
    || die "compiler gate: clang++ -v does not name $CSDK/bin/clang++.cfg"
  echo "compiler gate: clang++ reads $CSDK/bin/clang++.cfg"
  # The guest's loader, traced with qemu's -L redirection applied: it opens ld.so.cache and maps
  # nothing of it before it opens the next file, so the host's cache is never read.
  "$T/emulator/qemu-aarch64" -strace -L "$T/aarch64-root" -U LD_PRELOAD -U LD_LIBRARY_PATH -U LD_AUDIT \
    "$REAL" --version > "$G/version.txt" 2> "$G/loader-trace.txt" \
    || die "compiler gate: the emulated clang --version failed (build/compiler-gate/loader-trace.txt)"
  awk '
    /openat\(.*"\/etc\/ld\.so\.cache"/ { inside = 1; fd = $NF; seen++; next }
    inside && /mmap\(/ && index($0, "," fd ",0)") { mapped++ }
    inside && /openat\(/ { inside = 0 }
    END { exit !(seen > 0 && mapped == 0) }
  ' "$G/loader-trace.txt" \
    || die "compiler gate: the guest's loader read an ld.so.cache (build/compiler-gate/loader-trace.txt)"
  echo "compiler gate: the guest's loader maps no ld.so.cache; $(head -n 1 "$G/version.txt")"
fi

# Only the pinned wheels, and a requirements file carrying their pinned hashes.
REQS="$B/tools-requirements.txt"
: > "$REQS"
for wheel in $WHEELS; do
  cp "$(pinned "$wheel")" "$B/wheelhouse/"
  sha=$(grep "  $wheel\$" "$D/SHA256SUMS" | cut -c1-64)
  dist=${wheel%%-*}
  rest=${wheel#*-}
  printf '%s==%s --hash=sha256:%s\n' "$dist" "${rest%%-*}" "$sha" >> "$REQS"
done
uv pip install --python "$HOSTPY" --target "$T/pylib" --offline --no-index --find-links "$B/wheelhouse" --require-hashes -r "$REQS"

"$HOSTPY" -c "import platform, sys; assert platform.python_version() == sys.argv[1], sys.version" "$PYTHON_VERSION"
for tool in meson ninja cython; do
  command -v "$tool" > /dev/null || die "$tool is not on PATH from build/tools/pylib/bin"
done
# The pinned pkgconf binary itself, never the wheel's Python entry point, which would run a
# pkg-config it finds on PATH instead (spec 023). Steps 37 and 55 name it in their cross file.
[ -x "$PKGCONF" ] || die "the pkgconf wheel did not install $PKGCONF"
echo "tools: python $("$HOSTPY" -c 'import platform; print(platform.python_version())'), meson $(meson --version), ninja $(ninja --version), cython $(cython --version 2>&1 | cut -d' ' -f3), pkgconf $("$PKGCONF" --version)"
