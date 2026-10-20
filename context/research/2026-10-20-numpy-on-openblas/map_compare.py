"""Where python.wasm's bytes went: two link maps (step 60's python.map) summed by archive (basename,
numpy's module archives kept apart), and the largest movers. Usage: map_compare.py <base.map> <new.map>"""

import re
import sys
from collections import Counter

LINE = re.compile(r"^\s+\S+\s+[0-9a-f]+\s+([0-9a-f]+)\s+(\S+?)\((.+?)\):\((\S+)\)$")


def sizes(path):
    by_archive, by_object = Counter(), Counter()
    for line in open(path, errors="replace"):
        m = LINE.match(line.rstrip("\n"))
        if not m:
            continue
        size, archive, member = int(m[1], 16), m[2].rsplit("/", 1)[-1], m[3]
        by_archive[archive] += size
        by_object[f"{archive}({member})"] += size
    return by_archive, by_object


base_a, base_o = sizes(sys.argv[1])
new_a, new_o = sizes(sys.argv[2])
print(f"total mapped: base {sum(base_a.values()):,}, new {sum(new_a.values()):,}, "
      f"change {sum(new_a.values()) - sum(base_a.values()):+,}")
print("archives that moved by more than 2 KB:")
for k in sorted(set(base_a) | set(new_a), key=lambda k: new_a[k] - base_a[k]):
    d = new_a[k] - base_a[k]
    if abs(d) > 2048:
        print(f"  {d:+12,}  {k}")
grew = Counter({k: new_o[k] - base_o[k] for k in set(base_o) | set(new_o)})
print("objects that grew most:")
for k, d in grew.most_common(15):
    print(f"  {d:+12,}  {k}")
