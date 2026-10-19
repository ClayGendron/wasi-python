"""The README's trap rows, re-measured on one artifact set (spec 086, Decision 8).

    WASI_PYTHON_ARTIFACTS=<set> uv run python readme_edges.py > edges.jsonl

For each row, bisects between a depth that completes and one that traps, through
wasi_python.run, metered (fuel cap 10**11, as spec 071's limits were measured), on the snapshot and
the plain binary. The programs are spec 071's (tests/checks/test_v1_2_hostile_guest.py, LIMITS)
and spec 087's (its research folder, f4_edges.py), unchanged; this file runs them over every row
with each row's bounds. Counts depths, never time.
"""
import json

PRE = "import os, sys\nN = {n}\n"
import wasi_python

KINDS = {
  "setrecursionlimit": PRE + """sys.setrecursionlimit(10**6)
def f(k):
    return 0 if k == 0 else f(k - 1) + 1
print('ok', f(N), flush=True)
os._exit(0)""",
  "xpath-parens": PRE + """from lxml import etree
print('ok', etree.XML(b'<a/>').xpath('(' * N + '1' + ')' * N), flush=True)
os._exit(0)""",
  "xpath-predicates": PRE + """from lxml import etree
print('ok', len(etree.XML(b'<r><a/></r>').xpath('a' + '[1]' * N)), flush=True)
os._exit(0)""",
  "xslt-call-template": PRE + """from lxml import etree
X = 'http://www.w3.org/1999/XSL/Transform'
sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="/"><o><xsl:call-template name="t"><xsl:with-param name="n" select="{{N}}"/></xsl:call-template></o></xsl:template>
<xsl:template name="t"><xsl:param name="n"/><xsl:if test="$n &gt; 0"><xsl:call-template name="t"><xsl:with-param name="n" select="$n - 1"/></xsl:call-template></xsl:if></xsl:template>
</xsl:stylesheet>'''
print('ok', len(str(etree.XSLT(etree.XML(sheet.encode()))(etree.XML(b'<x/>')))), flush=True)
os._exit(0)""",
  "xslt-apply-templates": PRE + """from lxml import etree
X = 'http://www.w3.org/1999/XSL/Transform'
root = e = etree.Element('a')
for i in range(N - 1): e = etree.SubElement(e, 'a')
sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="*"><xsl:copy><xsl:apply-templates/></xsl:copy></xsl:template></xsl:stylesheet>'''
print('ok', etree.XSLT(etree.XML(sheet.encode()))(root).getroot().tag, flush=True)
os._exit(0)""",
  "c14n": PRE + """from lxml import etree
root = e = etree.Element('a')
for i in range(N - 1): e = etree.SubElement(e, 'a')
print('ok', len(etree.tostring(root, method='c14n')), flush=True)
os._exit(0)""",
  "relaxng": PRE + """from lxml import etree
rng = etree.RelaxNG(etree.XML(b'''<grammar xmlns="http://relaxng.org/ns/structure/1.0">
<start><ref name="A"/></start>
<define name="A"><element name="a"><optional><ref name="A"/></optional></element></define></grammar>'''))
root = e = etree.Element('a')
for i in range(N - 1): e = etree.SubElement(e, 'a')
print('ok', rng.validate(root), flush=True)
os._exit(0)""",
  "xslt-apply-bare": PRE + """from lxml import etree
X = 'http://www.w3.org/1999/XSL/Transform'
root = e = etree.Element('a')
for i in range(N - 1): e = etree.SubElement(e, 'a')
sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="*"><xsl:apply-templates/></xsl:template></xsl:stylesheet>'''
print('ok', len(str(etree.XSLT(etree.XML(sheet.encode()))(root))), flush=True)
os._exit(0)""",
  "limit-reached": PRE + """sys.setrecursionlimit(N)
def f(): return f()
try:
    f()
except RecursionError:
    print('ok', flush=True)
os._exit(0)""",
  "traceback-freed": PRE + """sys.setrecursionlimit(10**6)
def f(k):
    if k == 0: raise ValueError('bottom')
    return f(k - 1) + 1
try:
    f(N)
except ValueError:
    pass
print('ok', flush=True)
os._exit(0)""",
}

