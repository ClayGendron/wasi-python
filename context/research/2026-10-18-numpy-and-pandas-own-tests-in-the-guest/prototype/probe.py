import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "hx"))
import guest
S = Path(__file__).parent
for i, code in enumerate(sys.argv[1:]):
    w = S / "work" / f"probe{i}"; shutil.rmtree(w, ignore_errors=True); w.mkdir(parents=True)
    r = guest.run(S / "art/python-snapshot.wasm", ["-u", "-c", code], workdir=w, python_version="3.15",
                  stdlib=S / "art/python-stdlib.zip", fuel=10**11)
    print(repr(code), "->", r.exit_code, r.text.strip()[-200:], "|", (r.trapped or "").split("Caused by:")[-1].strip(" |")[:80], "|", r.stderr.decode()[-200:].strip())
