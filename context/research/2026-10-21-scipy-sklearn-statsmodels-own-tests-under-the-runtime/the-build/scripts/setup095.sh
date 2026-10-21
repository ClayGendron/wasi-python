#!/bin/sh
# Clone the main tree's frozen set and the pinned tarballs into this worktree.
set -e
M=/Users/claygendron/Git/Repos/wasi_python
W=$M/.claude/worktrees/agent-aab0b516adb4e5c06
mkdir -p "$W/build"
if [ ! -d "$W/build/artifacts" ]; then cp -c -Rp "$M/build/artifacts" "$W/build/artifacts"; fi
shasum -a 256 "$W/build/artifacts/SHA256SUMS" | cut -c1-8
(cd "$W/build/artifacts" && shasum -a 256 -c SHA256SUMS | tail -6)
for f in contourpy-1.4.0.tar.gz kiwisolver-1.5.1.tar.gz lxml-6.1.3.tar.gz matplotlib-3.11.2.tar.gz numpy-2.5.2.tar.gz pandas-3.0.6.tar.gz pillow-13.0.0.tar.gz Python-3.15.0.tar.xz regex-2026.9.29.tar.gz scikit_learn-1.9.1.tar.gz scipy-1.18.1.tar.gz statsmodels-0.15.0.tar.gz; do
  [ -f "$W/downloads/$f" ] || cp -c "$M/downloads/$f" "$W/downloads/$f"
done
ls "$W/downloads"
