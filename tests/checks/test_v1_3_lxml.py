"""v1.3: lxml, with libxml2 and libxslt built in. Files by path go through libxml2's own
input, which needs the carried patch on WASI (no `dup()`); what a stylesheet or an entity can reach
is only what a grant holds; the character encodings are wasi-libc's, as the README's table says;
and what the build leaves out fails in the named way."""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path

import pytest

from harness import jobs

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])

DOC = b'<?xml version="1.0"?>\n<!DOCTYPE d SYSTEM "d.dtd">\n<d k="v"><e>one</e><e>two</e></d>\n'
DTD = b"<!ELEMENT d (e+)>\n<!ATTLIST d k CDATA #REQUIRED>\n<!ELEMENT e (#PCDATA)>\n"
INC = (
    b'<?xml version="1.0"?>\n<top xmlns:xi="http://www.w3.org/2001/XInclude">'
    b'<xi:include href="doc.xml"/></top>\n'
)
ENT = b'<?xml version="1.0"?>\n<!DOCTYPE r [<!ENTITY e SYSTEM "secret.txt">]>\n<r>&e;</r>\n'
SECRET = b"SECRET\n"


def _grants(guest_workdir: Path) -> tuple[Path, Path, list[tuple[str, Path, bool]]]:
    """A read-only folder at /ro holding the documents, and an empty writable one at /rw."""
    ro = Path(tempfile.mkdtemp(prefix="ro-", dir=guest_workdir))
    rw = Path(tempfile.mkdtemp(prefix="rw-", dir=guest_workdir))
    for name, data in {
        "doc.xml": DOC,
        "d.dtd": DTD,
        "inc.xml": INC,
        "ent.xml": ENT,
        "secret.txt": SECRET,
    }.items():
        (ro / name).write_bytes(data)
    return ro, rw, [("/ro", ro, False), ("/rw", rw, True)]


FILES = """
import os, sys
from lxml import etree

def show(label, run):
    try:
        print(label, run())
    except Exception as e:
        print(label, "raises", type(e).__name__)

def open_fds():
    # wasmtime need not give the lowest free number to the next open, so the open descriptors
    # are counted, not the next one's number.
    found = []
    for fd in range(3, 256):
        try:
            os.fstat(fd)
            found.append(fd)
        except OSError:
            pass
    return found

XSL = b'''<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'>
<xsl:template match='/'><o><xsl:value-of select="document('file:///ro/doc.xml')/d/@k"/></o>
</xsl:template>
</xsl:stylesheet>'''
before = open_fds()
show("parse", lambda: etree.parse("/ro/doc.xml").getroot().get("k"))
show("parse 50", lambda: sorted({etree.parse("/ro/doc.xml").getroot().tag for _ in range(50)}))
show("iterparse", lambda: [(ev, el.tag) for ev, el in etree.iterparse("/ro/doc.xml")])
show("dtd", lambda: etree.DTD("/ro/d.dtd").validate(etree.parse("/ro/doc.xml")))
VALID = etree.XMLParser(dtd_validation=True)
show("dtd parser", lambda: etree.parse("/ro/doc.xml", VALID).getroot().tag)
def xinclude():
    t = etree.parse("/ro/inc.xml")
    t.xinclude()
    return [e.tag for e in t.getroot().iter()]
show("xinclude", xinclude)
show("document()", lambda: str(etree.XSLT(etree.XML(XSL))(etree.XML(b"<x/>"))).split("\\n")[1])
show("missing", lambda: etree.parse("/ro/nope.xml"))
show("descriptors kept", lambda: open_fds() == before)
show("write ro", lambda: etree.ElementTree(etree.XML(b"<w/>")).write("/ro/w.xml"))
show("ro unchanged", lambda: sorted(os.listdir("/ro")))
def write_rw():
    etree.ElementTree(etree.XML(b"<w>1</w>")).write("/rw/w.xml")
    with open("/rw/w.xml", "rb") as f:
        return f.read()
show("write rw", write_rw)
sys.stdout.flush()
etree.ElementTree(etree.XML(b"<o>-</o>")).write("-")
etree.ElementTree(etree.XML(b"<o>-</o>")).write("-")
print("after")
"""

