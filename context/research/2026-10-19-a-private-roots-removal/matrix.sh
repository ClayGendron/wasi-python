#!/bin/sh
# usage: matrix.sh MODE SOFT DEPTH...  ; each depth in a fresh temporary folder, then a second
# process (same soft limit) makes one plain call, whose sweep retries what is left; then every
# leftover is deleted by name.
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/084
export WASI_PYTHON_ARTIFACTS=$S/set
mode=$1; soft=$2; shift 2
cd /Users/claygendron/Git/Repos/wasi_python-084 || exit 1
for d in "$@"; do
  t=$S/temp/m-$mode-$soft-$d
  mkdir -p "$t"
  uv run python $S/probes/p_deep_root.py "$soft" "$d" "$t" "$mode" > "$t.json"
  uv run python $S/probes/p_sweep_once.py "$soft" "$t" > "$t.sweep.json"
  python3 - "$t.json" "$t.sweep.json" <<'EOF'
import json, sys
r = json.load(open(sys.argv[1])); w = json.load(open(sys.argv[2]))
roots = [n for n in r["left"] if n.startswith("wasi-python-root-") and not n.endswith(".lock")]
print(f"{r['python']} {r['mode']:7} soft={r['soft']:5} depth={r['depth']:5} exit={r['exit_code']} "
      f"raised={r['raised']} fds_at_remove={r['open_fds_at_remove']} errors={r['rmtree_errors']} "
      f"roots_left={len(roots)} levels={list(r['levels_left'].values())} "
      f"| next process: swept={w['swept']} roots_left={w['roots_left']}")
EOF
  for n in $(ls "$t"); do echo "  deleting $t/$n"; rm -rf "$t/$n"; done
  rmdir "$t"
done
