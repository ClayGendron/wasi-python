# Two to four calls of wasi_python.run at once, on threads and through run_async: each call's
# stdout, stderr and env must be its own.
import asyncio, threading, json, time
import wasi_python

CODE = (
    "import os, sys\n"
    "t = os.environ['TOKEN']\n"
    "for i in range(3000):\n"
    "    sys.stdout.write(t + '\\n'); sys.stderr.write(t + '\\n')\n"
    "    if i % 100 == 0: sys.stdout.flush()\n"
)

def one(tok, out):
    c = wasi_python.run(["-c", CODE], env={"TOKEN": tok}, deadline_s=60)
    out[tok] = c

results = {}
threads = [threading.Thread(target=one, args=(f"tok{i:02d}", results)) for i in range(4)]
t0 = time.monotonic()
for t in threads: t.start()
for t in threads: t.join()
report = {"threads": {}, "async": {}}
for tok, c in sorted(results.items()):
    lines_o = set(c.stdout.decode().split()); lines_e = set(c.stderr.decode().split())
    report["threads"][tok] = {"exit": c.exit_code, "trapped": c.trapped,
        "stdout_tokens": sorted(lines_o), "stderr_tokens": sorted(lines_e),
        "stdout_lines": c.stdout.count(b"\n"), "stderr_lines": c.stderr.count(b"\n")}

async def main():
    toks = [f"atok{i:02d}" for i in range(4)]
    cs = await asyncio.gather(*(wasi_python.run_async(["-c", CODE], env={"TOKEN": t}, deadline_s=60) for t in toks))
    for t, c in zip(toks, cs):
        report["async"][t] = {"exit": c.exit_code, "trapped": c.trapped,
            "stdout_tokens": sorted(set(c.stdout.decode().split())),
            "stderr_tokens": sorted(set(c.stderr.decode().split())),
            "stdout_lines": c.stdout.count(b"\n")}
asyncio.run(main())
report["wall_s"] = round(time.monotonic() - t0, 2)
print(json.dumps(report, indent=1))
