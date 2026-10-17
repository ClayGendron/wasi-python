#!/bin/sh
# Capture how two tools this build already runs (the pinned ninja, and uv) print the same work to a
# terminal and to a pipe. A pseudo-terminal comes from pty_run.py (stdlib pty), which makes escapes visible.
# Usage: capture_tty_vs_plain.sh <repo> <scratch dir> <out dir>
set -eu
REPO=$1; S=$2; OUT=$3
HERE=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
NINJA="$REPO/build/tools/pylib/bin/ninja"
mkdir -p "$S/ninja" "$OUT"
cat > "$S/ninja/build.ninja" <<'N'
rule slow
  command = sleep 1 && touch $out
  description = SLOW $out
build a: slow
build b: slow
build c: slow
build d: slow
N
run_ninja() { (cd "$S/ninja" && rm -f a b c d .ninja_log .ninja_deps && "$@"); }
run_ninja "$NINJA" -j1 > "$OUT/ninja.pipe.txt" 2>&1
run_ninja uv run --no-project python -I "$HERE/pty_run.py" "$OUT/ninja.tty.txt" "$NINJA" -j1
run_ninja env TERM=dumb uv run --no-project python -I "$HERE/pty_run.py" "$OUT/ninja.tty-term-dumb.txt" "$NINJA" -j1
# The second run reads .ninja_log: ETA from the previous run's timings (%W, %P).
(cd "$S/ninja" && rm -f a b c d && NINJA_STATUS='[%f/%t %p eta %W pred %P] ' "$NINJA" -j1) > "$OUT/ninja.status-eta.txt" 2>&1

# uv: install one pinned wheel, offline, into a throwaway venv.
WHEEL="$REPO/downloads/six-1.17.0-py2.py3-none-any.whl"
export UV_CACHE_DIR="$S/uv-cache"
uv venv -q "$S/venv"
uv pip install -p "$S/venv" --offline --no-cache "$WHEEL" > "$OUT/uv.pipe.txt" 2>&1
uv pip uninstall -q -p "$S/venv" six
uv run --no-project python -I "$HERE/pty_run.py" "$OUT/uv.tty.txt" uv pip install -p "$S/venv" --offline --no-cache "$WHEEL"
uv pip uninstall -q -p "$S/venv" six
NO_COLOR=1 uv run --no-project python -I "$HERE/pty_run.py" "$OUT/uv.tty-no-color.txt" uv pip install -p "$S/venv" --offline --no-cache "$WHEEL"
