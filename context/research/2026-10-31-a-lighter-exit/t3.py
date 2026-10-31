import sys; sys.path.insert(0, sys.argv[0].rsplit("/",1)[0])
from drv import go_with, variant, LAST
a = variant(sys.argv[1], snap=sys.argv[2] == "snapshot")
for code in sys.argv[3:]:
    r = go_with(a, code, snap=sys.argv[2] == "snapshot")
    print(r.fuel_used, r.exit_code, r.trapped, r.stdout[:200], r.stderr[-300:], LAST.get("msg", "")[:500])
