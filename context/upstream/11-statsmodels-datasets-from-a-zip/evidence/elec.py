import sys, hashlib
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
import pandas as pd
from statsmodels.datasets import elec_equip
try:
    d = elec_equip.load().data
    print("elec_equip", d.shape, hashlib.sha256(pd.util.hash_pandas_object(d, index=True).values.tobytes()).hexdigest()[:16])
except Exception as e:
    print("elec_equip", type(e).__name__)
