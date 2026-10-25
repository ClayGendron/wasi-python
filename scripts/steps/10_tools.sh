#!/bin/sh
# Step 10: unpack the toolchain and the host Python under build/tools/, replace the toolchain's wasm
# runtime with the host-neutral one, and install the build tools (Cython, meson, ninja,
# versioneer, pkgconf) from their pinned wheels: offline, with their hashes (pkgconf
# for matplotlib), and the build host's numpy, for f2py alone. On x86_64 Linux, put
# the arm64 Linux SDK's clang, under the pinned qemu-aarch64, behind the native SDK's clang, and
# stop unless it is in place.
set -eu
. "$(dirname "$0")/common.sh"

SDK_TGZ=$(pinned "$WASI_SDK_DIR.tar.gz")
WASMTIME_TXZ=$(pinned "$WASMTIME_DIR.tar.xz")
PYTHON_TGZ=$(pinned "$HOST_PYTHON_ARCHIVE")
SYSROOT_TGZ=$(pinned "wasi-sysroot-$WASI_SDK_VERSION.0.tar.gz")
RT_TGZ=$(pinned "libclang_rt-$WASI_SDK_VERSION.0.tar.gz")
WHEELS="$CYTHON_WHEEL meson-1.12.1-py3-none-any.whl
$NINJA_WHEEL versioneer-0.29-py3-none-any.whl $PKGCONF_WHEEL"

remove "$T" "$B/wheelhouse"
mkdir -p "$T" "$B/wheelhouse"
for archive in "$SDK_TGZ" "$WASMTIME_TXZ" "$PYTHON_TGZ"; do
  tar -xf "$archive" -C "$T"
