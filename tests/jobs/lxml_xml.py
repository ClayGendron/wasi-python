"""Golden job: lxml over libxml2 and libxslt, and pandas' XML and HTML readers on it (spec 046).
Usage: lxml_xml.py <data dir> <out dir>.

It writes three small files into the data folder first, then reads them back by path, so
libxml2's own file input (the carried patch's code on WASI) is what reads them. It prints only
what libxml2 2.14 (the oracle's wheel) and 2.15 (the guest's) share: no library version, no error
message, and no XSLT `method="html"` output, whose `<meta>` form changed in 2.15 (spec 046,
Decision 10). The encodings are those wasi-libc's iconv converts in full, each over its whole
repertoire in the Basic Multilingual Plane (Decision 9's first row; GBK and cp949 for parsing).
"""

import gzip
import hashlib
import io
import os
import sys

import lxml
import pandas as pd
from lxml import etree, objectify
from lxml import html as lhtml

data, out = sys.argv[1], sys.argv[2]
print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} lxml={lxml.__version__} "
    f"pandas={pd.__version__}"
)

# XPath: counts, namespaces, string functions, EXSLT regular expressions, sets and math.
doc = etree.fromstring(
    b"<r xmlns:a='urn:a'><i n='3'>gamma</i><i n='1'>alpha<a:b k='x'/></i>"
    b"<i n='2'>beta</i><!-- c --><?pi d?></r>"
)
EX = {
    "a": "urn:a",
    "re": "http://exslt.org/regular-expressions",
    "set": "http://exslt.org/sets",
    "math": "http://exslt.org/math",
}
print("count", doc.xpath("count(//i)"))
print(
    "ns",
    [e.tag for e in doc.xpath("//a:b", namespaces=EX)],
    doc.xpath("string(//a:b/@k)", namespaces=EX),
)
print("string", doc.xpath("concat(name(/*), '-', sum(//i/@n), '-', translate(//i[1], 'a', 'A'))"))
print(
    "substr", doc.xpath("substring-before(//i[2], 'ph')"), doc.xpath("normalize-space('  x  y ')")
)
print("regex", doc.xpath("//i[re:test(., '^[ab]')]/@n", namespaces=EX))
print("replace", doc.xpath("re:replace(string(//i[1]), 'm+', 'g', 'M')", namespaces=EX))
print("sets", [e.text for e in doc.xpath("set:distinct(//i | //i[1])", namespaces=EX)])
print(
    "math",
    doc.xpath("math:max(//i/@n)", namespaces=EX),
    doc.xpath("math:min(//i/@n)", namespaces=EX),
)
print(
    "comment pi", [type(n).__name__ for n in doc.xpath("//comment() | //processing-instruction()")]
)

# XSLT with the xml output method: sorting, a parameter, EXSLT strings.
xslt = etree.XSLT(
    etree.fromstring(
        b"""<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'
 xmlns:str='http://exslt.org/strings' extension-element-prefixes='str'>
<xsl:param name='tag' select="'v'"/>
<xsl:output method='xml' indent='no'/>
<xsl:template match='/'><out total='{sum(//i/@n)}'><xsl:for-each select='//i'>
<xsl:sort select='@n' data-type='number' order='descending'/>
<xsl:element name='{$tag}'><xsl:value-of select='str:padding(2, "*")'/>
<xsl:value-of select='str:concat(str:tokenize(., "a"))'/></xsl:element></xsl:for-each>
</out></xsl:template></xsl:stylesheet>"""
    )
)
print("xslt", str(xslt(doc)).strip())
print("xslt param", str(xslt(doc, tag=etree.XSLT.strparam("w"))).strip())

# objectify
o = objectify.fromstring(b"<r><a>41</a><b>s</b><c>1.5</c><d>true</d><e/></r>")
print("objectify", o.a + 1, o.b.text, type(o.c).__name__, o.c * 2, bool(o.d), type(o.e).__name__)

# C14N, 1.0 and 2.0
c = etree.fromstring(b"<r xmlns:z='urn:z' b='2' a='1'><x/><!-- k --></r>")
print("c14n", etree.tostring(c, method="c14n"))
print("c14n2", etree.tostring(c, method="c14n2", with_comments=False))

# lxml.html: links, text_content, a document with a <meta charset> head
h = lhtml.fromstring(
    "<div><a href='/x'>one</a> and <a href='https://e.org/y'>two</a><p>p <b>b</b></p></div>"
)
print("links", [(e.tag, attr, link) for e, attr, link, _ in h.iterlinks()])
print("text", h.text_content())
page = lhtml.document_fromstring(
    "<html><head><meta charset='utf-8'><title>t</title></head><body><p>é</p></body></html>"
)
print("html", lhtml.tostring(page))
print("html broken", etree.tostring(etree.HTML(b"<p>a<b>b<p>c"), method="html"))

# iterparse
events = etree.iterparse(io.BytesIO(b"<r><a>1</a><b><c/></b></r>"), events=("start", "end"))
print("iterparse", [(ev, el.tag) for ev, el in events])

# Files by path in the data folder: a parse, XInclude and a DTD validation.
with open(os.path.join(data, "doc.xml"), "wb") as f:
    f.write(
        b'<?xml version="1.0"?>\n<!DOCTYPE d SYSTEM "d.dtd">\n<d k="v"><e>one</e><e>two</e></d>\n'
    )
with open(os.path.join(data, "d.dtd"), "wb") as f:
    f.write(b"<!ELEMENT d (e+)>\n<!ATTLIST d k CDATA #REQUIRED>\n<!ELEMENT e (#PCDATA)>\n")
