"""Spec 078's build: the last depth that does not trap, through wasi_python.run (metered), for the
cases the README lists that the research did not measure at 8 MiB. Usage: edges078.py CASE..."""
import json, platform, sys
from wasi_python import run
T = """import os
N = {n}
{build}
try:
    {act}
    r = "ok"
except Exception as e:
    r = type(e).__name__ + " " + str(e)[:60]
print(r, flush=True)
os._exit(0)
"""
TREE = "from lxml import etree\nroot = etree.Element('a'); e = root\nfor i in range(N): e = etree.SubElement(e, 'a')"
RNG = TREE + """
rng = etree.RelaxNG(etree.XML('<grammar xmlns="http://relaxng.org/ns/structure/1.0"><start><ref name="a"/></start><define name="a"><element name="a"><optional><ref name="a"/></optional></element></define></grammar>'))"""
COPY = TREE + """
x = etree.XSLT(etree.XML('<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="a"><xsl:copy><xsl:apply-templates/></xsl:copy></xsl:template></xsl:stylesheet>'))"""
CASES = {
    "relaxng": (RNG, "rng.validate(etree.ElementTree(root))", 200000),
    "xslt-apply-copy": (COPY, "x(etree.ElementTree(root))", 200000),
}
def outcome(case, n):
    build, act, _ = CASES[case]
    d = run(["-c", T.format(n=n, build=build, act=act)], fuel=10**12, deadline_s=None)
    return d.trapped, d.stdout.decode().strip()
for case in sys.argv[1:]:
    hi = CASES[case][2]
    tr, out = outcome(case, hi)
    if not tr:
        print(json.dumps({"case": case, "max_ok": hi, "unbounded": True, "at": out[:80], "arch": platform.machine()})); continue
    lo, last = 0, ""
    h = hi - 1
    while lo < h:
        mid = (lo + h + 1) // 2
        tr, out = outcome(case, mid)
        if tr: h = mid - 1
        else: lo, last = mid, out
    print(json.dumps({"case": case, "max_ok": lo, "at": last[:80], "above": tr, "arch": platform.machine()}), flush=True)
