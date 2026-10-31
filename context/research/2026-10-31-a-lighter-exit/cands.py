"""The lighter exits, as Python run after the program, in place of the reactor's unfreeze and
Py_FinalizeEx. The wrapper runs the program through _reactor.run, as the C side does, then either
raises SystemExit(rc) (RUN 0: today's ending follows) or runs one candidate and leaves by
os._exit. Every variant compiles the same text, so their fuel differs only by what runs."""
WRAP = r'''
import _reactor, sys, os, gc, atexit, weakref
RUN = int("@RUN@")
NOTHING = object()
BASE = set(sys.modules)
def flush_std():
    ok = True
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception:
            ok = False
    return ok
def drop_main():
    main = sys.modules["__main__"].__dict__
    keep = _reactor._MAIN_NAMES
    for n in [n for n in main if main[n] is not keep.get(n, NOTHING)]:
        del main[n]
    for n in ("last_exc", "last_type", "last_value", "last_traceback"):
        if hasattr(sys, n):
            delattr(sys, n)
def wipe(d):
    for k in list(d):
        if k[:1] == "_" and k[:2] != "__":
            d[k] = None
    for k in list(d):
        if k != "__builtins__":
            d[k] = None
def young_modules():
    names = ["__main__"] + [n for n in sys.modules if n not in BASE]
    refs = []
    for n in names:
        m = sys.modules.get(n)
        if m is None:
            continue
        try:
            refs.append(weakref.ref(m))
        except TypeError:
            pass
        sys.modules[n] = None
    m = None
    gc.collect()
    for r in reversed(refs):
        m = r()
        if m is not None:
            wipe(m.__dict__)
    m = None
    gc.collect()
HOOKED = []
sys.addaudithook(lambda e, a: HOOKED.append(1) if e == "sys.addaudithook" else None)
INERT_MODULES = {"builtins", "_abc", "itertools", "_csv", "csv", "_struct", "re", "_sre", "re._compiler", "collections", "_collections", "functools", "_functools", "operator", "types", "typing", "weakref", "_weakref", "_weakrefset", "_frozen_importlib", "_frozen_importlib_external", "zipimport", "enum", "inspect", "_json", "json", "json.decoder", "json.encoder", "json.scanner", "_thread", "abc", "_colorize", "dataclasses", "linecache", "codecs", "encodings", "_reactor"}
def nothing_to_finalize():
    import io
    if HOOKED or gc.callbacks or sys.gettrace() or sys.getprofile():
        return "hook"
    if any(sys.monitoring.get_tool(i) for i in range(6)):
        return "monitoring"
    std = set()
    for s in (sys.__stdin__, sys.__stdout__, sys.__stderr__):
        b = getattr(s, "buffer", None)
        std.update(id(x) for x in (s, b, getattr(b, "raw", None)) if x is not None)
    for o in gc.get_objects():
        t = type(o)
        if id(o) in std or t is io.StringIO or t is io.BytesIO:
            continue
        if isinstance(o, weakref.ref):
            cb = o.__callback__
            if cb is not None and getattr(cb, "__module__", None) not in ("weakref", "_weakrefset", None):
                return "weakref callback " + repr(cb)[:60]
            continue
        if t is type:
            if not o.__flags__ & (1 << 14) and any("__del__" in c.__dict__ for c in o.__mro__ if c.__module__ != "builtins"):
                return "a class with __del__ whose instances are untracked"
            continue
        if isinstance(o, io.IOBase) and o.closed:
            continue
        if hasattr(t, "__del__"):
            return "finalizer " + t.__qualname__
        mods = {getattr(c, "__module__", "?") for c in t.__mro__}
        bad = [m for m in mods if m not in INERT_MODULES and not (getattr(sys.modules.get(m), "__file__", "") or "").endswith((".py", ".pyc")) and m != "__main__"]
        if bad:
            return "extension type " + t.__module__ + "." + t.__qualname__
    return None
@PRE@
rc = _reactor.run(@ARGV@, dict(os.environ))
if RUN == 1:  # X: flush the standard streams and leave
    os._exit(rc if flush_std() else 120)
if RUN == 2:  # A: atexit, flush, the program's __main__ dropped, a collection of the young heap
    atexit._run_exitfuncs(); flush_std(); drop_main(); gc.collect()
    os._exit(rc if flush_std() else 120)
if RUN == 3:  # AW: A, then every open writer flushed, as _reactor._end ends an image's call
    atexit._run_exitfuncs(); flush_std(); drop_main(); gc.collect()
    _reactor._flush_writers(gc.get_objects())
    os._exit(rc if flush_std() else 120)
if RUN == 4:  # B: atexit, flush, __main__ and the modules imported since the start torn down
    atexit._run_exitfuncs(); flush_std(); gc.collect(); young_modules()
    os._exit(rc if flush_std() else 120)
if RUN == 5:  # BW: B, then every open writer flushed
    atexit._run_exitfuncs(); flush_std(); gc.collect(); young_modules()
    _reactor._flush_writers(gc.get_objects())
    os._exit(rc if flush_std() else 120)
if RUN == 6:  # F: atexit and flush; leave at once when nothing is left to finalize, else today's ending
    atexit._run_exitfuncs()
    ok = True
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception as x:
            ok = False
            print("Exception ignored on flushing sys." + ("stdout" if s is sys.stdout else "stderr") + ":", file=sys.__stderr__)
            print(type(x).__name__ + ": " + str(x), file=sys.__stderr__)
    why = nothing_to_finalize()
    if os.environ.get("LX_WHY"):
        print("why:", why, file=sys.__stderr__)
    if why is None:
        for s in (sys.__stdout__, sys.__stderr__):
            try:
                s.flush()
            except Exception:
                pass
        os._exit(rc if ok else 120)
if RUN == 7:  # G: the collector switched off, so the shutdown's first collection is skipped
    gc.disable()
raise SystemExit(rc)
'''

NAMES = {0: "today", 1: "X flush+exit", 2: "A young", 3: "AW young+writers", 4: "B young modules", 5: "BW young modules+writers", 6: "F skip if nothing to finalize", 7: "G gc.disable"}
def wrapper(run, mode, prog):
    if mode == "c":
        argv, pre = ["python", "-c", prog], ""
    elif mode == "script":
        argv, pre = ["python", "/prog.py"], ""
    else:
        argv, pre = ["python", "-m", "prog"], 'sys.path.insert(0, "/")'
    return WRAP.replace("@RUN@", str(run)).replace("@PRE@", pre).replace("@ARGV@", repr(argv))
