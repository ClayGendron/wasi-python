"""Golden job: the files two packages read by path, read from the zip (spec 041, Decision 7).

Usage: files_from_the_zip.py <data dir> <out dir>. pandas' Styler renders through its jinja2
templates: a formatted, highlighted frame to HTML with a fixed uuid, `df.to_latex()`, a longtable
with a caption, plain text and Typst, and a custom template that extends `html_table.tpl`,
written to the data folder (every file in the output folder is compared byte for byte, so it stays
empty) and passed to `Styler.from_custom_template`. networkx reads its graph atlas: graph 100's
name and sorted edges, and the count and total edges of all 1,253 graphs. Natively the files are
on disk; in the guest they are members of the zip, which spec 041's two carried patches read.
"""

import sys
from importlib.metadata import version
from pathlib import Path

import networkx as nx
import pandas as pd
from pandas.io.formats.style import Styler

data = Path(sys.argv[1])
names = ("pandas", "jinja2", "networkx")
print("versions", " ".join(f"{d}={version(d)}" for d in names))


def show(label: str, text: str) -> None:
    print(f"--- {label} ({len(text)} characters)")
    print(text, end="" if text.endswith("\n") else "\n")


df = pd.DataFrame({"a": [1.5, 2.25, None], "b": ["x", "<y>", "z"]}, index=["r1", "r2", "r3"])
styled = df.style.set_uuid("job").format(precision=2).highlight_max(color="red")
show("df.style.to_html()", styled.to_html())
show("df.to_latex()", df.to_latex())
show("df.style.to_latex()", df.style.to_latex(environment="longtable", caption="A caption"))
show("df.style.to_string()", df.style.to_string())
show("df.style.to_typst()", df.style.to_typst())

(data / "mine.tpl").write_text(
    '{% extends "html_table.tpl" %}{% block table %}<p>mine</p>{{ super() }}{% endblock table %}'
)
Mine = Styler.from_custom_template(str(data), html_table="mine.tpl")
show("from_custom_template", Mine(df, uuid="custom").to_html())

g = nx.graph_atlas(100)
print("--- nx.graph_atlas(100)")
print(g.name, sorted(g.edges()))
atlas = nx.graph_atlas_g()
print("--- nx.graph_atlas_g()")
print(len(atlas), sum(h.number_of_edges() for h in atlas))
