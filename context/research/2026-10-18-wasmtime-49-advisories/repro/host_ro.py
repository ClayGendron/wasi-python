import json,sys
from wasi_python import run, Grant
from pathlib import Path
done=run(["-c",Path(sys.argv[2]).read_text()],grants=[Grant(sys.argv[1],"/work",writable=False)])
print("EXIT",done.exit_code,"TRAP",done.trapped)
for l in done.stdout.decode(errors="replace").splitlines():
    if l.startswith("RESULT "): print(json.dumps(json.loads(l[7:])))
