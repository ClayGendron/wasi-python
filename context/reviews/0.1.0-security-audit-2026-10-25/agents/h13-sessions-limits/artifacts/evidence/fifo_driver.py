# Trusted driver: for each mode, makes a fresh folder with a FIFO (and a plain file, and for
# `socket` a unix socket file) under scratch/work, runs fifo_child.py under the sandbox wrapper
# with a 12 s wall-clock bound, and for some modes acts on the FIFO or the child from outside.
import json, os, signal, socket, subprocess, sys, threading, time
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h13-sessions-limits/scratch"
WRAP = ["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", f"HOME={S}/home", f"TMPDIR={S}/tmp",
        f"WASI_PYTHON_CACHE={S}/cache", "/usr/bin/sandbox-exec", "-p",
        "(version 1)(allow default)(deny network*)",
        "./.venv/bin/python", "-I", f"{S}/evidence/fifo_child.py"]
BOUND = 12

def writer(path, at, hold, data):
    time.sleep(at)
    fd = os.open(path, os.O_WRONLY)  # rendezvous with the guest's blocked open
    if data: os.write(fd, data)
    time.sleep(hold); os.close(fd)

for mode in sys.argv[1:]:
    folder = f"{S}/work/{mode}"
    os.makedirs(folder, exist_ok=True)
    pipe = f"{folder}/pipe"
    if not os.path.exists(pipe): os.mkfifo(pipe, 0o600)
    with open(f"{folder}/plain.txt", "w") as f: f.write("hello\n")
    sock = None
    if mode == "socket":
        sock = socket.socket(socket.AF_UNIX); p = f"{folder}/sock"
        if os.path.exists(p): os.unlink(p)
        here = os.getcwd(); os.chdir(folder); sock.bind("sock"); os.chdir(here)
    if mode == "writer_late":
        threading.Thread(target=writer, args=(pipe, 4.0, 0.0, b"x"), daemon=True).start()
    if mode == "writer_holds":
        threading.Thread(target=writer, args=(pipe, 0.5, 9.0, b""), daemon=True).start()
    t = time.monotonic()
    proc = subprocess.Popen(WRAP + [folder, mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mode == "sigint":
        def ints():
            time.sleep(3.0); proc.send_signal(signal.SIGINT)
            time.sleep(2.0); proc.send_signal(signal.SIGINT)
        threading.Thread(target=ints, daemon=True).start()
    try:
        out, err = proc.communicate(timeout=BOUND)
        rec = {"mode": mode, "driver_wall_s": round(time.monotonic() - t, 2), "killed": False,
               "rc": proc.returncode}
    except subprocess.TimeoutExpired:
        proc.kill(); out, err = proc.communicate()
        rec = {"mode": mode, "driver_wall_s": round(time.monotonic() - t, 2), "killed": True}
    rec["child_lines"] = [l for l in out.decode().splitlines()][-6:]
    e = [l for l in err.decode().splitlines() if "RuntimeWarning" not in l and "return _call" not in l]
    if e: rec["stderr_tail"] = e[-4:]
    print(json.dumps(rec), flush=True)
    if sock: sock.close()
    # unblock any writer thread left waiting, then remove the FIFO
    try:
        fd = os.open(pipe, os.O_RDONLY | os.O_NONBLOCK); os.close(fd)
    except OSError: pass
