import sys; sys.path.insert(0, sys.argv[0].rsplit("/",1)[0])
from drv import go, LAST
r = go("pass", fuel=30_000_000)
print(r.trapped); print(LAST.get("msg","")[:3000])
