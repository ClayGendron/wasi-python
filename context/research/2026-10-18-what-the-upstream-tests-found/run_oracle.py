import subprocess, sys
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import jobs
r = subprocess.run(jobs.oracle_command("-I", *sys.argv[1:]), env=jobs.oracle_env(), capture_output=True, text=True)
print(r.stdout, r.stderr[-600:])
