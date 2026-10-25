import json, sys
from pathlib import Path
import wasi_python
S = Path(sys.argv[1]); ROOT = S / "work" / "root"; ROOT.mkdir(parents=True, exist_ok=True)
CACHE = str(S / "cache"); res = {}
PLANT = ("import os\nos.makedirs('/data', exist_ok=True)\n"
 "open('/data/_sysconfigdata__wasi_wasm32-wasi.py','w').write("
 "\"import sys\\nsys.stderr.write('PLANTED-R01\\\\n')\\nbuild_time_vars={'installed_base':'/usr/local'}\\n\")\n")
def call(label, argv, **kw):
    try:
        c = wasi_python.run(argv, root=str(ROOT), cache_dir=CACHE, deadline_s=120, **kw)
        e = c.stderr.decode("utf-8", "replace")
        res[label] = {"exit": c.exit_code, "ran": "PLANTED-R01" in e, "out": c.stdout.decode()[-200:], "err": e[-300:]}
    except Exception as x:
        res[label] = {"error": repr(x)}
ENV = {"_PYTHON_SYSCONFIGDATA_PATH": "/data"}
call("plant", ["-c", PLANT])
call("noenv", ["-c", "import pandas; print('ok')"])
call("env_snap", ["-c", "import pandas; print('ok')"], env=ENV)
call("env_plain", ["-c", "import pandas; print('ok')"], env=ENV, snapshot=False)
(S / "evidence" / "r01_result.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res))
