"""A measurement plugin for spec 095's builder (scratch, never in the repository): after each
check, append its metrics and facts to $FUEL095_OUT/<pid>.jsonl, whatever its verdict, since the
judge records metrics only for a passing check.

    PYTHONPATH=<this folder> FUEL095_OUT=<dir> uv run pytest -p fuel095 ...
"""

import json
import os
from pathlib import Path


def pytest_runtest_teardown(item):
    from harness import plugin as hp

    metrics = item.stash.get(hp.METRICS, {})
    facts = item.stash.get(hp.FACTS, {})
    if not metrics and not facts:
        return
    out = Path(os.environ["FUEL095_OUT"])
    out.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"node": item.nodeid, "metrics": metrics, "facts": facts}, default=str)
    with (out / f"{os.getpid()}.jsonl").open("a") as f:
        f.write(line + "\n")
