"""outside.py [path first on sys.path]: load_csv with a base_file outside statsmodels' datasets and a missing CSV."""
import sys, tempfile, os
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
from statsmodels.datasets import utils as du
d = tempfile.mkdtemp()
try:
    du.load_csv(os.path.join(d, "mine.py"), "missing.csv")
except Exception as e:
    print("outside, missing:", type(e).__name__)
open(os.path.join(d, "here.csv"), "w").write("a,b\n1,2\n")
print("outside, present:", du.load_csv(os.path.join(d, "mine.py"), "here.csv").shape)
