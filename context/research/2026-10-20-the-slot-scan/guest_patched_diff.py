import sys, wasi_python
PROG = '''
import importlib.util, sys
import lxml.html
spec = importlib.util.spec_from_file_location("lxml.html.diff", "/d/diff.py")
m = importlib.util.module_from_spec(spec); sys.modules["lxml.html.diff"] = m
try:
    spec.loader.exec_module(m)
except Exception as e:
    print(type(e).__name__, e)
else:
    print(m.htmldiff("<p>Hello world</p>", "<p>Hello there world</p>"))
'''
for name in ("g-pristine", "g-patched"):
    for snap in (False, True):
        d = wasi_python.run(["-c", PROG], grants=[wasi_python.Grant(f"build/096/{name}", "/d")], snapshot=snap, fuel=10**11)
        print(name, "snapshot" if snap else "plain", d.exit_code, d.stdout.decode().strip(), d.stderr.decode().strip()[-200:])
