# The deadline against waits: a sleep, a select, a busy loop, a raw host function that blocks,
# a large single write to stdout under a small output cap. Wall time per call is recorded.
import json, time
import wasi_python

def timed(label, argv, **kw):
    t = time.monotonic()
    c = wasi_python.run(argv, **kw)
    return {"case": label, "wall_s": round(time.monotonic() - t, 3), "exit": c.exit_code,
            "trapped": c.trapped, "stdout_len": len(c.stdout), "truncated": c.truncated,
            "stderr_tail": c.stderr[-200:].decode(errors="replace")}

out = []
out.append(timed("warm", ["-c", "pass"]))
out.append(timed("sleep5_deadline0.3", ["-c", "import time; time.sleep(5)"], deadline_s=0.3))
out.append(timed("select5_deadline0.3", ["-c", "import select; select.select([],[],[],5)"], deadline_s=0.3))
out.append(timed("busy_deadline0.3", ["-c", "while True: pass"], deadline_s=0.3))
out.append(timed("sleep_loop_deadline0.3", ["-c", "import time\nwhile True: time.sleep(0.001)"], deadline_s=0.3))

def slow_host(req):
    time.sleep(1.5)
    return b"ok"
out.append(timed("raw_host_blocks1.5_deadline0.3",
                 ["-c", "import _host\nfor _ in range(3): _host.call(b'x')"], deadline_s=0.3, host=slow_host))
out.append(timed("write_8MiBx50_cap1MiB",
                 ["-c", "import os\nb=b'x'*(8<<20)\nfor _ in range(50): os.write(1,b)"],
                 deadline_s=30, output_bytes=1 << 20))
for mb in (16, 64, 128):
    out.append(timed(f"single_write_{mb}MiB",
                     ["-c", f"import os\nb=b'x'*({mb}<<20)\nprint(os.write(1,b), file=__import__('sys').stderr)"],
                     deadline_s=30, output_bytes=1 << 20))
print(json.dumps(out, indent=1))
