"""Golden job: scipy's iterative solvers and integrators (spec 037, Decision 15). Usage:
scipy_solvers.py <data dir> <out dir> (both unused). Runs natively (the oracle) and in the guest;
its output must be byte-identical in both.

Floats print with 6 significant digits. Every solver and integrator is given a tolerance at least
1,000 times tighter than that, through the options its method actually takes (Nelder-Mead's
xatol and fatol, L-BFGS-B's ftol and gtol, SLSQP's ftol, hybr's xtol, BFGS's gtol, and xtol, ftol
and gtol for least_squares and curve_fit), with maxiter or maxfev far above what it needs, so
what prints is bounded by the tolerance, not by the path a step took. Each result's `success`
prints too: a stop on a cap would read False. A value at a minimum that is 0 prints as a bound.
"""

import sys

import numpy as np
import scipy
from scipy import integrate, optimize


def g(x, k=6):
    return format(float(x) + 0.0, f".{k}g")


def gs(values, k=6):
    return " ".join(g(v, k) for v in np.ravel(values))


def show(label, fn):
    try:
        out = fn()
    except Exception as e:  # the golden records a failure as text, so a difference names it
        out = f"RAISES {type(e).__name__} {str(e)[:120]}"
    print(label, "->", out)


def minimum(r):
    return f"success={r.success} x={gs(r.x)} fun<1e-12={bool(r.fun < 1e-12)}"


print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} scipy={scipy.__version__}")
x0 = np.array([-1.2, 1.0])
rosen, rosen_der = optimize.rosen, optimize.rosen_der

# optimize
show(
    "BFGS",
    lambda: minimum(
        optimize.minimize(
            rosen, x0, jac=rosen_der, method="BFGS", options={"gtol": 1e-10, "maxiter": 10_000}
        )
    ),
)
show(
    "Nelder-Mead",
    lambda: minimum(
        optimize.minimize(
            rosen,
            x0,
            method="Nelder-Mead",
            options={"xatol": 1e-10, "fatol": 1e-14, "maxiter": 100_000, "maxfev": 100_000},
        )
    ),
)
show(
    "L-BFGS-B",
    lambda: minimum(
        optimize.minimize(
            rosen,
            x0,
            jac=rosen_der,
            method="L-BFGS-B",
            options={"ftol": 1e-15, "gtol": 1e-10, "maxiter": 10_000},
        )
    ),
)


def slsqp():
    cons = [
        {"type": "ineq", "fun": lambda x: x[0] - 2 * x[1] + 2},
        {"type": "ineq", "fun": lambda x: -x[0] - 2 * x[1] + 6},
        {"type": "ineq", "fun": lambda x: -x[0] + 2 * x[1] + 2},
    ]
    r = optimize.minimize(
        lambda x: (x[0] - 1) ** 2 + (x[1] - 2.5) ** 2,
        [2.0, 0.0],
        method="SLSQP",
        bounds=[(0, None), (0, None)],
        constraints=cons,
        options={"ftol": 1e-12, "maxiter": 10_000},
    )
    return f"success={r.success} x={gs(r.x)} fun={g(r.fun)}"


show("SLSQP", slsqp)


def hybr():
    r = optimize.root(
        lambda x: [x[0] + 0.5 * (x[0] - x[1]) ** 3 - 1.0, 0.5 * (x[1] - x[0]) ** 3 + x[1]],
        [0.0, 0.0],
        method="hybr",
        options={"xtol": 1e-12, "maxfev": 100_000},
    )
    return f"success={r.success} x={gs(r.x)}"


show("root hybr", hybr)

t = np.linspace(0.0, 4.0, 25)
rng = np.random.Generator(np.random.PCG64(370))
y = 2.5 * np.exp(-1.3 * t) + 0.5 + 0.01 * rng.standard_normal(t.size)


def model(p, tt):
    return p[0] * np.exp(-p[1] * tt) + p[2]


def lsq():
    r = optimize.least_squares(
        lambda p: model(p, t) - y,
        [1.0, 1.0, 0.0],
        xtol=1e-12,
        ftol=1e-12,
        gtol=1e-12,
        max_nfev=100_000,
    )
    return f"success={r.success} x={gs(r.x)} cost={g(r.cost)}"


show("least_squares", lsq)


def fit():
    p, cov = optimize.curve_fit(
        lambda tt, a, k, c: model((a, k, c), tt),
        t,
        y,
        p0=[1.0, 1.0, 0.0],
        xtol=1e-12,
        ftol=1e-12,
        gtol=1e-12,
        maxfev=100_000,
    )
    return f"p={gs(p)} sd={gs(np.sqrt(np.diag(cov)))}"


show("curve_fit", fit)
show("brentq", lambda: g(optimize.brentq(lambda x: x**3 - 2 * x - 5, 2.0, 3.0, xtol=1e-14)))


def lp():
    r = optimize.linprog(
        [-1.0, 4.0],
        A_ub=[[-3.0, 1.0], [1.0, 2.0]],
        b_ub=[6.0, 4.0],
        bounds=[(None, None), (-3, None)],
        method="highs",
    )
    return f"status={r.status} x={gs(r.x)} fun={g(r.fun)}"


show("linprog", lp)


def mip():
    from scipy.optimize import Bounds, LinearConstraint, milp

    r = milp(
        c=[-1.0, -2.0],
        constraints=LinearConstraint(
            [[-1.0, 1.0], [3.0, 2.0], [2.0, 3.0]], [-np.inf, -np.inf, -np.inf], [1.0, 12.0, 12.0]
        ),
        integrality=[1, 1],
        bounds=Bounds([0, 0], [np.inf, np.inf]),
    )
    return f"status={r.status} x={gs(r.x)} fun={g(r.fun)}"


show("milp", mip)
cost = np.array([[4.0, 1.0, 3.0], [2.0, 0.0, 5.0], [3.0, 2.0, 2.0]])
show("linear_sum_assignment", lambda: [v.tolist() for v in optimize.linear_sum_assignment(cost)])

# integrate
show(
    "quad",
    lambda: (lambda r: g(r[0]))(
        integrate.quad(
            lambda x: np.exp(-x * x) * np.cos(3 * x),
            0.0,
            np.inf,
            epsabs=1e-13,
            epsrel=1e-11,
            limit=500,
        )
    ),
)
show(
    "dblquad",
    lambda: (lambda r: g(r[0]))(
        integrate.dblquad(
            lambda yy, xx: xx * yy * np.exp(-xx - yy),
            0.0,
            2.0,
            0.0,
            lambda xx: xx,
            epsabs=1e-13,
            epsrel=1e-11,
        )
    ),
)


def oscillator(_t, z):
    return [z[1], -4.0 * z[0] - 0.3 * z[1]]


def ivp(method):
    r = integrate.solve_ivp(
        oscillator, (0.0, 5.0), [1.0, 0.0], method=method, rtol=1e-10, atol=1e-12
    )
    return f"success={r.success} y(5)={gs(r.y[:, -1])}"


show("solve_ivp RK45", lambda: ivp("RK45"))
show("solve_ivp BDF", lambda: ivp("BDF"))
show(
    "odeint",
    lambda: gs(
        integrate.odeint(
            lambda z, _t: oscillator(_t, z), [1.0, 0.0], [0.0, 2.5, 5.0], rtol=1e-10, atol=1e-12
        )[1:]
    ),
)
show(
    "simpson",
    lambda: g(
        integrate.simpson(np.sin(np.linspace(0.0, np.pi, 41)), x=np.linspace(0.0, np.pi, 41))
    ),
)
