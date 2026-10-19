"""Relink python.wasm with a different PREIMPORT, from step 60's recorded commands (read-only use
of the main tree's build). Usage: relink.py <variant dir> <preimport string>."""
import shlex, subprocess, sys, pathlib
HERE = pathlib.Path("/Users/claygendron/Git/Repos/wasi_python")
W = HERE / "build/Python-3.15.0/cross-build/wasm32-wasip1"
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
pre = sys.argv[2]
compile_line, link_line = (HERE / "build/link/reactor-commands.txt").read_text().splitlines()[:2]
c = shlex.split(compile_line)
i = c.index("-o"); c[i + 1] = str(out / "reactor_main.o")
c.insert(i, f'-DPREIMPORT="{pre}"')
l = shlex.split(link_line)
l = [f"-Wl,--Map={out / 'python.map'}" if a.startswith("-Wl,--Map=") else a for a in l]
i = l.index("-o"); l[i + 1] = str(out / "python.wasm")
l = [str(out / "reactor_main.o") if a == "Modules/reactor_main.o" else a for a in l]
(out / "preimport.txt").write_text(pre + "\n")
for cmd in (c, l):
    r = subprocess.run(cmd, cwd=W, capture_output=True, text=True)
    (out / "relink.log").open("a").write(r.stdout + r.stderr)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd[:3])}...\n{r.stderr[-2000:]}")
print("ok", out / "python.wasm", (out / "python.wasm").stat().st_size)
