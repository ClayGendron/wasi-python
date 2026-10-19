CASES = {
"unwrap_call": """
import inspect, os
from unittest.mock import call
try:
    inspect.unwrap(call)
    print("ok")
except (RecursionError, ValueError) as e:
    print(type(e).__name__, str(e)[:80])
""",
"doctest_find": """
import doctest, types
from unittest.mock import call
m = types.ModuleType("dummy"); m.__dict__['inject_call'] = call
print(doctest.DocTestFinder().find(m))
""",
"except_handler": """
import sys
def set_relative_recursion_limit(n):
    depth = 1
    while True:
        try:
            sys.setrecursionlimit(depth)
        except RecursionError:
            depth += 1
        else:
            break
    sys.setrecursionlimit(depth+n)
def recurse_in_except():
    try:
        1/0
    except:
        recurse_in_except()
def recurse_after_except():
    try:
        1/0
    except:
        pass
    recurse_after_except()
def recurse_in_body_and_except():
    try:
        recurse_in_body_and_except()
    except:
        recurse_in_body_and_except()
set_relative_recursion_limit(10)
for f in (recurse_in_except, recurse_after_except, recurse_in_body_and_except):
    try:
        f()
        print(f.__name__, "no error")
    except RecursionError as e:
        print(f.__name__, "RecursionError", e)
""",
"except_body_only": """
import sys
sys.setrecursionlimit(30)
def r():
    try:
        r()
    except:
        r()
try:
    r()
except RecursionError as e:
    print("RecursionError", e)
""",
}