FILES_WANT = (
    "parse v\n"
    "parse 50 ['d']\n"
    "iterparse [('end', 'e'), ('end', 'e'), ('end', 'd')]\n"
    "dtd True\n"
    "dtd parser d\n"
    "xinclude ['top', 'd', 'e', 'e']\n"
    "document() <o>v</o>\n"
    "missing raises OSError\n"
    "descriptors kept True\n"
    "write ro raises PermissionError\n"
    "ro unchanged ['d.dtd', 'doc.xml', 'ent.xml', 'inc.xml', 'secret.txt']\n"
    "write rw b'<w>1</w>'\n"
    "<o>-</o><o>-</o>after\n"
)


@BINARY
def test_files_by_path_in_grants(guest, guest_workdir, which) -> None:
    """libxml2 reads and writes files by name through its own I/O, which calls `dup()` natively
    and the carried patch's code on WASI: a parse (fifty in a row, no
    descriptor left open), `iterparse`, a DTD, XInclude and XSLT's `document()` read a read-only
    grant; a missing file raises `OSError`; a write into the read-only grant raises
    `PermissionError` and leaves it unchanged, one into a writable grant lands; and `write("-")`
    reaches standard output twice without closing it. Without the patch libxml2 does not compile
    (Decision 4)."""
    ro, _, preopens = _grants(guest_workdir)
    r = guest(which, ["-c", FILES], preopens=preopens)
    assert r.exit_code == 0, r.describe()
    assert r.text == FILES_WANT, r.text
    assert sorted(p.name for p in ro.iterdir()) == [
        "d.dtd",
        "doc.xml",
        "ent.xml",
        "inc.xml",
        "secret.txt",
    ]


SAFETY = """
import json, os
from lxml import etree

out = {}

def case(label, run):
    try:
        out[label] = ["ok", run()]
    except Exception as e:
        out[label] = [type(e).__name__, str(e)]

XSL = "http://www.w3.org/1999/XSL/Transform"
READ = f'''<xsl:stylesheet version='1.0' xmlns:xsl='{XSL}'><xsl:template match='/'>
<o><xsl:value-of select="document('file:///ro/ent.xml')/r"/></o></xsl:template></xsl:stylesheet>'''
def write(href):
    return f'''<xsl:stylesheet version='1.0' xmlns:xsl='{XSL}'
 xmlns:exsl='http://exslt.org/common' extension-element-prefixes='exsl'>
<xsl:template match='/'><exsl:document href='{href}'><o>w</o></exsl:document><done/></xsl:template>
</xsl:stylesheet>'''
def apply(sheet, **kw):
    return str(etree.XSLT(etree.XML(sheet.encode()), **kw)(etree.XML(b"<x/>")))

AC = etree.XSLTAccessControl
case("xslt document() entity", lambda: apply(READ))
case("xslt document() DENY_ALL", lambda: apply(READ, access_control=AC.DENY_ALL))
case("xslt document() read_file=False", lambda: apply(READ, access_control=AC(read_file=False)))
case("xslt exsl:document ro", lambda: apply(write("/ro/out.xml")))
case("xslt exsl:document ro left", lambda: os.path.exists("/ro/out.xml"))
DENIED = write("/rw/denied.xml")
case("xslt exsl:document DENY_ALL", lambda: apply(DENIED, access_control=AC.DENY_ALL))
case("xslt exsl:document DENY_ALL left", lambda: os.path.exists("/rw/denied.xml"))
case("xslt exsl:document rw", lambda: (apply(write("/rw/out.xml")), open("/rw/out.xml").read())[1])

def entity(url, **kw):
    doc = f"<!DOCTYPE r [<!ENTITY e SYSTEM '{url}'>]><r>&e;</r>".encode()
    return etree.tostring(etree.fromstring(doc, etree.XMLParser(**kw) if kw else None)).decode()
case("entity default", lambda: entity("file:///ro/secret.txt"))
case("entity resolved", lambda: entity("file:///ro/secret.txt", resolve_entities=True))
NET = "http://127.0.0.1:9/x"
case("entity network", lambda: entity(NET, resolve_entities=True, no_network=False))
LAUGHS = "<!DOCTYPE r [<!ENTITY a 'aaaaaaaaaa'>" + "".join(
    f"<!ENTITY {n} '{('&' + p + ';') * 10}'>" for p, n in zip("abcdefg", "bcdefgh")
) + "]><r>&h;</r>"
case("billion laughs", lambda: len(etree.tostring(etree.fromstring(
    LAUGHS.encode(), etree.XMLParser(resolve_entities=True)))))
print(json.dumps(out))
"""

