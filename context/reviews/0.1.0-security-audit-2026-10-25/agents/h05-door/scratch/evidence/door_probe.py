"""Bounded local check of the door host::call (h05-door). Runs crafted WAT guests as the
snapshot through wasi_python.run(host=..., artifacts=...). Writes only under the scratch work dir
given as argv[1]. No network, no grants, no root."""
import sys, threading, json, struct
from pathlib import Path
import wasmtime
import wasi_python
from wasi_python import _call

work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
real = wasi_python.artifacts()
DOOR = '(import "host" "call" (func $door (param i32 i32 i32 i32) (result i32)))'
results = {}

def module(alloc_body, run_body, extra=""):
    return f"""(module {DOOR}
  (memory (export "memory") 1)
  (global $next (mut i32) (i32.const 4096))
  (global $depth (mut i32) (i32.const 0))
  {extra}
  (func (export "host_alloc") (param $n i32) (result i32) (local $p i32) (local $rc i32)
    {alloc_body})
  (func (export "run") (result i32) (local $rc i32) (local $p i32)
    {run_body}))"""

BUMP = """(local.set $p (global.get $next))
    (global.set $next (i32.add (global.get $next) (local.get $n)))
    (if (i32.gt_u (global.get $next) (i32.const 60000)) (then (global.set $next (i32.const 4096))))
    (local.get $p)"""
STD_RUN = "(call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 104))"
# run returns: rc<0 -> 100-rc ; else the answered length at 104
LEN_RUN = """(local.set $rc (call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 104)))
    (if (i32.lt_s (local.get $rc) (i32.const 0)) (then (return (i32.sub (i32.const 100) (local.get $rc)))))
    (i32.load (i32.const 104))"""

def go(name, wat, host, **kw):
    d = work / name
    d.mkdir(exist_ok=True)
    p = d / "probe.wasm"
    p.write_bytes(wasmtime.wat2wasm(wat))
    found = wasi_python.Artifacts(p, real.plain, real.stdlib_zip, real.manifest)
    calls = []
    def h(req):
        calls.append((len(req), threading.current_thread().name))
        return host(req)
    try:
        done = wasi_python.run([], host=h, artifacts=found, cache_dir=False, **kw)
        r = {"exit_code": done.exit_code, "trapped": done.trapped}
    except BaseException as e:
        r = {"raised": type(e).__module__ + "." + type(e).__name__, "msg": str(e)[:200]}
    r["host_calls"] = len(calls)
    r["host_threads"] = sorted({t for _, t in calls})
    r["main_thread"] = threading.main_thread().name
    results[name] = r
    print(name, json.dumps(r), flush=True)

ok = lambda req: b"cba"
# 1. re-entrant door from host_alloc, bounded depth 3
reent = """(if (i32.lt_u (global.get $depth) (i32.const 3)) (then
      (global.set $depth (i32.add (global.get $depth) (i32.const 1)))
      (drop (call $door (i32.const 16) (i32.const 3) (i32.const 200) (i32.const 204)))))
    """ + BUMP
go("reentrant_depth3", module(reent, LEN_RUN), ok)
# 2. re-entrant door from host_alloc, unbounded
reent_inf = """(drop (call $door (i32.const 16) (i32.const 3) (i32.const 200) (i32.const 204)))
    """ + BUMP
# skipped in run 2 (aborted run 1): go("reentrant_unbounded", module(reent_inf, STD_RUN), ok)
# 3. host_alloc returns a pointer 2 bytes before the end for a 3-byte answer; outs must stay 0
edge = "(i32.const 65534)"
go("alloc_past_end", module(edge, """(local.set $rc (call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 104)))
    (i32.add (i32.mul (i32.sub (i32.const 0) (local.get $rc)) (i32.const 10)) (i32.ne (i32.load (i32.const 100)) (i32.const 0)))"""), ok)
# 4. host_alloc returns exactly the last 3 bytes: allowed
go("alloc_exact_end", module("(i32.const 65533)", LEN_RUN), ok)
# 5. host_alloc grows memory and returns the new page
grow = "(local.set $p (i32.mul (memory.grow (i32.const 1)) (i32.const 65536))) (local.get $p)"
go("alloc_after_grow", module(grow, """(local.set $rc (call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 104)))
    (if (i32.ne (local.get $rc) (i32.const 0)) (then (return (i32.sub (i32.const 100) (local.get $rc)))))
    (i32.add (i32.mul (i32.load (i32.const 100)) (i32.const 0)) (i32.load8_u (i32.load (i32.const 100))))"""), ok)
# 6. request wraps the 32-bit space: ptr=0xFFFFFFFF len=2 -> host never called
go("request_wraps", module(BUMP, "(call $door (i32.const -1) (i32.const 2) (i32.const 100) (i32.const 104))"), ok)
# 7. out_len_ptr past memory -> host never called
go("outptr_past_end", module(BUMP, "(call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 65533))"), ok)
# 8. out_ptr_ptr negative (0xFFFFFFFC)
go("outptr_negative", module(BUMP, "(call $door (i32.const 16) (i32.const 3) (i32.const -4) (i32.const 104))"), ok)
# 9. zero-length frame exactly at the end of memory
go("zero_len_at_end", module(BUMP, LEN_RUN.replace("(i32.const 16) (i32.const 3)", "(i32.const 65536) (i32.const 0)")), ok)
# 10. host_alloc returns 0
go("alloc_null", module("(i32.const 0)", STD_RUN), ok)
# 11. host returns a non-bytes object
go("host_returns_str", module(BUMP, STD_RUN), lambda r: "text")
# 12. host raises RuntimeError with text
go("host_raises_exception", module(BUMP, STD_RUN), lambda r: (_ for _ in ()).throw(RuntimeError("secret text")))
# 13. host raises a wasmtime.Trap (an Exception subclass)
def raise_trap(r):
    raise wasmtime.Trap("from the host")
go("host_raises_trap", module(BUMP, STD_RUN), raise_trap)
# 14. MAX_RESPONSE bypass via a bytes subclass whose __bytes__ is larger (MAX patched to 1000, as the project's own check does)
class Big(bytes):
    def __bytes__(self):
        return b"z" * 5000
_call.MAX_RESPONSE = 1000
go("bytes_subclass_over_max", module(BUMP, LEN_RUN), lambda r: Big(b"ok"))
go("plain_over_max", module(BUMP, LEN_RUN), lambda r: b"z" * 5000)
_call.MAX_RESPONSE = 0x7FFFFFFF
# 15. a bytes subclass whose __len__ lies, returned by __bytes__: which thread runs __len__, and how many bytes are written
seen_len_threads = []
class Liar(bytes):
    def __len__(self):
        seen_len_threads.append(threading.current_thread().name)
        return 1
class Wrap(bytes):
    def __bytes__(self):
        return Liar(b"q" * 3000)
print("bytes(Wrap()) type:", type(bytes(Wrap(b"x"))).__name__, flush=True)
go("len_lies", module(BUMP, LEN_RUN), lambda r: Wrap(b"x"))
results["len_lies"]["__len__threads"] = sorted(set(seen_len_threads))
# 16. host raises KeyboardInterrupt (BaseException): documented to propagate
def kb(r):
    raise KeyboardInterrupt
go("host_raises_keyboardinterrupt", module(BUMP, STD_RUN), kb)
# 17. after all that, a normal real-guest call still works
d = wasi_python.run(["-c", "print('ok')"], cache_dir=False)
results["after"] = {"exit_code": d.exit_code, "stdout": d.stdout.decode()}
print("after", results["after"], flush=True)
(work / "results.json").write_text(json.dumps(results, indent=1))
