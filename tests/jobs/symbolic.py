"""Golden job: symbolic mathematics with sympy and mpmath (spec 039, Decisions 6 and 11).

Usage: symbolic.py <data dir> <out dir> (both unused). sympy solves, factors, expands,
integrates, differentiates, takes a limit and a series, inverts a matrix, finds eigenvalues,
solves an ODE, simplifies a float, adds rationals, evaluates pi to 40 digits, tests a Mersenne
prime and prints LaTeX. `lambdify` names `modules="numpy"`: sympy's default adds scipy when it
imports, so after spec 037 the job would pay for scipy for a reason outside this family;
`modules="numpy"` still runs `from numpy import *`, which reaches numpy.ctypeslib through the
ctypes stand-in. mpmath works at 30 digits.
"""

from importlib.metadata import version

import mpmath
import sympy as sp

print("versions", " ".join(f"{d}={version(d)}" for d in ("sympy", "mpmath")))

x, y = sp.symbols("x y")
print(sp.solve(x**2 - 2, x), sp.factor(x**3 - x), sp.expand((x + y) ** 3))
print(sp.integrate(sp.sin(x) ** 2, x), sp.integrate(sp.exp(-(x**2)), (x, -sp.oo, sp.oo)))
print(
    sp.diff(sp.atan(x) * sp.exp(x), x),
    sp.limit(sp.sin(x) / x, x, 0),
    sp.series(sp.cos(x), x, 0, 6),
)
print(sp.Matrix([[1, 2], [3, 4]]).inv(), sp.Matrix([[2, 1], [1, 2]]).eigenvals())
f = sp.Function("f")
print(sp.dsolve(f(x).diff(x, 2) + f(x), f(x)))
print(
    sp.nsimplify(0.333333333333),
    sp.Rational(3, 7) + sp.Rational(1, 7),
    sp.N(sp.pi, 40),
    sp.isprime(2**61 - 1),
)
print(
    sp.latex(sp.Integral(sp.sqrt(x), (x, 0, 1))),
    sp.lambdify(x, x**2 + 1, modules="numpy")(3),
)
mpmath.mp.dps = 30
print(mpmath.pi, mpmath.quad(mpmath.exp, [0, 1]), mpmath.zeta(3))
