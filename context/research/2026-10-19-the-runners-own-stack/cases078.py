"""The recursion shapes of spec 071's README list, its research memo (A1) and the 0.1.0a7 security
review's F4, each a function of its depth N. A case either acts and exits (os._exit, so freeing is
not what is measured) or frees (del)."""
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
except Exception as e:
    r = type(e).__name__ + " " + str(e)[:80]
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
DEEP_TREE = """from lxml import etree
root = etree.Element('a'); e = root
for i in range(N): e = etree.SubElement(e, 'a')"""
XSLT_CALL = """from lxml import etree
x = etree.XSLT(etree.XML('''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/"><xsl:call-template name="r"><xsl:with-param name="n" select="%d"/></xsl:call-template></xsl:template>
<xsl:template name="r"><xsl:param name="n"/><xsl:if test="$n &gt; 0"><xsl:call-template name="r"><xsl:with-param name="n" select="$n - 1"/></xsl:call-template></xsl:if></xsl:template>
</xsl:stylesheet>''' % N))"""
XSLT_APPLY = DEEP_TREE + """
x = etree.XSLT(etree.XML('''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="a"><b><xsl:apply-templates/></b></xsl:template></xsl:stylesheet>'''))"""
PYREC = """sys.setrecursionlimit(N + 200)
def g(n): return g(n - 1) + 1 if n else 0"""
CASES = {
    "free_list": f(LIST, 400000),
    "free_tuple": f("x = ()\nfor i in range(N): x = (x,)", 400000),
    "free_dict": f("x = {}\nfor i in range(N): x = {'k': x}", 400000),
    "repr_list": c(LIST, "repr(x)", 400000),
    "json_dumps": c(LIST, "import json; json.dumps(x)", 400000),
    "json_loads": c("s = '[' * N + ']' * N", "import json; json.loads(s)", 400000),
    "eq_list": c(LIST + "\ny = []\nfor i in range(N): y = [y]", "x == y", 400000),
    "hash_tuple": c("x = ()\nfor i in range(N): x = (x,)", "hash(x)", 400000),
    "map_chain": c("it = iter([1])\nfor i in range(N): it = map(abs, it)", "next(it)", 400000),
    "json_default": c(HOOK, "json.dumps(O(N), default=dflt)", 400000),
    "eval_parens": c("s = '(' * N + '1' + ')' * N", "eval(s)", 199),
    "eval_unary": c("s = '-' * N + '1'", "eval(s)", 400000),
    "compile_terms": c("s = '+'.join(['1'] * N)", "compile(s, 's', 'eval')", 400000),
    "exc_group": c("g = ValueError(0)\nfor i in range(N): g = ExceptionGroup('g', [g])", "import traceback; traceback.format_exception(g)", 100000),
    "expat": c(EXPAT, "h(None, None)", 20000),
    "sax": c(SAX, "xml.sax.parseString(b'<a/>', H())", 20000),
    "etree_target": c(ETREE, "ET.fromstring('<a/>', parser=ET.XMLParser(target=T()))", 20000),
    "py_recursion_limit_raised": c(PYREC, "g(N)", 400000),
    "xpath_parens": c("from lxml import etree", "etree.XML('<a/>').xpath('(' * N + '1' + ')' * N)", 6000),
    "xpath_predicates": c("from lxml import etree", "etree.XML('<a/>').xpath('/a' + '[1]' * N)", 6000),
    "xslt_call_template": c(XSLT_CALL, "x(etree.XML('<a/>'))", 4000),
    "xslt_apply_templates": c(XSLT_APPLY, "x(etree.ElementTree(root))", 4000),
    "c14n_deep_tree": c(DEEP_TREE, "etree.tostring(root, method='c14n')", 400000),
}
PYREC_UNBOUNDED = """sys.setrecursionlimit(N)
def f(): f()"""
CASES["py_unbounded_limit_raised"] = c(PYREC_UNBOUNDED, "f()", 1000000)
CASES["py_unbounded_print_tb"] = c(PYREC_UNBOUNDED + "\nimport traceback", "f()\n    r = 'none'\nexcept RecursionError as e:\n    traceback.print_exc()\n    r = 'printed'\n    print(r, N, flush=True); os._exit(0)\ntry:\n    pass", 1000000)
