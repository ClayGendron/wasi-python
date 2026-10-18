"""Probes for read-only code on the import path (research memo of 2026-10-18).

Run from the repository root, against an artifact set (read only):

    WASI_PYTHON_ARTIFACTS=<set> uv run python \
        context/research/2026-10-18-read-only-code-on-the-import-path/probe.py <scratch dir>

Nothing here changes the runner. Every probe calls today's `wasi_python.run` with an argv the
probe builds itself, which is exactly what a runner-only design would build: a `-c` prelude that
extends `sys.path` and then re-enters the reactor's own argument handling (`_reactor.run`). Each
probe runs on both binaries and prints one line per fact.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

from wasi_python import Grant, Mount, run
from wasi_python.mounts import Errno, Stat

ARGV0 = "/usr/local/bin/python.wasm"


def prelude(entries: list[str]) -> list[str]:
    """The runner-only form: one expression statement that binds no name in __main__."""
    src = (
        f"__import__('sys').path.extend({entries!r}) or "
        f"__import__('sys').exit(__import__('_reactor').run("
        f"[{ARGV0!r}, *__import__('sys').argv[1:]], dict(__import__('os').environ)))"
    )
    return ["-c", src]


def show(tag: str, done, *, stderr_lines: int = 3) -> None:
    out = done.stdout.decode(errors="replace").strip().replace("\n", " | ")
    err = done.stderr.decode(errors="replace").strip().splitlines()
    err_tail = " | ".join(err[-stderr_lines:]) if err else ""
    print(
        f"{tag}: exit={done.exit_code} trapped={done.trapped} fuel={done.fuel_used} "
        f"out=[{out}] err=[{err_tail}]"
    )


def tree(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


def main(scratch: Path) -> None:
    if scratch.exists():
        shutil.rmtree(scratch)
    code = scratch / "code"
    (code / "pkg").mkdir(parents=True)
    (code / "mylib.py").write_text("VALUE = 'mylib from the grant'\n")
    (code / "pkg" / "__init__.py").write_text("NAME = 'pkg'\n")
    (code / "pkg" / "__main__.py").write_text(
        "import sys\nprint('pkg main', sys.argv)\n"
    )
    (code / "main.py").write_text(
        "import sys, mylib\nprint('script', sys.argv, mylib.VALUE)\nraise SystemExit(3)\n"
    )
    (code / "boom.py").write_text("def f():\n    return 1 / 0\nf()\n")
    # Shadows: a stdlib name, a builtin name, a profile package, the guest package's name.
    for name in ("json", "numpy", "host", "csv"):
        (code / name).mkdir()
        (code / name / "__init__.py").write_text(f"SHADOW = 'grant {name}'\n")
    (code / "math.py").write_text("SHADOW = 'grant math'\n")
    (code / "uuid.py").write_text("SHADOW = 'grant uuid'\n")  # stdlib, not pre-imported
    # A zip library in the same grant, with a dist-info for importlib.metadata.
    with zipfile.ZipFile(code / "lib.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("zmod.py", "VALUE = 'zmod from lib.zip'\n")
        z.writestr("zpkg/__init__.py", "")
        z.writestr("zpkg/data.txt", "resource in a zip\n")
        z.writestr("zdist-1.2.dist-info/METADATA", "Metadata-Version: 2.1\nName: zdist\n"
                   "Version: 1.2\n")
    (code / "ddist-3.4.dist-info").mkdir()
    (code / "ddist-3.4.dist-info" / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: ddist\nVersion: 3.4\n"
    )
    before = tree(code)
    ro = Grant(str(code), "/code")

    for snap in (True, False):
        b = "snapshot" if snap else "plain"
        print(f"\n## {b}")

        # P1. Today's import path, flags and the environment's reach.
        done = run(
            ["-c", "import sys, os; print(sys.path, sys.flags.isolated, sys.flags.no_site,"
             " sys.dont_write_bytecode, sys.flags.dont_write_bytecode,"
             " os.environ.get('PYTHONPATH'), [type(h).__name__ for h in sys.path_hooks],"
             " [getattr(f, '__name__', type(f).__name__) for f in sys.meta_path])"],
            grants=[ro], env={"PYTHONPATH": "/code"}, snapshot=snap,
        )
        show(f"P1 {b} path-and-flags (PYTHONPATH=/code in env)", done)
        done = run(["-c", "import mylib"], grants=[ro], env={"PYTHONPATH": "/code"},
                   snapshot=snap)
        show(f"P1 {b} import mylib with PYTHONPATH only", done, stderr_lines=1)

        # P2. The prelude, in each of the reactor's modes.
        p = prelude(["/code"])
        cases = {
            "-c": ["-c", "import sys, mylib; print(mylib.VALUE, sys.argv, sys.path[-1])", "a1"],
            "-m": ["-m", "pkg", "x", "y"],
            "script": ["/code/main.py", "s1"],
            "-V": ["-V"],
            "-u -c": ["-u", "-c", "print('unbuffered ok')"],
            "orig_argv": ["-c", "import sys; print(sys.orig_argv[1:])", "q"],
            "main names": ["-c", "print(sorted(k for k in dir() if not k.startswith('__')))"],
            "sys.exit(7)": ["-c", "import sys; sys.exit(7)"],
            "exit msg": ["-c", "raise SystemExit('bye')"],
            "-c 1/0": ["-c", "1/0"],
            "script boom": ["/code/boom.py"],
            "missing script": ["/code/nope.py"],
            "stack depth": ["-c", "import traceback; print(len(traceback.extract_stack()))"],
        }
        for name, argv in cases.items():
            show(f"P2 {b} without prelude {name}", run(argv, grants=[ro], snapshot=snap))
            show(f"P2 {b} with prelude    {name}", run(p + argv, grants=[ro], snapshot=snap))
        done = run(p, grants=[ro], snapshot=snap,
                   stdin=b"import mylib, sys; print('stdin', mylib.VALUE, sys.argv)\n")
        show(f"P2 {b} with prelude    stdin", done)
        for argv in (["-c", "pass"], ["-c", "import mylib"]):
            a = run(argv, grants=[ro], snapshot=snap, fuel=10**12)
            c = run(p + argv, grants=[ro], snapshot=snap, fuel=10**12)
            print(f"P2 {b} fuel {argv[1]!r}: without={a.fuel_used} with={c.fuel_used} "
                  f"exit={a.exit_code},{c.exit_code}")

        # P3. Bytecode: nothing written to a read-only grant, even when a program asks.
        prog = "import mylib, pkg; print(mylib.VALUE, pkg.NAME)"
        show(f"P3 {b} import from grant", run(p + ["-c", prog], grants=[ro], snapshot=snap))
        prog2 = "import sys; sys.dont_write_bytecode = False\n" + prog
        show(f"P3 {b} import with dont_write_bytecode=False",
             run(p + ["-c", prog2], grants=[ro], snapshot=snap))
        print(f"P3 {b} grant unchanged on the host: {tree(code) == before}")
        w = scratch / f"w-{b}"
        w.mkdir()
        (w / "wmod.py").write_text("X = 1\n")
        prog3 = "import sys; sys.path.append('/w'); import wmod; print(wmod.X)"
        run(["-c", prog3], grants=[Grant(str(w), "/w", writable=True)], snapshot=snap)
        print(f"P3 {b} writable folder after an import, default flag: {tree(w)}")
        prog4 = "import sys; sys.dont_write_bytecode = False; sys.path.append('/w'); import wmod"
        run(["-c", prog4], grants=[Grant(str(w), "/w", writable=True)], snapshot=snap)
        print(f"P3 {b} writable folder after an import, flag False: {tree(w)}")
        # A valid .pyc in a read-only grant is read: compile it in the guest, then change the
        # source to the same size and restore its times, so only the .pyc can say X = 1.
        shutil.rmtree(w / "__pycache__", ignore_errors=True)
        run(["-c", "import py_compile; py_compile.compile('/w/wmod.py')"],
            grants=[Grant(str(w), "/w", writable=True)], snapshot=snap)
        st = (w / "wmod.py").stat()
        (w / "wmod.py").write_text("X = 2\n")
        os.utime(w / "wmod.py", ns=(st.st_atime_ns, st.st_mtime_ns))
        done = run(prelude(["/w"]) + ["-c", "import wmod; print(wmod.X, wmod.__spec__.cached)"],
                   grants=[Grant(str(w), "/w")], snapshot=snap)
        show(f"P3 {b} a valid .pyc in a read-only grant is used (1 = from .pyc)", done)

        # P4. A zip in the grant, resources and metadata.
        pz = prelude(["/code", "/code/lib.zip"])
        prog = (
            "import zmod, zpkg, importlib.resources as r, importlib.metadata as m\n"
            "print(zmod.VALUE, type(zmod.__loader__).__name__, zmod.__file__)\n"
            "print(r.files('zpkg').joinpath('data.txt').read_text().strip())\n"
            "print(m.version('zdist'), m.version('ddist'))\n"
        )
        show(f"P4 {b} zip on the path", run(pz + ["-c", prog], grants=[ro], snapshot=snap))

        # P5. invalidate_caches, and a file the host adds mid-call (through the door).
        def host(frame: bytes) -> bytes:
            (code / "late.py").write_text("V = 'late'\n")
            return b"ok"

        prog = (
            "import importlib, _host\n"
            "_host.call(b'write')\n"
            "try:\n    import late; print('seen without invalidate', late.V)\n"
            "except ImportError as e: print('not seen:', e)\n"
            "importlib.invalidate_caches()\n"
            "import late; print('after invalidate', late.V)\n"
        )
        done = run(p + ["-c", prog], grants=[ro], snapshot=snap, host=host)
        show(f"P5 {b} host adds late.py mid-call", done)
        (code / "late.py").unlink()
        before = tree(code)
        a = run(p + ["-c", "import mylib"], grants=[ro], snapshot=snap, fuel=10**12)
        c = run(p + ["-c", "import mylib, importlib; importlib.invalidate_caches()"],
                grants=[ro], snapshot=snap, fuel=10**12)
        print(f"P5 {b} fuel of invalidate_caches(): {c.fuel_used - a.fuel_used}")

        # P6. Shadowing: appended after the zip, then (for contrast) inserted before it.
        prog = (
            "import json, math, numpy, csv, uuid, host, mylib\n"
            "for m in (json, math, numpy, csv, uuid, host):\n"
            "    print(m.__name__, getattr(m, 'SHADOW', 'runtime'))\n"
        )
        show(f"P6 {b} appended", run(p + ["-c", prog], grants=[ro], snapshot=snap),
             stderr_lines=1)
        before_zip = ["-c", "import sys; sys.path.insert(0, '/code')\n" + prog]
        show(f"P6 {b} inserted before the zip",
             run(before_zip, grants=[ro], snapshot=snap), stderr_lines=1)

        # P7. A read-only mount on the path: provider calls per import.
        files = {
            "/": None,
            "/mlib.py": b"VALUE = 'mlib from a mount'\n",
            "/mpkg": None,
            "/mpkg/__init__.py": b"",
        }

        class Mem:
            def stat(self, path):
                if path not in files:
                    return Errno.ENOENT
                data = files[path]
                return Stat("dir") if data is None else Stat("file", len(data), 1)

            def list(self, path):
                if path not in files or files[path] is not None:
                    return Errno.ENOTDIR
                pre = path.rstrip("/") + "/"
                return [
                    (k[len(pre):], "dir" if v is None else "file")
                    for k, v in files.items()
                    if k != path and k.startswith(pre) and "/" not in k[len(pre):]
                ]

            def read(self, path):
                data = files.get(path, Errno.ENOENT)
                return Errno.EISDIR if data is None else data

        pm = prelude(["/m"])
        for prog in ("pass", "import json", "import mlib, mpkg; print(mlib.VALUE)",
                     "import nosuch1"):
            done = run(pm + ["-c", prog], mounts=[Mount(Mem(), "/m")], snapshot=snap)
            calls = {k: v for k, v in done.files.calls.items() if v}
            show(f"P7 {b} mount {prog!r} calls={calls}", done, stderr_lines=1)

        # P8. Why writable places must not lie under an import path entry.
        proj = scratch / f"proj-{b}"
        (proj / "out").mkdir(parents=True)
        out_rw = Grant(str(proj / "out"), "/out", writable=True)
        run(["-c", "open('/out/evil.py','w').write('print(\"planted code ran\")')"],
            grants=[out_rw], snapshot=snap)
        done = run(prelude(["/code2"]) + ["-c", "import out.evil"],
                   grants=[Grant(str(proj), "/code2")], snapshot=snap)
        show(f"P8 {b} host nesting: a later call imports what an earlier one wrote", done)
        (proj / "out" / "evil.py").unlink()
        nest = Grant(str(proj / "out"), "/code2/out", writable=True)
        done = run(prelude(["/code2"]) + ["-c",
                   "open('/code2/out/evil.py','w').write('print(\"planted code ran\")')\n"
                   "import out.evil"],
                   grants=[Grant(str(proj), "/code2"), nest], snapshot=snap)
        show(f"P8 {b} guest nesting: a writable grant under the entry", done)
        (proj / "out" / "evil.py").unlink()

        # P9. A writable root and a read-only grant on the path: the grant serves its prefix.
        done = run(p + ["-c", "import mylib; print(mylib.__file__)\n"
                        "open('/code/x.py', 'w')"], grants=[ro], root=True, snapshot=snap)
        show(f"P9 {b} root=True, entry /code", done, stderr_lines=1)

        # P10. Entries that do not exist, or are not importable, are skipped as CPython skips
        # them; a quote in a guest path survives the prelude's literal.
        odd = code / "it's here"
        odd.mkdir(exist_ok=True)
        (odd / "q.py").write_text("V = 'quoted'\n")
        done = run(prelude(["/code/missing.zip", "/code/mylib.py", "/code/it's here"])
                   + ["-c", "import q, sys; print(q.V, sys.path_importer_cache.get("
                      "'/code/missing.zip'), sys.path_importer_cache.get('/code/mylib.py'))"],
                   grants=[ro], snapshot=snap)
        show(f"P10 {b} missing and non-zip entries", done, stderr_lines=1)
        shutil.rmtree(odd)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
