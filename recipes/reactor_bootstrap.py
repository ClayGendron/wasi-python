"""The reactor's argument handling: the module `_reactor` (spec 003, Decision 6).

recipes/reactor_main.c calls `run(argv, environ)` once per instance, or
`turn(source, environ, stdin)` once per turn of a session (spec 055, Decision 3), and
`prepare(source, environ)` once in an instance whose memory the host makes a starting image of.
Step 60 compiles this file with the pinned host Python (the guest's own version) and links the
marshalled code into the reactor, so no start compiles it (scripts/freeze_bootstrap.py). Its
frames are named `<reactor>`, which `_report` strips from tracebacks.

Every program runs in a fresh `__main__` made at run time (spec 073): the snapshot's own was made
before `gc.freeze()`, and a file left open beside a function defined in it was never finalized.
A script and `-m` run in that `__main__` itself, as CPython's own entry points run them, not in
runpy's temporary module, which lost such a file on both binaries.

A call from a starting image runs in the image's own `__main__`, the module the host's code ran
in, so a call means what one program of the code and the call's means. It ends through `_end`,
without Python's teardown of every module the image holds: the call's own names are dropped and
collected, so what they held is finalized, and a writer it hung elsewhere is flushed.

A start from a checkpoint, a live session's memory after its turns, is a starting image's call
too: its first run or turn calls `_resume`, which takes the session's `__main__` as the image's
and puts the import path back, and its first turn sets up as a session's first turn does.
"""

import os
import sys

VERSION = (
    f"Python {sys.version.split()[0]} (wasm32-wasip1: numpy's default integer is "
    "32-bit; no threads; no ctypes, mmap, sockets, ssl, zstd or scipy.odr; "
    "compute about 1.3 to 2.3 times slower than native)"
)
IGNORED = {"-I", "-E", "-s", "-B"}
# The names the interpreter gave its own __main__ (Python/pylifecycle.c, add_main_module, and the
# module type): captured once, before any program, so a nested run (spec 054's prelude) cannot
# carry a program's names into the next __main__ (spec 073, Decision 1).
_MAIN_NAMES = dict(sys.modules["__main__"].__dict__)
_BASE_PATH = tuple(sys.path)  # the stdlib zip alone: a start from a checkpoint imports from it
_prepared = False  # the host's code ran here through prepare: this instance is a starting image
_NOTHING = object()
_image_underscore = _NOTHING  # builtins._ as the image holds it
_image_main = None  # the __main__ the host's code ran in


def _fresh_main():
    # A __main__ made after the snapshot's freeze, so the collector frees it at finalization as
    # it frees the plain binary's; the frozen one is dropped (spec 073, Decision 1).
    main = type(sys)("__main__")
    main.__dict__.update(_MAIN_NAMES)
    sys.modules["__main__"] = main
    return main


def _run_file(target, main):
    # A script file as CPython's _PyRun_SimpleFile runs it (Python/pythonrun.c): __file__ and a
    # file loader set in __main__ (SourcelessFileLoader for a .pyc, as set_main_loader), the code
    # run there, and __file__ removed again on every path (spec 073, Decision 2). The code is read
    # as runpy.run_path reads it, so an OSError still rises from runpy's frame (_only_runpy).
    # The loaders come from _frozen_importlib_external, where CPython's set_main_loader takes them
    # (_PyImport_GetImportlibExternalLoader): `from importlib.machinery import ...` would run that
    # module's __getattr__, which imports warnings into every script run (spec 073's build
    # review, B1).
    import _frozen_importlib_external as external
    import runpy

    code = runpy._get_code_from_file(target, "__main__")
    pyc = target.endswith(".pyc")
    loader = external.SourcelessFileLoader if pyc else external.SourceFileLoader
    g = main.__dict__
    g["__file__"] = target
    g["__loader__"] = loader("__main__", target)
    try:
        exec(code, g)
    finally:
        g.pop("__file__", None)


