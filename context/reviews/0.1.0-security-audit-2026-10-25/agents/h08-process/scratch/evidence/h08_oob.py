"""A guest read past its linear memory (numpy as_strided over a far address), run normally."""
import json
from wasi_python import run
GUEST = ("import numpy as np\nfrom numpy.lib.stride_tricks import as_strided\n"
         "a = np.zeros(1, dtype=np.uint8)\n"
         "b = as_strided(a, shape=(2,), strides=(0x7ff00000,))\n"
         "print(int(b[1]))\n")
done = run(["-c", GUEST], deadline_s=60)
print(json.dumps({"exit_code": done.exit_code, "trapped": done.trapped,
                  "stderr_tail": done.stderr[-300:].decode("utf-8", "replace")}))
