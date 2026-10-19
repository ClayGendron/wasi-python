"""Golden job: HTML and XML (spec 039, Decisions 9 and 11).

Usage: markup.py <data dir> <out dir> (both unused). One messy HTML page goes through
BeautifulSoup with `html.parser` and with `html5lib`, CSS selectors (soupsieve), and
`pd.read_html` with `flavor="bs4"` and with its default flavor, which is lxml (spec 046) and
gives the same table. Then a webencodings lookup, html5lib alone, xmltodict both ways, and
defusedxml parsing a plain document and refusing one that defines entities.
"""

import io
from importlib.metadata import version

import bs4
import defusedxml
import html5lib
import pandas as pd
import webencodings
import xmltodict
from defusedxml import ElementTree as DET

names = (
    "beautifulsoup4",
    "soupsieve",
    "html5lib",
    "webencodings",
    "defusedxml",
    "xmltodict",
    "lxml",
    "pandas",
)
print("versions", " ".join(f"{d}={version(d)}" for d in names))

page = """<html><head><meta charset="utf-8"><title>Q3</title></head><body>
<p class="note">Sales <b>by region</b><p>unclosed
<table id="t"><tr><th>region</th><th>units</th></tr>
<tr><td>north</td><td>3</td></tr><tr><td>south</td><td>5</td></table>
<a href="/a">A</a> <a href="/b" class="x">B</a></body></html>"""

for parser in ("html.parser", "html5lib"):
    s = bs4.BeautifulSoup(page, parser)
    hrefs = [a["href"] for a in s.select("a.x, a[href='/a']")]
    note = s.select_one("p.note").get_text(" ", strip=True)
    print(parser, s.title.string, hrefs, note, len(s.find_all("p")))

with_bs4 = pd.read_html(io.StringIO(page), flavor="bs4")[0]
print(with_bs4.to_csv(index=False), end="")
default = pd.read_html(io.StringIO(page))[0]
print("read_html default flavor equals bs4:", default.equals(with_bs4))

paragraph = html5lib.parse("<p>café", namespaceHTMLElements=False).find(".//p")
print(webencodings.lookup("latin1").name, paragraph.text)

xml = "<order id='7'><item sku='a'>2</item><item sku='b'>3</item></order>"
d = xmltodict.parse(xml)
print(d)
print(xmltodict.unparse(d, full_document=False))
print(DET.fromstring(xml).get("id"))
bomb = '<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><l>&b;</l>'
try:
    DET.fromstring(bomb)
except defusedxml.EntitiesForbidden as e:
    print("defusedxml:", type(e).__name__)
