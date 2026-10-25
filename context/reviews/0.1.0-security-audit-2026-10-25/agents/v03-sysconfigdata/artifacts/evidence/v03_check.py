"""Verifier v03: call 1 plants a sysconfigdata module in a writable root; call 2 on the same root
imports pandas with and without env _PYTHON_SYSCONFIGDATA_PATH=/data. Also a PYTHONPATH control
(isolated mode should ignore it) and the guest's sys.flags.ignore_environment."""
import json, sys
from pathlib import Path
import wasi_python

S = Path(sys.argv[1]); ROOT = S / "work" / "root"; ROOT.mkdir(parents=True, exist_ok=True)
OUT = S / "evidence" / "v03_result.json"; CACHE = str(S / "cache")
PLANT = (
    "import os\nos.makedirs('/data', exist_ok=True)\n"
    "open('/data/_sysconfigdata__wasi_wasm32-wasi.py','w').write("
    "\"import sys\\nsys.stderr.write('PLANTED-V03\\\\n')\\nbuild_time_vars={'installed_base':'/usr/local'}\\n\")\n"
    "open('/data/v03probe.py','w').write(\"import sys\\nsys.stderr.write('PLANTED-PYTHONPATH\\\\n')\\n\")\n"
    "print('planted')\n"
)
res = {}
def call(label, argv, **kw):
    try:
        c = wasi_python.run(argv, root=str(ROOT), cache_dir=CACHE, deadline_s=60, **kw)
        err = c.stderr.decode("utf-8", "replace")
        res[label] = {"argv": argv, "env": kw.get("env"), "snapshot": kw.get("snapshot", True),
                      "exit_code": c.exit_code, "planted_sysconfigdata_ran": "PLANTED-V03" in err,
                      "planted_pythonpath_ran": "PLANTED-PYTHONPATH" in err,
                      "stdout": c.stdout.decode("utf-8", "replace")[-300:], "stderr_tail": err[-300:]}
    except Exception as e:
        res[label] = {"error": repr(e)}
    print(label, json.dumps(res[label])[:300]); OUT.write_text(json.dumps(res, indent=1, sort_keys=True))
ENV = {"_PYTHON_SYSCONFIGDATA_PATH": "/data"}
call("plant", ["-c", PLANT])
call("flags", ["-c", "import sys; print(sys.flags.ignore_environment, sys.flags.isolated)"], env=ENV)
call("control_pandas_noenv", ["-c", "import pandas; print('ok')"])
call("env_pandas_snapshot", ["-c", "import pandas; print('ok')"], env=ENV)
call("env_pandas_plain", ["-c", "import pandas; print('ok')"], env=ENV, snapshot=False)
call("control_pythonpath", ["-c", "import v03probe"], env={"PYTHONPATH": "/data"})
