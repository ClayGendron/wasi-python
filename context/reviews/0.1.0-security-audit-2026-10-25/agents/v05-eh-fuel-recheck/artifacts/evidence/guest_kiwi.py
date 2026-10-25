# Guest: N-variable equality chain in kiwisolver, then K calls of one mode; prints loop time.
import sys, time
import kiwisolver as kw
n, k, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
solver = kw.Solver()
v = [kw.Variable("v%d" % i) for i in range(n + 1)]
solver.addConstraint(v[0] == 0)
for i in range(n):
    solver.addConstraint(v[i + 1] == v[i] + 1)
caught = 0
t0 = time.perf_counter()
for j in range(k):
    if mode == "fail":
        try:
            solver.addConstraint(v[n] == -1 - j)
        except kw.UnsatisfiableConstraint:
            caught += 1
    elif mode == "weak":
        c = (v[n] == -1 - j) | "weak"
        solver.addConstraint(c)
        solver.removeConstraint(c)
    elif mode == "ok":
        # The same required equality on the chain's end, but consistent with it: no throw.
        c = v[n] == n
        solver.addConstraint(c)
        solver.removeConstraint(c)
    elif mode == "py":
        sum(range(n * 20))
print("loop_s=%.4f caught=%d" % (time.perf_counter() - t0, caught))
