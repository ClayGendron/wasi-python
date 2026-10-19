import sys, time, wasi_python
PROG = """import regex, time
t0 = time.monotonic()
try:
    regex.search(r'(a|aa)+$', 'a'*100+'!', timeout={t}); print('completed')
except TimeoutError:
    print('TimeoutError after', round(time.monotonic() - t0, 2), 'guest s')
"""
for t in sys.argv[1].split(","):
    t0 = time.monotonic()
    r = wasi_python.run(["-c", PROG.format(t=t)], snapshot=False, deadline_s=12)
    print("timeout", t, "|", r.trapped, r.stdout.decode().strip(), "| host", round(time.monotonic() - t0, 1), "s", flush=True)
