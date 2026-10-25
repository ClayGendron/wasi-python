# Sourced by every build step: where things are, the line (scripts/line.conf),
# and the one host Python's environment.
# Downloads are untrusted data: they are unpacked under build/ and run only as build tools.
HERE=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
D="$HERE/downloads"
B="$HERE/build"
. "$HERE/scripts/line.sh"
. "$HERE/scripts/steps/remove.sh"
T="$B/tools"
SDK="$T/$WASI_SDK_DIR"
# The SDK whose clang compiles: $SDK itself on the arm64 hosts; on x86_64
# Linux the arm64 Linux SDK, whose clang step 10 puts behind $SDK/bin/clang under the emulator. Its
# sysroot and builtins are the ones the emulated driver links.
CSDK="$T/$COMPILER_SDK_DIR"
HOSTPY="$T/python/bin/python3"
PKGCONF="$T/pylib/pkgconf/.bin/pkgconf"  # the pinned pkgconf wheel's binary (step 10)
CP="$B/Python-$PYTHON_VERSION"
W="$CP/cross-build/wasm32-wasip1"
OUT="$B/out"

export WASI_SDK_PATH="$SDK"
# Step 10's shim for the pinned host Python comes first: every Python a step finds by name.
export PATH="$T/host-python:$T/pylib/bin:$T/$WASMTIME_DIR:$PATH"
export PYTHONPATH="$T/pylib"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$B/uv-cache}"
# Build tools must not leave bytecode caches inside the upstream source trees.
export PYTHONDONTWRITEBYTECODE=1

# Marshal writes a string as shared or not by its reference count in the compiling process, and
# that depends on whether the host Python loaded its own stdlib from bytecode caches or from source.
# A step that marshals code (60, 70) first removes any cache an outside run of the host Python left,
# so the same inputs always give the same bytes.
host_from_source() {
  find "$T/python/lib" -name __pycache__ -type d -prune | while read -r d; do remove "$d"; done
}

# Apply a tree's carried patches right after its unpack, before anything reads it.
patch_tree() {
  sh "$HERE/scripts/steps/apply_patches.sh" "$1" "$HERE/recipes/patches/$(basename "$1")"
}

# Fail the step with one line naming what is missing.
die() {
  echo "ERROR: $*" >&2
  exit 1
}

# The one line of downloads/SHA256SUMS that pins $1, found by its name field compared as text:
# never as a pattern, where a `.` would match any character and let an unpinned name pass on
# another name's line, and never as numbers (the empty strings make awk compare strings). The
# name reaches awk through the environment, which keeps its backslashes as written. No line, or
# more than one, fails the step.
pin_line() {
  PIN_NAME=$1 awk '
    NF == 2 && $2 "" == ENVIRON["PIN_NAME"] "" { n++; line = $0 }
    END { if (n == 1) print line; exit n == 1 ? 0 : n == 0 ? 4 : 5 }
  ' "$D/SHA256SUMS" && return 0
  case $? in
    4) die "$1 is not pinned in downloads/SHA256SUMS" ;;
    5) die "$1 is pinned twice in downloads/SHA256SUMS" ;;
    *) die "downloads/SHA256SUMS cannot be read" ;;
  esac
}

# The pinned file's path, its SHA-256 verified again here, so a step run on its own never uses
# bytes that changed after scripts/00_download.sh checked them.
pinned() {
  [ -s "$D/$1" ] || die "downloads/$1 is missing: run scripts/00_download.sh"
  pin_line "$1" > "$B/.pin-check"
  (cd "$D" && shasum -a 256 -c "$B/.pin-check" > /dev/null 2>&1) || die "downloads/$1 does not match its pin"
  rm -f "$B/.pin-check"
  printf '%s\n' "$D/$1"
}

# The SHA-256 that downloads/SHA256SUMS pins for $1, by the same exact selection.
pin_of() {
  pin_sum=$(pin_line "$1") || exit 1
  printf '%s\n' "${pin_sum%% *}"
}

# Every meson configure passes this, so a wrap that pkg-config does not satisfy fails the build
# instead of fetching a subproject over the network and building it in.
MESON_WRAP="--wrap-mode=nodownload"
