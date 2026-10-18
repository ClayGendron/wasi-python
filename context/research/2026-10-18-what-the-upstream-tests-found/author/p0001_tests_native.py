"""Run the amended patch 0001's code and its three tests natively (pinned oracle), WASI simulated."""
import errno, os, sys, tempfile, types, pathlib
import numpy as np
import numpy.lib._format_impl as fi
exec(compile(open("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/051-work/np/numpy-2.5.2/numpy/lib/_format_impl.py").read(), fi.__file__, "exec"), fi.__dict__)
import numpy.lib.format as F
for k in ("write_array", "read_array", "isfileobj"): setattr(F, k, fi.__dict__[k])
def dup(fd): raise OSError(errno.ENOTSUP, "Not supported")
src = open("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/051-work/np/numpy-2.5.2/numpy/lib/tests/test_format.py").read()
# pytest is not in the oracle: a minimal stand-in for raises/mark/monkeypatch.
import re, contextlib
class _Raises:
    def __init__(self, exc, match=None): self.exc, self.match = exc, match
    def __enter__(self): return self
    def __exit__(self, t, v, tb):
        assert t is not None and issubclass(t, self.exc), f"DID NOT RAISE {self.exc}"
        assert self.match is None or re.search(self.match, str(v)), f"no match: {v}"
        return True
class _Mark:
    def __getattr__(self, n): return lambda *a, **k: (lambda f: f)
pytest = types.SimpleNamespace(raises=_Raises, mark=_Mark(), skip=None, warns=None, param=lambda *a, **k: a)
sys.modules["pytest"] = pytest
mod = types.ModuleType("tf"); mod.__dict__["__name__"] = "tf"
exec(compile(src, "test_format.py", "exec"), mod.__dict__)
class MP:
    def setattr(self, obj, name, value): setattr(obj, name, value)
os.dup = dup; sys.platform = "wasi"
for name, fn, args in [("test_file_truncated", mod.test_file_truncated, ()),
                       ("test_save_masked_without_dup", mod.test_save_masked_without_dup, (MP(),))]:
    d = pathlib.Path(tempfile.mkdtemp())
    fn(d, *args); print(name, "passed")
n = 0
for arr in mod.basic_arrays + mod.record_arrays:
    d = pathlib.Path(tempfile.mkdtemp()); mod.test_save_load_without_dup(d, MP(), arr); n += 1
print("test_save_load_without_dup passed", n)
