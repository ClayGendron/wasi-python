"""Spec 083, criterion 4: two mutants of the build's driver, each in a scratch copy of the branch.
m-ino0: every inode answered 0; m-pinned: every time answered 1767225600 s, the build's pin.
Usage: uv run python -I mutate.py <copy dir> <mutant>"""
import sys
p = sys.argv[1] + "/tests/harness/guest.py"
s = open(p).read()
if sys.argv[2] == "m-ino0":
    old = "        return 0 if real == 0 else self.inos.setdefault(real, len(self.inos) + 1)"
    new = "        return 0  # mutant: every inode 0"
else:
    old = "        return (kept[0][1], kept[1][1], kept[2][1])"
    new = "        return (REALTIME_START_NS,) * 3  # mutant: the build's pinned time"
assert s.count(old) == 1
open(p, "w").write(s.replace(old, new))