# The host path outside every grant, in a run of its own that records no fuel: the guest's work
# moves with the path's length, and the path moves with the checkout. Its control
# reads the same file by its guest path, in the same run.
OUTSIDE = """
import json, sys
from lxml import etree

out = {}

def case(label, url):
    doc = f"<!DOCTYPE r [<!ENTITY e SYSTEM '{url}'>]><r>&e;</r>".encode()
    try:
        root = etree.fromstring(doc, etree.XMLParser(resolve_entities=True))
        out[label] = ["ok", etree.tostring(root).decode()]
    except Exception as e:
        out[label] = [type(e).__name__, str(e)]

case("entity by guest path, outside run", "file:///ro/secret.txt")
case("entity outside grants", "file://" + sys.argv[1])
print(json.dumps(out))
"""
OUTSIDE_KEYS = {"entity by guest path, outside run", "entity outside grants"}


@BINARY
def test_stylesheets_and_entities_reach_only_grants(guest, guest_workdir, which) -> None:
    """An XSLT with no access control loads a granted document with
    libxslt's own parse options, so the document's external entity on another granted file is
    read; `XSLTAccessControl.DENY_ALL` and `read_file=False` refuse the read. An `exsl:document`
    aimed at a read-only grant fails and writes nothing; under `DENY_ALL` it is refused; into a
    writable grant it writes. lxml's default parser refuses an external entity; with
    `resolve_entities=True` it reads a granted file, a host path outside every grant gives an
    empty element (the guest has no such path; on Windows the drive and backslashes are refused
    by name, so libxml2 reports the load failed, and still nothing is read), an `http:` entity
    gives an empty element (there is no network), and a billion-laughs document raises. The host
    path goes to a run of its own, which records no fuel and also reads the same file by its guest
    path; the measured run's inputs are guest paths only."""
    ro, rw, preopens = _grants(guest_workdir)
    host = str(ro / "secret.txt")
    # The path handed to the guest is the granted file itself, so the probe cannot pass on a
    # path that names nothing.
    assert Path(host).read_bytes() == SECRET and Path(host).samefile(ro / "secret.txt"), host
    outside = guest(which, ["-c", OUTSIDE, host], preopens=preopens, record=False)
    assert outside.exit_code == 0, outside.describe()
    r = guest(which, ["-c", SAFETY], preopens=preopens)
    assert r.exit_code == 0, r.describe()
    away, measured = json.loads(outside.text), json.loads(r.text)
    assert set(away) == OUTSIDE_KEYS and not OUTSIDE_KEYS & set(measured), (away, measured)
    got = {**measured, **away}
    bad = []

    def expect(label: str, kind: str, *parts: str) -> None:
        k, value = got[label]
        if k != kind or not all(p in str(value) for p in parts):
            bad.append(f"{label}: {k} {value!r}, want {kind} with {parts}")

    expect("xslt document() entity", "ok", "<o>SECRET\n</o>")
    expect("xslt document() DENY_ALL", "XSLTApplyError", "read rights", "denied")
    expect("xslt document() read_file=False", "XSLTApplyError", "read rights", "denied")
    expect("xslt exsl:document ro", "XSLTApplyError", "unable to save")
    expect("xslt exsl:document ro left", "ok", "False")
    expect("xslt exsl:document DENY_ALL", "XSLTApplyError", "write rights", "denied")
    expect("xslt exsl:document DENY_ALL left", "ok", "False")
    expect("xslt exsl:document rw", "ok", "<o>w</o>")
    expect("entity default", "XMLSyntaxError", "Entity 'e' not defined")
    expect("entity resolved", "ok", "<r>SECRET\n</r>")
    expect("entity by guest path, outside run", "ok", "<r>SECRET\n</r>")
    if sys.platform == "win32":
        # A Windows host path is no guest path at all: its drive and backslashes are refused by
        # name (EPERM), so libxml2 reports the load failed instead of an empty element. Either
        # way nothing outside the grants is read (a release dry run, 39203592916).
        expect(
            "entity outside grants", "XMLSyntaxError", "failed to load", "Operation not permitted"
        )
    else:
        expect("entity outside grants", "ok", "<r/>")
    # On every platform, whatever the kind of answer: the host's secret is never read.
    if "SECRET" in str(got["entity outside grants"][1]):
        bad.append("entity outside grants: the host's secret was read")
    expect("entity network", "ok", "<r/>")
    expect("billion laughs", "XMLSyntaxError", "amplification")
    assert not bad, "; ".join(bad)
    assert not (ro / "out.xml").exists() and (rw / "out.xml").is_file()


