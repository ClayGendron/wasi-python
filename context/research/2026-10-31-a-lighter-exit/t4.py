import sys, tempfile; sys.path.insert(0, sys.argv[0].rsplit("/",1)[0])
from drv import go
d = tempfile.mkdtemp(dir=sys.argv[0].rsplit("/",1)[0])
r = go("import os, sys; print(os.getcwd(), sys.path, sorted(sys.modules)[:5], len(sys.modules))", root=d)
print(r.stdout, r.stderr[-300:])
