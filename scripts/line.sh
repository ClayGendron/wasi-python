# Sourced with HERE set to the repository: scripts/line.conf checked against its grammar and loaded,
# then PYTHON_MM (3.15) and PYTHON_TAG (315) derived from PYTHON_VERSION (spec 005, Decision 2), and
# the running build host's own inputs set under their plain names (spec 012, Decision 1), the SDK
# whose clang compiles on it among them (spec 040, Decision 4).
LINE_CONF="$HERE/scripts/line.conf"
if grep -v -E '^(#.*|[A-Z][A-Z0-9_]*=[A-Za-z0-9._+-]+)$' "$LINE_CONF" > /dev/null; then
  echo "ERROR: scripts/line.conf has a line that is not NAME=value or a # comment" >&2
  exit 1
fi
. "$LINE_CONF"
# The running host's key, and its own inputs under the plain names (spec 012, Decision 1). A host
# with no key builds nothing.
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) HOST_KEY=MACOS_ARM64;;
  Linux-aarch64|Linux-arm64) HOST_KEY=LINUX_AARCH64;;
  Linux-x86_64) HOST_KEY=LINUX_X86_64;;
  *) echo "ERROR: no build host $(uname -s)-$(uname -m): the build hosts are MACOS_ARM64, LINUX_AARCH64 and LINUX_X86_64" >&2
     exit 1;;
esac
for name in WASI_SDK_DIR WASMTIME_DIR HOST_PYTHON_ARCHIVE CYTHON_WHEEL NINJA_WHEEL PKGCONF_WHEEL NUMPY_HOST_WHEEL COMPILER_SDK_DIR; do
  eval "value=\${${HOST_KEY}_$name:-}"
  [ -n "$value" ] || { echo "ERROR: scripts/line.conf has no ${HOST_KEY}_$name" >&2; exit 1; }
  eval "$name=\$value"
done
# The emulated compiler's packages, set only on a host that compiles with another host's SDK (spec
# 040, Decision 4); elsewhere they are empty.
for name in EMULATOR_DEB AARCH64_LIBC_DEB AARCH64_LIBSTDCXX_DEB AARCH64_LIBGCC_DEB AARCH64_LIBTINFO_DEB; do
  eval "$name=\${${HOST_KEY}_$name:-}"
done
PYTHON_MM=${PYTHON_VERSION%.*}
PYTHON_TAG=$(printf '%s' "$PYTHON_MM" | tr -d .)
