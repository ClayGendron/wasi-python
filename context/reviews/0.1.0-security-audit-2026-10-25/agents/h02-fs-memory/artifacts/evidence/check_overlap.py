"""Second bounded check (h02-fs-memory): the guard's fd_readdir with an aligned `used` pointer
lying over the listing (the re-list on the guard's own page), and plain wasmtime 49.0.0's
padding on the same folder for comparison."""
import importlib.util, json, struct, sys, tempfile
from pathlib import Path
REPO = Path("."); SCR = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("hfiles", REPO / "tests/harness/files.py")
H = importlib.util.module_from_spec(spec); sys.modules["hfiles"] = H; spec.loader.exec_module(H)
import wasmtime
END = H.MEMORY_END
out = []
def rec(name, **kw):
    out.append({"case": name, **kw}); print(name, kw)
def pads(data):
    found, pos = [], 0
    while pos + 24 <= len(data):
        found.append(data[pos + 21: pos + 24].hex()); pos += 24 + struct.unpack_from("<I", data, pos + 16)[0]
    return found
work = SCR / "work"; work.mkdir(exist_ok=True)
grant = Path(tempfile.mkdtemp(dir=work, prefix="grant2-"))
for i in range(40):
    (grant / (f"name{i:02d}" + "q" * (i % 7))).write_bytes(b"")
plain = H.grant_raw([(grant, "/g", False)])
g = H.Guarded([(grant, "/g", False)])
for who, raw in (("plain wasmtime", plain), ("guard", g.raw)):
    for label, buf, used in (("used at RESULT", H.DIRBUF, H.RESULT), ("used=buf+40 (second header)", H.DIRBUF, H.DIRBUF + 40),
                             ("buf=DIRBUF+2, used=DIRBUF (overlaps 2 bytes)", H.DIRBUF + 2, H.DIRBUF),
                             ("used=buf+400 (mid listing)", H.DIRBUF, H.DIRBUF + 400)):
        for trial in range(3):
            raw.put(0, b"\xaa" * END)
            try:
                e = raw("fd_readdir", 3, buf, 1500, 0, used); stop = None
            except H.Ends as x:
                e, stop = None, x.message
            n = raw.u32(used) if e == 0 else 0
            data = raw.get(buf, n)
            if used == H.RESULT:
                clean = data
            keep = lambda d: bytes(b for i, b in enumerate(d) if not (used - buf <= i < used - buf + 4))
            nonzero = [p for p in pads(clean) if p != "000000"] if used == H.RESULT else ([] if keep(data) == keep(clean) else ["differs from the clean listing outside the count"])
            if trial == 0 or nonzero:
                rec(f"{who}: {label} trial {trial}", errno=e, stop=stop, used=n, entries=len(pads(data)), nonzero_pads=nonzero[:8],
                    tail_after_used_kept_sentinel=raw.get(buf + n, 8).hex())
json.dump(out, open(SCR / "evidence" / "check_overlap.json", "w"), indent=1)
