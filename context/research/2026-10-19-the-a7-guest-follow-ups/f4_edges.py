"""F4: where each README row starts to trap at 512 KiB, through wasi_python.run, metered (fuel cap
10**11, as spec 071's limits were measured). Bisects each kind between a depth that completes and
one that traps, on the snapshot and the plain binary."""
import json, sys
import wasi_python

PRE = "import os, sys\nN = {n}\n"
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

kind, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
FUEL = None if sys.argv[4] == "unmetered" else 10**11
for snapshot in (True, False):
    print(json.dumps({"kind": kind, "mode": sys.argv[4], "binary": "snapshot" if snapshot else "plain", **edge(kind, lo, hi, snapshot)}), flush=True)
