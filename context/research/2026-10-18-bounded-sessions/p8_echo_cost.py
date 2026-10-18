"""P8: what echoing a turn's final expression costs, in fuel, through wasi_python.run on the
published snapshot: `ast` already imported? and a parse to AST plus compile against a plain compile."""
from wasi_python import run
SRC = "import math\nvalues = [math.sqrt(i) for i in range(100)]\ntotal = sum(values)\ntotal * 2\n"
pre = run(["-c", "import sys; print('ast' in sys.modules, 'linecache' in sys.modules)"], fuel=10**10)
print("P8 ast, linecache pre-imported in the snapshot:", pre.stdout.decode().strip())
base = "import sys\nsrc = %r\n" % SRC
plain = base + "for _ in range(100): compile(src, '<turn 1>', 'exec')\n"
echo = base + ("import ast\nfor _ in range(100):\n"
               "    tree = ast.parse(src, '<turn 1>')\n"
               "    last = tree.body.pop()\n"
               "    compile(tree, '<turn 1>', 'exec')\n"
               "    compile(ast.Expression(last.value), '<turn 1>', 'eval')\n")
imp = "import ast\n"
empty = "pass\n"
f = {}
for name, prog in (("empty", empty), ("import ast", imp), ("100 plain compiles", plain), ("100 echo compiles", echo)):
    runs = [run(["-c", prog], fuel=10**11).fuel_used for _ in range(3)]
    f[name] = min(runs)
    print(f"P8 {name}: fuel {runs}")
print("P8 per turn: plain compile %.0f, echo compile %.0f, import ast once %.0f" % (
    (f["100 plain compiles"] - f["empty"]) / 100, (f["100 echo compiles"] - f["import ast"]) / 100,
    f["import ast"] - f["empty"]))
