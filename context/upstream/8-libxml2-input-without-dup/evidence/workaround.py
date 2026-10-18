from lxml import etree
for enc in ("cp932", "euc-jp", "gb18030", "big5"):
    cs = []
    for cp in range(0xA0, 0x10000):
        if 0xD800 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF): continue
        try: chr(cp).encode(enc); cs.append(chr(cp))
        except UnicodeEncodeError: pass
    data = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, "".join("<c>%s</c>" % c for c in cs))).encode(enc)
    root = etree.fromstring(data.decode(enc).encode("utf-8"), etree.XMLParser(encoding="utf-8"))
    print(enc, len(cs), sum(1 for c, e in zip(cs, root) if e.text != c))
