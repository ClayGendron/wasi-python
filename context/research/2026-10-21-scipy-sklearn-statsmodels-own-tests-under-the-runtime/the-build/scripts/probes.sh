#!/bin/sh
# Probe scipy's time-limited mpmath tests alone, at the default clock or $CLOCK, three at once.
cd /Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06 || exit 1
P=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/probe.py
run() {
  uv run python "$P" scipy "${CAP:-600}" "scipy/special/tests/test_mpmath.py::TestSystematic::$1" 2>&1 \
    | grep -E 'passed|failed|^fuel' > "build/095/logs/probe-$1-${CLOCK:-default}.log"
}
for t in "$@"; do run "$t" & done
wait
for t in "$@"; do echo "$t: $(cat "build/095/logs/probe-$t-${CLOCK:-default}.log" | tr '\n' ' ')"; done
