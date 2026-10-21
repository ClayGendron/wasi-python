#!/bin/sh
# Rebuild pass 2's plan from pass 1's groups and estimates.
set -e
cd /Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad
cp "$S/groups-pass1.json" "$S/groups.json"
cp "$S/splits-pass1.json" "$S/splits.json"
rm -f "$S/filefuel.json"
uv run python "$S/split_plan.py" build/095/poll-pass1.tsv build/095/fuel/pass1 > /dev/null
uv run python "$S/pass2.py" "$@"
uv run python - "$S" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1] + "/splits.json"))
for f, ss in s.items():
    for x in ss:
        print(f, x["file"], len(x["groups"]), [k[:60] for k in x["keywords"]][:8])
EOF
