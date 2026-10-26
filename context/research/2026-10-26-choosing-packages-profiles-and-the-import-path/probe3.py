import sys
from pathlib import Path
from wasi_python import Grant, run
S = Path(sys.argv[1])
code = """
import plotly, plotly.graph_objects as go, importlib.metadata as m
fig = go.Figure(data=[go.Bar(x=['a', 'b'], y=[1, 3])])
s = fig.to_json()
print(m.version('plotly'), len(s), 'bar' in s)
html = fig.to_html(include_plotlyjs=False)
print(len(html))
"""
for label, folder in (("plotly from a source folder", S / "lib-plotly"),):
    d = run(["-c", code], grants=[Grant(folder, "/lib")], import_path=["/lib"], fuel=400_000_000_000)
    print(label, "exit", d.exit_code, "fuel", f"{d.fuel_used:,}", d.stdout.decode().strip().replace("\n", " | "), d.stderr.decode().strip().splitlines()[-1:] )
