import shutil, sys
from pathlib import Path
from wasi_python import Grant, run
ARGV0 = "/usr/local/bin/python.wasm"
def prelude(entries):
    return ["-c", "__import__('linecache')._interactive_cache.clear() or "
            f"__import__('sys').path.extend({entries!r}) or "
            "__import__('sys').exit(__import__('_reactor').run("
            f"[{ARGV0!r}, *__import__('sys').argv[1:]], dict(__import__('os').environ)))"]
code = Path(sys.argv[1]); shutil.rmtree(code, ignore_errors=True); code.mkdir(parents=True)
(code / "pytz.py").write_text("import sys\nsys.stderr.write('HIT pytz\\n')\nraise ImportError('stub')\n")
(code / "_hashlib.py").write_text("import sys\nsys.stderr.write('HIT _hashlib\\n')\n")
(code / "s_eval.py").write_text("eval('1/0')\n")
(code / "s_exec.py").write_text("exec('x = 1/0')\n")
g = [Grant(str(code), "/code")]
for snap in (True, False):
    b = "snapshot" if snap else "plain"
    for prog in ("import pandas; print(pandas.__version__)", "import hashlib"):
        d = run(prelude(["/code"]) + ["-c", prog], grants=g, snapshot=snap)
        err = d.stderr.decode()
        print(b, repr(prog), "exit", d.exit_code, "hits", err.count("HIT "), [l for l in err.splitlines() if l.startswith(("HIT", "AttributeError"))], d.stdout)
    for argv, stdin in ((["/code/s_eval.py"], None), (["/code/s_exec.py"], None), ([], b"eval('1/0')\n")):
        x = run(argv, grants=g, snapshot=snap, stdin=stdin)
        y = run(prelude(["/code"]) + argv, grants=g, snapshot=snap, stdin=stdin)
        old = run(["-c", "__import__('sys').path.extend(['/code']) or __import__('sys').exit(__import__('_reactor').run(['/usr/local/bin/python.wasm', *__import__('sys').argv[1:]], dict(__import__('os').environ)))"] + argv, grants=g, snapshot=snap, stdin=stdin)
        print(b, argv or "stdin", "fixed equal", (x.exit_code, x.stdout, x.stderr) == (y.exit_code, y.stdout, y.stderr), "memo prelude equal", (x.stderr == old.stderr))
