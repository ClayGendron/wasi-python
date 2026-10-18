"""Drive the judge's own guest driver (tests/harness/guest.py, wasmtime-py 49.0.0) and the Rust
spike over the same jobs, and compare exit code, stdout, stderr, written files and exact fuel.

Run from anywhere:
    uv run --frozen --project <repo> python compare.py <rust-binary> <label> [job ...]

Judge mode: both sides use Config(consume_fuel) only, the stdlib zip at /usr/local/lib, a fresh
root at /, and the judge's fixed random and clock streams. The Rust side gets a layout built the
same way as guest.run builds its own (same order of grants, same argv and env).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/sets/s-8eb9e35734deeb21"
SPIKE = REPO / "build/rust-spike"
sys.path.insert(0, str(REPO / "tests"))

from harness import guest, jobs  # noqa: E402

PY_VERSION = "3.15.0"
REPEATS = int(os.environ.get("REPEATS", "3"))
COLLECTOR = os.environ.get("COLLECTOR") or None  # "drc": wasmtime-py's collector
EPOCH = os.environ.get("EPOCH") == "1"  # the Rust side with epoch_interruption on (the runner's Config)
STDLIB = SET / "python-stdlib.zip"
BIN = {"plain": SET / "python.wasm", "snapshot": SET / "python-snapshot.wasm"}
MPL_ENV = {"MPLCONFIGDIR": "/mplconfig"}


def job_files(job: str) -> dict[str, bytes]:
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes()}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    return files


def golden(job: str, which: str) -> dict:
    files = {**job_files(job), "/out/.keep": b""}
    argv = [f"/jobs/{job}.py", "/data", "/out"]
    return dict(which=which, argv=argv, files=files, golden=job)


PLOT_FILES = {**job_files("plot_line"), "/out/.keep": b"", "/png/.keep": b""}

RO_RW = """
import os
print(sorted(os.listdir('/ro')))
print(open('/ro/in.txt').read())
try:
    open('/ro/new.txt', 'w').write('no')
    print('ro write: allowed')
except OSError as e:
    print('ro write:', type(e).__name__, e.errno)
open('/rw/out.txt', 'w').write('written by the guest\\n')
print('rw write: ok')
"""

JOBS: dict[str, dict] = {
    "hello-plain": dict(which="plain", argv=["-c", "print('hello')"]),
    "hello-snapshot": dict(which="snapshot", argv=["-c", "print('hello')"]),
    "numpy_csv-plain": golden("numpy_csv", "plain"),
    "pandas_csv-plain": golden("pandas_csv", "plain"),
    "numpy_random-plain": golden("numpy_random", "plain"),
    "compress-plain": golden("compress", "plain"),
    "sqlite-plain": golden("sqlite", "plain"),
    "callbacks-snapshot": golden("callbacks", "snapshot"),
    "pandas_tz-snapshot": golden("pandas_tz", "snapshot"),
    "plot_line-snapshot": dict(
        which="snapshot",
        argv=["/jobs/plot_line.py", "/data", "/out", "/png/plot.png"],
        files=PLOT_FILES,
        env=MPL_ENV,
        mpl_data=True,
        golden="plot_line",
    ),
    "exit3-stderr-plain": dict(
        which="plain",
        argv=["-c", "import sys; sys.stderr.write('boom\\n'); print('out'); sys.exit(3)"],
    ),
    "zerodiv-snapshot": dict(which="snapshot", argv=["-c", "print('before'); 1/0"]),
    "env-argv-snapshot": dict(
        which="snapshot",
        argv=["-c", "import os, sys; print(sys.argv); print(os.environ['SPIKE'])", "a", "b c"],
        env={"SPIKE": "yes", "ZED": "1"},
    ),
    "grants-ro-rw-snapshot": dict(which="snapshot", argv=["-c", RO_RW], grants=True),
    # Not in the default sample: a probe of fd_readdir alone (spec 048's 49.0.2/49.0.3 change).
    "listdir-snapshot": dict(
        which="snapshot",
        argv=["-c", "import os\nd='/usr/local/lib/python315.zip/matplotlib/mpl-data/fonts/ttf'\n"
              "n=sum(len(os.listdir(d)) for _ in range(20)); print(n)"],
        mpl_data=True,
    ),
    "stat-snapshot": dict(
        which="snapshot",
        argv=["-c", "import os\nd='/usr/local/lib/python315.zip/matplotlib/mpl-data/fonts/ttf'\n"
              "print(sum(os.stat(d).st_size > -1 for _ in range(2000)))"],
        mpl_data=True,
    ),
    "mpl-fontcache-snapshot": dict(
        which="snapshot",
        argv=["-c", "import matplotlib; matplotlib.use('agg'); import matplotlib.pyplot as plt; print('ok')"],
        env=MPL_ENV, mpl_data=True,
    ),
    "mpl-savefig-snapshot": dict(
        which="snapshot",
        argv=["-c", "import matplotlib; matplotlib.use('agg'); import matplotlib.pyplot as plt\n"
              "fig, ax = plt.subplots(); ax.plot([1, 2, 3]); ax.set_title('t')\n"
              "fig.canvas.draw(); print('drawn')"],
        env=MPL_ENV, mpl_data=True,
    ),
    "fuel-trap-startup-plain": dict(which="plain", argv=["-c", "print(1)"], fuel=50_000_000),
    "fuel-trap-loop-snapshot": dict(
        which="snapshot", argv=["-c", "while True: pass"], fuel=1_000_000_000
    ),
}


PROBES = ("listdir-snapshot", "stat-snapshot", "mpl-fontcache-snapshot", "mpl-savefig-snapshot")


def grant_dirs(base: Path) -> list[tuple[str, Path, bool]]:
    ro, rw = base / "grant-ro", base / "grant-rw"
    ro.mkdir(parents=True, exist_ok=True)
    rw.mkdir(parents=True, exist_ok=True)
    (ro / "in.txt").write_text("read-only input\n")
    return [("/ro", ro, False), ("/rw", rw, True)]


def render_out(root: Path, out_name: str = "out") -> bytes:
    d = root / out_name
    return jobs.render(b"", d) if d.is_dir() else b""


def golden_ok(spec: dict, stdout: bytes, root: Path) -> bool | None:
    """Whether the rendered output equals the job's golden (tests/jobs/<job>.expected)."""
    job = spec.get("golden")
    if job is None:
        return None
    parts = [stdout]
    out = root / "out"
    for f in sorted(p for p in out.rglob("*") if p.is_file() and p.name != ".keep"):
        parts.append(f"=== {f.relative_to(out).as_posix()}\n".encode())
        parts.append(f.read_bytes())
    return jobs.compare(jobs.expected_path(job).read_bytes(), b"".join(parts)) is None


