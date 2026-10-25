"""Bounded local check: which plain imports run a module planted by an earlier call, when the
embedder passes env={"_PYTHON_SYSCONFIGDATA_PATH": <a folder in the reused root>}.

Call 1 plants /data/_sysconfigdata__wasi_wasm32-wasi.py in a writable root. Each later call, on
the same root, runs only `import <package>` with that one env entry; a control call per package
runs without it."""

import json
import sys
from pathlib import Path

import wasi_python

SCRATCH = Path(sys.argv[1])
ROOT = SCRATCH / "work" / "root2"
OUT = SCRATCH / "evidence" / "sysconfigdata_path_result.json"
ROOT.mkdir(parents=True, exist_ok=True)
CACHE = str(SCRATCH / "cache")

PLANT = (
    "import os\n"
    "os.makedirs('/data', exist_ok=True)\n"
    "open('/data/_sysconfigdata__wasi_wasm32-wasi.py', 'w').write(\n"
    "    \"import sys\\nsys.stderr.write('PLANTED:sysconfigdata ran in a later call\\\\n')\\n\"\n"
    "    \"from _sysconfigdata__wasi_wasm32_wasi_real import *\\n\" if False else\n"
    "    \"import sys\\nsys.stderr.write('PLANTED:sysconfigdata ran in a later call\\\\n')\\nbuild_time_vars = {'installed_base': '/usr/local', 'Py_GIL_DISABLED': 0}\\n\")\n"
    "print('planted')\n"
)
results = {}


def call(label, argv, **kw):
    c = wasi_python.run(argv, root=str(ROOT), cache_dir=CACHE, **kw)
    err = c.stderr.decode("utf-8", "replace")
    results[label] = {
        "argv": argv,
        "env": kw.get("env"),
        "snapshot": kw.get("snapshot", True),
        "exit_code": c.exit_code,
        "planted_ran": "PLANTED:" in err,
        "stdout": c.stdout.decode("utf-8", "replace")[-400:],
        "stderr_tail": err[-400:],
    }
    print(label, results[label]["exit_code"], results[label]["planted_ran"])


call("plant", ["-c", PLANT])
ENV = {"_PYTHON_SYSCONFIGDATA_PATH": "/data"}
for pkg in ["numpy", "pandas", "scipy", "sklearn", "joblib", "matplotlib", "statsmodels.api"]:
    call(f"control_{pkg}", ["-c", f"import {pkg}; print('ok')"])
    call(f"env_{pkg}", ["-c", f"import {pkg}; print('ok')"], env=ENV)
call("env_pandas_plain", ["-c", "import pandas; print('ok')"], env=ENV, snapshot=False)
OUT.write_text(json.dumps(results, indent=1, sort_keys=True))