# `XSLTAccessControl` governs what a stylesheet reads
# while it runs, not the stylesheets it imports or includes, which libxslt loads through the parser
# it was parsed with. The imported stylesheet declares an external entity on a granted file. These
# two checks have a grant of their own, so `_grants`, `FILES_WANT` and every recorded fuel above
# stay as they were.
IMPORTED = (
    b'<?xml version="1.0"?>\n'
    b'<!DOCTYPE xsl:stylesheet [<!ENTITY s SYSTEM "/ro/secret.txt">]>\n'
    b'<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">\n'
    b'<xsl:template name="leak"><leak>&s;</leak></xsl:template>\n'
    b"</xsl:stylesheet>\n"
)


def _import_grant(guest_workdir: Path) -> list[tuple[str, Path, bool]]:
    """A fresh read-only folder at /ro holding only the imported stylesheet and the secret."""
    ro = Path(tempfile.mkdtemp(prefix="ro-import-", dir=guest_workdir))
    (ro / "ent.xsl").write_bytes(IMPORTED)
    (ro / "secret.txt").write_bytes(SECRET)
    return [("/ro", ro, False)]


IMPORTS = """
import json
from lxml import etree

XSL = "http://www.w3.org/1999/XSL/Transform"
AC = etree.XSLTAccessControl
PARSER = None  # a refusing parser, in the resolver's check

def sheet(how, href):
    return f'''<xsl:stylesheet version="1.0" xmlns:xsl="{XSL}"><xsl:{how} href="{href}"/>
<xsl:template match="/"><o><xsl:call-template name="leak"/></o></xsl:template></xsl:stylesheet>'''

def apply(how, href, base_url=None, access_control=AC.DENY_ALL):
    root = etree.fromstring(sheet(how, href).encode(), PARSER, base_url=base_url)
    return str(etree.XSLT(root, access_control=access_control)(etree.XML(b"<x/>")))

out = {}

def case(label, *args, **kw):
    try:
        out[label] = ["ok", apply(*args, **kw)]
    except Exception as e:
        out[label] = [type(e).__name__, str(e)]
"""

DENY_ALL_IMPORTS = (
    IMPORTS
    + """
for how in ("import", "include"):
    case(f"{how} file: href", how, "file:///ro/ent.xsl")
    case(f"{how} relative href", how, "ent.xsl", base_url="file:///ro/main.xsl")
    case(f"{how} path href", how, "/ro/ent.xsl", base_url="/ro/main.xsl")
    case(f"{how} read_file=False", how, "file:///ro/ent.xsl", access_control=AC(read_file=False))
    case(f"{how} absent", how, "file:///ro/none.xsl")
print(json.dumps(out))
"""
)


@BINARY
def test_deny_all_leaves_a_stylesheets_imports_to_its_parser(guest, guest_workdir, which) -> None:
    """The README's sentence: `XSLTAccessControl.DENY_ALL` does not cover a stylesheet's own
    `xsl:import` and `xsl:include`. Compiled under `DENY_ALL`, or with `read_file=False`, a
    stylesheet that imports or includes a granted one, by a `file:` href, by a relative href
    against a base URL, or by a path against a path base, carries that stylesheet's external
    entity, so the output holds the granted file. An absent file fails to compile, naming its
    URL: compiling tells whether a granted file exists."""
    r = guest(which, ["-c", DENY_ALL_IMPORTS], preopens=_import_grant(guest_workdir))
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    bad = []
    for how in ("import", "include"):
        for form in ("file: href", "relative href", "path href", "read_file=False"):
            k, value = got[f"{how} {form}"]
            if k != "ok" or "<o><leak>SECRET\n</leak></o>" not in value:
                bad.append(f"{how} {form}: {k} {value!r}, want the granted file in the output")
        k, value = got[f"{how} absent"]
        if k != "XSLTParseError" or "file:///ro/none.xsl" not in value:
            bad.append(f"{how} absent: {k} {value!r}, want XSLTParseError naming its URL")
    assert not bad, "; ".join(bad)


REFUSED_IMPORTS = (
    IMPORTS
    + """
class Refused(Exception):
    pass

class Refuse(etree.Resolver):
    def resolve(self, url, pubid, context):
        raise Refused("refused " + url)

PARSER = etree.XMLParser()
PARSER.resolvers.add(Refuse())
for how in ("import", "include"):
    case(f"{how} file: href", how, "file:///ro/ent.xsl")
    case(f"{how} relative href", how, "ent.xsl", base_url="file:///ro/main.xsl")
    case(f"{how} path href", how, "/ro/ent.xsl", base_url="/ro/main.xsl")
print(json.dumps(out))
"""
)


