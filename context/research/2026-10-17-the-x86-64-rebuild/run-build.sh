#!/bin/sh
# Inside the container: clone the change (/src, read-only) to /work/wasi_python, record the host
# tools, and run the whole recipe from an empty downloads/ and an empty build/. Outputs to /out.
set -eu
R=/work/wasi_python
rm -rf "$R"
git clone -q /src "$R"
cd "$R"
[ "$(ls downloads)" = "SHA256SUMS" ] || { echo "downloads/ is not empty" >&2; exit 1; }
[ ! -e build ] || { echo "build/ exists" >&2; exit 1; }
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
  echo "commit: $(git rev-parse HEAD)"
  dpkg-query -W -f '${Package} ${Version}\n' gcc libc6-dev make curl xz-utils git perl
} > /out/host-tools.txt
start=$(date +%s)
status=0
sh scripts/build.sh > /out/build-output.txt 2>&1 || status=$?
echo "exit: $status, wall: $(( $(date +%s) - start ))s" >> /out/build-output.txt
ls downloads > /out/downloads.txt
mkdir -p /out/logs && cp build/logs/* /out/logs/ 2>/dev/null || true
if [ -d build/artifacts ]; then
  rm -rf /out/artifacts && cp -R build/artifacts /out/artifacts
  sha256sum build/artifacts/python.wasm build/artifacts/python-snapshot.wasm build/artifacts/python-stdlib.zip build/artifacts/MANIFEST build/artifacts/SHA256SUMS > /out/artifacts.sha256
  wc -c build/artifacts/python.wasm build/artifacts/python-snapshot.wasm build/artifacts/python-stdlib.zip > /out/artifacts.size
fi
cat /out/build-output.txt
