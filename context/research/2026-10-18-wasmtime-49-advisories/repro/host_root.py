import json,sys
from wasi_python import run
from pathlib import Path
done=run(["-c",Path(sys.argv[1]).read_text()],root=True)
print("EXIT",done.exit_code,"TRAP",done.trapped)
for l in done.stdout.decode(errors="replace").splitlines():
    if l.startswith("RESULT "): print(json.dumps(json.loads(l[7:]),indent=1))
