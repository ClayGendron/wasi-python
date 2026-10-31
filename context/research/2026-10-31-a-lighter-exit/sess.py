"""A session's end: a turn leaves an unclosed file beside a function, an atexit handler and a
__del__; close() runs the shutdown. usage: sess.py"""
import sys, os, tempfile; sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from drv import A, C, variant
from wasi_python import Session
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
T1 = "f = open('a.txt', 'w'); f.write('x' * 100)\ndef g(): pass\nimport atexit\natexit.register(lambda: open('b.txt', 'w').write('atexit'))"
T2 = "class D:\n    def __del__(s): open('c.txt', 'w').write('del')\nd = D()\nimport json\njson.keep = open('e.txt', 'w'); json.keep.write('y' * 50)"
for label, arts, snap in (("snapshot today", A, True), ("plain today", A, False), ("snapshot E no-op free", variant(os.path.join(HERE, "bins/snap-nofree2.wasm")), True), ("snapshot D stop after modules", variant(os.path.join(HERE, "bins/snap-nointerp.wasm")), True)):
    d = tempfile.mkdtemp(dir=os.path.join(HERE, "tmp"))
    s = Session(root=d, artifacts=arts, snapshot=snap, cache_dir=C)
    s.run(T1); s.run(T2); s.close()
    got = {n: os.path.getsize(os.path.join(d, n)) for n in sorted(os.listdir(d)) if n.endswith(".txt")}
    print(label, got)
