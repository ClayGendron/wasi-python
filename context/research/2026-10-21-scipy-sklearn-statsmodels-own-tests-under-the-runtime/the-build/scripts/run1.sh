#!/bin/sh
# One serial lane of release groups with the poller and the measurement plugin. Usage: run1.sh <pass> <nodeid file>
W=/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/095b
cd "$W" || exit 1
P=$1
rm -f build/095/poll-stop
uv run python "$S/poller.py" /private/var/folders/_c/n40__q_16zs0cbn45nb3c_nw0000gn/T/judge-wasi_python-db9c1a34d5d6 "build/095/poll-$P.tsv" --until-file build/095/poll-stop &
while [ -e /Users/claygendron/Git/Repos/wasi_python/build/lane.lock ]; do sleep 30; done
PYTHONPATH="$S/plug" FUEL095_OUT="build/095/fuel/$P" uv run pytest -p no:cacheprovider -p fuel095 \
  --tier release --progress-latest "build/095/records/$P.json" "@$2" > "build/095/logs/$P.log" 2>&1
touch build/095/poll-stop
tail -n 1 "build/095/logs/$P.log"
