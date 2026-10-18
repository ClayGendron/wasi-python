import json, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "hx"))
import guest  # noqa: E402
S = Path(__file__).parent
which, target, outname = sys.argv[1:4]
crashers = []
for it in range(40):
    work = S / "work" / f"{outname}-{it}"
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    des = [a for c in crashers for a in ("--deselect", c)]
    r = guest.run(S / "art/python-snapshot.wasm", ["-u", "/t/tests/_judge/drive4.py", which, target, *des],
                  workdir=work, python_version="3.15", stdlib=S / "art/python-stdlib.zip",
                  env={"TMPDIR": "/tmp", "HOME": "/tmp"}, fuel=4 * 10**12,
                  preopens=[("/t", S / "tgrant", False)])
    shutil.rmtree(work, ignore_errors=True)
    last, done, end, counts = None, set(), None, {}
    nonpass = []
    for line in r.text.splitlines():
        if not line.startswith("@@"):
            continue
        line = line[2:]
        if line.startswith("S "):
            last = line[2:]
        elif line.startswith("R "):
            _, o, rest = line.split(" ", 2)
            done.add(rest.split(" -- ")[0]); counts[o] = counts.get(o, 0) + 1
            if o != "passed":
                nonpass.append(line[2:])
        elif line.startswith("END"):
            end = line
    if end is not None or r.trapped is None:
        break
    trap = r.trapped.split("Caused by:")[-1].strip(" |") if r.trapped else ""
    frame0 = r.trapped.split("|")[1].strip() if r.trapped and "|" in r.trapped else ""
    crashers.append(last)
    print("CRASH", last, "|", trap, "|", frame0, flush=True)
rec = {"target": target, "crashers": crashers, "final_counts": counts, "fuel_last": r.fuel,
       "end": end, "trapped": r.trapped, "nonpass": nonpass}
with (S / "out" / outname).open("w") as f:
    json.dump(rec, f, indent=1)
print("DONE", target, counts, len(crashers), flush=True)
