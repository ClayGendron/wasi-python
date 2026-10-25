"""Bounded local check: two consecutive wasi_python.run calls on one writable root under scratch.

Call 1 (the planting guest) writes Python files and config files at every place a later
interpreter or package might read code from. Each planted file, if it ever runs, prints
PLANTED:<tag> to stderr. Later calls run benign programs with defaults, with env= overrides of
HOME, TMPDIR and PYTHON* variables, with import_path entries, and on the plain binary; the check
records every PLANTED tag seen in each later call's output.
"""

import json
import os
import sys
from pathlib import Path

import wasi_python
from wasi_python import Grant

SCRATCH = Path(sys.argv[1])
ROOT = SCRATCH / "work" / "root1"
RO = SCRATCH / "work" / "ro_lib"
OUT = SCRATCH / "evidence" / "reused_root_result.json"

ROOT.mkdir(parents=True, exist_ok=True)
RO.mkdir(parents=True, exist_ok=True)
(RO / "benign_mod.py").write_text("VALUE = 7\n")

PLANT = r'''
import os
def body(tag):
    return "import sys\nsys.stderr.write('PLANTED:%s\\n')\n" % tag
files = {
    "/sitecustomize.py": body("sitecustomize_root"),
    "/usercustomize.py": body("usercustomize_root"),
    "/evil.pth": "import sys; sys.stderr.write('PLANTED:pth_root\\n')\n",
    "/pyvenv.cfg": "home = /\ninclude-system-site-packages = true\n",
    "/usr/local/pyvenv.cfg": "home = /\ninclude-system-site-packages = true\n",
    "/usr/local/bin/pyvenv.cfg": "home = /\n",
    "/usr/local/bin/pybuilddir.txt": "planted\n",
    "/usr/local/lib/python3.15/os.py": body("lib_os"),
    "/usr/local/lib/python3.15/site-packages/evil.pth": "import sys; sys.stderr.write('PLANTED:pth_sitepackages\\n')\n",
    "/usr/local/lib/python3.15/site-packages/sitecustomize.py": body("sitecustomize_sp"),
    "/usr/local/lib/python315.zip": "not a zip",
    "/json.py": body("json_shadow"),
    "/numpy.py": body("numpy_shadow"),
    "/platform.py": body("platform_shadow"),
    "/argparse.py": body("argparse_shadow"),
    "/__main__.py": body("dunder_main"),
    "/startup.py": body("pythonstartup"),
    "/.pythonrc.py": body("pythonrc"),
    "/_sysconfigdata__wasi_wasm32-wasi.py": body("sysconfigdata_root") + "build_time_vars = {}\n",
    "/_sysconfigdata_.py": body("sysconfigdata_short") + "build_time_vars = {}\n",
    "/planted_backend.py": body("mpl_backend"),
    "/evilhook.py": body("breakpoint_mod") + "def f(*a, **k):\n    pass\n",
    "/reportlab_mods.py": body("reportlab_mods_root"),
    "/reportlab_settings.py": body("reportlab_settings_root"),
    "/.reportlab_mods": body("reportlab_mods_home_root"),
    "/.reportlab_settings": body("reportlab_settings_home_root"),
    "/tmp/.reportlab_mods": body("reportlab_mods_tmp"),
    "/tmp/.reportlab_settings": body("reportlab_settings_tmp"),
    "/tmp/sitecustomize.py": body("sitecustomize_tmp"),
    "/tmp/json.py": body("json_tmp"),
    "/matplotlibrc": "backend: module://planted_backend\n",
    "/turtle.cfg": "width = 0.5\n",
    "/.pdbrc": "!import sys; sys.stderr.write('PLANTED:pdbrc\\n')\n",
    "/.local/lib/python3.15/site-packages/usercustomize.py": body("usersite"),
}
planted, failed = [], []
rootfd = os.open("/", os.O_RDONLY)
for path, text in files.items():
    try:
        os.makedirs(os.path.dirname(path) or "/", exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        planted.append(path)
    except OSError as e:
        # The same place reached relative to the root's own descriptor, under the zip's preopen.
        rel = path.lstrip("/")
        try:
            here = rootfd
            for part in rel.split("/")[:-1]:
                try:
                    os.mkdir(part, dir_fd=here)
                except FileExistsError:
                    pass
                here = os.open(part, os.O_RDONLY, dir_fd=here)
            fd = os.open(rel.split("/")[-1], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, dir_fd=here)
            os.write(fd, text.encode())
            os.close(fd)
            planted.append(path + " (via root fd)")
        except OSError as e2:
            failed.append((path, str(e), str(e2)))
print("planted", planted)
print("failed", failed)
print(sorted(os.listdir("/")))
'''

