#!/bin/sh
# Spec 040, Decision 1, on x86_64 Linux: inside this folder's container on linux/amd64, with
#   /src    a clone of the repository at the change (read-only)
#   /cache  the downloads, kept between runs (verified again by scripts/00_download.sh)
#   /in     decision1-host.sh's output folder, holding npy_math_complex.i (read-only)
#   /out    this run's output
#
# 1. The x86_64 Linux SDK's own clang, unpacked apart from the build, on the one file: the object,
#    the pass print and the scheduler sweep (decision1-sweep.sh).
# 2. Step 10 itself, which puts the arm64 Linux SDK's clang under the pinned qemu-aarch64 behind
#    $SDK/bin/clang, then the same sweep through $SDK/bin/clang.
set -eu
R=/work/wasi_python
rm -rf /work
git clone -q /src "$R"
cd "$R"
for f in /cache/*; do
  [ -f "$f" ] && cp "$f" downloads/
done
git checkout -q downloads/SHA256SUMS
sh scripts/00_download.sh > /out/download.txt 2>&1
for f in downloads/*; do
  [ "$(basename "$f")" = SHA256SUMS ] || cp "$f" /cache/
done
tail -n 1 /out/download.txt
HERE="$R/context/research/2026-10-17-the-x86-64-rebuild"
{
  echo "uname: $(uname -srm)"
  echo "commit: $(git rev-parse HEAD)"
  echo "file: $(wc -c < /in/npy_math_complex.i | tr -d ' ') bytes, $(sha256sum /in/npy_math_complex.i | cut -c1-16)"
} | tee /out/host.txt

mkdir -p /tmp/native
tar -xzf downloads/wasi-sdk-33.0-x86_64-linux.tar.gz -C /tmp/native
echo "== the x86_64 Linux SDK's clang, native"
sh "$HERE/decision1-sweep.sh" /tmp/native/wasi-sdk-33.0-x86_64-linux/bin/clang /in/npy_math_complex.i /out/linux-x86_64-native

echo "== step 10"
sh scripts/steps/10_tools.sh > /out/step10.txt 2>&1 || { tail -n 5 /out/step10.txt; exit 1; }
grep '^compiler gate' /out/step10.txt
echo "== \$SDK/bin/clang after step 10: the arm64 Linux SDK's clang under qemu-aarch64"
sh "$HERE/decision1-sweep.sh" build/tools/wasi-sdk-33.0-x86_64-linux/bin/clang /in/npy_math_complex.i /out/linux-x86_64-emulated
