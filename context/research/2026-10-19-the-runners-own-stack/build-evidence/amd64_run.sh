#!/bin/sh
# Spec 078, criterion 19 (and the x86-64 edges): in linux/amd64, a copy of the worktree.
set -x
mkdir -p /tmp/w && cd /w && tar --exclude=./.venv --exclude=./build/cwasm-cache --exclude=./build/harness --exclude=./build/amd64 --exclude=./build/progress -cf - . | tar -xf - -C /tmp/w
cd /tmp/w
export UV_PROJECT_ENVIRONMENT=/tmp/venv UV_LINK_MODE=copy
uv sync -q
uv run python -c "import platform, sys; print(platform.machine(), platform.libc_ver(), sys.version)"
uv run pytest -p no:cacheprovider -n 3 -q tests/checks/test_v1_3_upstream_suites.py -k "cpython-a or cpython-b or cpython-c" > /out/cpython-groups.log 2>&1
tail -15 /out/cpython-groups.log
uv run pytest -p no:cacheprovider -n 3 -q tests/checks/test_v1_2_hostile_guest.py -k "deep_data or small_calling or ctrl_c or raising or tears_down or guest_thread or callers" > /out/hostile.log 2>&1
tail -15 /out/hostile.log
uv run python build/edges/edges078.py relaxng xslt-apply-copy > /out/edges.jsonl 2>&1
cat /out/edges.jsonl
echo ALL-DONE