PROBE = r'''
import sys, os
print("sys.path", sys.path)
print("flags", sys.flags.isolated, sys.flags.ignore_environment, sys.flags.no_site, sys.flags.safe_path)
print("HOME", os.environ.get("HOME"), "cwd", os.getcwd(), "prefix", sys.prefix, sys.base_prefix)
mods = ["json", "argparse", "platform", "site", "sysconfig", "gettext", "tempfile", "pdb",
        "numpy", "pandas", "matplotlib", "matplotlib.pyplot", "reportlab", "reportlab.rl_config",
        "lxml.etree", "scipy.stats", "sklearn.linear_model", "statsmodels.api", "seaborn",
        "sympy", "networkx", "joblib", "PIL.Image", "openpyxl", "yaml", "jinja2", "tqdm",
        "wrapt", "cloudpickle", "fontTools.ttLib", "reportlab.pdfgen.canvas"]
for m in mods:
    try:
        __import__(m)
    except BaseException as e:
        print("import-failed", m, type(e).__name__, str(e)[:120])
import sysconfig
try:
    sysconfig.get_config_vars(); sysconfig.get_platform(); sysconfig.get_paths()
except BaseException as e:
    print("sysconfig-failed", type(e).__name__, str(e)[:120])
try:
    import matplotlib
    print("mpl backend", matplotlib.get_backend())
except BaseException as e:
    print("mpl-backend-failed", type(e).__name__, str(e)[:120])
print("probe-done")
'''

MAIN_PY = "import json, platform, argparse\nprint('script ran', json.__file__)\n"

results = {}


def call(label, argv, **kw):
    kw.setdefault("cache_dir", str(SCRATCH / "cache"))
    try:
        c = wasi_python.run(argv, root=str(ROOT), **kw)
        err = c.stderr.decode("utf-8", "replace")
        out = c.stdout.decode("utf-8", "replace")
        tags = sorted({line.split(":", 1)[1] for line in err.splitlines() if line.startswith("PLANTED:")})
        results[label] = {
            "exit_code": c.exit_code,
            "trapped": c.trapped,
            "planted_ran": tags,
            "stdout_tail": out[-3000:],
            "stderr_tail": err[-2000:],
        }
    except Exception as e:  # an argument refusal is a result too
        results[label] = {"raised": f"{type(e).__name__}: {e}"}
    print(label, json.dumps(results[label].get("planted_ran", results[label].get("raised"))))


call("1_plant", ["-c", PLANT])
call("2_defaults_snapshot", ["-c", PROBE])
call("3_defaults_plain", ["-c", PROBE], snapshot=False)
ENV = {
    "HOME": "/",
    "TMPDIR": "/",
    "PYTHONPATH": "/",
    "PYTHONSTARTUP": "/startup.py",
    "PYTHONHOME": "/",
    "PYTHONUSERBASE": "/.local",
    "PYTHONBREAKPOINT": "evilhook.f",
    "PYTHONSAFEPATH": "",
    "PYTHONINSPECT": "1",
    "PYTHONNOUSERSITE": "",
    "PYTHONPLATLIBDIR": "/",
    "MPLCONFIGDIR": "/",
    "MPLBACKEND": "module://planted_backend",
    "XDG_CONFIG_HOME": "/",
}
call("4_env_home_tmp_python_snapshot", ["-c", PROBE + "\nbreakpoint()\n"], env=ENV)
call("5_env_home_tmp_python_plain", ["-c", PROBE], env=ENV, snapshot=False)
call("6_env_sysconfigdata_path", ["-c", PROBE], env={"_PYTHON_SYSCONFIGDATA_PATH": "/"})
call(
    "7_import_path_ro_grant",
    ["-c", "import benign_mod, json, sys; print(benign_mod.VALUE, json.__file__, sys.path)"],
    grants=[Grant(str(RO), "/ro")],
    import_path=["/ro"],
)
call("8_import_path_served_by_root", ["-c", "print(1)"], import_path=["/tmp"])
(ROOT / "main.py").write_text(MAIN_PY)  # the embedder's own fresh script
call("9_script_mode", ["/main.py"])
call("10_dash_m", ["-m", "json.tool", "/pyvenv.cfg"])
call("11_session_like_pdb", ["-c", "import pdb; print('pdb imported')"])

OUT.write_text(json.dumps(results, indent=1, sort_keys=True))
print("written", OUT)