def _refresh(unbuffered):
    # Per call: what a snapshot froze at build time becomes what a fresh interpreter would see.
    rnd = sys.modules.get("random")
    if rnd is not None:
        rnd.seed()
    nprand = sys.modules.get("numpy.random")
    if nprand is not None:
        nprand.seed()
    # A starting image may hold more generators seeded at import: each is seeded afresh, as a
    # fresh import would seed it, and the next temporary name comes from a new sequence.
    tf = sys.modules.get("tempfile")
    if tf is not None:
        tf._name_sequence = None
    sympy_random = sys.modules.get("sympy.core.random")
    if sympy_random is not None:
        sympy_random.seed()  # its two module-level generators
    recipes = sys.modules.get("more_itertools.recipes")
    if recipes is not None:
        recipes._private_randrange.__self__.seed()  # is_prime's private generator
    grower = sys.modules.get("sklearn.ensemble._hist_gradient_boosting.grower")
    if grower is not None:
        for default in grower.TreeGrower.__init__.__defaults__ or ():
            bits = getattr(default, "bit_generator", None)
            if bits is not None:  # the generator a grower made without one uses
                bits.state = type(bits)().state
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
    while tb is not None and tb.tb_frame.f_code.co_filename == "<reactor>":
        tb = tb.tb_next  # run's own helpers (spec 073: _run_file reads the script)
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
    try:
        main = _image_main if _prepared else _fresh_main()
        if mode == "-c":
            sys.argv = ["-c", *rest]
            code = compile(target, "<string>", "exec")
            import linecache  # as CPython's -c: tracebacks show the source line

            linecache._register_code(code, target, "<string>")
            exec(code, main.__dict__)
        elif mode == "-m":
            import runpy

            sys.argv = [target, *rest]
            runpy._run_module_as_main(target)  # CPython's own -m (spec 073, Decision 3)
        elif mode == "script":
            import pkgutil

            sys.argv = [target, *rest]
            if pkgutil.get_importer(target) is None:  # a file, as runpy.run_path tells it
                _run_file(target, main)
            else:  # a directory or a zip, as CPython runs one (Modules/main.c)
                import runpy

                sys.path.insert(0, target)
                runpy._run_module_as_main("__main__", alter_argv=False)
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


# Sessions (spec 055, Decision 3): one interpreter across turns.
_turns = 0  # the turns run in this instance: each one's code is named <turn N>
_quit = False  # set by the session's exit() and quit(), as ipykernel's exiter sets exit_now


def _setup(environ):
    """The first turn's setup, once and unnumbered: the environment, the import path from argv,
    argv as the interactive interpreter has it, exit() and quit() rebound, and the reseed."""
    argv, env = environ
    if env is not None:
        os.environ.clear()
        os.environ.update(env)
    argv = list(argv or [])
    for entry in argv[1:]:
        if entry.startswith("/"):  # absolute, read-only folders only; anything else is skipped
            sys.path.append(entry)
    sys.argv = [""]
    sys.orig_argv = argv[:1]
    import _sitebuiltins
    import builtins

    class _SessionQuitter(_sitebuiltins.Quitter):
        # As site's Quitter, but it asks for the session to end and leaves stdin open.
        def __call__(self, code=None):
            global _quit
            _quit = True
            raise SystemExit(code)

    for name in ("exit", "quit"):
        old = getattr(builtins, name, None)
        eof = getattr(old, "eof", "Ctrl-D (i.e. EOF)")
        setattr(builtins, name, _SessionQuitter(name, eof))
    _refresh(False)


def _run_turn(text, name):
    """Run a turn's source in __main__, echoing a final expression as the interactive
    interpreter does."""
    import ast
    import linecache

    tree = ast.parse(text, name, "exec")
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
    code = compile(tree, name, "exec")
    linecache._register_code(code, text, name)
    main = sys.modules["__main__"].__dict__
    exec(code, main)
    if last is not None:
        expr = compile(last, name, "eval")
        linecache._register_code(expr, text, name)
        sys.displayhook(eval(expr, main))


def _turn_reader(data, old):
    """A text reader over a turn's stdin bytes, with the replaced reader's encoding and errors,
    split at "\\n" as the interpreter's own stdin is on this platform."""
    import io

    return io.TextIOWrapper(
        io.BytesIO(data),
        encoding=getattr(old, "encoding", None) or "utf-8",
        errors=getattr(old, "errors", None) or "strict",
        newline="\n",
    )


def turn(source, environ, stdin=None):
    """One turn: (status, quit). `source` is the code's bytes, or None when the host had no
    memory for them; `environ` is (argv, env) on the first turn, None after. `stdin` is the
    turn's stdin bytes, None when the host gave none (`sys.stdin` is left as it is), or False
    when it had no memory for them. A given stdin is `sys.stdin` for the turn, and the old reader
    comes back at its end unless the turn replaced it."""
    global _turns
    status = 0
    old = given = None
    try:
        if environ is not None:
            _setup(environ)
        _turns += 1
        if source is None:
            raise MemoryError("no memory for this turn's code")
        if stdin is False:
            raise MemoryError("no memory for this turn's stdin")
        if stdin is not None:
            old = sys.stdin
            given = sys.stdin = _turn_reader(stdin, old)
        _run_turn(source.decode("utf-8"), f"<turn {_turns}>")
    except SystemExit as exc:
        status = _exit_code(exc)
    except BaseException as exc:
        _report(exc, False)  # strips the <reactor> frames from exc.__traceback__
        sys.last_exc = exc
        sys.last_type, sys.last_value, sys.last_traceback = type(exc), exc, exc.__traceback__
        status = 1
    finally:
        if given is not None and sys.stdin is given:
            sys.stdin = old
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
    return (status, _quit)


