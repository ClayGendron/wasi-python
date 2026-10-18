import errno, os, sys, tempfile
import numpy as np
import numpy.lib._format_impl as fi
src = open("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/051-work/np/numpy-2.5.2/numpy/lib/_format_impl.py").read()
exec(compile(src, fi.__file__, "exec"), fi.__dict__)
import numpy.lib.format as F
for k in ("write_array", "read_array", "isfileobj"): setattr(F, k, fi.__dict__[k])
def dup(fd): raise OSError(errno.ENOTSUP, "Not supported")
os.dup = dup
sys.platform = "wasi"
d = tempfile.mkdtemp()
for arr in [np.arange(6).reshape(2, 3), np.asfortranarray(np.arange(6.0).reshape(2, 3)), np.zeros(0)]:
    p = os.path.join(d, "a.npy"); np.save(p, arr); b = np.load(p)
    print("roundtrip", np.array_equal(arr, b), b.flags.f_contiguous == arr.flags.f_contiguous)
for xm in [np.ma.masked_array([1, 2, 3], mask=[False, True, False]),
           np.ma.masked_array(np.asfortranarray(np.ones((2, 3))), mask=False)]:
    try:
        np.save(os.path.join(d, "m.npy"), xm); print("masked saved")
    except NotImplementedError as e:
        print("masked NotImplementedError", e)
import io
bio = io.BytesIO(); np.save(bio, np.ma.masked_array([1, 2], mask=[0, 1])); print("BytesIO masked saved", len(bio.getvalue()))
