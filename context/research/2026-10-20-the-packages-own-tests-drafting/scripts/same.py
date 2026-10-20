import sys, tarfile, zipfile, hashlib, os
wheel, src = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(wheel)
wf = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith(".py") and ".dist-info/" not in n}
t = tarfile.open(src)
sf = {}
for m in t.getmembers():
    if m.isfile() and m.name.endswith(".py"):
        rel = m.name.split("/", 1)[1]
        sf[rel] = hashlib.sha256(t.extractfile(m).read()).hexdigest()
same = diff = missing = 0; diffs = []; miss = []
for n, h in wf.items():
    cands = [r for r in (n, "src/" + n, "lib/" + n, "Lib/" + n) if r in sf]
    if not cands: missing += 1; miss.append(n); continue
    if sf[cands[0]] == h: same += 1
    else: diff += 1; diffs.append(n)
print(f"{os.path.basename(wheel)}: {len(wf)} .py in wheel; same {same}, differ {diff} {diffs[:4]}, absent {missing} {miss[:4]}")