def files_digest(root: Path, spec: dict) -> dict[str, str]:
    """Every file under the root that the job did not put there: the guest's writes."""
    import hashlib

    given = {p.lstrip("/") for p in spec.get("files", {})}
    out = {}
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = f.relative_to(root).as_posix()
        if rel in given or rel.startswith("mplconfig/"):
            continue
        out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    return out


def run_python(name: str, spec: dict, work: Path) -> dict:
    extra = grant_dirs(work / f"py-{name}") if spec.get("grants") else None
    t = time.perf_counter()
    r = guest.run(
        BIN[spec["which"]],
        spec["argv"],
        workdir=work,
        python_version=PY_VERSION,
        stdlib=STDLIB,
        files=spec.get("files"),
        env=spec.get("env"),
        fuel=spec.get("fuel", guest.DEFAULT_FUEL),
        preopens=extra,
        mpl_data=spec.get("mpl_data", False),
    )
    wall = time.perf_counter() - t
    written = files_digest(r.root, spec)
    if extra:
        written.update({f"[rw]/{k}": v for k, v in files_digest(extra[1][1], {}).items()})
    return dict(
        exit_code=r.exit_code,
        trapped=r.trapped,
        trap_cause=r.trap_cause,
        fuel=r.fuel,
        stdout=r.stdout,
        stderr=r.stderr,
        written=written,
        golden=golden_ok(spec, r.stdout, r.root),
        wall_s=round(wall, 2),
    )


def layout_for_rust(name: str, spec: dict, base: Path) -> dict:
    """The same layout guest.run makes (root, root/usr/local/lib, lib/python315.zip, files, the
    mpl-data grant), with the grants in the same order."""
    root, io, lib = base / "root", base / "io", base / "lib"
    (root / "usr/local/lib").mkdir(parents=True)
    io.mkdir()
    zname = guest.stdlib_name(PY_VERSION, STDLIB)
    lib.mkdir()
    os.link(STDLIB, lib / zname)
    for gp, content in (spec.get("files") or {}).items():
        dest = root / gp.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    preopens = [[str(lib), "/usr/local/lib", False]]
    if spec.get("mpl_data"):
        data = guest.mpl_data_dir(STDLIB, base.parent)
        preopens.append([str(data), f"/usr/local/lib/{zname}/matplotlib/mpl-data", False])
    preopens.append([str(root), "/", True])
    extra = grant_dirs(base) if spec.get("grants") else []
    for gp, host, w in extra:
        preopens.append([str(host), gp, w])
    return dict(
        id=name,
        wasm=str(BIN[spec["which"]]),
        argv=[guest.ARGV0, *spec["argv"]],
        env=sorted((spec.get("env") or {}).items()),
        preopens=preopens,
        fuel=spec.get("fuel", guest.DEFAULT_FUEL),
        mode="judge",
        stdout_path=str(io / "stdout"),
        stderr_path=str(io / "stderr"),
        _root=str(root),
        _rw=str(extra[1][1]) if extra else None,
    )


