"""Every derived number the memo quotes, from the TSVs beside it.

    uv run --no-sync python -I analyze.py <outputs dir>   (writes outputs/derived.txt)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path(sys.argv[1])


def load(name):
    with open(OUT / name) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def fuel(rows, binary, zipname, case):
    (r,) = [r for r in rows if r["binary"] == binary and r["zip"] == zipname and r["case"] == case]
    assert r["exit"] == "0", r
    return int(r["fuel_used"])


lines = []


def say(s):
    lines.append(s)
    print(s)


M = 1e6
N1, N4 = 1751, 7004
start = load("start.tsv")
say("== start.tsv (plain unless named)")
for z in ("zip-1x", "zip-2x", "zip-3x", "zip-4x"):
    say(f"{z}: pass {fuel(start, 'plain', z, 'pass') / M:.1f} M")
p1, p4 = fuel(start, "plain", "zip-1x", "pass"), fuel(start, "plain", "zip-4x", "pass")
say(f"plain pass slope: {(p4 - p1) / (N4 - N1):,.0f} fuel/member")
r1 = fuel(start, "plain", "zip-1x", "zipimport._read_directory x1") - p1
r4 = fuel(start, "plain", "zip-4x", "zipimport._read_directory x1") - p4
say(f"one more zipimport read: {r1 / M:.1f} M (1x), {r4 / M:.1f} M (4x); slope {(r4 - r1) / (N4 - N1):,.0f}/member")
say(f"plain pass minus one read at 1x (the part that does not grow): {(p1 - r1) / M:.1f} M")
x3 = (fuel(start, "plain", "zip-4x", "zipimport._read_directory x3") - p4) / 3
say(f"three more reads at 4x: {x3 / M:.1f} M each")
s_pass = fuel(start, "snapshot", "zip-1x", "pass")
say(f"snapshot pass {s_pass / M:.1f} M; snapshot one more read "
    f"{(fuel(start, 'snapshot', 'zip-1x', 'zipimport._read_directory x1') - s_pass) / M:.1f} M")
say(f"stored vs deflated, 4x pass: {fuel(start, 'plain', 'zip-4x-stored', 'pass') / M:.1f} vs {p4 / M:.1f} M")


def slope(rows, binary, case, base, za="zip-1x", zb="zip-4x", na=N1, nb=N4):
    a = fuel(rows, binary, za, case) - fuel(rows, binary, za, base)
    b = fuel(rows, binary, zb, case) - fuel(rows, binary, zb, base)
    return a, b, (b - a) / (nb - na)


for case, base in (
    ("zipfile.ZipFile x1", "import zipfile"),
    ("zipfile.Path + name set x1", "import zipfile"),
    ("resources read x1", "import importlib.resources"),
    ("ZoneInfo Europe/Paris", "import zoneinfo"),
):
    a, b, s = slope(start, "plain", case, base)
    say(f"{case} (minus {base}): {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {s:,.0f}/member")
a = (fuel(start, "plain", "zip-1x", "resources read x5") - fuel(start, "plain", "zip-1x", "resources read x1")) / 4
b = (fuel(start, "plain", "zip-4x", "resources read x5") - fuel(start, "plain", "zip-4x", "resources read x1")) / 4
say(f"each later resource read: {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {(b - a) / (N4 - N1):,.0f}/member")
a = fuel(start, "plain", "zip-1x", "ZoneInfo Paris+Tokyo") - fuel(start, "plain", "zip-1x", "ZoneInfo Europe/Paris")
b = fuel(start, "plain", "zip-4x", "ZoneInfo Paris+Tokyo") - fuel(start, "plain", "zip-4x", "ZoneInfo Europe/Paris")
say(f"second zone: {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {(b - a) / (N4 - N1):,.0f}/member")
for case, base in (("resources read x1", "import importlib.resources"), ("ZoneInfo Europe/Paris", "import zoneinfo")):
    say(f"snapshot {case}: {(fuel(start, 'snapshot', 'zip-1x', case) - fuel(start, 'snapshot', 'zip-1x', base)) / M:.1f} M")
say(f"snapshot each later read: {(fuel(start, 'snapshot', 'zip-1x', 'resources read x5') - fuel(start, 'snapshot', 'zip-1x', 'resources read x1')) / 4 / M:.1f} M")
say(f"snapshot second zone: {(fuel(start, 'snapshot', 'zip-1x', 'ZoneInfo Paris+Tokyo') - fuel(start, 'snapshot', 'zip-1x', 'ZoneInfo Europe/Paris')) / M:.1f} M")

cand = load("candidates.tsv")
say("\n== candidates.tsv (cost = case minus base on the same binary and zip)")
for case in (
    "zipimport x1",
    "zipimport, unpack helpers as C calls",
    "zipimport, _path_join as a C call",
    "zipimport, both as C calls",
    "rewrite struct, no implied dirs",
    "rewrite struct",
    "rewrite from_bytes",
):
    a, b, s = slope(cand, "plain", case, "base")
    say(f"{case}: {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {s:,.0f}/member")
a, b, s = slope(cand, "plain", "marshal dumps + loads", "marshal dumps")
say(f"marshal.loads of zipimport's dict: {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {s:,.0f}/member")
for label, case in (("stock", "stock"), ("cached root", "cached root"), ("index", "index")):
    a, b, s = slope(cand, "plain", f"{case}: Paris", "tz base")
    a5 = (fuel(cand, "plain", "zip-1x", f"{case}: Paris + 4 more") - fuel(cand, "plain", "zip-1x", f"{case}: Paris")) / 4
    b5 = (fuel(cand, "plain", "zip-4x", f"{case}: Paris + 4 more") - fuel(cand, "plain", "zip-4x", f"{case}: Paris")) / 4
    say(f"{label}: first zone {a / M:.1f} M (1x), {b / M:.1f} M (4x), slope {s:,.0f}/member; "
        f"each later zone {a5 / M:.2f} M (1x), {b5 / M:.2f} M (4x)")
for z in ("zip-1x", "zip-4x"):
    e = (fuel(cand, "plain", z, "index: Paris + every zone") - fuel(cand, "plain", z, "index: Paris")) / 598
    say(f"index: each of the 598 zone loads after Paris on {z}: {e / M:.3f} M")
e = (fuel(cand, "plain", "zip-1x", "cached root: Paris + every zone") - fuel(cand, "plain", "zip-1x", "cached root: Paris")) / 598
say(f"cached root: each of the 598 zone loads after Paris on zip-1x: {e / M:.3f} M")
sb = fuel(cand, "snapshot", "zip-1x", "tz base")
for case in ("stock: Paris", "stock: Paris + 4 more", "cached root: Paris", "cached root: Paris + 4 more",
             "index: Paris", "index: Paris + 4 more", "index: Paris + every zone"):
    say(f"snapshot {case}: {(fuel(cand, 'snapshot', 'zip-1x', case) - sb) / M:.1f} M")
say("equality rows: " + "; ".join(f"{r['binary']} {r['zip']}: {r['stdout']}" for r in cand if r["case"] == "index: equal to stock"))
say("rewrite equality: " + "; ".join(f"{r['binary']} {r['zip']} {r['case']}: {r['stdout']}" for r in cand if r["case"].startswith("rewrite ") and r["stdout"]))

fol = load("followup.tsv")
say("\n== followup.tsv")
for case in ("metadata version, stock", "metadata version, index", "metadata miss, stock", "metadata miss, index"):
    a, b, s = slope(fol, "plain", case, "base", "zip-1x-meta", "zip-4x-meta", 1752, 7005)
    say(f"{case}: {a / M:.1f} M (1x), {b / M:.1f} M (4x); slope {s:,.0f}/member")
sb = fuel(fol, "snapshot", "zip-1x", "base")
for case in ("metadata miss, stock", "metadata miss, index"):
    say(f"snapshot {case}: {(fuel(fol, 'snapshot', 'zip-1x', case) - sb) / M:.1f} M")
pb = fuel(fol, "snapshot", "zip-1x", "pandas base")
for case in ("pandas tz, stock", "pandas tz, index"):
    say(f"snapshot {case}: {(fuel(fol, 'snapshot', 'zip-1x', case) - pb) / M:.1f} M")
pb = fuel(fol, "plain", "zip-1x", "pandas base")
for case in ("pandas tz, stock", "pandas tz, index"):
    say(f"plain {case}: {(fuel(fol, 'plain', 'zip-1x', case) - pb) / M:.1f} M")

inv = load("invalidate.tsv")
say("\n== invalidate.tsv")
for binary, z in (("snapshot", "zip-1x"), ("plain", "zip-1x"), ("plain", "zip-4x")):
    rows = {r["case"]: int(r["fuel_used"]) for r in inv if r["binary"] == binary and r["zip"] == z}
    say(f"{binary} {z}: invalidate_caches then an import costs "
        f"{(rows['invalidate_caches + import json.tool'] - rows['import json.tool']) / M:.1f} M more")

say("\n== projections at 6,630 members (0.1.0's zip, INFERRED, linear)")
n = 6630
fixed = (p1 - r1)
say(f"plain pass today's reader: {(fixed + n * 77_200) / M:.0f} M; struct rewrite: {(fixed + n * 24_300) / M:.0f} M; "
    f"C reader at marshal.loads' cost: {(fixed + n * 12_000) / M:.0f} M")
say(f"stock resource read, first: about {n * 124_000 / M:.0f} M; each later: about {n * 124_000 / M:.0f} M")
(OUT / "derived.txt").write_text("\n".join(lines) + "\n")
