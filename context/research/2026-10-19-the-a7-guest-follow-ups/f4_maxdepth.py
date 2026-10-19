import sys, wasi_python
PROG = r'''
import os
from lxml import etree
X = 'http://www.w3.org/1999/XSL/Transform'
etree.XSLT.set_global_max_depth({D})
def run(name, sheet, doc):
    try:
        etree.XSLT(etree.XML(sheet.encode()))(doc)
        print(name, 'completed', flush=True)
    except etree.XSLTApplyError as e:
        print(name, 'XSLTApplyError', str(e)[:60], flush=True)
deep = e = etree.Element('a')
for i in range({N}): e = etree.SubElement(e, 'a')
CALL = f"""<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="/"><o><xsl:call-template name="t"><xsl:with-param name="n" select="{N}"/></xsl:call-template></o></xsl:template>
<xsl:template name="t"><xsl:param name="n"/><xsl:if test="$n &gt; 0"><xsl:call-template name="t"><xsl:with-param name="n" select="$n - 1"/></xsl:call-template></xsl:if></xsl:template>
</xsl:stylesheet>"""
COPY = f"""<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}"><xsl:template match="*"><xsl:copy><xsl:apply-templates/></xsl:copy></xsl:template></xsl:stylesheet>"""
HEAVY = f"""<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}"><xsl:template match="*">
<xsl:variable name="v" select="count(ancestor::*)"/><xsl:variable name="w" select="concat(name(), $v)"/>
<b x="{{{{$w}}}}"><c><d><xsl:for-each select="*"><xsl:sort select="name()"/><e><xsl:choose><xsl:when test="$v &gt; -1"><xsl:apply-templates select="."/></xsl:when></xsl:choose></e></xsl:for-each></d></c></b>
</xsl:template></xsl:stylesheet>"""
run('call-template', CALL, etree.XML(b'<x/>'))
run('apply-templates copy', COPY, deep)
run('apply-templates heavy', HEAVY, deep)
os._exit(0)
'''
for D, N in [(250, 2000), (300, 2000), (3000, 2000)]:
    for fuel in (10**11, None):
        r = wasi_python.run(["-c", PROG.format(D=D, N=N)], fuel=fuel, snapshot=True)
        print("max_depth", D, "N", N, "metered" if fuel else "unmetered", "|", r.trapped, "|", r.stdout.decode().strip().replace("\n", " / "), "|", r.stderr.decode()[-200:].strip(), flush=True)