@BINARY
def test_a_refusing_resolver_stops_a_stylesheets_imports(guest, guest_workdir, which) -> None:
    """The README's remedy: parse the stylesheet from its bytes with a parser whose resolver
    refuses every URL. Then each of the three imports and includes that load under `DENY_ALL`
    alone raises the resolver's own exception, naming the URL it refused, and nothing of the
    granted file is read."""
    r = guest(which, ["-c", REFUSED_IMPORTS], preopens=_import_grant(guest_workdir))
    assert r.exit_code == 0, r.describe()
    assert "SECRET" not in r.text, r.text
    got = json.loads(r.text)
    want = {
        "file: href": "file:///ro/ent.xsl",
        "relative href": "file:///ro/ent.xsl",
        "path href": "/ro/ent.xsl",
    }
    bad = []
    for how in ("import", "include"):
        for form, url in want.items():
            k, value = got[f"{how} {form}"]
            if (k, value) != ("Refused", f"refused {url}"):
                bad.append(f"{how} {form}: {k} {value!r}, want Refused naming {url}")
    assert not bad, "; ".join(bad)


# Each encoding over its whole BMP repertoire (every character Python's codec encodes, one element
# each), parsed from a document in that encoding and written back to it. The lines are the guest's,
# as the upstream facts sheet on libxml2's input without dup records them in its evidence, but
# GB18030's, which the revised guard fails as invalid bytes instead of refusing; a wasi-sdk whose
# iconv tables change turns this red, and the README's table changes with it.
ENCODINGS = """
import hashlib
from lxml import etree
ENCS = ["windows-1252", "iso-8859-2", "iso-8859-15", "cp1251", "koi8-r", "tis-620", "shift_jis",
        "cp932", "euc-jp", "iso-2022-jp", "gbk", "gb18030", "gb2312", "big5", "euc-kr", "cp949",
        "cp950", "utf-16"]
def chars(enc):
    out = []
    for cp in range(0xA0, 0x10000):
        if 0xD800 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF):
            continue
        try:
            chr(cp).encode(enc)
        except UnicodeEncodeError:
            continue
        out.append(chr(cp))
    return out
def first(bad):
    return (" e.g. " + ",".join("U+%04X" % ord(c) for c in bad[:4])) if bad else ""
for enc in ENCS:
    cs = chars(enc)
    body = "".join("<c>%s</c>" % c for c in cs)
    doc = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, body)).encode(enc)
    try:
        got = [e.text for e in etree.fromstring(doc)]
        bad = [c for c, g in zip(cs, got) if c != g]
        p = "parse %d/%d bad %d%s" % (len(cs) - len(bad), len(cs), len(bad), first(bad))
    except Exception as e:
        p = "parse RAISES %s %s" % (type(e).__name__, str(e)[:60])
    try:
        raw = etree.tostring(etree.fromstring("<r>%s</r>" % body), encoding=enc)
        txt = raw.decode(enc)
        txt = txt.split("?>", 1)[1] if txt.startswith("<?xml") else txt
        got = [e.text for e in etree.fromstring(txt)]
        bad = [c for c, g in zip(cs, got) if c != g]
        w = "write bad %d sha %s%s" % (len(bad), hashlib.sha256(raw).hexdigest()[:12], first(bad))
    except Exception as e:
        w = "write RAISES %s %s" % (type(e).__name__, str(e)[:50])
    print(enc, "|", p, "|", w)
"""

