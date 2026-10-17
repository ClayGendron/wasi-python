#!/bin/sh
# The detector: link every object of the archive (whole-archive), leave libc undefined, count wasm-ld's
# "function signature mismatch" warnings (one per symbol whose callers and definition disagree).
# usage: link_whole.sh <archive> <log>
set -u
SDK=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos
$SDK/bin/wasm-ld --no-entry --allow-undefined --no-gc-sections --export-all \
  --whole-archive "$1" --no-whole-archive -o "$(dirname "$2")/../work/$(basename "${2%.log}").wasm" > "$2" 2>&1
echo "link exit=$?"
printf 'signature mismatch warnings: '; grep -c "function signature mismatch" "$2"
printf 'other warnings/errors: '; grep -v "^>>>" "$2" | grep -vc "function signature mismatch\|^$"
