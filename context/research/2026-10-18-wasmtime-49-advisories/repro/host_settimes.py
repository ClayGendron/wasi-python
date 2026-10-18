import json,sys,faulthandler
faulthandler.enable()
from wasi_python import run
from pathlib import Path
try:
    done=run(["-c",Path(sys.argv[1]).read_text()], root=True)
    print("HOST-SURVIVED EXIT",done.exit_code,"TRAP",done.trapped)
    for l in done.stdout.decode(errors="replace").splitlines():
        if l.startswith("RESULT "): print(json.dumps(json.loads(l[7:])))
    print("STDERR", done.stderr.decode(errors='replace')[-500:])
except BaseException as e:
    print("HOST-RAISED", type(e).__name__, str(e)[:300])
