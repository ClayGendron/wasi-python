# Session limits and the state machine: lifetime caps a turn; idle ends a resting session; a
# trapping turn ends the session; per-turn output cap; a turn claimed before the lifetime but
# started after it (run_async behind a busy one-worker executor).
import asyncio, json, time, threading, concurrent.futures
import wasi_python
from wasi_python import Session, SessionEnded

out = []
def rec(**kw): out.append(kw)

# 1. lifetime caps a turn with no deadline of its own
s = Session(lifetime_s=1.0, deadline_s=None, idle_s=None, shutdown_s=0)
t = time.monotonic(); c = s.run("import time\ntime.sleep(10)")
rec(case="lifetime_caps_turn", wall_s=round(time.monotonic()-t,3), trapped=c.trapped, ended=s.ended)
s.close()

# 2. idle ends a resting session
s = Session(idle_s=0.5, shutdown_s=0)
c = s.run("x = 1"); time.sleep(1.5)
try:
    s.run("print(x)"); r = "ran"
except SessionEnded as e:
    r = "SessionEnded:" + e.reason
rec(case="idle_then_turn", result=r, ended=s.ended); s.close()

# 3. a hostile (trapping) turn ends the session; the next turn is refused
s = Session(shutdown_s=0, deadline_s=0.3)
c1 = s.run("while True: pass")
try:
    s.run("print('benign')"); r = "ran"
except SessionEnded as e:
    r = "SessionEnded:" + e.reason
rec(case="trap_then_benign", first_trapped=c1.trapped, second=r, ended=s.ended); s.close()

# 4. per-turn output cap and fresh streams per turn
s = Session(output_bytes=1000, shutdown_s=0)
a = s.run("print('A'*5000)"); b = s.run("print('B')")
rec(case="output_per_turn", a_len=len(a.stdout), a_trunc=a.truncated, b=b.stdout.decode())
s.close()

# 5. close() from another thread stops a running turn
s = Session(deadline_s=None, lifetime_s=None, idle_s=None, shutdown_s=0)
res = {}
th = threading.Thread(target=lambda: res.setdefault("c", s.run("while True: pass")))
th.start(); time.sleep(0.5); t = time.monotonic(); s.close(); th.join(10)
rec(case="close_stops_turn", close_wait_s=round(time.monotonic()-t,3), trapped=res["c"].trapped if "c" in res else None, ended=s.ended)

# 6. a turn claimed before the lifetime but started after it
async def queued():
    ex = concurrent.futures.ThreadPoolExecutor(1)
    s = Session(lifetime_s=1.0, deadline_s=None, idle_s=None, shutdown_s=0)
    s.run("pass")
    blocker = ex.submit(time.sleep, 2.0)
    t = time.monotonic()
    code = ("import time\nn=0\nt=time.perf_counter()\n"
            "while True:\n n+=1\n if n % 10000 == 0: print(n, round(time.perf_counter()-t,4), flush=True)")
    c = await s.run_async(code, executor=ex)
    rec(case="queued_turn_after_lifetime", awaited_s=round(time.monotonic()-t,3),
        trapped=c.trapped, stdout_tail=c.stdout.decode()[-120:], ended=s.ended)
    s.close(); ex.shutdown()
asyncio.run(queued())
print(json.dumps(out, indent=1))
