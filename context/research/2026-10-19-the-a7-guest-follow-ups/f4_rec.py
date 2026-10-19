import sys, wasi_python
FORMS = {
 "unbounded, uncaught, limit L": "import sys\nsys.setrecursionlimit({L})\ndef f(): return f()\nf()",
 "unbounded, caught, limit L": "import sys\nsys.setrecursionlimit({L})\ndef f(): return f()\ntry:\n    f()\nexcept RecursionError as e:\n    print('RecursionError', e)",
 "bounded N=L-50, limit L": "import sys\nsys.setrecursionlimit({L})\ndef f(k): return 0 if k == 0 else f(k-1)+1\nprint('ok', f({L}-50))",
 "bounded via list.sort key": "import sys\nsys.setrecursionlimit({L})\ndef f(k): return 0 if k == 0 else sorted([1], key=lambda x: f(k-1))[0]\nprint('ok', f({L}-50))",
}
for L in (1000, 2000, 3000, 10000, 100000):
    for name, prog in FORMS.items():
        r = wasi_python.run(["-c", prog.format(L=L)], fuel=10**11, snapshot=sys.argv[1] == "snapshot")
        err = r.stderr.decode(errors="replace").strip().splitlines()
        print(L, name, "|", r.exit_code, r.trapped, "|", r.stdout.decode().strip()[:80], "|", err[-1][:100] if err else "", flush=True)
