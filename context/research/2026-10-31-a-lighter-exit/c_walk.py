PD = "import pandas as pd\ndf = pd.DataFrame({'k': [1, 2, 1, 2], 'v': [1.0, 2.0, 3.0, 4.0]})\nprint(df.groupby('k').v.sum().to_dict())\n"
NP = "import numpy as np\nprint(np.arange(10).sum())\n"
G = "import gc, os\nn = len(gc.get_objects())\nprint('young', n, flush=True)\nos._exit(0)"
G0 = "import gc, os\nn = 0\nprint('young', n, flush=True)\nos._exit(0)"
CASES = {"pass walk": G, "pass nowalk": G0, "numpy walk": NP + G, "numpy nowalk": NP + G0, "pandas walk": PD + G, "pandas nowalk": PD + G0}
BINARIES = ("snapshot",)
