# Trusted driver: runs guest_probe.py on both binaries, twice each, with default limits.
import json, sys, pathlib
import wasi_python
here = pathlib.Path(__file__).parent
code = (here / 'guest_probe.py').read_text()
out = {}
for snap in (True, False):
    for i in (1, 2):
        c = wasi_python.run(['-c', code], snapshot=snap, env={'PYTHONSTARTUP': '/x.py', 'PYTHONPATH': '/planted', 'PYTHONHASHSEED': '123', 'PYTHONINSPECT': '1'})
        key = f'snapshot={snap} run={i}'
        try:
            out[key] = json.loads(c.stdout)
        except Exception:
            out[key] = {'exit': c.exit_code, 'stdout': c.stdout[-2000:].decode('utf-8', 'replace'), 'stderr': c.stderr[-3000:].decode('utf-8', 'replace')}
        out[key]['_exit_code'] = c.exit_code
print(json.dumps(out, indent=1, sort_keys=True))
