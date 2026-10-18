import numpy as np, pandas as pd, pickle, io
df = pd.DataFrame({"a":[1,2],"b":["x","y"]})
print(df.groupby("b").a.sum().to_dict(), np.arange(4).sum(), len(pickle.dumps(df)), pd.read_csv(io.StringIO("a,b\n1,2")).shape)
import numpy.random as r; print(type(r.default_rng(0)).__module__, r.default_rng(0).integers(10))
