#!/bin/sh
# Step 52: the Rust modules (recipes/rust/modules.txt: orjson 3.13.0 and the build's own probe,
# _rust_probe) as one static library, build/rust/lib/librust_modules.a, for step 60. One umbrella
# crate links them all, so Rust's standard library is linked once. The standard library itself is
# rebuilt from rust-src with the line's panic strategy (RUST_PANIC), on the pinned stable compiler,
# which RUSTC_BOOTSTRAP=1 lets take -Zbuild-std. Cargo runs offline from an empty cargo home whose
# one file points crates-io at the pinned crates, unpacked here with each file's SHA-256, and the
# host's own Rust settings are unset first. Then the archive keeps only the crates' own objects
# (scripts/rust_objects.py keep), its direct WASI imports are routed through the wrapped entropy
# call by a written shim (imports), and it must define exactly the listed init functions (inits)
# and none of the SDK runtime's names (foreign). Needs steps 10 and 20.
set -eu
. "$(dirname "$0")/common.sh"

RUST="$T/rust"
[ -x "$RUST/bin/cargo" ] || die "no Rust toolchain at build/tools/rust: run step 10"
[ -f "$W/pyconfig.h" ] || die "no WASI pyconfig.h at $W: run step 20"
LIBPYTHON="$W/libpython$PYTHON_MM.a"
[ -s "$LIBPYTHON" ] || die "no $LIBPYTHON: run step 20"
case "$RUST_PANIC" in
  unwind|abort) ;;
  *) die "scripts/line.conf's RUST_PANIC is $RUST_PANIC, not unwind or abort" ;;
esac
R="$B/rust"
O="$B/orjson-3.13.0"
VENDOR="$R/vendor"
CH="$R/cargo-home"
TARGET="$R/target"
remove "$R" "$O" "$B/Cargo.toml" "$B/Cargo.lock"
mkdir -p "$VENDOR" "$CH" "$R/lib"

# Cargo reads .cargo/config.toml from every folder above the one it runs in, $HOME/.cargo among
# them when the checkout lies under $HOME: any such file would change the build without a word.
dir=$B
while :; do
  for f in "$dir/.cargo/config" "$dir/.cargo/config.toml"; do
    [ ! -e "$f" ] || die "$f would reach cargo's build: move it, or build from another folder"
  done
  [ "$dir" != / ] || break
  dir=$(dirname "$dir")
done

# 1. orjson's tree, with its carried patch: the library is also an rlib, so the umbrella links it.
tar -xzf "$(pinned orjson-3.13.0.tar.gz)" -C "$B"
[ -d "$O" ] || die "the pinned sdist did not unpack to build/orjson-3.13.0"
patch_tree "$O"
ORJSON_VERSION=$(sed -n 's/^Version: //p' "$O/PKG-INFO" | head -n 1)
[ "$ORJSON_VERSION" = 3.13.0 ] || die "orjson's PKG-INFO says version $ORJSON_VERSION"

# 2. The crates: each crates.io package of the lock from its pin, then rust-src's vendored crates,
# which the standard library's build resolves through crates-io too.
"$HOSTPY" -I "$HERE/scripts/rust_vendor.py" crates "$HERE/recipes/rust/Cargo.lock" "$D/SHA256SUMS" "$D" "$VENDOR" \
  > "$R/vendor.log" 2>&1 || { grep '^ERROR' "$R/vendor.log" | head -n 20; die "the pinned crates did not unpack (build/rust/vendor.log)"; }
"$HOSTPY" -I "$HERE/scripts/rust_vendor.py" std "$RUST/lib/rustlib/src/rust/library/vendor" "$VENDOR" \
  >> "$R/vendor.log" 2>&1 || { grep '^ERROR' "$R/vendor.log" | head -n 20; die "rust-src's vendored crates did not join the pinned ones (build/rust/vendor.log)"; }

# 3. The workspace, rooted at build/ so every path crate hashes into its symbols by a path inside
# it; the source replacement; PyO3's view of the line's CPython, static and 32-bit.
cp "$HERE/recipes/rust/Cargo.toml" "$HERE/recipes/rust/Cargo.lock" "$B/"
cp -R "$HERE/recipes/rust/modules" "$R/modules"
cat > "$CH/config.toml" <<EOF
[source.crates-io]
replace-with = "pinned"

