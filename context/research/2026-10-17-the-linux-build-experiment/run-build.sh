#!/bin/sh
# Inside the container: clone the scratch clone (/src, read-only) to /work/wasi_python, bring its
# downloads, record the host tools, and run the whole recipe from an empty build/.
set -eu
R=/work/wasi_python
rm -rf "$R"
git clone -q /src "$R"
for f in /src/downloads/*; do
  [ "$(basename "$f")" = SHA256SUMS ] || cp "$f" "$R/downloads/"
done
cd "$R"
{
  echo "uname: $(uname -srm)"
  grep PRETTY_NAME /etc/os-release
  echo "sh: $(readlink -f /bin/sh)"
  echo "uv: $(uv --version)"
  echo "gcc: $(gcc --version | head -n 1)"
  echo "make: $(make --version | head -n 1)"
  echo "git: $(git --version)"
  echo "shasum: $(shasum --version)"
  echo "tar: $(tar --version | head -n 1)"
  echo "xz: $(xz --version | head -n 1)"
  echo "curl: $(curl --version | head -n 1)"
  echo "locale: LANG=${LANG:-unset} LC_ALL=${LC_ALL:-unset}"
  dpkg-query -W -f '${Package} ${Version}\n' gcc libc6-dev make curl xz-utils git perl
} > /out/host-tools.txt
start=$(date +%s)
sh scripts/build.sh > /out/build-output.txt 2>&1 || true
echo "wall: $(( $(date +%s) - start ))s" >> /out/build-output.txt
cat /out/build-output.txt
sha256sum build/artifacts/* > /out/artifacts.sha256 2>/dev/null || true