def run_rust(binary: Path, names: list[str], work: Path) -> dict[str, dict]:
    batch_jobs = []
    for k in range(REPEATS):
        for n in names:
            base = work / f"rs-{n}-{k}"
            batch_jobs.append(layout_for_rust(f"{n}#{k}", JOBS[n], base))
    batch = dict(consume_fuel=True, epoch_interruption=EPOCH, collector=COLLECTOR, jobs=batch_jobs)
    t = time.perf_counter()
    p = subprocess.run(
        [str(binary)], input=json.dumps(batch).encode(), capture_output=True, check=False
    )
    wall = time.perf_counter() - t
    if p.returncode != 0:
        raise SystemExit(f"rust runner exited {p.returncode}: {p.stderr.decode()[-2000:]}")
    out = {}
    for line in p.stdout.decode().splitlines():
        o = json.loads(line)
        j = next(j for j in batch_jobs if j["id"] == o["id"])
        if "error" in o:
            out[o["id"]] = dict(error=o["error"])
            continue
        root = Path(j["_root"])
        written = files_digest(root, JOBS[o["id"].split("#")[0]])
        if j["_rw"]:
            written.update({f"[rw]/{k}": v for k, v in files_digest(Path(j["_rw"]), {}).items()})
        out[o["id"]] = dict(
            exit_code=o["exit_code"],
            trapped=o["trapped"],
            trap_cause=o["trap_cause"],
            fuel=o["fuel_used"],
            stdout=Path(j["stdout_path"]).read_bytes(),
            stderr=Path(j["stderr_path"]).read_bytes(),
            written=written,
            golden=golden_ok(JOBS[o["id"].split("#")[0]], Path(j["stdout_path"]).read_bytes(), root),
            module_ms=o["module_ms"],
            module_from=o["module_from"],
            run_ms=o["run_ms"],
        )
    out["_wall_s"] = round(wall, 2)
    return out


def main() -> None:
    binary = Path(sys.argv[1])
    label = sys.argv[2]
    names = sys.argv[3:] or [n for n in JOBS if n not in PROBES]
    work = SPIKE / "work" / f"{label}-{int(time.time())}"
    work.mkdir(parents=True)
    t = time.perf_counter()
    py: dict[str, list[dict]] = {n: [] for n in names}
    for k in range(REPEATS):
        for n in names:
            py[n].append(run_python(n, JOBS[n], work / f"py-{k}"))
            r = py[n][-1]
            print(f"py {n}#{k}: exit={r['exit_code']} trapped={r['trapped']} fuel={r['fuel']}",
                  file=sys.stderr, flush=True)
    py_wall = time.perf_counter() - t
    rs_all = run_rust(binary, names, work)
    rows = []
    for n in names:
        a = py[n]
        b = [rs_all[f"{n}#{k}"] for k in range(REPEATS)]
        errs = [x["error"][:300] for x in b if "error" in x]
        if errs:
            rows.append(dict(job=n, error=errs[0]))
            continue
        first = a[0]
        same = lambda key: all(x[key] == first[key] for x in a + b)  # noqa: E731
        fp, fr = [x["fuel"] for x in a], [x["fuel"] for x in b]
        row = dict(
            job=n,
            exit=[first["exit_code"], b[0]["exit_code"]],
            trapped=[first["trapped"], b[0]["trapped"]],
            exit_equal=same("exit_code"),
            trapped_equal=same("trapped"),
            stdout_equal=same("stdout"),
            stderr_equal=same("stderr"),
            written_equal=same("written"),
            golden=[first["golden"], b[0]["golden"]],
            n_written=len(first["written"]),
            fuel_py=fp,
            fuel_rs=fr,
            py_repeats=len(set(fp)) == 1,
            rs_repeats=len(set(fr)) == 1,
            fuel_exact=len(set(fp + fr)) == 1,
            cross_delta=(min(fr) - max(fp), max(fr) - min(fp)),
            stdout_bytes=len(first["stdout"]),
            stderr_bytes=len(first["stderr"]),
        )
        row["outputs_match"] = all(
            row[k] for k in ("exit_equal", "trapped_equal", "stdout_equal", "stderr_equal", "written_equal")
        )
        if not row["stderr_equal"]:
            row["stderr_py_tail"] = first["stderr"][-300:].decode(errors="replace")
            row["stderr_rs_tail"] = b[0]["stderr"][-300:].decode(errors="replace")
        if not row["stdout_equal"]:
            row["stdout_py_head"] = first["stdout"][:300].decode(errors="replace")
            row["stdout_rs_head"] = b[0]["stdout"][:300].decode(errors="replace")
        rows.append(row)
    result = dict(
        label=label,
        binary=str(binary),
        repeats=REPEATS,
        python_driver_wall_s=round(py_wall, 2),
        rust_wall_s=rs_all["_wall_s"],
        rust_module_ms={k: [v.get("module_from"), v.get("module_ms")] for k, v in rs_all.items()
                        if k != "_wall_s" and v.get("module_from") != "memory"},
        rows=rows,
    )
    dest = Path(__file__).parent / "results" / f"judge-{label}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result, indent=1))
    for r in rows:
        print(json.dumps(r))
    print(f"outputs matched {sum(1 for r in rows if r.get('outputs_match'))}/{len(rows)}; "
          f"fuel exact {sum(1 for r in rows if r.get('fuel_exact'))}/{len(rows)}; wrote {dest}")


if __name__ == "__main__":
    main()
