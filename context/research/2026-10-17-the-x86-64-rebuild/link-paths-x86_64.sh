#!/bin/sh
# Spec 040, acceptance criterion 3's link paths, on x86_64 Linux: after step 10, a C++ program
# linked through $SDK/bin/clang++ (the emulated driver, the native wasm-ld) takes libc++,
# libc++abi and the compiler-rt builtins from the arm64 SDK's replaced directories, and each is
# the neutral tarball's member. Mounts as decision1-x86_64.sh (/src, /cache, /out).
set -eu
R=/work/wasi_python
rm -rf /work
git clone -q /src "$R"
cd "$R"
for f in /cache/*; do
  [ -f "$f" ] && cp "$f" downloads/
done
git checkout -q downloads/SHA256SUMS
sh scripts/00_download.sh > /dev/null 2>&1
sh scripts/steps/10_tools.sh > /out/link-step10.txt 2>&1
SDK=$R/build/tools/wasi-sdk-33.0-x86_64-linux
CSDK=$R/build/tools/wasi-sdk-33.0-arm64-linux
mkdir -p /tmp/l && cd /tmp/l
printf '#include <string>\n#include <stdexcept>\nint main(int c, char **v) {\n  try { if (c > 5) throw std::runtime_error(v[0]); }\n  catch (const std::exception &e) { return (int)std::string(e.what()).size(); }\n  volatile long double x = c;\n  x = x * 1.5L;\n  return (int)x;\n}\n' > p.cpp
"$SDK/bin/clang++" --target=wasm32-wasip1 -O2 -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false \
  p.cpp -o p.wasm -lunwind -Wl,--Map=p.map
for name in libc++.a libc++abi.a libclang_rt.builtins.a; do
  path=$(grep -o "[^ ]*/$name(" p.map | sort -u | sed 's/($//')
  real=$(readlink -f "$path")
  case "$real" in "$CSDK"/*) where="under the arm64 SDK";; *) where="NOT under the arm64 SDK";; esac
  echo "$name: $real ($where) $(sha256sum "$real" | cut -c1-16)"
done | tee /out/link-paths.txt
for m in wasi-sysroot-33.0+m.tar.gz:lib/wasm32-wasip1/eh/libc++.a wasi-sysroot-33.0+m.tar.gz:lib/wasm32-wasip1/eh/libc++abi.a libclang_rt-33.0+m.tar.gz:wasm32-unknown-wasip1/libclang_rt.builtins.a; do
  t=${m%%:*} member=${m#*:}
  mkdir -p /tmp/n && tar -xzf "$R/downloads/$t" -C /tmp/n --strip-components=1 "$(tar -tzf "$R/downloads/$t" | grep "/$member\$")"
  echo "neutral $member: $(sha256sum "/tmp/n/$member" | cut -c1-16)"
done | tee -a /out/link-paths.txt
