"""Depth edges at one stack: each case takes N and either frees (del) or acts then os._exit(0)."""
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
except SyntaxError as e:
    r = "SyntaxError " + str(e)
print(r, N, flush=True)
os._exit(0)
"""
FREE = """import os
N = {n}
{build}
del x
print("ok", N, flush=True)
os._exit(0)
"""
def c(build, act, hi): return (lambda n: T.replace("{n}", str(n)).replace("{build}", build).replace("{act}", act), hi)
def f(build, hi): return (lambda n: FREE.replace("{n}", str(n)).replace("{build}", build), hi)
LIST = "x = []\nfor i in range(N): x = [x]"
EXPAT = """import xml.parsers.expat as E
d = 0
def h(name, attrs):
    global d
    d += 1
    if d < N:
        p = E.ParserCreate(); p.StartElementHandler = h; p.Parse('<a/>', True)"""
SAX = """import xml.sax
d = 0
class H(xml.sax.ContentHandler):
    def startElement(self, n, a):
        global d
        d += 1
        if d < N: xml.sax.parseString(b'<a/>', H())"""
ETREE = """import xml.etree.ElementTree as ET
d = 0
class T(ET.TreeBuilder):
    def start(self, tag, attrs):
        global d
        d += 1
        if d < N: ET.fromstring('<a/>', parser=ET.XMLParser(target=T()))
        return super().start(tag, attrs)"""
HOOK = """import json
class O:
    def __init__(self, k): self.k = k
def dflt(o): return [O(o.k - 1)] if o.k > 0 else []"""
CASES = {
    "free_list": f(LIST, 20000),
    "free_dict": f("x = {}\nfor i in range(N): x = {'k': x}", 20000),
    "free_tuple": f("x = ()\nfor i in range(N): x = (x,)", 20000),
    "repr_list": c(LIST, "repr(x)", 20000),
    "json_dumps": c(LIST, "import json; json.dumps(x)", 20000),
    "json_loads": c("s = '[' * N + ']' * N", "import json; json.loads(s)", 20000),
    "eq_list": c(LIST + "\ny = []\nfor i in range(N): y = [y]", "x == y", 20000),
    "hash_tuple": c("x = ()\nfor i in range(N): x = (x,)", "hash(x)", 20000),
    "map_chain": c("it = iter([1])\nfor i in range(N): it = map(abs, it)", "next(it)", 20000),
    "json_default": c(HOOK, "json.dumps(O(N), default=dflt)", 20000),
    "eval_parens": c("s = '(' * N + '1' + ')' * N", "eval(s)", 199),
    "eval_unary": c("s = '-' * N + '1'", "eval(s)", 20000),
    "exc_group": c("g = ValueError(0)\nfor i in range(N): g = ExceptionGroup('g', [g])", "import traceback; traceback.format_exception(g)", 5000),
    "expat": c(EXPAT, "h(None, None)", 2000),
    "sax": c(SAX, "xml.sax.parseString(b'<a/>', H())", 2000),
    "etree_target": c(ETREE, "ET.fromstring('<a/>', parser=ET.XMLParser(target=T()))", 2000),
}
