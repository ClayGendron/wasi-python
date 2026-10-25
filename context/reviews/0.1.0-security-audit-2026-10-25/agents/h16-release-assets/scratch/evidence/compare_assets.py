"""Hash every inner file of the v0.1.0 tarball and wheel (read in memory, never extracted
or executed) and compare with build/artifacts and the tagged commit's runner files."""
import hashlib, io, os, subprocess, sys, tarfile, zipfile

DL, REPO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TAR = os.path.join(DL, "wasi-python-0.1.0-wasm32-wasip1.tar.xz")
WHL = os.path.join(DL, "wasi_python-0.1.0-py3-none-any.whl")
LOCAL = os.path.join(REPO, "build", "artifacts")
TAG = "2cd47507"
h = lambda b: hashlib.sha256(b).hexdigest()
lines = []
p = lines.append

def local_tree(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            full = os.path.join(d, f)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                out[rel] = "SYMLINK"
            else:
                with open(full, "rb") as fh:
                    out[rel] = (h(fh.read()), os.path.getsize(full))
    return out

loc = local_tree(LOCAL)
p("# Local build/artifacts")
for k in sorted(loc):
    p(f"{loc[k][0] if loc[k]!='SYMLINK' else 'SYMLINK'}  {loc[k][1] if loc[k]!='SYMLINK' else ''}  {k}")
p("local SHA256SUMS hash: " + loc.get("SHA256SUMS", ("missing",))[0])

# Tarball
p("\n# Tarball members")
tar_files = {}
with tarfile.open(TAR, "r:xz") as t:
    for m in t.getmembers():
        kind = "file" if m.isfile() else ("dir" if m.isdir() else ("SYMLINK->" + m.linkname if m.issym() else ("HARDLINK->" + m.linkname if m.islnk() else "other")))
        if m.isfile():
            data = t.extractfile(m).read()
            tar_files[m.name] = data
            p(f"{h(data)}  {m.size}  mode={oct(m.mode)} uid={m.uid} gid={m.gid} {m.uname}/{m.gname} mtime={m.mtime}  {m.name}")
        else:
            p(f"{kind}  mode={oct(m.mode)}  {m.name}")
# strip the top-level folder
def strip(name):
    parts = name.split("/", 1)
    return parts[1] if len(parts) == 2 else name
tar_rel = {strip(k): v for k, v in tar_files.items()}
p("\n# Tarball vs build/artifacts")
diff = 0
for k in sorted(set(tar_rel) | set(loc)):
    a = h(tar_rel[k]) if k in tar_rel else None
    b = loc[k][0] if k in loc and loc[k] != "SYMLINK" else None
    st = "SAME" if a == b else ("ONLY-IN-TAR" if b is None else ("ONLY-LOCAL" if a is None else "DIFFERENT"))
    if st != "SAME":
        diff += 1
    p(f"{st:11} {k}  tar={a}  local={b}")
p(f"tarball differences: {diff}")

# Inner SHA256SUMS coverage
if "SHA256SUMS" in tar_rel:
    listed = {}
    for ln in tar_rel["SHA256SUMS"].decode().splitlines():
        if ln.strip():
            hh, name = ln.split(None, 1)
            listed[name.lstrip("*")] = hh
    p("\n# Files named in the tarball's inner SHA256SUMS: " + ", ".join(sorted(listed)))
    p("# Tarball files NOT named in its inner SHA256SUMS: " + ", ".join(sorted(k for k in tar_rel if k not in listed and k != "SHA256SUMS")))
    for name, hh in sorted(listed.items()):
        ok = name in tar_rel and h(tar_rel[name]) == hh
        p(f"  inner-sums {'OK ' if ok else 'BAD'} {name}")

# Wheel
p("\n# Wheel members")
with zipfile.ZipFile(WHL) as z:
    infos = z.infolist()
    wfiles = {}
    for i in infos:
        data = z.read(i.filename)
        wfiles[i.filename] = data
        attr = (i.external_attr >> 16)
        p(f"{h(data)}  {i.file_size}  attr={oct(attr)}  {i.filename}")
    names = [i.filename for i in infos]
    dup = {n for n in names if names.count(n) > 1}
    p(f"duplicate names in wheel: {sorted(dup)}")
    p("suspicious names: " + str([n for n in names if n.startswith('/') or '..' in n.split('/') or '\\' in n]))

p("\n# Wheel artifacts copy vs build/artifacts")
pref = "wasi_python/artifacts/"
w_art = {k[len(pref):]: v for k, v in wfiles.items() if k.startswith(pref)}
diff = 0
for k in sorted(set(w_art) | set(loc)):
    a = h(w_art[k]) if k in w_art else None
    b = loc[k][0] if k in loc and loc[k] != "SYMLINK" else None
    st = "SAME" if a == b else ("ONLY-IN-WHL" if b is None else ("ONLY-LOCAL" if a is None else "DIFFERENT"))
    if st != "SAME":
        diff += 1
    p(f"{st:11} {k}  whl={a}  local={b}")
p(f"wheel artifacts differences: {diff}")

p("\n# Wheel runner files vs git show 2cd47507:src/<file>")
tagged = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", TAG, "src/wasi_python"], capture_output=True, text=True, check=True).stdout.split()
tagged_rel = {t[len("src/"):]: t for t in tagged}
diff = 0
w_code = {k: v for k, v in wfiles.items() if k.startswith("wasi_python/") and not k.startswith(pref)}
for k in sorted(set(w_code) | set(tagged_rel)):
    if k in tagged_rel:
        b = subprocess.run(["git", "-C", REPO, "show", f"{TAG}:{tagged_rel[k]}"], capture_output=True, check=True).stdout
        bh = h(b)
    else:
        bh = None
    a = h(w_code[k]) if k in w_code else None
    st = "SAME" if a == bh else ("ONLY-IN-WHL" if bh is None else ("ONLY-IN-TAG" if a is None else "DIFFERENT"))
    if st != "SAME":
        diff += 1
    p(f"{st:11} {k}  whl={a}  tag={bh}")
p(f"wheel runner differences: {diff}")
p("\n# Other wheel members (dist-info etc.)")
for k in sorted(wfiles):
    if not k.startswith("wasi_python/"):
        p(f"  {k}")
for k in ("wasi_python-0.1.0.dist-info/RECORD",):
    if k in wfiles:
        rec = wfiles[k].decode()
        p("\n# RECORD vs member hashes")
        import base64, csv
        bad = 0; missing = []
        recnames = set()
        for row in csv.reader(io.StringIO(rec)):
            if not row: continue
            name, hv, size = row
            recnames.add(name)
            if not hv: continue
            algo, val = hv.split("=", 1)
            dig = base64.urlsafe_b64encode(hashlib.sha256(wfiles[name]).digest()).rstrip(b"=").decode()
            if dig != val: bad += 1; p(f"  RECORD-MISMATCH {name}")
        p(f"  RECORD mismatches: {bad}; members not in RECORD: {sorted(set(wfiles)-recnames)}")
with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(l for l in lines if any(s in l for s in ("differences", "DIFFERENT", "ONLY-", "NOT named", "RECORD", "duplicate", "suspicious", "SYMLINK", "HARDLINK", "BAD", "SHA256SUMS hash"))))
