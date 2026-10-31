"""Run every probe natively, on both binaries today, and under each candidate on the snapshot.
usage: matrix.py <out.tsv> [variant=path ...]  (a variant is a spike binary run with today's ending)"""
import sys, os, tempfile, subprocess, zipfile, gzip, sqlite3, shutil
HERE = os.path.dirname(os.path.abspath(sys.argv[0])); sys.path.insert(0, HERE)
from concurrent.futures import ProcessPoolExecutor
from probes import PROBES
from cands import wrapper, NAMES
HOSTPY = "/Users/claygendron/Git/Repos/wasi_python-wt/167-pdfplumber-plotly-xarray-and-zstd/build/tools/python/bin/python3"
def files(d):
    out = []
    for n in sorted(os.listdir(d)):
        if n in ("prog.py", "__pycache__", "tmp", "usr"):
            continue
        p = os.path.join(d, n)
        if n.startswith("tmp"):
            out.append("tmp*"); continue
        if n.endswith(".zip"):
            try: zipfile.ZipFile(p).read("m"); out.append(n + ":ok")
            except Exception: out.append(n + ":BAD")
        elif n.endswith(".gz"):
            try: out.append(n + (":ok" if len(gzip.open(p).read()) == 1000 else ":short"))
            except Exception: out.append(n + ":BAD")
        elif n == "t.db":
            try: out.append(n + ":rows=" + str(sqlite3.connect(p).execute("select count(*) from t").fetchone()[0]))
            except Exception as e: out.append(n + ":" + type(e).__name__)
        else:
            out.append(f"{n}:{os.path.getsize(p)}")
    return " ".join(out)
def errsum(err):
    keys = []
    for line in err.splitlines():
        if line.startswith("why:"):
            continue
        for k in ("Exception ignored", "ZeroDivisionError", "bye", "OSError", "err no newline", "ResourceWarning", "Error"):
            if k in line and k not in keys:
                keys.append(k)
    return ",".join(keys)
def one(job):
    name, how, variants = job
    VARIANTS.update(variants)
    mode, prog = PROBES[name]
    d = tempfile.mkdtemp(dir=os.path.join(HERE, "tmp"))
    if mode != "c":
        open(os.path.join(d, "prog.py"), "w").write(prog)
    if how == "native":
        cmd = [HOSTPY, "-I", "-c", prog] if mode == "c" else [HOSTPY, "-I", "prog.py"] if mode == "script" else [HOSTPY, "-E", "-s", "-m", "prog"]
        p = subprocess.run(cmd, cwd=d, capture_output=True)
        rc, out, err, fuel = p.returncode, p.stdout, p.stderr, ""
    else:
        from drv import go_with, A, variant
        binary, cand = how
        snap = binary != "plain"
        arts = A if binary in ("snapshot", "plain") else variant(VARIANTS[binary])
        r = go_with(arts, wrapper(cand, mode, prog), snap=snap, root=d, env={"LX_WHY": "1"} if cand == 6 else None)
        rc, out, err, fuel = r.exit_code if r.trapped is None else r.trapped, r.stdout, r.stderr, r.fuel_used
    res = (out.decode(errors="replace").strip().replace("\n", "/"), str(rc), errsum(err.decode(errors="replace")), files(d))
    shutil.rmtree(d, ignore_errors=True)
    label = how if how == "native" else f"{how[0]}:{NAMES[how[1]]}"
    if how != "native" and how[1] == 6 and "why:" in err.decode(errors="replace"): label += ""
    why = [l for l in err.decode(errors='replace').splitlines() if l.startswith('why:')]
    return name, label + (' [' + why[0][5:] + ']' if why else ''), fuel, res
VARIANTS = {}
if __name__ == "__main__":
    out = sys.argv[1]
    for v in sys.argv[2:]:
        k, p = v.split("="); VARIANTS[k] = p
    os.makedirs(os.path.join(HERE, "tmp"), exist_ok=True)
    CANDS = [int(c) for c in os.environ.get("LX_CANDS", "1,2,3,4,5").split(",") if c]
    hows = ["native", ("plain", 0), ("snapshot", 0)] + [("snapshot", c) for c in CANDS] + [("plain", c) for c in CANDS if c == 6] + [(k, 0) for k in VARIANTS]
    only = os.environ.get("LX_ONLY")
    jobs = [(n, h, VARIANTS) for n in PROBES for h in hows if not only or n.startswith(tuple(only.split(",")))]
    with ProcessPoolExecutor(8) as ex, open(out, "w") as fh:
        for name, label, fuel, res in ex.map(one, jobs):
            fh.write("\t".join([name, label, str(fuel), *res]) + "\n")
