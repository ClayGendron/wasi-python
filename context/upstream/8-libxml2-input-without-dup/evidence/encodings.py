from lxml import etree
txt = {"gbk": "中文", "gb18030": "中文", "gb2312": "中文", "big5": "中文", "euc-kr": "한국", "shift_jis": "日本", "iso-2022-jp": "日本", "euc-jp": "日本", "cp1251": "привет", "cp1252": "café €", "koi8-r": "привет", "iso-8859-15": "€", "utf-32": "x€", "mac-roman": "é", "cp437": "é", "tis-620": "ไทย", "windows-874": "ไทย", "cp932": "日本", "cp949": "한국", "cp950": "中文", "hz": "中文"}
out = []
for enc, t in txt.items():
    try:
        data = ('<?xml version="1.0" encoding="%s"?><r>%s</r>' % (enc, t)).encode(enc)
    except LookupError:
        out.append((enc, "python-has-no-codec")); continue
    try: p = etree.fromstring(data).text == t
    except Exception as e: p = type(e).__name__
    try: w = etree.tostring(etree.fromstring("<r>%s</r>" % t), encoding=enc).decode(enc).endswith("<r>%s</r>" % t)
    except Exception as e: w = type(e).__name__
    out.append((enc, p, w))
print(out)
