"""h15: call 1 plants modules, a dist-info with entry points, matplotlibrc files and a pickle in a
writable root at /data; later calls on the same root set env keys that bundled packages read
(name-based selectors, folder-based config, sklearn's data home) and look for planted markers."""
import json, sys
from pathlib import Path
import wasi_python

S = Path(sys.argv[1]); ROOT = S / "work" / "root"; ROOT.mkdir(parents=True, exist_ok=True)
OUT = S / "evidence" / "h15_result.json"; CACHE = str(S / "cache")
PLANT = r'''
import os, pickle
for d in ("/data/sk", "/data/mpl", "/data/sage", "/data/matplotlib", "/data/fakenx-1.0.dist-info"):
    os.makedirs(d, exist_ok=True)
def mod(path, tag):
    open(path, "w").write("import sys\nsys.stderr.write('PLANT-%s\\n')\nx = None\n" % tag)
mod("/data/sage/__init__.py", "sage"); mod("/data/sage/all.py", "sage-all")
for n in ("gmpy2", "gmpy", "mybackend", "mypickler", "symengine", "flint", "sitecustomize",
          "usercustomize", "start", "mydom", "mysax"):
    mod("/data/%s.py" % n, n)
open("/data/fakenx-1.0.dist-info/METADATA", "w").write("Metadata-Version: 2.1\nName: fakenx\nVersion: 1.0\n")
open("/data/fakenx-1.0.dist-info/entry_points.txt", "w").write(
    "[networkx.backends]\nfake = mybackend\n[networkx.backend_info]\nfake = mybackend:x\n[matplotlib.backend]\nfake = mybackend\n")
for d in ("/data/mpl", "/data/matplotlib"):
    open(d + "/matplotlibrc", "w").write("backend: module://mybackend\n")
class P:
    def __reduce__(self):
        return (exec, ("import sys; sys.stderr.write('PLANT-sklearn-pickle\\n')",))
open("/data/sk/cal_housing_py3.pkz", "wb").write(pickle.dumps(P()))
print("planted", sorted(os.listdir("/data")))
'''
NAMES_ENV = {
    "MPMATH_SAGE": "1", "SAGE_ROOT": "/data", "LOKY_PICKLER": "mypickler",
    "NETWORKX_AUTOMATIC_BACKENDS": "fake", "NETWORKX_BACKEND_PRIORITY": "fake",
    "USE_SYMENGINE": "1", "SYMPY_GROUND_TYPES": "flint", "PYTHON_DOM": "mydom",
    "PY_SAX_PARSER": "mysax", "PYTHONPATH": "/data", "PYTHONUSERBASE": "/data",
    "PYTHONSTARTUP": "/data/start.py", "JOBLIB_TEMP_FOLDER": "/data", "SCIPY_ARRAY_API": "1",
}
NAMES = r'''
import sys, os
print("cwd", os.getcwd()); print("path", sys.path)
r = {}
def t(label, f):
    try:
        f(); r[label] = "ok"
    except BaseException as e:
        r[label] = type(e).__name__ + ": " + str(e)[:160]
t("mpmath", lambda: __import__("mpmath").mpf(1))
t("sympy", lambda: __import__("sympy").Symbol("x"))
def nx():
    import networkx as nx
    g = nx.path_graph(4); nx.shortest_path(g, 0, 3)
t("networkx", nx)
def loky():
    import joblib
    from joblib.externals.loky.backend import reduction
    reduction.set_loky_pickler("mypickler")
t("loky", loky)
def dom():
    import xml.dom; xml.dom.getDOMImplementation()
t("dom", dom)
def sax():
    import xml.sax; xml.sax.make_parser()
t("sax", sax)
t("scipy", lambda: __import__("scipy.linalg"))
print("results", r)
'''
MPL = r'''
import sys
r = {}
try:
    import matplotlib
    r["rc_backend"] = str(matplotlib.rcParams._get_backend_or_none())
    r["configdir"] = matplotlib.get_configdir()
    r["matplotlib_fname"] = matplotlib.matplotlib_fname()
    import matplotlib.pyplot as plt
    plt.figure(); r["pyplot"] = "ok"
except BaseException as e:
    r["error"] = type(e).__name__ + ": " + str(e)[:200]
print("results", r)
'''
SK = r'''
from sklearn.datasets import fetch_california_housing
try:
    fetch_california_housing(download_if_missing=False)
    print("loaded")
except BaseException as e:
    print("after-load", type(e).__name__, str(e)[:160])
'''
res = {}
def call(label, argv, **kw):
    try:
        c = wasi_python.run(argv, root=str(ROOT), cache_dir=CACHE, deadline_s=180, **kw)
        err = c.stderr.decode("utf-8", "replace"); out = c.stdout.decode("utf-8", "replace")
        res[label] = {"env": kw.get("env"), "exit_code": c.exit_code, "trapped": c.trapped,
                      "planted_markers": sorted({l for l in err.splitlines() if l.startswith("PLANT-")}),
                      "stdout_tail": out[-1500:], "stderr_tail": err[-800:]}
    except Exception as e:
        res[label] = {"error": repr(e)}
    print(label, json.dumps(res[label])[:600], flush=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True))
call("plant", ["-c", PLANT])
call("names_control_noenv", ["-c", NAMES])
call("names_env", ["-c", NAMES], env=NAMES_ENV)
call("mpl_control_noenv", ["-c", MPL])
call("mpl_env_MPLBACKEND", ["-c", MPL], env={"MPLBACKEND": "module://mybackend"})
call("mpl_env_configdirs", ["-c", MPL], env={"MPLCONFIGDIR": "/data/mpl", "MATPLOTLIBRC": "/data/mpl/matplotlibrc", "XDG_CONFIG_HOME": "/data"})
call("mpl_env_entrypoint_name", ["-c", MPL], env={"MPLBACKEND": "fake"})
call("sklearn_control_noenv", ["-c", SK])
call("sklearn_env_SCIKIT_LEARN_DATA", ["-c", SK], env={"SCIKIT_LEARN_DATA": "/data/sk"})
