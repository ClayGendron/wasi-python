import hashlib
import sys
from pathlib import Path

import jinja2
import networkx as nx
import pandas as pd

data = Path(sys.argv[1])
df = pd.DataFrame({"a": [1.5, 2.25, None], "b": ["x", "<y>", "z"]}, index=["r1", "r2", "r3"])
calls = {
    "df.style.to_html()": lambda: df.style.set_uuid("j").format(precision=2).highlight_max(color="red").to_html(),
    "df.to_latex()": lambda: df.to_latex(),
    "df.style.to_latex()": lambda: df.style.to_latex(environment="longtable", caption="c"),
    "df.style.to_string()": lambda: df.style.to_string(),
    "df.style.to_typst()": lambda: df.style.to_typst(),
    "custom": None,
    "nx.graph_atlas(100)": lambda: repr((sorted(nx.graph_atlas(100).edges()), nx.graph_atlas(100).name)),
    "nx.graph_atlas_g()": lambda: repr((len(gs := nx.graph_atlas_g()), sum(g.number_of_edges() for g in gs))),
}
(data / "mine.tpl").write_text('{% extends "html_table.tpl" %}{% block table %}<p>mine</p>{{ super() }}{% endblock table %}')
def custom():
    from pandas.io.formats.style import Styler
    S = Styler.from_custom_template(str(data), html_table="mine.tpl")
    return S(df, uuid="k").to_html()
calls["custom"] = custom
for name, f in calls.items():
    try:
        out = f()
        print(name, "ok", len(out), hashlib.sha256(out.encode()).hexdigest()[:16])
    except Exception as e:
        print(name, "FAIL", type(e).__name__, getattr(e, "name", None) or str(e)[:80])
from pandas.io.formats.style_render import StylerRenderer
print("loader", type(StylerRenderer.loader).__name__)
