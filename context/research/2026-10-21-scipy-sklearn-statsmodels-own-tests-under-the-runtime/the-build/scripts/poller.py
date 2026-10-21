"""Tail every guest stream under the judge's guest folder and log each line with the wall time,
so a folder-wide session's time per file can be read afterwards (a packing estimate only; the
groups' fuel is always the judge's own measurement).

    python3 poller.py <guest tmp> <log> [--until-file <path>]
"""

import sys
import time
from pathlib import Path

root, log = Path(sys.argv[1]), Path(sys.argv[2])
stop = Path(sys.argv[4]) if len(sys.argv) > 4 else None
pos: dict[Path, int] = {}
with log.open("a") as out:
    while stop is None or not stop.exists():
        for f in root.glob("guest-*/run-*/root/tmp/upstream/outcomes.txt"):
            try:
                with f.open("rb") as fh:
                    fh.seek(pos.get(f, 0))
                    data = fh.read()
            except OSError:
                continue
            if not data:
                continue
            cut = data.rfind(b"\n") + 1
            pos[f] = pos.get(f, 0) + cut
            now = time.time()
            run = f.parents[3].name + "/" + f.parents[4].name
            for line in data[:cut].decode(errors="replace").splitlines():
                if line[:2] in ("S ", "C ", "E ", "K ", "P "):
                    out.write(f"{now:.2f}\t{run}\t{line[:300]}\n")
            out.flush()
        time.sleep(0.5)
