"""Runs guest_exn_churn.py through the wasi_python runner (wasmtime-py 49.0.0, engine at
its defaults: GC and exceptions on, DRC collector) and prints how the call ended. Run
under the brief's sandbox wrapper; no writable grant or root."""
import os, sys, time
from wasi_python import run

here = os.path.dirname(os.path.abspath(__file__))
code = open(os.path.join(here, "guest_exn_churn.py")).read()
rounds = sys.argv[1] if len(sys.argv) > 1 else "2000"
budget = sys.argv[2] if len(sys.argv) > 2 else "8"
snapshot = (sys.argv[3] if len(sys.argv) > 3 else "1") == "1"
fuel = int(sys.argv[4]) if len(sys.argv) > 4 else None  # a cap selects the metered engine
t = time.monotonic()
done = run(["-c", code, rounds, budget], root=True, deadline_s=120, snapshot=snapshot, fuel=fuel)
print("host_elapsed_s", round(time.monotonic() - t, 1), "snapshot", snapshot, "fuel", fuel)
print("exit_code", done.exit_code, "trapped", done.trapped)
print("stdout", done.stdout.decode(errors="replace")[-2000:])
print("stderr", done.stderr.decode(errors="replace")[-3000:])
