import json, sys
from pathlib import Path
from wasi_python import run, Grant

grant_host = sys.argv[1]      # scratch .../layout/grant
prog = Path(sys.argv[2]).read_text()

done = run(["-c", prog], grants=[Grant(grant_host, "/work", writable=True)])
print("EXIT", done.exit_code, "TRAP", done.trapped)
print("STDERR", done.stderr.decode(errors="replace")[-2000:])
for line in done.stdout.decode(errors="replace").splitlines():
    if line.startswith("RESULT "):
        print(json.dumps(json.loads(line[7:]), indent=2))
