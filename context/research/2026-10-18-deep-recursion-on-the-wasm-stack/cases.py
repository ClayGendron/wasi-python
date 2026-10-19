"""Guest cases. Each prints one line: the outcome, and a depth where it can count one.

A case that counts writes its depth to fd 2 at every level, so a trap still leaves the last depth.
"""

COUNTED = '''
import os, sys
n = 0
def mark():
    global n
    n += 1
    os.write(2, b"%d\\n" % n)
{body}
try:
    go()
    print("ok", n)
except RecursionError as e:
    print("RecursionError", n, e)
except MemoryError as e:
    print("MemoryError", n, e)
'''

NESTED = '''
import sys
N = {n}
{build}
try:
    {act}
    print("ok", N)
except RecursionError as e:
    print("RecursionError", N, e)
except MemoryError as e:
    print("MemoryError", N, e)
except ValueError as e:
    print("ValueError", N, e)
'''


def counted(body: str) -> str:
    return COUNTED.replace("{body}", body)


def nested(n: int, build: str, act: str) -> str:
    return NESTED.replace("{n}", str(n)).replace("{build}", build).replace("{act}", act)


LIST = "l = []\nfor i in range(N): l = [l]"
DICT = "d = {}\nfor i in range(N): d = {'k': d}"
TUPLE = "t = ()\nfor i in range(N): t = (t,)"

CASES = {
    "hello": "print('hello')",
    "py_recursion": counted("def f():\n    mark(); f()\ndef go(): f()"),
    "repr_self": counted(
        "class A:\n    def __repr__(self):\n        mark(); return repr(self)\ndef go(): repr(A())"
    ),
    "getattr_self": counted(
        "class A:\n    def __getattr__(self, k):\n        mark(); return getattr(self, k)\n"
        "def go(): A().x"
    ),
    "eq_self": counted(
        "class A:\n    def __eq__(self, o):\n        mark(); return self == o\ndef go(): A() == 1"
    ),
    "len_self": counted("class A:\n    def __len__(self):\n        mark(); return len(self)\ndef go(): len(A())"),
    "map_lambda": counted(
        "def go():\n    f = lambda x: (mark(), list(map(f, [x])))\n    f(1)"
    ),
    "sorted_key": counted("def k(x):\n    mark(); return sorted([1], key=k)\ndef go(): k(1)"),
    "repr_list_1e5": nested(100000, LIST, "repr(l)"),
    "repr_list_1e4": nested(10000, LIST, "repr(l)"),
    "repr_list_1e3": nested(1000, LIST, "repr(l)"),
    "repr_dict_1e5": nested(100000, DICT, "repr(d)"),
    "eq_list_1e5": nested(100000, LIST, "l == eval('l')"),
    "hash_tuple_1e5": nested(100000, TUPLE, "hash(t)"),
    "json_dumps_1e5": nested(100000, LIST, "import json; json.dumps(l)"),
    "json_loads_1e5": nested(100000, "s = '[' * N + ']' * N", "import json; json.loads(s)"),
    "pickle_dumps_1e5": nested(100000, LIST, "import pickle; pickle.dumps(l)"),
    "pickle_loads_1e5": nested(100000, "import pickle\ns = b'(' * 0", "pickle.loads(b'\\x80\\x04' + b']' * N + b'a' * (N - 1) + b'.')"),
    "copy_deepcopy_1e5": nested(100000, LIST, "import copy; copy.deepcopy(l)"),
    "eval_parens_1e3": nested(1000, "s = '(' * N + ')' * N", "eval(s)"),
    "eval_unary_1e5": nested(100000, "s = '-' * N + '1'", "eval(s)"),
    "eval_binop_1e5": nested(100000, "s = '1' + '+1' * N", "eval(s)"),
    "eval_list_1e5": nested(100000, "s = '[' * N + ']' * N", "eval(s)"),
    "compile_nested_if": nested(
        2000, "s = ''.join(' ' * i + 'if 1:\\n' for i in range(N)) + ' ' * N + 'pass\\n'", "compile(s, 's', 'exec')"
    ),
    "ast_literal_1e5": nested(100000, "s = '[' * N + ']' * N", "import ast; ast.literal_eval(s)"),
    "re_nested_groups": nested(10000, "s = '(' * N + 'a' + ')' * N", "import re; re.compile(s)"),
    "re_backtrack": nested(30, "s = 'a' * N + 'b'", "import re; re.match('(a*)*c', s)"),
    "str_format_nested": nested(100000, LIST, "'{}'.format(l)"),
    "exc_context_1e5": nested(
        100000,
        "e = None\nfor i in range(N):\n    x = ValueError(i); x.__context__ = e; e = x",
        "import traceback; traceback.format_exception(e)",
    ),
    "exc_group_1e4": nested(
        10000,
        "g = ValueError(0)\nfor i in range(N): g = ExceptionGroup('g', [g])",
        "import traceback; traceback.format_exception(g)",
    ),
    "partial_recursive_repr": counted(
        "import functools\ndef go():\n    f = functools.partial(min)\n    f.__setstate__((f, (), {}, {}))\n    repr(f)"
    ),
    "partial_recursive_pickle": nested(
        0,
        "import functools, pickle\nf = functools.partial(min)\nf.__setstate__((f, (), {}, {}))",
        "pickle.dumps(f)",
    ),
    "map_chain_1e5": nested(100000, "it = iter([1])\nfor i in range(N): it = map(abs, it)", "next(it)"),
    "numpy_objarr_1e4": nested(
        10000,
        "import numpy as np\nx = None\nfor i in range(N):\n    y = np.empty((), object); y[()] = x; x = y",
        "repr(x)",
    ),
    "pandas_nested_repr": nested(
        10000, "import pandas as pd\n" + LIST, "repr(pd.Series([l]))"
    ),
    "setrecursionlimit_1e5": counted(
        "import sys\nsys.setrecursionlimit(100000)\nclass A:\n    def __repr__(self):\n"
        "        mark(); return repr(self)\ndef go(): repr(A())"
    ),
}