with open(os.path.join(data, "inc.xml"), "wb") as f:
    f.write(
        b'<?xml version="1.0"?>\n<top xmlns:xi="http://www.w3.org/2001/XInclude">'
        b'<xi:include href="doc.xml"/></top>\n'
    )
t = etree.parse(os.path.join(data, "doc.xml"))
print("parse path", t.getroot().get("k"), [e.text for e in t.getroot()], t.docinfo.system_url)
print("iterparse path", [(ev, el.tag) for ev, el in etree.iterparse(os.path.join(data, "doc.xml"))])
inc = etree.parse(os.path.join(data, "inc.xml"))
inc.xinclude()
print("xinclude", [e.tag for e in inc.getroot().iter()], inc.getroot()[0].get("k"))
dtd = etree.DTD(os.path.join(data, "d.dtd"))
print("dtd", dtd.validate(t), dtd.validate(etree.fromstring(b"<d><x/></d>")))
print(
    "dtd parser",
    etree.parse(os.path.join(data, "doc.xml"), etree.XMLParser(dtd_validation=True)).getroot().tag,
)

# XML Schema and RELAX NG
xsd = etree.XMLSchema(
    etree.XML(
        b"<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'>"
        b"<xs:element name='r'><xs:complexType><xs:sequence>"
        b"<xs:element name='n' type='xs:int' maxOccurs='3'/></xs:sequence></xs:complexType>"
        b"</xs:element></xs:schema>"
    )
)
print(
    "xsd", xsd.validate(etree.XML(b"<r><n>5</n></r>")), xsd.validate(etree.XML(b"<r><n>x</n></r>"))
)
rng = etree.RelaxNG(
    etree.XML(
        b"<element name='r' xmlns='http://relaxng.org/ns/structure/1.0'>"
        b"<oneOrMore><element name='n'><text/></element></oneOrMore></element>"
    )
)
print("relaxng", rng.validate(etree.XML(b"<r><n>t</n></r>")), rng.validate(etree.XML(b"<r/>")))

# Writing by path, plain and gzip-compressed (lxml compresses through Python's gzip when libxml2
# has no zlib, as here).
w = etree.ElementTree(etree.XML(b"<w a='1'><v>\xc3\xa9</v></w>"))
w.write(os.path.join(out, "w.xml"), xml_declaration=True, encoding="UTF-8")
w.write(os.path.join(data, "w.xml.gz"), compression=6)
with gzip.open(os.path.join(data, "w.xml.gz")) as f:
    print("gzip", f.read())


# Encodings that wasi-libc's iconv converts in full, each over its whole BMP repertoire.
def chars(enc):
    found = []
    for cp in range(0xA0, 0x10000):
        if 0xD800 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF):
            continue
        try:
            chr(cp).encode(enc)
        except UnicodeEncodeError:
            continue
        found.append(chr(cp))
    return found


def differ(cs, root):
    return sum(1 for ch, e in zip(cs, root, strict=True) if e.text != ch)


for enc in ("windows-1252", "iso-8859-2", "iso-8859-15", "cp1251", "koi8-r", "tis-620", "utf-16"):
    cs = chars(enc)
    body = "".join(f"<c>{ch}</c>" for ch in cs)
    parsed = etree.fromstring(f'<?xml version="1.0" encoding="{enc}"?><r>{body}</r>'.encode(enc))
    raw = etree.tostring(etree.fromstring(f"<r>{body}</r>"), encoding=enc)
    back = etree.fromstring(raw)
    print(
        "encoding",
        enc,
        len(cs),
        differ(cs, parsed),
        differ(cs, back),
        hashlib.sha256(raw).hexdigest(),
    )
for enc in ("gbk", "cp949"):
    cs = chars(enc)
    body = "".join(f"<c>{ch}</c>" for ch in cs)
    parsed = etree.fromstring(f'<?xml version="1.0" encoding="{enc}"?><r>{body}</r>'.encode(enc))
    print("encoding", enc, len(cs), differ(cs, parsed))

# pandas: read_html with no flavor (lxml is its first), read_xml with an XPath and with a
# stylesheet, and to_xml through lxml into the output folder.
table = (
    "<table><thead><tr><th>a</th><th>b</th></tr></thead><tbody>"
    "<tr><td>1</td><td>x</td></tr><tr><td>2</td><td>y</td></tr></tbody></table>"
)
print("read_html", pd.read_html(io.StringIO(table))[0].to_dict("list"))
xml = (
    "<data><row><a>1</a><b>x</b></row><row><a>2</a><b>y</b></row><row><a>3</a><b>z</b></row></data>"
)
print("read_xml", pd.read_xml(io.StringIO(xml)).to_dict("list"))
print("read_xml xpath", pd.read_xml(io.StringIO(xml), xpath="//row[a>1]").to_dict("list"))
sheet = (
    "<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'>"
    "<xsl:template match='/'><data><xsl:for-each select='//row'><r><s><xsl:value-of select='a*10'/>"
    "</s><t><xsl:value-of select='b'/></t></r></xsl:for-each></data></xsl:template>"
    "</xsl:stylesheet>"
)
print(
    "read_xml stylesheet",
    pd.read_xml(io.StringIO(xml), stylesheet=io.StringIO(sheet)).to_dict("list"),
)
frame = pd.DataFrame({"a": [1, 2], "b": ["x", "é"], "c": [1.5, None]})
frame.to_xml(os.path.join(out, "frame.xml"), parser="lxml")
print("to_xml", frame.to_xml(parser="lxml", index=False, root_name="t", row_name="u"))