# Starting images: the host's code run once, the instance then imaged by the host.


def prepare(source, environ):
    """Run the host's code in __main__ as the start of a starting image: its exit status. The
    making call's environment and import path serve the code alone: `sys.path` and the importer
    cache are restored after it on every path, so a call from the image imports from its own."""
    global _MAIN_NAMES, _prepared, _image_underscore, _image_main
    argv, env = environ
    path = list(sys.path)
    status = 0
    try:
        os.environ.clear()
        os.environ.update(env)
        for entry in argv[1:]:
            if entry.startswith("/"):  # absolute, read-only folders only, as a session's
                sys.path.append(entry)
        sys.argv = [""]
        sys.orig_argv = list(argv[:1])
        if source is None:
            raise MemoryError("no memory for the code")
        import linecache

        text = source.decode("utf-8")
        code = compile(text, "<snapshot>", "exec")
        linecache._register_code(code, text, "<snapshot>")
        _image_main = sys.modules["__main__"]
        exec(code, _image_main.__dict__)
    except SystemExit as exc:
        status = _exit_code(exc)
    except BaseException as exc:
        _report(exc, False)
        status = 1
    finally:
        sys.path = path
        for key in [k for k in sys.path_importer_cache if k not in path]:
            del sys.path_importer_cache[key]
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
    if status == 0:
        import builtins

        # Every name the code left, double-underscore names too: the end of a call drops
        # exactly what the call bound.
        _MAIN_NAMES = dict(_image_main.__dict__)
        _image_underscore = builtins.__dict__.get("_", _NOTHING)
        _prepared = True
    return status


def _resume():
    """The start of an instance a checkpoint's image was copied into, before its first run or
    turn: the import path the bootstrap began with, and the importer cache without the session's
    other entries, so the start imports only from its own path; the session's `__main__` taken
    as the image's, with every name it holds, so a call's end drops only what the call bound; and
    the session's heap frozen out of the collector's way, as a starting image's is."""
    global _MAIN_NAMES, _prepared, _image_underscore, _image_main
    import builtins
    import gc

    sys.path = list(_BASE_PATH)
    for key in [k for k in sys.path_importer_cache if k not in _BASE_PATH]:
        del sys.path_importer_cache[key]
    _image_main = sys.modules["__main__"]
    _MAIN_NAMES = dict(_image_main.__dict__)
    _image_underscore = builtins.__dict__.get("_", _NOTHING)
    _prepared = True
    gc.freeze()


def _end():
    """The end of a call from a starting image: True, or False when a standard stream could not
    be flushed. The image's frozen heap is left as it is; only the call's own objects are
    walked and collected."""
    import atexit
    import builtins
    import gc

    atexit._run_exitfuncs()
    main = _image_main.__dict__
    for name in [n for n in main if main[n] is not _MAIN_NAMES.get(n, _NOTHING)]:
        del main[name]
    for name in ("last_exc", "last_type", "last_value", "last_traceback"):
        if hasattr(sys, name):
            delattr(sys, name)
    if builtins.__dict__.get("_", _NOTHING) is not _image_underscore:
        builtins.__dict__.pop("_", None)  # a session's last echoed value
    gc.collect()
    _flush_writers(gc.get_objects())
    ok = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            ok = False
    return ok


def _flush_writers(objects):
    """Flush every open text file and buffered writer among `objects`. A writer stacked on another
    (a gzip file's own buffer) pushes bytes into the lower one when it flushes, so the writers'
    pass is repeated while a pass moved any of them, three passes at most."""
    import io

    texts = [o for o in objects if isinstance(o, io.TextIOWrapper)]
    writers = [o for o in objects if isinstance(o, (io.BufferedWriter, io.BufferedRandom))]
    del objects
    for f in texts:
        _flush_one(f)
    for _ in range(3):
        if not any([_flush_one(f) for f in writers]):
            break


def _flush_one(f):
    """Flush `f` if it is open: whether it may have written (always, when its raw stream cannot
    tell its position). An exception is printed as one ignored in a finalizer, and dropped."""
    try:
        if f.closed:
            return False
    except Exception:
        return False  # a detached wrapper
    before = _position(f)
    try:
        f.flush()
    except Exception as exc:
        try:
            print(f"Exception ignored in: {f!r}", file=sys.stderr)
            sys.__excepthook__(type(exc), exc, exc.__traceback__)
        except Exception:
            pass
        return False
    return before is None or _position(f) != before


def _position(f):
    try:
        return f.raw.tell()
    except Exception:
        return None
