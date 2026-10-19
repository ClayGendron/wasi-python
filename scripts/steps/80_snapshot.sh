#!/bin/sh
# Step 80: the Wizer snapshot (build/out/python-snapshot.wasm): the reactor with the interpreter
# initialized and the stdlib's bootstrap imported, no package (PREIMPORT, spec 069). One preopen,
# at /, holding the stdlib zip where the guest finds it: wasi-libc's preopen table is snapshotted,
# and so are zipimport's offsets, so the snapshot runs only beside this exact zip (spec 003,
# Decisions 1 and 9).
# The snapshot is made by the pinned wasmtime's own `wasmtime wizer`, which reads the
# exception-handling proposal (spec 005, Decision 5): the door import gets a stub that traps if
# called (the snapshot never calls it), WASI is on, stdio is not inherited, and no compile cache is
# written to the builder's home.
set -eu
. "$(dirname "$0")/common.sh"

ROOT="$B/wizer-root"
ZIP="usr/local/lib/python$PYTHON_TAG.zip"
remove "$ROOT" "$OUT/python-snapshot.wasm"
mkdir -p "$ROOT/usr/local/lib"
cp "$OUT/python-stdlib.zip" "$ROOT/$ZIP"
FLAGS="-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func wizer.initialize"
# The command as run, with the build's paths named generically, for MANIFEST's x-wizer line.
echo "wasmtime wizer $FLAGS --dir <root with $ZIP>::/ -o python-snapshot.wasm python.wasm" \
  > "$OUT/wizer-command.txt"
"$T/$WASMTIME_DIR/wasmtime" wizer $FLAGS --dir "$ROOT::/" -o "$OUT/python-snapshot.wasm" "$OUT/python.wasm"
echo "snapshot: $(wc -c < "$OUT/python-snapshot.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$OUT/python-snapshot.wasm" | cut -c1-16)"
