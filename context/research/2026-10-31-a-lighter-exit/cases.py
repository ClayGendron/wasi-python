"""Run named cases on both binaries. usage: cases.py <module with CASES> <out.tsv> [reps_plain]"""
import sys, importlib.util
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
from concurrent.futures import ProcessPoolExecutor
def one(args):
    name, code, snap = args
    from drv import go
    r = go(code, snap=snap)
    out = r.stdout.decode(errors="replace").strip().replace("\n", " | ")[:600]
    err = r.stderr.decode(errors="replace").strip().replace("\n", " | ")[-400:]
    return name, "snapshot" if snap else "plain", r.fuel_used, r.exit_code, r.trapped, out, err
if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("c", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    only = getattr(m, "BINARIES", ("snapshot", "plain"))
    jobs = []
    for n, c in m.CASES.items():
        if "snapshot" in only: jobs.append((n, c, True))
        if "plain" in only: jobs += [(n, c, False)] * reps
    with ProcessPoolExecutor(8) as ex, open(sys.argv[2], "w") as fh:
        for row in ex.map(one, jobs):
            line = "\t".join(str(x) for x in row)
            fh.write(line + "\n"); print(line, flush=True)
