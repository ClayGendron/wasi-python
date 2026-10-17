"""Research: copy the artifact zip and add the matplotlib stack as .pyc (no tests, no mpl-data)."""
import sys, zipfile, importlib.util
from importlib._bootstrap_external import _code_to_hash_pyc
from pathlib import Path, PurePosixPath
src_zip, out_zip = Path(sys.argv[1]), Path(sys.argv[2])
trees = [Path(p) for p in sys.argv[3].split(",")]   # dirs whose children are top-level packages
wheels = [Path(p) for p in sys.argv[4].split(",")]
SKIP_DIRS = {"tests", "test", "__pycache__", "mpl-data", "web_backend"}
def pyc(source: bytes, name: str) -> bytes:
    code = compile(source, name, "exec", dont_inherit=True, optimize=0)
    return bytes(_code_to_hash_pyc(code, importlib.util.source_hash(source), checked=False))
added = {}
for t in trees:
    for p in sorted(t.rglob("*")):
        rel = p.relative_to(t)
        if p.is_dir() or SKIP_DIRS & set(rel.parts):
            continue
        if p.suffix == ".py":
            added[str(PurePosixPath(*rel.parts)) + "c"] = pyc(p.read_bytes(), "/" + str(rel))
        elif p.suffix in (".pyi", ".so", ".deps", ".a", ".h", ".c", ".cpp", ".typed"):
            continue
        else:
            added[str(PurePosixPath(*rel.parts))] = p.read_bytes()
for w in wheels:
    with zipfile.ZipFile(w) as z:
        for n in z.namelist():
            parts = PurePosixPath(n).parts
            if parts[0].endswith(".dist-info") or SKIP_DIRS & set(parts) or n.endswith("/"):
                continue
            if n.endswith(".py"):
                added[n + "c"] = pyc(z.read(n), "/" + n)
            elif not n.endswith((".pyi", ".typed", ".pyx", ".c")):
                added[n] = z.read(n)
with zipfile.ZipFile(src_zip) as zi, zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zo:
    names = set(zi.namelist())
    clash = names & set(added)
    assert not clash, sorted(clash)[:5]
    for info in zi.infolist():
        zo.writestr(info, zi.read(info))
    for n in sorted(added):
        zi_ = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)); zi_.compress_type = zipfile.ZIP_DEFLATED; zi_.external_attr = 0o644 << 16
        zo.writestr(zi_, added[n])
print(len(added), "members added; non-pyc:", sorted(n for n in added if not n.endswith(".pyc"))[:20])
