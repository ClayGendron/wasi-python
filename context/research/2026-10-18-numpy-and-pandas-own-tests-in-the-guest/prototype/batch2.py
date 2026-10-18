import json, os, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "hx"))
import guest  # noqa: E402
S = Path(__file__).parent
which, binary, outname = sys.argv[1:4]
units = sys.argv[4:]
fuel_cap = int(float(os.environ.get("FUEL", "4e12")))
with (S / "out" / outname).open("a") as f:
    for i, unit in enumerate(units):
        tag = f"{outname}-{i}"
        work = S / "work" / tag
        shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
        extra = unit.split("|")
        r = guest.run(S / "art" / binary, ["-u", "/t/tests/_judge/drive4.py", which, *extra],
                      workdir=work, python_version="3.15", stdlib=S / "art/python-stdlib.zip",
                      env={"TMPDIR": "/tmp", "HOME": "/tmp"}, fuel=fuel_cap,
                      preopens=[("/t", S / "tgrant", False)])
        counts, nonpass, last_start, end = {}, [], None, None
        done = set()
        for line in r.text.splitlines():
            if not line.startswith("@@"):
                continue
            line = line[2:]
            if line.startswith("S "):
                last_start = line[2:]
            elif line.startswith("R "):
                _, o, rest = line.split(" ", 2)
                nid = rest.split(" -- ")[0]
                counts[o] = counts.get(o, 0) + 1
                done.add(nid)
                if o != "passed":
                    nonpass.append(line[2:])
            elif line.startswith("END "):
                end = int(line[4:])
        crasher = last_start if (end is None and last_start not in done) else None
        rec = {"unit": unit, "exit": r.exit_code, "end": end, "trapped": r.trapped, "fuel": r.fuel,
               "counts": counts, "crasher": crasher, "nonpass": nonpass,
               "stderr_tail": r.stderr.decode(errors="replace")[-800:] if end is None else ""}
        f.write(json.dumps(rec) + "\n"); f.flush()
        shutil.rmtree(work, ignore_errors=True)
        print(unit, r.fuel, counts, (r.trapped or "")[:80], crasher, flush=True)
