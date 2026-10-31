import sys, collections
rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
by = collections.defaultdict(dict); labels = []
for name, label, fuel, out, rc, err, files in rows:
    base = label.split(' [')[0]
    by[name][base] = (out, rc, err, files)
    if ' [' in label: by[name][base + '#why'] = label.split(' [', 1)[1][:-1]
    if base not in labels: labels.append(base)
print("probe".ljust(46), " ".join(l.split(":")[-1][:9].ljust(9) for l in labels[1:]))
for name, d in by.items():
    nat = d["native"]
    cells = []
    for l in labels[1:]:
        cells.append((("same" if d[l] == nat else "DIFF") + ("*" if d.get(l + '#why') not in (None, 'None') else "")).ljust(9))
    print(name[:46].ljust(46), " ".join(cells))
if "-v" in sys.argv:
    for name, d in by.items():
        nat = d["native"]
        print(f"\n{name}\n   native: {nat}")
        for l in labels[1:]:
            if d[l] != nat: print(f"   {l}: {d[l]}")
