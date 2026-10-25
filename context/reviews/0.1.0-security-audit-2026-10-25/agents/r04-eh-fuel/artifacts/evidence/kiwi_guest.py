# Guest program: a chain of N required equalities, then K calls in one mode.
#   fail: a required equality that conflicts; kiwi's C++ throws UnsatisfiableConstraint,
#         which the extension catches in C++ and turns into a Python exception.
#   weak: the same conflicting equality at weak strength, added and removed (no throw).
#   py:   pure-Python control, sum(range(20N)) per iteration.
#   none: no calls (baseline for setup cost).
import sys, time, kiwisolver as k
N, K, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
s = k.Solver()
xs = [k.Variable("x%d" % i) for i in range(N + 1)]
s.addConstraint(xs[0] == 0)
for i in range(N):
    s.addConstraint(xs[i + 1] == xs[i] + 1)
t = time.perf_counter()
caught = 0
for j in range(K):
    if mode == "fail":
        try:
            s.addConstraint(xs[N] == -1 - j)
        except k.UnsatisfiableConstraint:
            caught += 1
    elif mode == "weak":
        c = (xs[N] == -1 - j) | "weak"
        s.addConstraint(c)
        s.removeConstraint(c)
    elif mode == "py":
        sum(range(N * 20))
print("loop_s=%.4f caught=%d" % (time.perf_counter() - t, caught))
