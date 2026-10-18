import sys, hashlib
if len(sys.argv) > 1: sys.path.insert(0, sys.argv[1])
from lxml import etree
ENCS = ["windows-1252", "iso-8859-2", "iso-8859-15", "cp1251", "koi8-r", "tis-620", "shift_jis", "cp932", "euc-jp", "iso-2022-jp", "gbk", "gb18030", "gb2312", "big5", "euc-kr", "cp949", "cp950", "utf-16"]
def chars(enc):
    out = []
    for cp in range(0xA0, 0x10000):
        if 0xD800 <= cp < 0xE000 or 0xE000 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF): continue
        c = chr(cp)
        try: c.encode(enc)
        except UnicodeEncodeError: continue
        out.append(c)
    return out
for enc in ENCS:
    cs = chars(enc)
    body = "".join("<c>%s</c>" % c for c in cs)
    doc = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, body)).encode(enc)
    try:
        got = [e.text for e in etree.fromstring(doc)]
        bad = [c for c, g in zip(cs, got) if c != g]
        p = "parse %d/%d bad %d%s" % (len(cs) - len(bad), len(cs), len(bad), (" e.g. " + ",".join("U+%04X" % ord(c) for c in bad[:4])) if bad else "")
    except Exception as e:
        p = "parse RAISES %s %s" % (type(e).__name__, str(e)[:60])
    try:
        root = etree.fromstring("<r>%s</r>" % body)
        raw = etree.tostring(root, encoding=enc)
        txt = raw.decode(enc)
        got = [e.text for e in etree.fromstring(txt.split("?>", 1)[1] if txt.startswith("<?xml") else txt)]
        bad = [c for c, g in zip(cs, got) if c != g]
        w = "write bad %d sha %s%s" % (len(bad), hashlib.sha256(raw).hexdigest()[:12], (" e.g. " + ",".join("U+%04X" % ord(c) for c in bad[:4])) if bad else "")
    except Exception as e:
        w = "write RAISES %s %s" % (type(e).__name__, str(e)[:50])
    print(enc, "|", p, "|", w)
