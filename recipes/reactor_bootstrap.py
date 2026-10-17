"""The reactor's argument handling: the module `_reactor` (spec 003, Decision 6).

recipes/reactor_main.c calls `run(argv, environ)` once per instance. Step 60 compiles this file with
the pinned host Python (the guest's own version) and links the marshalled code into the reactor, so no
start compiles it (scripts/freeze_bootstrap.py). Its frames are named `<reactor>`, which `_report`
strips from tracebacks.
"""

import os
import sys

VERSION = (
    f"Python {sys.version.split()[0]} (wasm32-wasip1: numpy's default integer is "
    "32-bit; no threads; no ctypes, mmap, sockets, ssl, sqlite3, bz2 or lzma; "
    "compute about 1.3 to 2.3 times slower than native)"
)
IGNORED = {"-I", "-E", "-s", "-B"}


def _refresh(unbuffered):
    # Per call: what a snapshot froze at build time becomes what a fresh interpreter would see.
    rnd = sys.modules.get("random")
    if rnd is not None:
        rnd.seed()
    nprand = sys.modules.get("numpy.random")
    if nprand is not None:
        nprand.seed()
    lg = sys.modules.get("logging")
    if lg is not None:
        import time

        lg._startTime = time.time()
    zi = sys.modules.get("zoneinfo")
    if zi is not None and "PYTHONTZPATH" in os.environ:
        zi.reset_tzpath()
    if unbuffered:
        # As CPython's -u: text written straight through to the raw file, no buffer between.
        import io

        for name, fd in (("stdout", 1), ("stderr", 2)):
            old = getattr(sys, name)
            old.flush()
            new = io.TextIOWrapper(
                io.FileIO(fd, "w", closefd=False),
                encoding=old.encoding,
                errors=old.errors,
                write_through=True,
            )
            setattr(sys, name, new)
            setattr(sys, f"__{name}__", new)
    elif not sys.stdout.line_buffering and sys.stdout.isatty():
        sys.stdout.reconfigure(line_buffering=True)


def _exit_code(exc):
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code & 0xFF
    print(code, file=sys.stderr)
    return 1


def _report(exc, script):
    # As CPython's own entry points do: the user's frames only, through sys.excepthook.
    strip = {"<reactor>"}
    runpy = sys.modules.get("runpy")
    if script and runpy is not None:
        strip.add(runpy.run_path.__code__.co_filename)
    tb = exc.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_filename in strip:
        tb = tb.tb_next
    exc.__traceback__ = tb  # the default hook prints the exception's own traceback
    try:
        sys.excepthook(type(exc), exc, tb)
    except BaseException as hook_exc:
        print("Error in sys.excepthook:", file=sys.stderr)
        sys.__excepthook__(type(hook_exc), hook_exc, hook_exc.__traceback__)
        print("\nOriginal exception was:", file=sys.stderr)
        sys.__excepthook__(type(exc), exc, tb)


def _only_runpy(tb):
    # The script could not be opened: every frame below the reactor's is runpy's own.
    runpy = sys.modules.get("runpy")
    name = runpy.run_path.__code__.co_filename if runpy is not None else None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename != name:
            return False
        tb = tb.tb_next
    return True


def run(argv, environ):
    sys.orig_argv = list(argv)
    os.environ.clear()
    os.environ.update(environ)
    args = argv[1:]
    mode, target, rest, unbuffered = "stdin", None, [], False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-c", "-m"):
            if i + 1 >= len(args):
                print(f"Argument expected for the {a} option", file=sys.stderr)
                return 2
            mode, target, rest = a, args[i + 1], args[i + 2 :]
            break
        if a in ("-V", "--version"):
            print(VERSION)
            return 0
        if a == "-X":
            i += 2
            continue
        if a.startswith("-X") or a in IGNORED:
            i += 1
            continue
        if a == "-u":
            unbuffered = True
            i += 1
            continue
        if a == "-":
            mode, target, rest = "stdin", "-", args[i + 1 :]
            break
        if a.startswith("-"):
            print(f"unknown option {a}", file=sys.stderr)
            return 2
        mode, target, rest = "script", a, args[i + 1 :]
        break
    _refresh(unbuffered)
    main = sys.modules["__main__"]
    try:
        if mode == "-c":
            sys.argv = ["-c", *rest]
            code = compile(target, "<string>", "exec")
            import linecache  # as CPython's -c: tracebacks show the source line

            linecache._register_code(code, target, "<string>")
            exec(code, main.__dict__)
        elif mode == "-m":
            import runpy

            sys.argv = [target, *rest]
            runpy.run_module(target, run_name="__main__", alter_sys=True)
        elif mode == "script":
            import runpy

            sys.argv = [target, *rest]
            runpy.run_path(target, run_name="__main__")
        else:
            sys.argv = [target or "", *rest]
            exec(compile(sys.stdin.read(), "<stdin>", "exec"), main.__dict__)
        return 0
    except SystemExit as exc:
        return _exit_code(exc)
    except OSError as exc:
        if mode == "script" and _only_runpy(exc.__traceback__.tb_next):
            print(
                f"{argv[0] if argv else 'python'}: can't open file {target!r}: "
                f"[Errno {exc.errno}] {exc.strerror}",
                file=sys.stderr,
            )
            return 2
        _report(exc, mode == "script")
        return 1
    except BaseException as exc:
        _report(exc, mode == "script")
        return 1
    finally:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
