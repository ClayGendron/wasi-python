"""Spec 071 criterion 10: lxml's callbacks (libxml2, libxslt) that call back into lxml, bounded to a
depth N. Each prints how it ended: ok, RecursionError, or another exception's type, and the depth."""
T = """import os, sys
from lxml import etree
N, d = {n}, 0
{body}
try:
    go()
    r = "ok"
except RecursionError as e:
    r = "RecursionError " + str(e)[:40]
except Exception as e:
    r = type(e).__name__ + " " + str(e)[:60]
print(r, d, flush=True)
os._exit(0)
"""
def c(body, hi=3000): return (lambda n: T.replace("{n}", str(n)).replace("{body}", body), hi)
TARGET = '''class Tg:
    def start(self, tag, attrib):
        global d
        d += 1
        if d < N: etree.fromstring('<a/>', etree.XMLParser(target=Tg()))
    def close(self): return None
def go(): etree.fromstring('<a/>', etree.XMLParser(target=Tg()))'''
XPATH = '''doc = etree.fromstring('<a/>')
def f(ctx):
    global d
    d += 1
    if d < N: doc.xpath('f()', extensions={(None, 'f'): f})
    return 1
def go(): doc.xpath('f()', extensions={(None, 'f'): f})'''
RESOLVER = '''class R(etree.Resolver):
    def resolve(self, url, pid, ctx):
        global d
        d += 1
        if d < N: parse()
        return self.resolve_string('', ctx)
def parse():
    p = etree.XMLParser(load_dtd=True, no_network=False); p.resolvers.add(R())
    etree.fromstring('<!DOCTYPE a SYSTEM "x.dtd"><a/>', p)
def go(): parse()'''
XSLT = '''SHEET = etree.XML('<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:x="urn:x"><xsl:template match="/"><a><xsl:value-of select="x:f()"/></a></xsl:template></xsl:stylesheet>')
DOC = etree.XML('<a/>')
def f(ctx):
    global d
    d += 1
    if d < N: etree.XSLT(SHEET)(DOC)
    return 'x'
etree.FunctionNamespace('urn:x')['f'] = f
def go(): etree.XSLT(SHEET)(DOC)'''
CASES = {"lxml_target": c(TARGET), "lxml_xpath_ext": c(XPATH), "lxml_resolver": c(RESOLVER), "lxml_xslt_ext": c(XSLT)}
