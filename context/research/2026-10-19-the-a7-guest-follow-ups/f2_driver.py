"""F2: DENY_ALL and a stylesheet's own xsl:import / xsl:include (the review's x04b and x04c)."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))  # the repository's tests/
from harness import guest as g, paths

wasm = Path(sys.argv[1]); setdir = Path(sys.argv[2]); work = Path(tempfile.mkdtemp(dir=sys.argv[3]))
m = paths.parse_manifest((setdir / "MANIFEST").read_text())
ro = work / "ro-host"; ro.mkdir()
XSL = "http://www.w3.org/1999/XSL/Transform"
(ro / "data.txt").write_bytes(b"GRANTED\n")
(ro / "ent.xsl").write_text(f"""<?xml version="1.0"?>
<!DOCTYPE xsl:stylesheet [<!ENTITY s SYSTEM "/ro/data.txt">]>
<xsl:stylesheet version="1.0" xmlns:xsl="{XSL}">
<xsl:template name="leak"><leak>&s;</leak></xsl:template>
</xsl:stylesheet>
""")
PROG = '''
import json
from lxml import etree
XSL = "http://www.w3.org/1999/XSL/Transform"
AC = etree.XSLTAccessControl
def sheet(how, href):
    return f"""<xsl:stylesheet version="1.0" xmlns:xsl="{XSL}"><xsl:{how} href="{href}"/>
<xsl:template match="/"><o><xsl:call-template name="leak"/></o></xsl:template></xsl:stylesheet>""".encode()
class Refuse(etree.Resolver):
    def resolve(self, url, pubid, context):
        raise ValueError("refused: " + url)
def refusing():
    p = etree.XMLParser()
    p.resolvers.add(Refuse())
    return p
out = {}
def case(label, run):
    try:
        out[label] = ["ok", run()]
    except Exception as e:
        out[label] = [type(e).__name__, str(e)[:160]]
for how in ("import", "include"):
    case(f"{how} DENY_ALL", lambda: str(etree.XSLT(etree.XML(sheet(how, "/ro/ent.xsl")), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL file: URL", lambda: str(etree.XSLT(etree.XML(sheet(how, "file:///ro/ent.xsl")), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL relative, base_url", lambda: str(etree.XSLT(etree.XML(sheet(how, "ent.xsl"), base_url="file:///ro/main.xsl"), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL absolute path, base_url", lambda: str(etree.XSLT(etree.XML(sheet(how, "/ro/ent.xsl"), base_url="/ro/main.xsl"), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL read_file=False", lambda: str(etree.XSLT(etree.XML(sheet(how, "file:///ro/ent.xsl")), access_control=AC(read_file=False, read_network=False))(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL absent file: URL", lambda: str(etree.XSLT(etree.XML(sheet(how, "file:///ro/none.xsl")), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} DENY_ALL absent file", lambda: str(etree.XSLT(etree.XML(sheet(how, "/ro/none.xsl")), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} refusing resolver", lambda: str(etree.XSLT(etree.XML(sheet(how, "/ro/ent.xsl"), refusing()), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} refusing resolver, file: URL", lambda: str(etree.XSLT(etree.XML(sheet(how, "file:///ro/ent.xsl"), refusing()), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
    case(f"{how} refusing resolver, relative", lambda: str(etree.XSLT(etree.XML(sheet(how, "ent.xsl"), refusing(), base_url="file:///ro/main.xsl"), access_control=AC.DENY_ALL)(etree.XML(b"<x/>"))))
print(json.dumps(out, indent=0))
'''
r = g.run(wasm, ["-c", PROG], workdir=work, python_version=m.python, stdlib=setdir / "python-stdlib.zip",
          preopens=[("/ro", ro, False)], fuel=10**11, measured=False)
print("exit", r.exit_code, r.trapped, "fuel", r.fuel)
print(r.stdout.decode()); print(r.stderr.decode()[-1500:])
