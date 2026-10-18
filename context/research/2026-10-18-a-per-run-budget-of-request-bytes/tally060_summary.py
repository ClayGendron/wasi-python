"""Summarise tally060.py's per-process files: per frame host, the bytes it admitted (read and
parsed) and the bytes of every frame, refused ones included."""
import glob
import json
import sys

rows = []
for p in glob.glob(f"{sys.argv[1]}/tally-*.json"):
    rows += json.load(open(p))
rows = [r for r in rows if r["frames"]]
print("frame hosts that saw a frame:", len(rows))
for k in ("admitted", "all", "frames", "max_frame"):
    v = sorted(r[k] for r in rows)
    print(f"{k:9s} max {v[-1]:>11,d}  top five {v[-5:]}  median {v[len(v) // 2]}")
print("the five largest by admitted bytes:")
for r in sorted(rows, key=lambda r: -r["admitted"])[:5]:
    print(" ", r)
