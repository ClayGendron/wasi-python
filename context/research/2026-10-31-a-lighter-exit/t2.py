import sys; sys.path.insert(0, sys.argv[0].rsplit("/",1)[0])
from drv import go, LAST
r = go("pass", fuel=1_000_000)
print(len(LAST["frames"]), LAST["frames"][-3:], LAST["frames"][:2])
