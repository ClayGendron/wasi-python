import shutil, sys
from pathlib import Path
from wasi_python import Grant, run
ARGV0 = "/usr/local/bin/python.wasm"
def prelude(entries):
    return ["-c", "__import__('linecache')._interactive_cache.clear() or "
            f"__import__('sys').path.extend({entries!r}) or "
            "__import__('sys').exit(__import__('_reactor').run("
            f"[{ARGV0!r}, *__import__('sys').argv[1:]], dict(__import__('os').environ)))"]
root = Path(sys.argv[1]); shutil.rmtree(root, ignore_errors=True)
a, h = root / "a", root / "h"; a.mkdir(parents=True); h.mkdir()
(a / "pytz.py").write_text("import sys\nsys.stderr.write('HIT pytz\\n')\nraise ImportError('stub')\n")
(h / "_hashlib.py").write_text("import sys\nsys.stderr.write('HIT _hashlib\\n')\n")
for snap in (True, False):
    b = "snapshot" if snap else "plain"
    for d_, prog in ((a, "import pandas; print(pandas.__version__)"), (h, "import hashlib")):
        d = run(prelude(["/e"]) + ["-c", prog], grants=[Grant(str(d_), "/e")], snapshot=snap)
        err = d.stderr.decode()
        print(b, repr(prog), "exit", d.exit_code, "hits", err.count("HIT "), err.splitlines()[-1:] , d.stdout)
