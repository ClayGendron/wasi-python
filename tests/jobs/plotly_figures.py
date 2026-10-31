"""Golden job: interactive figures with plotly.

Usage: plotly_figures.py <data dir> <out dir>. It reads sales.csv from the data dir and writes two
HTML files to the out dir. A `go.Figure` of sales.csv and a `px.scatter` of plotly's own iris
dataset are built; their JSON (through the standard library's json, `engine="json"`, so no
orjson can change the bytes) is printed as length and SHA-256, and so is each HTML page. Every
page has a fixed `div_id`, since plotly otherwise draws a random UUID for each. `write_html` writes
one page with plotly.js inside (`include_plotlyjs=True`, a page that works offline) and one that
loads it from plotly's CDN; `to_html` makes a fragment. The election map's GeoJSON is read from
plotly's datasets. Static images need kaleido, which is not installed: `to_image` raises, as it
does natively without it.
"""

import csv
import hashlib
import os
import sys
from importlib.metadata import version

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

print("versions", f"plotly={version('plotly')}")
data_dir, out_dir = sys.argv[1], sys.argv[2]


def digest(text):
    data = text.encode() if isinstance(text, str) else text
    return f"{len(data)} {hashlib.sha256(data).hexdigest()[:16]}"


with open(os.path.join(data_dir, "sales.csv"), newline="") as f:
    rows = list(csv.DictReader(f))
print("rows", len(rows), sorted(rows[0]))
key, value = sorted(rows[0])[0], sorted(rows[0])[-1]

fig = go.Figure(
    go.Bar(x=[r[key] for r in rows], y=[r[value] for r in rows], name="sales"),
    layout=go.Layout(title="Sales", template="plotly_white"),
)
fig.add_trace(go.Scatter(x=[r[key] for r in rows], y=[r[value] for r in rows], mode="lines"))
print("figure", len(fig.data), [t.type for t in fig.data], fig.layout.title.text)
print("figure json", digest(fig.to_json(engine="json")))

iris = px.data.iris()
print("iris", iris.shape, list(iris.columns))
scatter = px.scatter(iris, x="sepal_width", y="sepal_length", color="species", trendline=None)
print("scatter", len(scatter.data), [t.name for t in scatter.data])
print("scatter json", digest(scatter.to_json(engine="json")))
print("tips", px.data.tips().shape, "gapminder", px.data.gapminder().shape)

geo = px.data.election_geojson()
print("election geojson", geo["type"], len(geo["features"]), sorted(geo["features"][0]))

fragment = pio.to_html(scatter, include_plotlyjs=False, full_html=False, div_id="iris")
print("fragment", digest(fragment))
offline = os.path.join(out_dir, "offline.html")
scatter.write_html(offline, include_plotlyjs=True, div_id="iris")
with open(offline, "rb") as f:
    page = f.read()
print("offline page", digest(page), b"plotly.js v" in page)
cdn = os.path.join(out_dir, "cdn.html")
fig.write_html(cdn, include_plotlyjs="cdn", div_id="sales")
with open(cdn, "rb") as f:
    page = f.read()
print("cdn page", digest(page), b"https://cdn.plot.ly/plotly-" in page)
os.remove(offline)  # 4.8 MB of plotly.js: its digest above is enough
os.remove(cdn)

try:
    fig.to_image(format="png")
except Exception as e:
    print("to_image", type(e).__name__, "kaleido" in str(e).lower())
