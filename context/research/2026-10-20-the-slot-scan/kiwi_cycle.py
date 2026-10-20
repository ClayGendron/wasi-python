# Spec 096: one garbage cycle through all four kiwisolver types. CPython's delete_garbage
# (Python/gc.c) calls tp_clear on the collectable objects in their tracking order, here the
# order of allocation: the Variable, the Term, the Expression, the Constraint, then the list.
# The list holds every one of them and itself, so each object is still alive when its turn
# comes, and each type's tp_clear is called through its pointer in turn.
import gc
import kiwisolver as kiwi

gc.disable()
v = kiwi.Variable("x")
t = v * 2.0
e = t + 1.0
c = e >= 0.0
hold = [v, t, e, c]
hold.append(hold)
v.setContext(hold)
print(type(t).__name__, type(e).__name__, type(c).__name__)
del v, t, e, c, hold
print("collected", gc.collect() >= 5)
print("ok")
