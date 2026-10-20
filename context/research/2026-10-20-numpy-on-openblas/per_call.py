"""Fuel per call from phase2-probes.txt: (operation - baseline) / calls, plain binary, on 099's
built set (the base) and spec 100's. Usage: per_call.py <phase2-probes.txt>"""

import re
import sys

rows = {}
for line in open(sys.argv[1]):
    m = re.match(r"(small|ops)-(set\d+)-(\w+) plain exit 0 trapped None fuel (\d+)", line)
    if m:
        rows[(m[1], m[2], m[3])] = int(m[4])
print("# from phase2-probes.txt: (op - none) / calls, plain binary")
for kind, ops, reps in (
    ("small", ("np_matmul3", "np_inv3"), 2000),
    ("ops", ("np_inv", "np_svd", "np_eigh", "np_matmul"), 5),
):
    for op in ops:
        per = {s: (rows[(kind, s, op)] - rows[(kind, s, "none")]) / reps for s in ("set099", "set100")}
        print(
            f"{op}: base (099) {per['set099']:,.0f}, built (100) {per['set100']:,.0f} fuel per call,"
            f" ratio {per['set100'] / per['set099']:.3f}"
        )
