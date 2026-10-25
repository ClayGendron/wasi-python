"""For every pinned name, and every literal name a build step passes to pinned(), list the
SHA256SUMS lines that pinned()'s grep pattern ("  <name>$", basic regex: '.' is any character)
matches. Data only: reads downloads/SHA256SUMS, scripts/line.conf and scripts/steps/*.sh."""
import re, sys, pathlib
repo = pathlib.Path(sys.argv[1])
rows = [l.split("  ", 1) for l in (repo / "downloads/SHA256SUMS").read_text().splitlines() if l.strip()]
names = [r[1] for r in rows]
def bre(name):  # BRE: only . * [ ] ^ $ \ are special; + ? ( ) { } | are literal
    out = ""
    for ch in name:
        out += "." if ch == "." else re.escape(ch)
    return re.compile("  " + out + "$")
lines = ["  ".join(r) for r in rows]
bad = []
for n in names:
    hits = [l.split("  ", 1)[1] for l in lines if bre(n).search(l)]
    if hits != [n]:
        bad.append((n, hits))
print("pinned names whose pattern matches a line other than their own:", bad)
called = set()
for sh in sorted((repo / "scripts/steps").glob("*.sh")):
    for m in re.finditer(r'pinned "?([A-Za-z0-9_.+${}-]+)"?\)', sh.read_text()):
        called.add(m.group(1))
conf = dict(re.findall(r"^([A-Z0-9_]+)=(\S+)$", (repo / "scripts/line.conf").read_text(), re.M))
unresolved, missing = [], []
for c in sorted(called):
    if "$" in c:
        unresolved.append(c); continue
    if c not in names:
        missing.append(c)
print("literal names passed to pinned():", len([c for c in called if "$" not in c]))
print("literal names with no exact pin line:", missing)
print("names built from variables (checked by hand against line.conf):", unresolved)
