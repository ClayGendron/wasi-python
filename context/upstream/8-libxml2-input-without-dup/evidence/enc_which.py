from lxml import etree
for enc, cs in (("shift_jis", "¥‾＼"), ("iso-2022-jp", "＼"), ("gb2312", "―・")):
    for c in cs:
        doc = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, c)).encode(enc)
        try: g = etree.fromstring(doc).text
        except Exception as e: g = type(e).__name__
        print(enc, "U+%04X" % ord(c), c.encode(enc).hex(), "->", "U+%04X" % ord(g) if isinstance(g, str) and len(g) == 1 else repr(g))
