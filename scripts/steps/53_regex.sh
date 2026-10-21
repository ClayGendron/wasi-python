#!/bin/sh
# Step 53: regex 2026.9.29's one C extension module, regex._regex, for wasm32-wasip1.
# Its two C files are compiled here as regex's setup.py compiles them: setup.py adds
# one macro, Py_GIL_DISABLED, and only on a free-threaded CPython, which the line's is not. The
# tree gets its one carried patch first (recipes/patches/regex-2026.9.29/, Decision 3: five
# callbacks gain the parameter CPython passes). The module becomes a static archive beside a .deps
# file, written by scripts/wasi-cc at its import path under build/regex-build/ for step 60, as
# numpy's and pandas' are. The package's Python files are staged under build/regex-install/ for
# step 70: the sdist keeps regex.egg-info/ beside the package, which the zip refuses at a tree's
# top. Needs steps 10 and 20.
set -eu
. "$(dirname "$0")/common.sh"

[ -f "$W/pyconfig.h" ] || die "no WASI pyconfig.h at $W: run step 20"
REGEX_TGZ=$(pinned regex-2026.9.29.tar.gz)
R="$B/regex-2026.9.29"
OBJ="$B/regex-build"
INST="$B/regex-install"
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
remove "$R" "$OBJ" "$INST"
mkdir -p "$OBJ/regex" "$INST"
tar -xzf "$REGEX_TGZ" -C "$B"
[ -d "$R" ] || die "the pinned tarball did not unpack to build/regex-2026.9.29"
patch_tree "$R"
REGEX_VERSION=$(sed -n 's/^Version: //p' "$R/PKG-INFO" | head -n 1)
[ "$REGEX_VERSION" = 2026.9.29 ] || die "regex's PKG-INFO says version $REGEX_VERSION"

# -DNDEBUG, as CPython's release build and regex's wheels compile, and the prefix map: no build
# path in the binary.
CFLAGS="-O2 -DNDEBUG -ffile-prefix-map=$HERE=/wasi-python-build -I$CP/Include -I$W"
for m in _regex _regex_unicode; do
  "$HERE/scripts/wasi-cc" $CFLAGS -c "$R/src/$m.c" -o "$OBJ/$m.o" > "$OBJ/$m.log" 2>&1 \
    || { tail -n 20 "$OBJ/$m.log"; die "regex's $m.c did not compile (build/regex-build/$m.log)"; }
  echo "$m.c: $(grep -c 'warning:' "$OBJ/$m.log" || :) warnings (build/regex-build/$m.log)"
done
"$HERE/scripts/wasi-cc" -shared -o "$OBJ/regex/_regex$SUFFIX" "$OBJ/_regex.o" "$OBJ/_regex_unicode.o"
[ -s "$OBJ/regex/_regex$SUFFIX" ] || die "step 53 made no regex/_regex$SUFFIX"

# The package; step 70's rules leave its tests/ folder out of the zip.
cp -R "$R/regex" "$INST/regex"
n=$(find "$INST/regex" -name '*.py' -not -path '*/tests/*' | wc -l | tr -d ' ')
echo "regex: 1 extension archive under build/regex-build; $n Python modules under build/regex-install"