KINDS.update({
  "free-list": "import os\nN = {n}\nx = []\nfor i in range(N): x = [x]\ndel x\nprint('ok', flush=True)",
  "free-dict": "import os\nN = {n}\nx = {{}}\nfor i in range(N): x = {{'a': x}}\ndel x\nprint('ok', flush=True)",
  "json-loads": "import json, os\nN = {n}\nx = json.loads('[' * N + ']' * N)\nprint('ok', flush=True)\nos._exit(0)",
  "repr-nested": "import os\nN = {n}\nx = []\nfor i in range(N): x = [x]\nrepr(x)\nprint('ok', flush=True)\nos._exit(0)",
  "eq-nested": "import os\nN = {n}\na, b = [], []\nfor i in range(N): a, b = [a], [b]\nprint('ok', a == b, flush=True)\nos._exit(0)",
  "eval-parens": "import os\nN = {n}\neval('(' * N + '1' + ')' * N)\nprint('ok', flush=True)\nos._exit(0)",
  "expat-handler": """import os
import xml.parsers.expat as E
N, d = {n}, 0
def h(name, attrs):
    global d
    d += 1
    if d < N:
        p = E.ParserCreate(); p.StartElementHandler = h; p.Parse('<a/>', True)
h(None, None)
print('ok', d, flush=True)
os._exit(0)
""",
})

def once(kind, n, snapshot):
    r = wasi_python.run(["-c", KINDS[kind].format(n=n)], snapshot=snapshot, fuel=FUEL)
    out = r.stdout.decode(errors="replace").strip()
    err = r.stderr.decode(errors="replace").strip().splitlines()
    if r.trapped:
        return "trap:" + r.trapped
    if r.exit_code == 0 and out.startswith("ok"):
        return "ok"
    return "raise:" + (err[-1][:120] if err else repr(out))

def edge(kind, lo, hi, snapshot):
    """lo completes, hi traps (checked), bisect to the last completing depth."""
    a, b = once(kind, lo, snapshot), once(kind, hi, snapshot)
    if a != "ok" or not b.startswith("trap"):
        return {"lo": lo, "lo_got": a, "hi": hi, "hi_got": b}
    while hi - lo > 1:
        mid = (lo + hi) // 2
        got = once(kind, mid, snapshot)
        if got == "ok":
            lo = mid
        elif got.startswith("trap"):
            hi = mid
        else:
            return {"lo": lo, "hi": hi, "odd": (mid, got)}
    after = wasi_python.run(["-c", "print('ok')"], snapshot=snapshot, fuel=10**11)
    return {"last_ok": lo, "first_trap": hi, "trap": b, "next_call": after.stdout.decode().strip()}


# row: (low bound that completes, high bound that traps), around the README's figure
ROWS = {
  "expat-handler": (40, 400), "free-list": (1000, 4000), "free-dict": (650, 2600),
  "json-loads": (550, 2200), "repr-nested": (900, 3600), "eq-nested": (675, 2700),
  "eval-parens": (65, 199), "traceback-freed": (1350, 5400), "xpath-parens": (180, 750),
  "xpath-predicates": (2300, 9200), "xslt-call-template": (240, 960),
  "xslt-apply-templates": (235, 940), "xslt-apply-bare": (335, 1340), "c14n": (750, 3000),
  "relaxng": (215, 860),
}
FUEL = 10**11
for kind, (lo, hi) in ROWS.items():
    for snapshot in (True, False):
        print(json.dumps({"kind": kind, "binary": "snapshot" if snapshot else "plain",
                          **edge(kind, lo, hi, snapshot)}), flush=True)
