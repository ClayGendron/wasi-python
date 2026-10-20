import importlib.util, sys
try:
    import cython; print("cython importable")
except ImportError:
    print("no cython")
import lxml, lxml.html
print("lxml", lxml.__version__)
spec = importlib.util.spec_from_file_location("lxml.html.diff", sys.argv[1])
m = importlib.util.module_from_spec(spec); sys.modules["lxml.html.diff"] = m
try:
    spec.loader.exec_module(m); print("loads")
except Exception as e:
    print(type(e).__name__, e)
