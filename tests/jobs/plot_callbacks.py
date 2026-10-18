"""Golden job: the callbacks spec 023's carried patches fixed (Usage: plot_callbacks.py <data dir>
<out dir>).

Each of kiwisolver's 17 no-argument methods and 4 strength getters, and Pillow's two Arrow export
methods, is called once. Each was defined with fewer parameters than CPython calls it with, and
trapped the guest (`indirect call type mismatch`) before kiwisolver's patch 0001 and Pillow's patch
0001. `Solver.dump()` prints from C, so Python's output is flushed before it and it goes last.
"""

import sys

import kiwisolver as k
from PIL import Image

print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} kiwisolver={k.__version__}")
x = k.Variable("x")
x.setContext("ctx")
s = k.Solver()
c = x + 2 >= 10
s.addConstraint(c)
s.updateVariables()
e = c.expression()
t = e.terms()[0]
print(x.name(), x.context(), x.value())
print(c.op(), c.strength(), c.violated(), e.constant(), e.value(), len(e.terms()))
print(t.variable().name(), t.coefficient(), t.value())
print(k.strength.weak, k.strength.medium, k.strength.strong, k.strength.required)
print(len(s.dumps()) > 0)
s.reset()
print(x.value())
im = Image.new("RGBA", (2, 2), (1, 2, 3, 4))
print(type(im.im.__arrow_c_schema__()).__name__, type(im.im.__arrow_c_array__()).__name__)

sys.stdout.flush()
s.dump()
