"""The two advisories' probes against wasmtime's own WASI (no runner, no guard): the trailing-slash
symlink rename, and fd_readdir's padding bytes. Uses the judge's raw module driver."""
import importlib.metadata as md, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/src")
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import files

out = {"wasmtime_py": md.version("wasmtime"), "platform": sys.platform}
base = Path(tempfile.mkdtemp(prefix="wt-probe-", dir="/Users/claygendron/Git/Repos/wasi_python/build/scratch-wt50"))
grant, outside = base / "grant", base / "outside"
grant.mkdir(); outside.mkdir(); (outside / "canary.txt").write_text("CANARY")
raw = files.grant_raw([(grant, "/work", True)])
out["symlink errno"] = raw.symlink("../outside", 3, "up")
out["rename up/ -> stolen errno"] = raw.rename(3, "up/", 3, "stolen")
out["grant after"] = sorted(p.name for p in grant.iterdir())
out["outside exists"] = outside.exists()
out["stolen is dir with canary"] = (grant / "stolen" / "canary.txt").exists()
out["escaped"] = not outside.exists() and (grant / "stolen" / "canary.txt").exists()
# a file named with a trailing slash, as source
(grant / "f.txt").write_bytes(b"f")
out["rename f.txt/ -> e errno"] = raw.rename(3, "f.txt/", 3, "e")
out["grant after 2"] = sorted(p.name for p in grant.iterdir())
# fd_readdir padding: list the grant 200 times into a buffer; count entries with a non-zero
# byte in the three padding bytes after d_type (offsets 21..24 of each 24-byte header)
nonzero = 0; entries = 0; samples = set()
for _ in range(200):
    errno, used, data = raw.readdir(3)
    pos = 0
    while pos + 24 <= used:
        header = data[pos:pos + 24]
        namlen = int.from_bytes(header[16:20], "little")
        pad = header[21:24]
        entries += 1
        if pad != b"\0\0\0":
            nonzero += 1; samples.add(pad.hex())
        pos += 24 + namlen
out["readdir entries"] = entries
out["entries with non-zero padding"] = nonzero
out["padding samples"] = sorted(samples)[:5]
print(json.dumps(out, indent=1))
