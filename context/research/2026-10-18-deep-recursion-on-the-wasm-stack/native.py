"""Run each guest case under a native Python, each in its own process; one line per case."""
import importlib.util, subprocess, sys
spec = importlib.util.spec_from_file_location("cases", sys.argv[2]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for name in sys.argv[3:] or m.CASES:
    p = subprocess.run([sys.argv[1], "-I", "-c", m.CASES[name]], capture_output=True, text=True, timeout=600, cwd="/tmp")
    out = p.stdout.strip().splitlines(); err = p.stderr.strip().splitlines()
    print(name, "|", "rc", p.returncode, "|", (out[-1] if out else "")[:90], "| err-last", (err[-1] if err else "")[:60], "| err-lines", len(err))
