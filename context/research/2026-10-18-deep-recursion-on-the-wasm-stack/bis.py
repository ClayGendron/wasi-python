"""Depth cases: each builds a structure of depth N, acts on it, prints, and leaves with os._exit(0)
so that freeing the structure is not part of the case (the *_free cases measure freeing alone)."""
T = """import os, sys
N = {n}
{build}
try:
    {act}
    r = "ok"
except RecursionError as e:
    r = "RecursionError " + str(e)
except MemoryError as e:
    r = "MemoryError " + str(e)
os.write(1, (r + "\\n").encode())
os._exit(0)
"""
LIST = "l = []\nfor i in range(N): l = [l]"
DICT = "d = {}\nfor i in range(N): d = {'k': d}"
TUPLE = "t = ()\nfor i in range(N): t = (t,)"
def c(build, act, hi=100000):
    return (lambda n: T.replace("{n}", str(n)).replace("{build}", build).replace("{act}", act), hi)
CASES = {
    "list_free": c(LIST, "l = None"),
    "dict_free": c(DICT, "d = None"),
    "tuple_free": c(TUPLE, "t = None"),
    "repr_list": c(LIST, "repr(l)"),
    "json_dumps": c(LIST, "import json; json.dumps(l)"),
    "json_loads": c("s = '[' * N + ']' * N", "import json; json.loads(s)"),
    "pickle_dumps": c(LIST, "import pickle; pickle.dumps(l)"),
    "hash_tuple": c(TUPLE, "hash(t)"),
    "eq_list": c(LIST + "\nm = []\nfor i in range(N): m = [m]", "l == m"),
    "eval_binop": c("s = '1' + '+1' * N", "eval(s)"),
    "map_chain": c("it = iter([1])\nfor i in range(N): it = map(abs, it)", "next(it)"),
    "exc_context": c("e = None\nfor i in range(N):\n    x = ValueError(i); x.__context__ = e; e = x", "import traceback; traceback.format_exception(e)", 20000),
    "repr_self_limit": c("sys.setrecursionlimit(100000)\nclass A:\n    def __repr__(self): return repr(self)", "repr(A())", 1),
}
NODE = "class Node:\n    __slots__ = ('next',)\nn = None\nfor i in range(N):\n    x = Node(); x.next = n; n = x"
CASES.update({
    "node_free": c(NODE, "n = None"),
    "lru_fib": c("import functools\n@functools.lru_cache(None)\ndef f(k): return 0 if k == 0 else f(k - 1) + 1", "f(N)", 990),
    "repr_list_obj": c(LIST, "str(l)"),
})
CASES.update({
    "eval_unary": c("s = '-' * N + '1'", "eval(s)", 100000),
    "eval_parens": c("s = '(' * N + '1' + ')' * N", "eval(s)", 199),
    "eval_lists": c("s = '[' * N + ']' * N", "eval(s)", 199),
    "eval_attr": c("s = 'x' + '.y' * N", "compile(s, 's', 'eval')", 100000),
    "eval_call": c("s = 'f' + '()' * N", "compile(s, 's', 'eval')", 100000),
    "eval_not": c("s = 'not ' * N + '1'", "compile(s, 's', 'eval')", 100000),
    "eval_power": c("s = '2' + '**2' * N", "compile(s, 's', 'eval')", 100000),
    "exc_group": c("g = ValueError(0)\nfor i in range(N): g = ExceptionGroup('g', [g])", "import traceback; traceback.format_exception(g)", 20000),
    "set_free": c("s = frozenset()\nfor i in range(N): s = frozenset([s])", "s = None"),
})