[source.pinned]
directory = "$VENDOR"

[net]
offline = true
EOF
cat > "$R/pyo3.cfg" <<EOF
implementation=CPython
version=$PYTHON_MM
shared=false
abi3=false
lib_name=python$PYTHON_MM
pointer_width=32
build_flags=
suppress_build_script_link_lines=true
EOF

# 4. The build. The host's own Rust settings are unset: a RUSTFLAGS, a wrapper (sccache would put
# an unpinned tool in the compile), a CARGO_BUILD_* or CARGO_PROFILE_* would each change the bytes.
# The target's flags go by CARGO_ENCODED_RUSTFLAGS, which cargo reads before any other, and reach
# only the target's crates, not build scripts or proc macros. The more specific path prefix comes
# last, since rustc applies the last that matches: the standard library's sources read as Rust's
# own release builds name them. orjson's library is a cdylib too, which cargo links though nothing
# uses it, and CPython's functions are not there to resolve: the link leaves them undefined, as an
# extension module's do until the interpreter loads it. The static library takes no link flags.
unset RUSTFLAGS RUSTC_WRAPPER RUSTC_WORKSPACE_WRAPPER CARGO_ENCODED_RUSTFLAGS RUSTDOCFLAGS
for v in $(env | sed -n 's/^\(CARGO_BUILD_[A-Za-z0-9_]*\)=.*/\1/p; s/^\(CARGO_PROFILE_[A-Za-z0-9_]*\)=.*/\1/p; s/^\(CARGO_TARGET_[A-Za-z0-9_]*\)=.*/\1/p'); do
  unset "$v"
done
COMMIT=$("$RUST/bin/rustc" -vV | sed -n 's/^commit-hash: //p')
[ -n "$COMMIT" ] || die "build/tools/rust's rustc -vV names no commit-hash"
US=$(printf '\037')
RUSTFLAGS_TARGET="-Cpanic=$RUST_PANIC${US}-Clink-arg=--allow-undefined${US}--remap-path-prefix=$HERE=/wasi-python-build${US}--remap-path-prefix=$RUST/lib/rustlib/src/rust=/rustc/$COMMIT"
(
  cd "$B"
  env CARGO_HOME="$CH" CARGO_TARGET_DIR="$TARGET" RUSTC="$RUST/bin/rustc" CARGO="$RUST/bin/cargo" \
    RUSTC_BOOTSTRAP=1 PYO3_CONFIG_FILE="$R/pyo3.cfg" CARGO_PROFILE_RELEASE_PANIC="$RUST_PANIC" \
    CARGO_ENCODED_RUSTFLAGS="$RUSTFLAGS_TARGET" CC_wasm32_wasip1="$HERE/scripts/wasi-cc" \
    AR_wasm32_wasip1="$SDK/bin/llvm-ar" CFLAGS_wasm32_wasip1="-O2 -DNDEBUG -ffile-prefix-map=$HERE=/wasi-python-build" \
    "$RUST/bin/cargo" build --release --frozen --offline --target wasm32-wasip1 \
    "-Zbuild-std=std,panic_$RUST_PANIC" -p wasi_python_rust
) > "$R/cargo.log" 2>&1 || { tail -n 20 "$R/cargo.log"; die "cargo build failed (build/rust/cargo.log)"; }
# The crates whose code the library holds, for their notices (scripts/assemble_artifacts.py): the
# build graph cargo resolves for wasm32-wasip1, ours and the standard library's, proc macros and
# path crates left out. LTO's result cannot be read back crate by crate, so the graph is the list.
tree_of() { # working folder, package, features...
  (
    cd "$1"
    env CARGO_HOME="$CH" CARGO_TARGET_DIR="$TARGET" RUSTC="$RUST/bin/rustc" RUSTC_BOOTSTRAP=1 \
      PYO3_CONFIG_FILE="$R/pyo3.cfg" "$RUST/bin/cargo" tree --frozen --offline -e normal,no-proc-macro \
      --target wasm32-wasip1 --prefix none --format '{p}' -p "$2" ${3:+--features "$3"}
  ) 2>> "$R/cargo.log" | sed -n 's/^\([A-Za-z0-9_-]*\) v\([^ ]*\)\( (\*)\)\{0,1\}$/\1 \2/p'
}
# std's panic-unwind feature is what -Zbuild-std=std,panic_unwind turns on; abort needs none.
STD_FEATURES=""
[ "$RUST_PANIC" = abort ] || STD_FEATURES=panic-unwind
{ tree_of "$B" wasi_python_rust; tree_of "$RUST/lib/rustlib/src/rust/library" std "$STD_FEATURES"; } \
  | sort -u > "$R/linked-crates.txt"
