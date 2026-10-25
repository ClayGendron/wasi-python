"""Repack build/artifacts with the tagged release/version.py write_assets (reads the set, writes
only under scratch) and compare the result with the published tarball; and compute the tagged
release/licences.py combined LICENSE from build/artifacts and compare it with the published
wheel's .dist-info/licenses/LICENSE (read from the zip, not executed)."""
import hashlib, importlib.util, subprocess, sys, zipfile
from pathlib import Path

REPO, DL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
TAG = "2cd47507"
def load(name, rel):
    src = subprocess.run(["git", "-C", str(REPO), "show", f"{TAG}:{rel}"], capture_output=True, check=True).stdout
    p = OUT / f"tagged_{name}.py"
    p.write_bytes(src)
    spec = importlib.util.spec_from_file_location(f"tagged_{name}", p)
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m
version = load("version", "release/version.py")
licences = load("licences", "release/licences.py")
h = lambda b: hashlib.sha256(b).hexdigest()
art = REPO / "build" / "artifacts"
pub_tar = DL / "wasi-python-0.1.0-wasm32-wasip1.tar.xz"
pub_whl = DL / "wasi_python-0.1.0-py3-none-any.whl"
outdir = OUT / "repack"
paths = version.write_assets(art, pub_whl, outdir, "0.1.0")
rep_tar = outdir / pub_tar.name
print("repacked tarball sha256:", h(rep_tar.read_bytes()))
print("published tarball sha256:", h(pub_tar.read_bytes()))
print("tarball byte-identical:", rep_tar.read_bytes() == pub_tar.read_bytes())
import lzma
print("decompressed tar byte-identical:", lzma.decompress(rep_tar.read_bytes()) == lzma.decompress(pub_tar.read_bytes()))
print("repacked outer SHA256SUMS equals published:", (outdir / "SHA256SUMS").read_bytes() == (DL / "SHA256SUMS").read_bytes())
tagged_licence = subprocess.run(["git", "-C", str(REPO), "show", f"{TAG}:LICENSE"], capture_output=True, check=True).stdout.decode()
want = licences.combined(tagged_licence, art)
with zipfile.ZipFile(pub_whl) as z:
    got = z.read("wasi_python-0.1.0.dist-info/licenses/LICENSE").decode()
print("wheel dist-info LICENSE == combined(tagged LICENSE, build/artifacts/LICENSES):", got == want, h(got.encode()), h(want.encode()))
print("licences.parts count:", len(licences.parts(art)), "(LICENSES/*.txt only; non-.txt files not appended):",
      sorted(p.name for p in (art / "LICENSES").iterdir() if p.suffix != ".txt"))
for p in paths:
    p.unlink()
