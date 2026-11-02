CASES = {"frozen census": r'''
import gc, io, types, weakref, collections, sys
young = {id(o) for o in gc.get_objects()}
gc.unfreeze()
c = collections.Counter()
for o in gc.get_objects():
    if id(o) in young: continue
    t = type(o)
    if isinstance(o, (types.GeneratorType, types.CoroutineType, types.AsyncGeneratorType)): c["generator " + str(o.gi_suspended if hasattr(o, "gi_suspended") else "?")] += 1
    elif isinstance(o, io.IOBase): c["io " + t.__name__ + (" closed" if o.closed else " open")] += 1
    elif isinstance(o, weakref.ref) and o.__callback__ is not None: c["weakref cb " + getattr(o.__callback__, "__qualname__", "?")] += 1
    elif hasattr(t, "__del__"): c["__del__ " + t.__module__ + "." + t.__qualname__] += 1
    elif t is type and any("__del__" in k.__dict__ for k in o.__mro__): c["class with __del__ " + o.__qualname__] += 1
    else: c["other"] += 1
print({k: v for k, v in c.items() if not k.startswith(("other", "class with"))}, sum(v for k, v in c.items() if k.startswith("class with")))
'''}
BINARIES = ("snapshot",)
