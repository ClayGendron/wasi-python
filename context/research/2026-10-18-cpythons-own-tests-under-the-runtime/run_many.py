"""Run many regrtest modules, one guest session each, one guest at a time.

uv run python run_many.py <modules file> <fuel cap> <per-module wall limit s> [regrtest options...]

The parent starts a child process per batch of modules (the child deserializes the compiled
snapshot once and runs its modules in turn, each in a fresh instance). The child writes the module
it is on to a progress file before each session. When one module outlives the wall limit, the parent
kills the batch, records the module that was running as `hang`, and starts the next batch after it. A
module already recorded under runs/ is skipped, so the run resumes.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_one  # noqa: E402

RUNS = run_one.RUNS
PROGRESS = run_one.WORK / "progress.txt"
BATCH = 40


def child(fuel: int, opts: list[str], mods: list[str]) -> None:
    for m in mods:
        PROGRESS.write_text(f"{m} {time.time()}\n")
        sys.argv = ["run_one", m, str(fuel), "--", *opts, m]
        run_one.main()
        sys.stdout.flush()


def main() -> None:
    if sys.argv[1] == "--child":
        fuel = int(float(sys.argv[2]))
        sep = sys.argv.index("--")
        child(fuel, sys.argv[3:sep], sys.argv[sep + 1 :])
        return
    mods = [m.strip() for m in Path(sys.argv[1]).read_text().split() if m.strip()]
    fuel, limit, opts = sys.argv[2], float(sys.argv[3]), sys.argv[4:]
    RUNS.mkdir(parents=True, exist_ok=True)
    todo = [m for m in mods if not (RUNS / f"{m}.json").exists()]
    print(f"{len(todo)} of {len(mods)} to run", flush=True)
    while todo:
        batch = todo[:BATCH]
        cmd = [sys.executable, __file__, "--child", fuel, *opts, "--", *batch]
        PROGRESS.write_text(f"{batch[0]} {time.time()}\n")
        p = subprocess.Popen(cmd)
        while p.poll() is None:
            time.sleep(1)
            name, started = PROGRESS.read_text().split()
            if time.time() - float(started) > limit:
                p.kill()
                p.wait()
                rec = {"label": name, "hang": True, "wall_s": round(time.time() - float(started), 1)}
                (RUNS / f"{name}.json").write_text(json.dumps(rec))
                print(f"{name}: HANG (killed after {limit}s)", flush=True)
                break
        name = PROGRESS.read_text().split()[0]
        if p.returncode != 0 and not (RUNS / f"{name}.json").exists():
            rec = {"label": name, "host_crash": p.returncode}
            (RUNS / f"{name}.json").write_text(json.dumps(rec))
            print(f"{name}: host process ended {p.returncode}", flush=True)
        todo = [m for m in todo if not (RUNS / f"{m}.json").exists()]


if __name__ == "__main__":
    main()
