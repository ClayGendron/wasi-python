"""The fuel noise test: run a job with the judge's driver, then run the Rust spike twice on the very
same root folder (same files, inodes and times), and compare fuel. If the Rust runs equal the
Python run exactly, the noise between fresh roots is the guest reading host file metadata, not a
difference between runners.

    COLLECTOR=drc uv run --frozen --project <repo> python same_root.py <rust-binary> <cwasm-dir> <tag>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import compare as c  # noqa: E402

TRIALS = 4
NAMES = ["numpy_random-plain", "numpy_csv-plain", "pandas_csv-plain", "pandas_tz-snapshot",
         "callbacks-snapshot", "compress-plain"]


def main() -> None:
    binary, cwasm_dir, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    collector = os.environ.get("COLLECTOR") or None
    work = c.SPIKE / "work" / f"same-root-{tag}-{int(time.time())}"
    work.mkdir(parents=True)
    rows = []
    for trial in range(TRIALS):
        batch_jobs, py = [], {}
        for n in NAMES:
            spec = c.JOBS[n]
            r = c.guest.run(c.BIN[spec["which"]], spec["argv"], workdir=work / f"t{trial}",
                            python_version=c.PY_VERSION, stdlib=c.STDLIB, files=spec.get("files"),
                            env=spec.get("env"), fuel=c.guest.DEFAULT_FUEL)
            py[n] = r
            base = r.root.parent
            for k in range(2):
                io = base / f"rs-io-{k}"
                io.mkdir()
                batch_jobs.append(dict(
                    id=f"{n}#{k}", wasm=str(c.BIN[spec["which"]]),
                    cwasm=str(cwasm_dir / f"{spec['which']}.cwasm"),
                    argv=[c.guest.ARGV0, *spec["argv"]],
                    env=sorted((spec.get("env") or {}).items()),
                    preopens=[[str(base / "lib"), "/usr/local/lib", False], [str(r.root), "/", True]],
                    fuel=c.guest.DEFAULT_FUEL, mode="judge",
                    stdout_path=str(io / "stdout"), stderr_path=str(io / "stderr")))
        # The Rust runs come after every Python run of the trial, on the same roots.
        batch = dict(consume_fuel=True, epoch_interruption=False, collector=collector,
                     jobs=batch_jobs)
        p = subprocess.run([str(binary)], input=json.dumps(batch).encode(), capture_output=True,
                           check=True)
        out = {o["id"]: o for o in map(json.loads, p.stdout.decode().splitlines())}
        for n in NAMES:
            f = [py[n].fuel, out[f"{n}#0"]["fuel_used"], out[f"{n}#1"]["fuel_used"]]
            rows.append(dict(trial=trial, job=n, py=f[0], rs_first=f[1], rs_second=f[2],
                             exact=len(set(f)) == 1))
            print(json.dumps(rows[-1]), flush=True)
    dest = Path(__file__).parent / "results" / f"same-root-{tag}.json"
    dest.write_text(json.dumps(rows, indent=1))
    print(f"exact {sum(r['exact'] for r in rows)}/{len(rows)}; wrote {dest}")


if __name__ == "__main__":
    main()
