"""Run a job file (tab-separated: family, label, fuel, pytest args...) one guest at a time,
skipping labels already done, and stopping the running guest while the lane's lock exists.

    uv run python build/095b/survey/runjobs.py <jobs.tsv>
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

W = Path.cwd()
SURVEY = W / "build/095b/survey"
LOCK = Path("/Users/claygendron/Git/Repos/wasi_python/build/lane.lock")


def wait_lock() -> None:
    while LOCK.exists():
        time.sleep(20)


def main() -> None:
    jobs = Path(sys.argv[1]).read_text().splitlines()
    for line in jobs:
        if not line.strip() or line.startswith("#"):
            continue
        fam, lab, fuel, *args = line.split("\t")
        env = dict(os.environ)
        if lab.endswith("@clock1ms"):
            env["CLOCK_STEP_NS"] = "1000000"
        if (SURVEY / "out" / lab / "result.json").exists():
            continue
        wait_lock()
        log = W / "build/095b/logs" / f"{lab}.log"
        with log.open("w") as fh:
            p = subprocess.Popen(
                ["uv", "run", "python", "build/095b/survey/survey.py", fam, lab, fuel,
                 "--continue-on-collection-errors", "-pprobe095mods", *args],
                stdout=fh, stderr=subprocess.STDOUT, start_new_session=True, env=env,
            )
            # Stopping another process is not permitted here, so a guest the lane's lock finds
            # running is ended and its job run again once the lock is gone.
            while p.poll() is None:
                time.sleep(5)
                if LOCK.exists():
                    p.send_signal(signal.SIGTERM)
                    p.wait()
                    print(lab, "ended for the lane's lock; again later", flush=True)
                    jobs.append(line)
                    break
        res = SURVEY / "out" / lab / "result.json"
        if res.exists():
            r = json.loads(res.read_text())
            print(lab, r["fuel"], r["exit"], r["trapped"], json.dumps(r["counts"]), flush=True)
        else:
            print(lab, "NO RESULT", flush=True)


if __name__ == "__main__":
    main()
