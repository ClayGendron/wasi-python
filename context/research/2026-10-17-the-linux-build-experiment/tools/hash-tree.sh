#!/bin/sh
# Hash every build output that can reach the artifacts, relative to build/ (run with cwd = build/).
find Python-3.15.0/cross-build/wasm32-wasip1 numpy-build pandas-build zlib-wasi link out numpy-install pandas-install \
  -type f \( -name '*.o' -o -name '*.a' -o -name '*.so' -o -name '*.h' -o -name '*.c' -o -name '*.wasm' -o -name '*.zip' -o -name '*.py' -o -name '*.deps' -o -name '*.txt' -o -name '*.map' \) 2>/dev/null \
  | LC_ALL=C sort | while read -r f; do printf '%s  %s\n' "$(shasum -a 256 "$f" | cut -c1-64)" "$f"; done
