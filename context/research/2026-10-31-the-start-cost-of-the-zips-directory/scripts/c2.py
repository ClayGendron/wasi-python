from pathlib import Path
PRE = (Path(__file__).parent / "parts.py").read_text()
B = {
 "base": "pass",
 "cd read": "stage(P, 0)",
 "unpack": "stage(P, 1)",
 "+names": "stage(P, 2)",
 "+paths": "stage(P, 3)",
 "+tuples": "stage(P, 4)",
 "+dict insert": "stage(P, 5)",
 "+implied (=recipe)": "stage(P, 6)",
 "recipe _fast": "import _zip_directory as z; z._fast(P)",
 "recipe _fast gc off": "import _zip_directory as z; gc.disable(); z._fast(P)",
 "stage5 + implied_sorted": "implied_sorted(stage(P, 5))",
 "recipe _fast + clear": "import _zip_directory as z; z._fast(P).clear()",
 "recipe _fast + dumps": "import _zip_directory as z; b = marshal.dumps(z._fast(P))",
 "recipe _fast + dumps + loads": "import _zip_directory as z; b = marshal.dumps(z._fast(P)); marshal.loads(b)",
 "len dumps": "import _zip_directory as z; print(len(marshal.dumps(z._fast(P))))",
 "eq check": "import _zip_directory as z; f=z._fast(P); g=implied_sorted(stage(P,5)); print(f==g, list(f)==list(g), len(f))",
 "cache clear": "import zipimport as z; z._zip_directory_cache.clear()",
 "exit": "import os; os._exit(0)",
 "cache clear + exit": "import zipimport as z, os; z._zip_directory_cache.clear(); os._exit(0)",
}
CASES = {k: PRE + "\n" + v for k, v in B.items()}