done
[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"

# The one host Python every step runs. build/tools/host-python/ holds
# python, python3 and python<major>.<minor>, each exec'ing $HOSTPY, and common.sh puts it first on
# PATH, so meson's find_program, an `env python3` shebang (HarfBuzz's and matplotlib's generators)
# and configure's probes (CPython's PYTHON_FOR_REGEN) all find the pinned interpreter. Behind it,
# scripts/build.sh puts a refusing stand-in for every other Python name. The gate (Decision 5):
# each name resolves to the shim, and the route a shebang takes reaches the pinned prefix.
SHIM="$T/host-python"
mkdir -p "$SHIM"
for name in python python3 "python$PYTHON_MM"; do
  printf '#!/bin/sh\nexec "%s" "$@"\n' "$HOSTPY" > "$SHIM/$name"
  chmod 755 "$SHIM/$name"
done
for name in python python3 "python$PYTHON_MM"; do
  found=$(command -v "$name" || echo nothing)
  [ "$found" = "$SHIM/$name" ] || die "host python gate: $name is $found, not $SHIM/$name"
done
prefix=$(/usr/bin/env python3 -c 'import sys; print(sys.prefix)') \
  || die "host python gate: /usr/bin/env python3 failed"
[ "$prefix" = "$T/python" ] || die "host python gate: /usr/bin/env python3's prefix is $prefix, not $T/python"
behind=$(command -v python2 || echo none)
echo "host python: python3 is ${SHIM#"$HERE"/}/python3, Python $("$HOSTPY" -c 'import platform; print(platform.python_version())'), prefix ${prefix#"$HERE"/}; behind it python2 is ${behind#"$HERE"/}"

# The wasm runtime every host links: a host tarball keeps only its compiler.
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

# x86_64 Linux compiles with the arm64 Linux SDK's clang under the pinned qemu-aarch64:
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

  # The gate: the build stops here, in one line, unless each probe holds.
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

# Every compile contracts nothing. -ffp-contract=off goes into the
# toolchain's own configuration files, bin/clang.cfg and bin/clang++.cfg, which every clang and
# clang++ call reads whatever the caller (CPython's driver, wasi-cc and wasi-cxx, meson, autoconf,
# a direct compile), so no compile can miss it. wasi-sdk's x86_64 and aarch64 builds of the same
# clang order two stack slots differently only where the IR holds llvm.fmuladd, which this flag
# removes. Every SDK tree
# under build/tools/ gets it: $SDK, and $CSDK when the fallback's switch puts another tree's clang
# behind $SDK/bin/clang. On wasm32 nothing fuses a multiply and an add, so run-time arithmetic
# does not change; a constant the compiler folds moves to the value the run time computes.
contract_off() { # an SDK tree
  for cfg in clang.cfg clang++.cfg; do
    f="$1/bin/$cfg"
    [ -f "$f" ] || die "compiler gate: $1 has no bin/$cfg"
    [ -z "$(tail -c 1 "$f")" ] || printf '\n' >> "$f"
    printf '%s\n' "-ffp-contract=off" >> "$f"
    [ "$(grep -c -x -F -- '-ffp-contract=off' "$f")" = 1 ] \
      || die "compiler gate: $f does not hold -ffp-contract=off exactly once"
  done
}
contract_off "$SDK"
[ "$CSDK" = "$SDK" ] || contract_off "$CSDK"
# The gate: each driver's -cc1 line carries -ffp-contract=off once and no other -ffp-contract=
# value, through $SDK/bin/<driver> as every step calls it (the launcher, when the switch is thrown).
G="$B/compiler-gate"
mkdir -p "$G"
printf 'int main(void) { return 0; }\n' > "$G/fp-probe.c"
fp_probe() { # the driver's name, then its language flags
  name=$1
  shift
  "$SDK/bin/$name" --target=wasm32-wasip1 -### -c "$@" "$G/fp-probe.c" -o "$G/fp-probe.o" \
    > "$G/fp-$name.txt" 2>&1 || die "compiler gate: $name -### failed (build/compiler-gate/fp-$name.txt)"
  cc1=$(grep -F -- '"-cc1"' "$G/fp-$name.txt" | head -n 1)
  [ -n "$cc1" ] || die "compiler gate: $name -### printed no -cc1 line (build/compiler-gate/fp-$name.txt)"
  values=$(printf '%s\n' "$cc1" | grep -o -E -- '"-ffp-contract=[^"]*"' | tr '\n' ' ')
  [ "$values" = '"-ffp-contract=off" ' ] \
    || die "compiler gate: $name's -cc1 line carries ${values:-no -ffp-contract}, not -ffp-contract=off once (build/compiler-gate/fp-$name.txt)"
  echo "compiler gate: $name contracts nothing (-ffp-contract=off)"
}
fp_probe clang
fp_probe clang++ -x c++

# Only the pinned wheels, and a requirements file carrying their pinned hashes.
REQS="$B/tools-requirements.txt"
: > "$REQS"
for wheel in $WHEELS; do
  cp "$(pinned "$wheel")" "$B/wheelhouse/"
  sha=$(pin_of "$wheel")
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
# pkg-config it finds on PATH instead. Steps 37 and 55 name it in their cross file.
[ -x "$PKGCONF" ] || die "the pkgconf wheel did not install $PKGCONF"
# f2py's numpy: the build host's own pinned numpy wheel, in a folder of its
# own, never in build/tools/pylib, where it would shadow the host-side numpy stand-in that pandas'
# and scipy's builds import. scripts/f2py-host runs f2py from it, on scipy's .pyf files only.
F2PY="$T/f2py-numpy"
cp "$(pinned "$NUMPY_HOST_WHEEL")" "$B/wheelhouse/"
sha=$(pin_of "$NUMPY_HOST_WHEEL")
printf 'numpy==2.5.2 --hash=sha256:%s\n' "$sha" > "$B/f2py-requirements.txt"
uv pip install --python "$HOSTPY" --target "$F2PY" --offline --no-index --find-links "$B/wheelhouse" --require-hashes -r "$B/f2py-requirements.txt"
f2py_version=$(PYTHONPATH="$F2PY" "$HOSTPY" -s -c 'import numpy; print(numpy.__version__)')
[ "$f2py_version" = 2.5.2 ] || die "build/tools/f2py-numpy holds numpy $f2py_version, not 2.5.2"
echo "tools: python $("$HOSTPY" -c 'import platform; print(platform.python_version())'), meson $(meson --version), ninja $(ninja --version), cython $(cython --version 2>&1 | cut -d' ' -f3), pkgconf $("$PKGCONF" --version), f2py numpy $f2py_version"
