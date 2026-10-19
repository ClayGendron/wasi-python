import sys, wasi_python
FORMS = {
 "limit-reached": "import sys\nsys.setrecursionlimit({L})\ndef f(): return f()\ntry:\n    f()\nexcept RecursionError as e:\n    print('ok RecursionError')",
 "valueerror-at-depth": "import sys\nsys.setrecursionlimit(10**6)\ndef f(k):\n    if k == 0: raise ValueError('bottom')\n    return f(k-1)+1\ntry:\n    f({L})\nexcept ValueError:\n    print('ok ValueError')",
 "valueerror-caught-del-tb": "import sys\nsys.setrecursionlimit(10**6)\ndef f(k):\n    if k == 0: raise ValueError('bottom')\n    return f(k-1)+1\ntry:\n    f({L})\nexcept ValueError as e:\n    t = e.__traceback__\n    print('caught', flush=True)\n    del e\nprint('ok', flush=True)\ndel t\nprint('ok freed')",
}
def once(name, L, snap):
    r = wasi_python.run(["-c", FORMS[name].format(L=L)], fuel=10**11, snapshot=snap)
    return ("trap" if r.trapped else ("ok" if r.exit_code == 0 and r.stdout.decode().strip().splitlines()[-1].startswith("ok") else "other:" + r.stderr.decode()[-100:])), r.stdout.decode().strip().replace("\n", "/")
for name in FORMS:
    for L in (2000, 2500, 3000, 5000, 20000):
        print(name, L, once(name, L, True), flush=True)
