CASES = {
 "pass": "pass",
 "os._exit(0)": "import os; os._exit(0)",
 "unfreeze+exit": "import gc, os; gc.unfreeze(); os._exit(0)",
 "atexit+flush+exit": "import atexit, sys, os; atexit._run_exitfuncs(); sys.stdout.flush(); sys.stderr.flush(); os._exit(0)",
 "collect young+exit": "import gc, os; gc.collect(); os._exit(0)",
 "unfreeze+collect+exit": "import gc, os; gc.unfreeze(); gc.collect(); os._exit(0)",
}
