import sys, importlib
bad = []
for n in sorted(sys.builtin_module_names):
    if "." not in n:
        continue
    try:
        m = importlib.import_module(n)
    except Exception as e:
        bad.append((n, "import " + type(e).__name__))
        continue
    if m.__name__ != n:
        bad.append((n, m.__name__))
print(len([n for n in sys.builtin_module_names if "." in n]), bad)