ENCODINGS_WANT = """\
windows-1252 | parse 123/123 bad 0 | write bad 0 sha 11fcdbb6ed71
iso-8859-2 | parse 96/96 bad 0 | write bad 0 sha 3f742bebbca3
iso-8859-15 | parse 96/96 bad 0 | write bad 0 sha 680fc7d462a3
cp1251 | parse 127/127 bad 0 | write bad 0 sha aeddde1ef3fe
koi8-r | parse 128/128 bad 0 | write bad 0 sha 1d9eaa70ec32
tis-620 | parse 87/87 bad 0 | write bad 0 sha a0105d61c2ba
shift_jis | parse 6941/6944 bad 3 e.g. U+00A5,U+203E,U+FF3C | write bad 3 sha 4e792f506586 e.g. \
U+00A5,U+203E,U+FF3C
cp932 | parse RAISES XMLSyntaxError Invalid bytes in character encoding, line 1, column 37 (<str | \
write bad 460 sha 2c4c06cb25f9 e.g. U+00A2,U+00A3,U+00AC,U+2016
euc-jp | parse RAISES XMLSyntaxError Invalid bytes in character encoding, line 1, column 38 (<str \
| write bad 6069 sha aa83972b2b9c e.g. U+00A1,U+00A4,U+00A5,U+00A6
iso-2022-jp | parse 6880/6881 bad 1 e.g. U+FF3C | write bad 1 sha 963cc0734703 e.g. U+FF3C
gbk | parse 21791/21791 bad 0 | write RAISES LookupError unknown encoding: 'gbk'
gb18030 | parse RAISES XMLSyntaxError Invalid bytes in character encoding, line 1, column 39 (<str \
| write RAISES LookupError unknown encoding: 'gb18030'
gb2312 | parse 7443/7445 bad 2 e.g. U+2015,U+30FB | write RAISES LookupError unknown encoding: \
'gb2312'
big5 | parse RAISES XMLSyntaxError Invalid bytes in character encoding, line 1, column 36 (<str | \
write RAISES LookupError unknown encoding: 'big5'
euc-kr | parse 8226/17048 bad 8822 e.g. U+AC02,U+AC03,U+AC05,U+AC06 | write RAISES LookupError \
unknown encoding: 'euc-kr'
cp949 | parse 17048/17048 bad 0 | write RAISES LookupError unknown encoding: 'cp949'
cp950 | parse RAISES XMLSyntaxError Invalid bytes in character encoding, line 1, column 37 (<str | \
write RAISES LookupError unknown encoding: 'cp950'
utf-16 | parse 56926/56926 bad 0 | write bad 0 sha 716351c8ebbd
"""


@pytest.mark.slow
def test_encodings_are_wasi_libcs_as_documented(guest) -> None:
    """The guest's character conversion is wasi-libc's iconv, measured over
    each encoding's whole repertoire. Seven encodings round-trip every character; Shift_JIS,
    ISO-2022-JP and GB2312 read a few characters as other characters (mapping conventions); cp932,
    EUC-JP, Big5 and cp950 documents fail; the CJK writes but Shift_JIS's and ISO-2022-JP's raise
    `LookupError`; and GB18030, which wasi-libc decodes wrongly without an error, fails at its
    first non-ASCII byte (`recipes/iconv_refusals.c`). About 31 G fuel, so on the snapshot only."""
    r = guest("snapshot", ["-c", ENCODINGS], fuel=40 * 10**9)
    assert r.exit_code == 0, r.describe()
    assert r.text == ENCODINGS_WANT, r.text


WORKAROUND = """
from lxml import etree
for enc in ("cp932", "euc-jp", "gb18030", "big5"):
    cs = []
    for cp in range(0xA0, 0x10000):
        if 0xD800 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF):
            continue
        try:
            chr(cp).encode(enc)
            cs.append(chr(cp))
        except UnicodeEncodeError:
            pass
    body = "".join("<c>%s</c>" % c for c in cs)
    data = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, body)).encode(enc)
    root = etree.fromstring(data.decode(enc).encode("utf-8"), etree.XMLParser(encoding="utf-8"))
    print(enc, len(cs), sum(1 for c, e in zip(cs, root) if e.text != c))
"""


@pytest.mark.slow
def test_the_readmes_encoding_workaround_reads_what_iconv_cannot(guest) -> None:
    """The README's workaround for the partial encodings: decode with
    Python's codec, parse the UTF-8. Over each whole repertoire, cp932, EUC-JP, GB18030 and Big5
    give native's counts, which are Python's own round-trip gaps (6 and 2), not libxml2's."""
    r = guest("snapshot", ["-c", WORKAROUND], fuel=20 * 10**9)
    assert r.exit_code == 0, r.describe()
    assert r.text == "cp932 7395 6\neuc-jp 13010 2\ngb18030 56926 0\nbig5 13706 0\n", r.text


