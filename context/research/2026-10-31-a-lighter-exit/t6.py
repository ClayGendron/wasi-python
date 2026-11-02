import sys, os, tempfile, subprocess; sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from drv import go
from probes import PROBES
prog = PROBES["P44 scandir left open, warnings on"][1]
d = tempfile.mkdtemp(dir=os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "tmp"))
r = go(prog, root=d); print("guest:", r.stderr.decode()[-400:])
d2 = tempfile.mkdtemp(dir=os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "tmp"))
p = subprocess.run(["/Users/claygendron/Git/Repos/wasi_python-wt/167-pdfplumber-plotly-xarray-and-zstd/build/tools/python/bin/python3", "-I", "-c", prog], cwd=d2, capture_output=True)
print("native:", p.stderr.decode()[-400:], p.stdout)
p = subprocess.run(["/Users/claygendron/Git/Repos/wasi_python-wt/167-pdfplumber-plotly-xarray-and-zstd/build/tools/python/bin/python3", "-I", "-c", prog + "\nimport os; print(sorted(os.listdir('.')))"], cwd=d2, capture_output=True)
print("native2:", p.stderr.decode()[-400:], p.stdout)
