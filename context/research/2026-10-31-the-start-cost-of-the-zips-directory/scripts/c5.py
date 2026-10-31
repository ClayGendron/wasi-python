from pathlib import Path
PRE = (Path(__file__).parent / "lazy2.py").read_text()
B = {"base": "pass", "lazy read": "lazy_read(P)",
 "lazy eq": "import _zip_directory as z\nf=z._fast(P); g=lazy_read(P); n=len(g); zipimport._zip_directory_cache[P]=g; load_all()\nprint(n, f==g)",
 "exit": "import os; os._exit(0)", "clear + exit": "import zipimport as z, os; z._zip_directory_cache.clear(); os._exit(0)"}
CASES = {k: PRE + "\n" + v for k, v in B.items()}
