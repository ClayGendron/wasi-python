"""N8's prototype walk on a __call__ cycle: an object whose class's __call__ is the object."""
import runpy
import sys

ns = runpy.run_path(sys.argv[1])  # n8_060.py: prints its own lines, defines walk
walk = ns["walk"]


class Loop:
    pass


obj = Loop()
Loop.__call__ = obj
try:
    walk("t", obj)
    print("cycle: walked without error")
except TypeError as e:
    print("cycle: TypeError:", e)
