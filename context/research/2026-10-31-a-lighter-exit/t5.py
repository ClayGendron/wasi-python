import sys; sys.path.insert(0, sys.argv[0].rsplit("/",1)[0])
from drv import go
for snap in (True, False):
    r = go("""import gc, weakref, sys
for o in gc.get_objects():
    if isinstance(o, weakref.ref) and o.__callback__ is not None:
        cb = o.__callback__
        print(type(o).__name__, type(o()).__name__, getattr(cb, '__qualname__', type(cb).__name__), getattr(getattr(cb, '__code__', None), 'co_filename', '?'))
""", snap=snap)
    print("snapshot" if snap else "plain"); print(r.stdout.decode()[:3000], r.stderr.decode()[-500:])
