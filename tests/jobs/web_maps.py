"""Golden job: web maps with folium, branca and xyzservices.

Usage: web_maps.py <data dir> <out dir> (both unused). folium draws a map with a marker, a
circle marker, a GeoJSON layer from a dict, a choropleth of a pandas frame, a branca linear
colour scale, a layer control and a marker cluster, and renders its HTML page and its notebook
view, each printed as length and SHA-256. Each element's id is a fresh random UUID, so each is
replaced, in the order it first appears, by a numbered token before the HTML is hashed. The
page loads Leaflet and its plugins from CDNs when a browser opens it; nothing is fetched here.
branca gives a ColorBrewer scheme and xyzservices a tile URL and its count of providers.
"""

import hashlib
import re
from importlib.metadata import version

import branca
import folium
import pandas as pd
import xyzservices.providers as xyz
from branca.colormap import LinearColormap
from branca.utilities import color_brewer
from folium import plugins

print(
    "versions",
    f"folium={version('folium')}",
    f"branca={version('branca')}",
    f"xyzservices={version('xyzservices')}",
    branca.__version__,
)
UUID_HEX = re.compile(r"[0-9a-f]{32}")


def fixed(html):
    seen = {}
    return UUID_HEX.sub(lambda m: seen.setdefault(m[0], f"ID{len(seen)}"), html), len(seen)


def digest(text):
    data = text.encode()
    return f"{len(data)} {hashlib.sha256(data).hexdigest()[:16]}"


def square(x, y, name):
    ring = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]
    return {
        "type": "Feature",
        "id": name,
        "properties": {"name": name},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


shapes = {"type": "FeatureCollection", "features": [square(2, 48, "a"), square(3, 48, "b")]}
frame = pd.DataFrame({"name": ["a", "b"], "value": [3.0, 7.5]})

m = folium.Map(location=[48.85, 2.35], zoom_start=6, tiles="OpenStreetMap")
folium.Marker([48.85, 2.35], popup="Paris", tooltip="a marker").add_to(m)
folium.CircleMarker([45.76, 4.84], radius=8, color="crimson", fill=True).add_to(m)
folium.GeoJson(shapes, name="squares", tooltip=folium.GeoJsonTooltip(["name"])).add_to(m)
folium.Choropleth(
    geo_data=shapes,
    data=frame,
    columns=["name", "value"],
    key_on="feature.id",
    fill_color="YlGn",
    legend_name="value",
    name="choropleth",
).add_to(m)
scale = LinearColormap(["green", "yellow", "red"], vmin=0, vmax=10, caption="scale")
scale.add_to(m)
cluster = plugins.MarkerCluster(name="cluster").add_to(m)
for lat, lon in ((43.30, 5.37), (43.60, 1.44), (44.84, -0.58)):
    folium.Marker([lat, lon]).add_to(cluster)
folium.LayerControl().add_to(m)

page, ids = fixed(m.get_root().render())
print("page", digest(page), "ids", ids)
view, view_ids = fixed(m._repr_html_())
print("view", digest(view), "ids", view_ids)
print("scale", scale(2.5), scale(7.5), len(scale.to_step(5).colors))
print("brewer", color_brewer("YlGn", 6))
print("tiles", xyz.CartoDB.Positron.build_url(), len(xyz.flatten()))
