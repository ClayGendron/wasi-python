"""One line per cap_probe.py run (out/cap-<which>-<MiB>.json), in the order the runs were made."""

import json
import sys

work = sys.argv[1]
runs = [("plain", m) for m in (1024, 256, 160, 128, 112, 96, 88, 80, 76, 72, 64)]
runs += [("snapshot", m) for m in (72, 68, 64)]
print("# main set SHA256SUMS f12cd25c, wasi-python run --memory-bytes <MiB << 20> --stdin cap_probe.py")
for which, mib in runs:
    d = json.load(open(f"{work}/out/cap-{which}-{mib}.json"))
    print(f"{mib} MiB {which}: exit {d['exit_code']}, trapped {d['trapped']} | "
          + " / ".join(d["stdout"].splitlines()) + " | stderr: " + repr(d["stderr"].strip()))
