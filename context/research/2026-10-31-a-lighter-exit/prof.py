"""Fuel-sampled profile: run CODE with fuel caps start..end step, record the wasm stack at each trap.
usage: prof.py <snapshot|plain> <start> <end> <step> <out.tsv> <code>"""
import sys, re
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
def one(args):
    snap, fuel, code = args
    from drv import go, LAST
    r = go(code, snap=snap, fuel=fuel)
    if r.trapped != "out of fuel":
        return fuel, "END:" + str(r.exit_code)
    names = LAST.get("frames", [])
    return fuel, ";".join(reversed(names))
if __name__ == "__main__":
    b, s, e, st, out, code = sys.argv[1:7]
    snap = b == "snapshot"
    jobs = [(snap, f, code) for f in range(int(s), int(e), int(st))]
    with ProcessPoolExecutor(8) as ex, open(out, "w") as fh:
        for fuel, stack in ex.map(one, jobs):
            fh.write(f"{fuel}\t{stack}\n")