CASES.update({
    "property_self": counted("class A:\n    @property\n    def x(self):\n        mark(); return self.x\ndef go(): A().x"),
    "init_self": counted("class A:\n    def __init__(self):\n        mark(); A()\ndef go(): A()"),
    "hash_self": counted("class A:\n    def __hash__(self):\n        mark(); return hash(self)\ndef go(): hash(A())"),
    "str_self": counted("class A:\n    def __str__(self):\n        mark(); return str(self)\ndef go(): str(A())"),
    "format_self": counted("class A:\n    def __format__(self, s):\n        mark(); return format(self, s)\ndef go(): format(A(), '')"),
    "iter_self": counted("class A:\n    def __iter__(self):\n        mark(); return iter(self)\ndef go(): iter(A())"),
    "eval_rec": counted("def f():\n    mark(); return eval('f()')\ndef go(): f()"),
    "exec_rec": counted("def f():\n    mark(); exec('f()')\ndef go(): f()"),
    "gen_chain": counted("def g():\n    mark(); yield from g()\ndef go(): next(g())"),
    "lru_rec": counted("import functools\n@functools.lru_cache(None)\ndef f(k):\n    mark(); return f(k + 1)\ndef go(): f(0)"),
    "reduce_rec": counted("import functools\ndef f(a, b):\n    mark(); return functools.reduce(f, [1, 2])\ndef go(): f(0, 0)"),
    "min_key": counted("def k(x):\n    mark(); return min([1, 2], key=k)\ndef go(): k(1)"),
    "dataclass_repr": counted("import dataclasses\n@dataclasses.dataclass\nclass N:\n    n: object = None\ndef go():\n    x = N(); x.n = x\n    class M:\n        def __repr__(s):\n            mark(); return repr([s])\n    repr(M())"),
    "pickle_reduce": counted("import pickle\nclass A:\n    def __reduce__(self):\n        mark(); return (A, (A(),))\ndef go(): pickle.dumps(A())"),
    "json_default": counted("import json\ndef d(o):\n    mark(); return [object()]\ndef go(): json.dumps(object(), default=d)"),
    "numpy_vectorize": counted("import numpy as np\ndef f(x):\n    mark(); return np.vectorize(f)(np.array([x]))[0]\ndef go(): f(1)"),
    "numpy_frompyfunc": counted("import numpy as np\ndef f(x):\n    mark(); return u(x)\nu = np.frompyfunc(f, 1, 1)\ndef go(): f(1)"),
    "numpy_apply_along": counted("import numpy as np\ndef f(a):\n    mark(); return np.apply_along_axis(f, 0, a)\ndef go(): f(np.zeros(1))"),
    "pandas_apply": counted("import pandas as pd\ndef f(x):\n    mark(); return pd.Series([x]).apply(f)\ndef go(): f(1)"),
    "pandas_map": counted("import pandas as pd\ndef f(x):\n    mark(); return pd.Series([x]).map(f).iloc[0]\ndef go(): f(1)"),
    "re_sub_rec": counted("import re\ndef r(m):\n    mark(); return re.sub('a', r, 'a')\ndef go(): r(None)"),
    "sorted_cmp": counted("import functools\ndef c(a, b):\n    mark(); sorted([1, 2], key=functools.cmp_to_key(c)); return 0\ndef go(): c(1, 2)"),
})
