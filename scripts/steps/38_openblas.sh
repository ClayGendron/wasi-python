#!/bin/sh
# Step 38: OpenBLAS 0.3.34 for wasm32-wasip1, its C LAPACK the LAPACK (spec 037, Decisions 3 to 5):
# unpacked from its pinned tarball, its three carried patches applied (every C LAPACK subroutine
# returns void), copied, built in the copy with make (the judged tree stays its tarball plus the
# patches whatever make writes) through scripts/wasi-cc, and installed under build/openblas-wasi/.
# The five WASI fixes are make variables and one empty stand-in header, never a patch. Then the
# link-whole gate: every object of the archive linked into a throwaway module, and the step stops on
# any `signature mismatch`. Needs step 10.
set -eu
. "$(dirname "$0")/common.sh"

TOP=OpenBLAS-0.3.34
TARBALL=$(pinned "$TOP.tar.gz")
SRC="$B/$TOP"
WORK="$B/openblas-build"
INST="$B/openblas-wasi"
GATE="$B/openblas-gate"
remove "$SRC" "$WORK" "$INST" "$GATE"
tar -xzf "$TARBALL" -C "$B"
[ -d "$SRC" ] || die "the pinned tarball did not unpack to build/$TOP"
patch_tree "$SRC"
cp -Rp "$SRC" "$WORK"

# The make line (Decision 4). Every host fact that reaches a compile is pinned here: the Fortran
# vendor f_check would otherwise take from a compiler on PATH (it falls back to GFORTRAN when it
# finds none, f_check:63-68), and the core count getarch writes (it reaches a compile only through
# NUM_THREADS, pinned too). HOSTCC builds OpenBLAS's getarch for the build host. c_check names NM
# and OBJCOPY after the wrapper's folder; libs, netlib and install never run them.
#   ARCH=wasm, -DARCH_WASM   OpenBLAS knows wasm only through __EMSCRIPTEN__
#   -D_WASI_EMULATED_MMAN    its buffer is mmap'd: wasi-libc's emulation (malloc), linked at step 60
#   -DNO_SYSV_IPC            no System V shared memory
#   -include sched.h         its one WASI call, sched_yield, which python.wasm already imports
#   recipes/openblas-include an empty <sys/ipc.h>, which memory.c includes outside its guard
# WASM128_GENERIC compiles OpenBLAS's kernels with -msimd128: the one new wasm feature (decision 29).
CFLAGS="-O2 -ffile-prefix-map=$HERE=/wasi-python-build -D_WASI_EMULATED_SIGNAL"
CFLAGS="$CFLAGS -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID -D_WASI_EMULATED_MMAN"
CFLAGS="$CFLAGS -DNO_SYSV_IPC -include sched.h -DARCH_WASM -I$HERE/recipes/openblas-include"
openblas_make() { # targets and extra variables
  make -C "$WORK" "$@" \
    CC="$HERE/scripts/wasi-cc" HOSTCC=cc \
    AR="$SDK/bin/llvm-ar" RANLIB="$SDK/bin/llvm-ranlib" \
    TARGET=WASM128_GENERIC ARCH=wasm OSNAME=WASI NOFORTRAN=1 C_LAPACK=1 NO_LAPACKE=1 \
    USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NUM_CORES=1 F_COMPILER=GFORTRAN \
    NO_SHARED=1 NO_AFFINITY=1 DYNAMIC_ARCH=0 \
    CFLAGS="$CFLAGS"
}
# Two runs, never `make libs netlib`: given both goals at once, GNU make 4 runs them in parallel and
# both `ar -ru` the one archive, which loses members (a Linux arm64 build lost 20, EXECUTED). Each
# run is parallel inside; the archive takes libs's members, then netlib's, in prerequisite order.
openblas_make -j8 libs > "$WORK.log" 2>&1 || { tail -n 30 "$WORK.log"; die "OpenBLAS's make libs failed (build/openblas-build.log)"; }
openblas_make -j8 netlib >> "$WORK.log" 2>&1 || { tail -n 30 "$WORK.log"; die "OpenBLAS's make netlib failed (build/openblas-build.log)"; }
openblas_make install PREFIX="$INST" > "$WORK-install.log" 2>&1 || { tail -n 30 "$WORK-install.log"; die "OpenBLAS's make install failed"; }
LIB="$INST/lib/libopenblas.a"
[ -s "$LIB" ] || die "make install wrote no build/openblas-wasi/lib/libopenblas.a"
for f in include/cblas.h include/f77blas.h include/openblas_config.h lib/pkgconfig/openblas.pc; do
  [ -f "$INST/$f" ] || die "make install wrote no build/openblas-wasi/$f"
done
echo "config.h:"
cat "$WORK/config.h"
echo "warnings: $(grep -c 'warning:' "$WORK.log" || :)"
grep -o '\[-W[a-z0-9-]*\]' "$WORK.log" | sort | uniq -c | sort -rn || :

# The link-whole gate (Decision 4): every object linked into one module, libc left undefined; one
# `signature mismatch` per name whose callers and definition disagree. A clash a direct call never
# reaches would trap at run time through a pointer, so none may be left.
mkdir -p "$GATE"
"$SDK/bin/wasm-ld" --no-entry --allow-undefined --no-gc-sections --export-all \
  --whole-archive "$LIB" --no-whole-archive -o "$GATE/whole.wasm" > "$GATE/link.log" 2>&1 \
  || { tail -n 20 "$GATE/link.log"; die "the link-whole gate's link failed (build/openblas-gate/link.log)"; }
n=$(grep -c 'signature mismatch' "$GATE/link.log" || :)
if [ "$n" != 0 ]; then
  first=$(grep -m 1 'signature mismatch' "$GATE/link.log")
  die "link-whole gate: $n signature mismatches in libopenblas.a, the first: $first"
fi
remove "$GATE/whole.wasm"
echo "link-whole gate: 0 signature mismatches"
echo "openblas: libopenblas.a $(wc -c < "$LIB" | tr -d ' ') bytes, $(shasum -a 256 "$LIB" | cut -c1-16)"
