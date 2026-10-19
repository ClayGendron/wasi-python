#!/bin/sh
set -x
mkdir -p /tmp/m && cd /m && tar -cf - . | tar -xf - -C /tmp/m && cd /tmp/m
export UV_PROJECT_ENVIRONMENT=/tmp/venv UV_LINK_MODE=copy
uv sync -q
uv run python -c "import platform; print(platform.machine(), platform.libc_ver())"
uv run pytest -p no:cacheprovider -n 3 -q tests/checks/test_v1_3_upstream_suites.py -k "c-stack" > /out/main-traps.log 2>&1
tail -5 /out/main-traps.log
uv run python - <<'PY' > /out/main-traps-facts.txt
import json
d = json.load(open("build/progress/latest.json"))
for node, c in sorted(d["checks"].items()):
    if "test_upstream_trap" in node:
        print(node.split("[")[1].rstrip("]"), c.get("outcome"), c.get("facts", {}).get("trap"), c.get("metrics", {}).get("fuel"))
PY
cat /out/main-traps-facts.txt
echo ALL-DONE
