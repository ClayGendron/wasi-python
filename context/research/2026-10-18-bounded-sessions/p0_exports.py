import sys; sys.path.insert(0, sys.argv[1])
import h
for snap in (True, False):
    m = h.module(True, snap)
    print("snapshot" if snap else "plain", sorted((e.name, type(e.type).__name__) for e in m.exports))
