"""probe_datasets.py [path to put first on sys.path]: every bundled statsmodels dataset, loaded, as a digest."""
import hashlib, importlib, sys
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
import statsmodels.datasets as ds
import pandas as pd
names = sorted(n for n in ds.__all__ if n not in ("get_rdataset", "get_data_home", "clear_data_home", "check_internet", "webuse"))
ok = 0
for n in names:
    m = getattr(ds, n)
    try:
        d = m.load_pandas() if hasattr(m, "load_pandas") else m.load()
        frame = d.data
        h = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()[:16]
        print(n, frame.shape, h); ok += 1
    except Exception as e:
        print(n, type(e).__name__)
print("loaded", ok, "of", len(names), "from", ds.__file__.split("/statsmodels/")[0].rsplit("/", 1)[-1])
