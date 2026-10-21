"""Run survey jobs one at a time, in order, from a jobs file (one job a line: family label fuel
args...; '#' comments). A job whose result.json exists is skipped. While the main tree's
build/lane.lock exists the running job is stopped (SIGSTOP) and continued after (SIGCONT). From
the worktree:

    uv run python <scripts>/queue.py <jobs file>
"""

import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

W = Path.cwd()
LOCK = Path("/Users/claygendron/Git/Repos/wasi_python/build/lane.lock")
SURVEY = W / "build/067/survey"
HERE = Path(__file__).parent
LOG = SURVEY / "queue.log"


def log(msg: str) -> None:
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def watch(p: subprocess.Popen) -> None:
    stopped = False
    while p.poll() is None:
        locked = LOCK.exists()
        if locked and not stopped:
            os.killpg(p.pid, signal.SIGSTOP)
            stopped = True
            log(f"lane.lock: stopped {p.pid}")
        elif not locked and stopped:
            os.killpg(p.pid, signal.SIGCONT)
            stopped = False
            log(f"lane.lock gone: continued {p.pid}")
        time.sleep(5)


def main() -> None:
    jobs = []
    for line in Path(sys.argv[1]).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            jobs.append(shlex.split(line))
    for job in jobs:
        label = job[1]
        if (SURVEY / "out" / label / "result.json").exists():
            continue
        while LOCK.exists():
            time.sleep(10)
        log(f"start {label}")
        with open(SURVEY / "queue-out.log", "a") as out:
            p = subprocess.Popen(["uv", "run", "python", str(HERE / "survey.py"), *job],
                                 cwd=W, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            t = threading.Thread(target=watch, args=(p,), daemon=True)
            t.start()
            p.wait()
        log(f"end {label} exit {p.returncode}")


if __name__ == "__main__":
    main()
