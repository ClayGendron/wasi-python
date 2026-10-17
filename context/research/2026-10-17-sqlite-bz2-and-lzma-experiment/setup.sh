#!/bin/sh
# Experiment: _bz2, _lzma and _sqlite3 as builtins on the 3.15 line, in a scratch clone (nothing in
# the real repository changes).
#
#   setup.sh <real repository> <empty scratch directory>
#
# Then, in <scratch>/repo: sh scripts/build.sh (every step, 35_stdlib_libs included).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd -P)
REAL=$(cd "$1" && pwd -P)
SCRATCH=$(cd "$2" && pwd -P)
R="$SCRATCH/repo"
[ ! -e "$R" ] || { echo "ERROR: $R exists"; exit 1; }
git clone -q "$REAL" "$R"
mkdir -p "$R/downloads"
for f in "$REAL"/downloads/*; do
  [ "$(basename "$f")" = SHA256SUMS ] || cp -c "$f" "$R/downloads/"
done
# The three new sources, each fetched into its own empty directory and checked against the hash this
# experiment recorded (cross-checked: SQLite's published SHA3-256, GitHub's asset digest for xz, and
# the release signatures of bzip2 and xz).
fetch() { # url name sha256
  d="$SCRATCH/dl-$2"
  mkdir "$d"
  curl -fsSL -o "$d/$2" "$1"
  echo "$3  $d/$2" | shasum -a 256 -c - > /dev/null
  cp "$d/$2" "$R/downloads/$2"
  echo "$3  $2" >> "$R/downloads/SHA256SUMS"
}
fetch https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz bzip2-1.0.8.tar.gz \
  ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269
fetch https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz xz-5.8.4.tar.gz \
  0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9
fetch https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz sqlite-autoconf-3540100.tar.gz \
  926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e
cp "$HERE/35_stdlib_libs.sh" "$R/scripts/steps/"
# The edits are plain text substitutions; any Python 3.11+ runs them (-I: nothing from the clone).
uv run --no-project python -I "$HERE/edit.py" "$R"
git -C "$R" add -A scripts downloads
git -C "$R" -c user.name=exp -c user.email=exp@localhost commit -q -m "experiment: _bz2, _lzma, _sqlite3 as builtins"
echo "clone ready at $R"
