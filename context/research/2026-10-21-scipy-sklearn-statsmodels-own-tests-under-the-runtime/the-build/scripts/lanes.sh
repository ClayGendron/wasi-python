#!/bin/sh
# Run a pass's three lanes of release groups side by side, with the poller, each lane serial,
# waiting while the lane's lock exists before each lane starts. Usage: lanes.sh <pass>
cd /Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06 || exit 1
P=$1
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242
rm -f build/095/poll-stop
python3 "$S/scratchpad/poller.py" /private/var/folders/_c/n40__q_16zs0cbn45nb3c_nw0000gn/T/judge-wasi_python-db9c1a34d5d6 "build/095/poll-$P.tsv" --until-file build/095/poll-stop &
pids=""
for i in 1 2 3; do
  [ -s "build/095/$P-lane$i.txt" ] || continue
  (
    while [ -e /Users/claygendron/Git/Repos/wasi_python/build/lane.lock ]; do sleep 30; done
    PYTHONPATH="$S/plug" FUEL095_OUT="build/095/fuel/$P" uv run pytest -p no:cacheprovider -p fuel095 \
      --tier release --progress-latest "build/095/records/$P-lane$i.json" "@build/095/$P-lane$i.txt" \
      > "build/095/logs/$P-lane$i.log" 2>&1
  ) &
  pids="$pids $!"
done
for p in $pids; do wait "$p"; done
touch build/095/poll-stop
tail -n 1 build/095/logs/$P-lane*.log
