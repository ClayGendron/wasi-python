import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))  # the repository's tests/
from harness import guest as g, paths
setdir = Path(sys.argv[1]); work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
m = paths.parse_manifest((setdir / "MANIFEST").read_text())
for wasm in sys.argv[3:]:
    for prog in ("pass", "import regex", "import regex; regex.search(r'(a|aa)+$', 'a'*12+'!', timeout=3)"):
        r = g.run(Path(wasm), ["-c", prog], workdir=work, python_version=m.python, stdlib=setdir / "python-stdlib.zip")
        print(Path(wasm).parent.name, repr(prog), r.exit_code, r.fuel, flush=True)