GB18030 = """
import io, json
import lxml.html
import pandas as pd
from lxml import etree

TEXT = "中文网页：数据表格" + chr(0xF900) + chr(0xF901)
out = {}

def case(label, run):
    try:
        out[label] = ["ok", run()]
    except Exception as e:
        out[label] = [type(e).__name__, str(e)[:80]]

xml = ('<?xml version="1.0" encoding="GB18030"?><r>%s</r>' % TEXT).encode("gb18030")
page = ('<html><head><meta charset="gb18030"><title>t</title></head><body><p>%s</p>'
        '<p>after</p></body></html>' % TEXT).encode("gb18030")
table = ('<html><head><meta charset="gb18030"></head><body><table><tr><th>名</th></tr>'
         '<tr><td>中文</td></tr></table></body></html>').encode("gb18030")
case("xml", lambda: etree.fromstring(xml).text)
def recover():
    p = etree.XMLParser(recover=True)
    r = etree.fromstring(xml, p)
    return [None if r is None else r.text, [e.type_name for e in p.error_log]]
case("xml recover", recover)
def html():
    p = lxml.html.HTMLParser()
    d = lxml.html.document_fromstring(page, parser=p)
    return [[e.text for e in d.iter("p")], [e.type_name for e in p.error_log]]
case("lxml.html", html)
case("read_html", lambda: pd.read_html(io.BytesIO(table))[0].to_dict("list"))
def cut(body):
    doc = ('<html><head><meta charset="gb18030"></head><body>%s</body></html>' % body)
    tabs = pd.read_html(io.BytesIO(doc.encode("gb18030")))
    return [{c: [None if v != v else v for v in t[c].tolist()] for c in t}
            | {"dtypes": [str(d) for d in t.dtypes]} for t in tabs]
case("read_html straddling", lambda: cut(
    "<table><tr><th>k</th><th>v</th></tr><tr><td>a</td><td>1</td></tr><tr><td>b</td><td>2</td>"
    "</tr><tr><td>中文</td><td>3</td></tr><tr><td>c</td><td>4</td></tr></table>"
    "<table><tr><th>z</th></tr><tr><td>9</td></tr></table>"))
case("read_html ascii header", lambda: cut(
    "<table><tr><th>code</th><th>name</th></tr><tr><td>600000</td><td>浦发银行</td></tr>"
    "<tr><td>600036</td><td>招商银行</td></tr></table>"))
case("encoding=", lambda: etree.fromstring(xml, etree.XMLParser(encoding="gb18030")).text)
case("write", lambda: etree.tostring(etree.fromstring("<r>中</r>"), encoding="gb18030"))
case("python's codec, xml", lambda: etree.fromstring(xml.decode("gb18030").split("?>", 1)[1]).text)
case("python's codec, html", lambda: lxml.html.document_fromstring(page.decode("gb18030"))
     .findtext(".//p"))
case("python's codec, read_html", lambda: pd.read_html(io.StringIO(table.decode("gb18030")))[0]
     .to_dict("list"))
print(json.dumps(out, ensure_ascii=False))
"""
TEXT = "中文网页：数据表格" + chr(0xF900) + chr(0xF901)


@BINARY
def test_gb18030_is_never_silently_wrong(guest, which) -> None:
    """wasi-libc decodes 1,617 GB18030 characters wrongly without an error, so the guard
    (`recipes/iconv_refusals.c`) lets a GB18030 decode pass ASCII and fail at the first byte
    above it. In no mode is
    a character decoded wrongly: strict XML raises "Invalid bytes"; `recover=True` keeps no
    root; lxml's HTML parser ends the text there (an `ERR_INVALID_ENCODING` in its error log),
    where refusing the encoding made it read the page as windows-1252; `read_html` of a Chinese
    table finds no table with lxml, falls back to bs4, which reads the bytes as UTF-8,
    and raises UnicodeDecodeError (ImportError before bs4 was in the build), but a table that
    reaches the first non-ASCII byte comes back cut there with no exception (the README's one silent
    case, pinned as documented); asking for GB18030 by name, to read or to write, raises
    `LookupError`. Python's own codec, then lxml, reads every character."""
    r = guest(which, ["-c", GB18030])
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    invalid = "Invalid bytes in character encoding"
    assert got["xml"][0] == "XMLSyntaxError" and invalid in got["xml"][1], got["xml"]
    assert got["xml recover"] == ["ok", [None, ["ERR_INVALID_ENCODING"]]], got["xml recover"]
    assert got["lxml.html"] == ["ok", [[None], ["ERR_INVALID_ENCODING"]]], got["lxml.html"]
    assert got["read_html"][0] == "UnicodeDecodeError", got["read_html"]
    # The silent case the README names: a table that reaches the first
    # non-ASCII byte comes back cut there, with no exception; its last row may be all NaN, a column
    # may turn float, and the rows and tables after it are missing. Pinned as documented.
    straddling = [{"k": ["a", "b", None], "v": [1.0, 2.0, None], "dtypes": ["str", "float64"]}]
    assert got["read_html straddling"] == ["ok", straddling], got["read_html straddling"]
    header = [{"code": [600000], "name": [None], "dtypes": ["int64", "float64"]}]
    assert got["read_html ascii header"] == ["ok", header], got["read_html ascii header"]
    assert got["encoding="][0] == "LookupError", got["encoding="]
    assert got["write"][0] == "LookupError", got["write"]
    assert got["python's codec, xml"] == ["ok", TEXT], got["python's codec, xml"]
    assert got["python's codec, html"] == ["ok", TEXT], got["python's codec, html"]
    want = ["ok", {"名": ["中文"]}]
    assert got["python's codec, read_html"] == want, got["python's codec, read_html"]


