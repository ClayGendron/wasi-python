import sys
from pathlib import Path
from wasi_python import Grant, Session, run
S = Path(sys.argv[1])
code = "import rich, faker, slugify, importlib.metadata as m; print(rich.__file__, m.version('faker'))"
d = run(["-c", code], grants=[Grant(S / "lib-target", "/lib")], import_path=["/lib"], fuel=100_000_000_000)
print("uv --target folder:", d.exit_code, f"{d.fuel_used:,}", d.stdout.decode().strip(), d.stderr.decode().strip()[-200:])
with Session(grants=[Grant(S / "lib-compiled", "/lib")], import_path=["/lib"], fuel=100_000_000_000) as s:
    a = s.run("import io, rich; from rich.console import Console")
    b = s.run("buf = io.StringIO(); Console(file=buf, width=30, color_system=None).print('[b]x[/b]'); print(buf.getvalue().strip())")
    print("session: turn 1 fuel", f"{a.fuel_used:,}", "turn 2 fuel", f"{b.fuel_used:,}", b.stdout.decode().strip(), a.stderr.decode()[-100:], b.stderr.decode()[-100:])
