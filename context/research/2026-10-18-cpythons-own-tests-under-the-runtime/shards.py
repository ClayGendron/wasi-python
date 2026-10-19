"""Split the suite into N shards from the per-module pass, and run each shard as one session.

uv run python shards.py plan <per-module.tsv> <N> <out dir>     write shard-<k>.txt files
uv run python shards.py run <shard file> <label>                 one guest session, every module

Balancing: greedy, largest first, on each module's session cost less the fixed start of a session
(about 1.14 G fuel), by fuel (a test counts operations; the wall clock is a benchmark fact).
Left out: the modules that trapped the guest at wasmtime's default stack (they are trap entries).
"""

import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

START_G = 1.14
TRAPPED = {"test_doctest", "test_exceptions", "test_functools", "test_syntax", "test_traceback"}
OPTS = ["-u", "all,-cpu,-gui,-largefile"]


def plan(tsv: str, n: int, out: str) -> None:
    rows = [r for r in csv.DictReader(open(tsv), delimiter="\t") if r["module"] not in TRAPPED]
    rows.sort(key=lambda r: -float(r["fuel_G"]))
    shards = [[0.0, []] for _ in range(n)]
    for r in rows:
        s = min(shards, key=lambda s: s[0])
        s[0] += max(float(r["fuel_G"]) - START_G, 0.0)
        s[1].append(r["module"])
    Path(out).mkdir(parents=True, exist_ok=True)
    for k, (g, mods) in enumerate(shards):
        Path(out, f"shard-{k}.txt").write_text("\n".join(sorted(mods)) + "\n")
        print(f"shard-{k}: {len(mods)} modules, {g:.1f} G expected beyond one start")


def run(shard: str, label: str) -> None:
    import run_one

    mods = Path(shard).read_text().split()
    sys.argv = ["run_one", label, os.environ.get("CPY_FUEL", "1.5e12"), "--", *OPTS, *mods]
    run_one.main()


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        run(sys.argv[2], sys.argv[3])