[ -s "$R/linked-crates.txt" ] || die "cargo tree named no crate (build/rust/cargo.log)"
LIB="$TARGET/wasm32-wasip1/release/libwasi_python_rust.a"
[ -s "$LIB" ] || die "cargo wrote no target/wasm32-wasip1/release/libwasi_python_rust.a"

# 5. Only the crates' own objects: the umbrella's, and the C orjson's build script compiles.
OBJS="$HERE/scripts/rust_objects.py"
A="$R/lib/librust_modules.a"
"$HOSTPY" -I "$OBJS" keep "$SDK/bin/llvm-ar" "$LIB" "$A" "$TARGET" wasi_python_rust orjson rust_probe \
  > "$R/keep.log" 2>&1 || { cat "$R/keep.log"; die "the Rust library holds a member that is neither a module's nor compiler_builtins' (build/rust/keep.log)"; }
kept=$(sed -n 's/^keep: \([0-9]*\) kept.*/\1/p' "$R/keep.log")
dropped=$(sed -n 's/^keep: [0-9]* kept, \([0-9]*\) dropped.*/\1/p' "$R/keep.log")

# 6. The direct WASI imports, each routed through __wasi_random_get, which the reactor's link
# wraps; anything else the link's inputs do not define stops the step.
SYSROOT="$CSDK/share/wasi-sysroot/lib/wasm32-wasip1"
set -- "$CSDK"/lib/clang/*/lib/wasm32-unknown-wasip1/libclang_rt.builtins.a
BUILTINS=$1
RUNTIME="$SYSROOT/libc.a $SYSROOT/eh/libc++abi.a $SYSROOT/eh/libunwind.a $SYSROOT/libsetjmp.a $SYSROOT/libwasi-emulated-mman.a $BUILTINS"
for lib in $RUNTIME; do
  [ -s "$lib" ] || die "the SDK has no $lib"
done
# shellcheck disable=SC2086
"$HOSTPY" -I "$OBJS" imports "$SDK/bin/llvm-nm" "$SDK/bin/llvm-cxxfilt" "$A" "$R/entropy_shim.c" "$LIBPYTHON" $RUNTIME \
  > "$R/imports.log" 2>&1 || { cat "$R/imports.log"; die "the Rust library imports what the shim does not route (build/rust/imports.log)"; }
shimmed=$(sed -n 's/^imports: \([0-9]*\) entropy.*/\1/p' "$R/imports.log")
"$HERE/scripts/wasi-cc" -O2 -c "$R/entropy_shim.c" -o "$R/entropy_shim.o" > "$R/shim.log" 2>&1 \
  || { cat "$R/shim.log"; die "build/rust/entropy_shim.c did not compile"; }
"$SDK/bin/llvm-ar" rsD "$A" "$R/entropy_shim.o"

# 7. The archive's gates: exactly the listed init functions, and nothing the runtime defines.
"$HOSTPY" -I "$OBJS" inits "$SDK/bin/llvm-nm" "$A" "$HERE/recipes/rust/modules.txt" > "$R/inits.log" 2>&1 \
  || { cat "$R/inits.log"; die "the Rust library's init functions are not modules.txt's (build/rust/inits.log)"; }
# shellcheck disable=SC2086
"$HOSTPY" -I "$OBJS" foreign "$SDK/bin/llvm-nm" "$A" $RUNTIME > "$R/foreign.log" 2>&1 \
  || { head -n 20 "$R/foreign.log"; die "the Rust library defines a name the SDK's runtime defines (build/rust/foreign.log)"; }
cat "$R/keep.log" "$R/imports.log" "$R/inits.log" "$R/foreign.log" | grep -v '^shimmed:' || :
echo "rust: wasi_python_rust (orjson $ORJSON_VERSION, _rust_probe), panic=$RUST_PANIC, $kept objects kept, $dropped dropped, $shimmed entropy imports shimmed, $(wc -c < "$A" | tr -d ' ') bytes"
