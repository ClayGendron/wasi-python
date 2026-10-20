"""Write 099's-tip runs as .out files (a header line, then stdout) and say whether the two binaries agree."""

import json
import sys

work, dst = sys.argv[1], sys.argv[2]
for p in ("singular300", "nan_probe", "xerbla_probe"):
    outs = {}
    for which in ("plain", "snapshot"):
        d = json.load(open(f"{work}/out/099-{p}-{which}.json"))
        outs[which] = d["stdout"]
        head = (f"# 099's built tip b0e1593, SHA256SUMS 7519b047, {which} binary, wasi-python run --stdin {p}.py: "
                f"exit {d['exit_code']}, trapped {d['trapped']}, stderr {d['stderr']!r}\n")
        open(f"{dst}/{p.replace('_probe', '')}-099-{which}.out", "w").write(head + d["stdout"])
    print(p, "plain == snapshot:", outs["plain"] == outs["snapshot"])
    print(outs["plain"])