DECOMPRESS = """
from lxml import etree
print(sorted(etree.LIBXML_FEATURES & {"zlib", "lzma"}))
try:
    etree.parse("/w.xml.gz", etree.XMLParser(decompress=True))
    print("parsed")
except etree.XMLSyntaxError:
    print("XMLSyntaxError")
"""


@BINARY
def test_libxml2_has_no_zlib(guest, which) -> None:
    """libxml2 is built without zlib, so `XMLParser(decompress=True)` on a
    gzip file raises `XMLSyntaxError`, as the README says; lxml compresses its own output through
    Python's gzip (the golden job)."""
    files = {"/w.xml.gz": gzip.compress(b"<w>1</w>", mtime=0)}
    r = guest(which, ["-c", DECOMPRESS], files=files)
    assert r.exit_code == 0, r.describe()
    assert r.text == "[]\nXMLSyntaxError\n", r.text


SCHEMATRON = """
from lxml import etree
try:
    import lxml.isoschematron
    print("imported")
except ImportError as e:
    print("ImportError", e)
s = etree.Schematron(etree.XML(
    b"<schema xmlns='http://www.ascc.net/xml/schematron'><pattern name='p'>"
    b"<rule context='r'><assert test='@k'>k</assert></rule></pattern></schema>"))
print(s.validate(etree.XML(b"<r k='1'/>")), s.validate(etree.XML(b"<r/>")))
"""


@BINARY
def test_isoschematron_is_left_out_and_schematron_validates(guest, which) -> None:
    """`lxml.isoschematron` reads its stylesheets by file path and their licences are not approved:
    a stand-in raises `ImportError` saying so. libxml2's own Schematron,
    `etree.Schematron`, validates."""
    r = guest(which, ["-c", SCHEMATRON])
    assert r.exit_code == 0, r.describe()
    lines = r.text.splitlines()
    assert lines[0].startswith("ImportError lxml.isoschematron is not in this build"), r.text
    assert "licences" in lines[0], r.text
    assert lines[1:] == ["True False"], r.text


READ_HTML = """
import io
import pandas as pd
t = "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>x</td></tr></table>"
print(pd.read_html(io.StringIO(t))[0].to_dict("list"))
"""


@BINARY
def test_read_html_uses_lxml_by_default(guest, which) -> None:
    """pandas' `read_html` with no `flavor` tries lxml first, so with lxml
    built in it returns the table instead of raising `ImportError`."""
    r = guest(which, ["-c", READ_HTML])
    assert r.exit_code == 0, r.describe()
    assert r.text == "{'a': [1], 'b': ['x']}\n", r.text


HTML_DIFF = """
from lxml.html.diff import htmldiff
print(htmldiff("<p>Hello world</p>", "<p>Hello there world</p>"))
"""


@BINARY
def test_lxml_html_diff_imports(guest, which) -> None:
    """`lxml.html.diff` imports and diffs as natively. The guest runs it as plain Python with no
    Cython, and its `fake_cython` lacked `final`, so `@cython.final` called a string until carried
    patch 0001, upstream's own line."""
    r = guest(which, ["-c", HTML_DIFF])
    assert r.exit_code == 0, r.describe()
    assert r.text == "<p>Hello <ins>there</ins> world</p>\n", r.text


@pytest.mark.slow
def test_lxml_xml_job_matches_native(guest) -> None:
    """The golden job: XPath, XSLT, objectify, C14N, lxml.html, files by
    path, validation, compressed output, the full-coverage encodings, and pandas' readers, equal
    to native lxml 6.1.3 at the guest's pins."""
    job = "lxml_xml"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest("plain", [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.render(r.stdout, r.root / "out"))
    assert why is None, why
