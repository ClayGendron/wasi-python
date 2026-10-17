#!/bin/sh
# Experiment: the pinned recipe on a second host (aarch64 Linux in a container), in a scratch clone
# of the repository (nothing in the real repo changes).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd -P)
REAL=<repo>
R="$HERE/repo"
rm -rf "$R"
git clone -q "$REAL" "$R"
mkdir -p "$R/downloads"
# The real repo's pinned build inputs (APFS clones, no copy), then the Linux ones fetch.sh verified.
grep -v '^#' "$REAL/downloads/SHA256SUMS" | while read -r sha name; do
  [ -f "$REAL/downloads/$name" ] && cp -c "$REAL/downloads/$name" "$R/downloads/"
done
cd "$HERE/dl-linux" && shasum -a 256 -c SHA256SUMS > /dev/null
grep -v '  uv-' SHA256SUMS | while read -r sha name; do
  cp -c "$name" "$R/downloads/"
  echo "$sha  $name" >> "$R/downloads/SHA256SUMS"
done
# The host-neutral wasm runtime (edit 8), verified against its published digests.
cd "$HERE/dl-neutral"
printf '063bc1b56582b9923e08ac9b89e58789618d851763f01530b3ff20b9e5df0ca3  wasi-sysroot-33.0+m.tar.gz\nd3302760b78c8c50f2875650833b3584479131eab9ec2e6c72f7dfec26288be3  libclang_rt-33.0+m.tar.gz\n' > SHA256SUMS
shasum -a 256 -c SHA256SUMS > /dev/null
cp -c wasi-sysroot-33.0+m.tar.gz libclang_rt-33.0+m.tar.gz "$R/downloads/"
cat SHA256SUMS >> "$R/downloads/SHA256SUMS"
cd "$R"
uv run --no-project python -I "$HERE/edit.py" "$R"
git -C "$R" add -A && git -C "$R" -c user.name=exp -c user.email=exp@localhost commit -q -m "experiment: a host-aware recipe (macOS arm64, Linux aarch64, Linux x86_64)"
git -C "$R" diff HEAD~1 --stat
echo "clone ready at $R"
