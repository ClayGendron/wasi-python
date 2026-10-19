"""A second process under the same soft limit makes one plain call (no root): its first call's
sweep retries the dead roots in TEMP. usage: p_sweep_once.py SOFT TEMP"""

import json
import os
import resource
import sys
import tempfile

soft, temp = int(sys.argv[1]), sys.argv[2]
resource.setrlimit(resource.RLIMIT_NOFILE, (soft, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
tempfile.tempdir = temp
import wasi_python  # noqa: E402
from wasi_python import runner  # noqa: E402

done = wasi_python.run(["-c", "print(1)"])
left = [n for n in os.listdir(temp) if n.startswith("wasi-python-root-") and not n.endswith(".lock")]
print(json.dumps({"exit": done.exit_code, "swept": runner._sweep_state["swept"],
                  "roots_left": len(left)}))
