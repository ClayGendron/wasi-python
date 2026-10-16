# Sourced by every build step (spec 003): where things are, and the one host Python's environment.
# Downloads are untrusted data: they are unpacked under build/ and run only as build tools.
HERE=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
D="$HERE/downloads"
B="$HERE/build"
T="$B/tools"
SDK="$T/wasi-sdk-24.0-arm64-macos"
HOSTPY="$T/python/bin/python3"
CP="$B/Python-3.14.8"
W="$CP/cross-build/wasm32-wasip1"
OUT="$B/out"

export WASI_SDK_PATH="$SDK"
export PATH="$T/pylib/bin:$T/wasmtime-v49.0.3-aarch64-macos:$T/wizer-v11.0.3-aarch64-macos:$PATH"
export PYTHONPATH="$T/pylib"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$B/uv-cache}"
# Build tools must not leave bytecode caches inside the upstream source trees (spec 003, Decision 4).
export PYTHONDONTWRITEBYTECODE=1

# Marshal writes a string as shared or not by its reference count in the compiling process, and
# that depends on whether the host Python loaded its own stdlib from bytecode caches or from source.
# A step that marshals code (60, 70) first removes any cache an outside run of the host Python left,
# so the same inputs always give the same bytes.
host_from_source() {
  find "$T/python/lib" -name __pycache__ -type d -prune -exec rm -rf {} +
}

# Fail the step with one line naming what is missing.
die() {
  echo "ERROR: $*" >&2
  exit 1
}

# The pinned file's path, its SHA-256 verified again here, so a step run on its own never uses
# bytes that changed after scripts/00_download.sh checked them.
pinned() {
  [ -s "$D/$1" ] || die "downloads/$1 is missing: run scripts/00_download.sh"
  grep "  $1\$" "$D/SHA256SUMS" > "$B/.pin-check" || die "$1 is not pinned in downloads/SHA256SUMS"
  (cd "$D" && shasum -a 256 -c "$B/.pin-check" > /dev/null 2>&1) || die "downloads/$1 does not match its pin"
  rm -f "$B/.pin-check"
  printf '%s\n' "$D/$1"
}
