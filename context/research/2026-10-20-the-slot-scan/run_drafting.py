import sys, wasi_python
src = open(sys.argv[1]).read()
for snap in (False, True):
    d = wasi_python.run(["-c", src], root=True, snapshot=snap, fuel=10**12, env={"MPLCONFIGDIR": "/tmp"})
    print(f"--- snapshot={snap} exit={d.exit_code} fuel={getattr(d,'fuel_used',None)}")
    print(d.stdout.decode(errors="replace").rstrip())
    err = d.stderr.decode(errors="replace").strip().splitlines()
    print("stderr tail:", err[-3:])
    for k in ("trap", "trapped", "reason"):
        if hasattr(d, k): print(k, getattr(d, k))
