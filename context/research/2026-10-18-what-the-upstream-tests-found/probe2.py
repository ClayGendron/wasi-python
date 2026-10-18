import sys, shutil
from pathlib import Path
sys.path.insert(0, "/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/proto/hx")
import guest
S = Path(__file__).parent
ART = S.parent.parent / "proto/art"
PROG = """import io, warnings, pandas as pd
warnings.simplefilter('always')
with warnings.catch_warnings(record=True) as w:
    pd.read_csv(io.StringIO('a;b\\n1;2\\n'), sep=None)
for x in w: print(x.category.__name__, x.filename, x.lineno)
from pandas.util._exceptions import find_stack_level
print('find_stack_level', find_stack_level())
import pandas.core.frame as f; print(f.DataFrame.__init__.__code__.co_filename)
"""
for z in sys.argv[1:]:
    for i, (label, argv) in enumerate([("prog", ["-c", PROG]), ("pass", ["-c", "pass"]), ("import pandas", ["-c", "import pandas"])]):
        w = S / "work" / f"{Path(z).stem}{i}"; shutil.rmtree(w, ignore_errors=True); w.mkdir(parents=True)
        r = guest.run(ART / "python.wasm", argv, workdir=w, python_version="3.15", stdlib=S / z, fuel=10**11)
        print(Path(z).stem, label, r.exit_code, r.fuel, r.text.strip().replace("\n", " | ")[:300], r.stderr.decode()[-200:].strip())
