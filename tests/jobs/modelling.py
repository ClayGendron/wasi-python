"""Golden job: graphs and model formulas (spec 039, Decision 11).

Usage: modelling.py <data dir> <out dir> (both unused). networkx on Zachary's karate club (its
size, a shortest path, the top three by betweenness, Louvain communities with a fixed seed) and
on a small weighted directed graph (Dijkstra, a topological order, a minimum spanning tree);
patsy builds `y ~ x + C(g)` on a small frame, and numpy fits it by least squares. Nothing here
needs scipy, so the output does not depend on whether spec 037 has landed.
"""

from importlib.metadata import version

import networkx as nx
import numpy as np
import pandas as pd
import patsy

names = ("networkx", "patsy", "numpy", "pandas")
print("versions", " ".join(f"{d}={version(d)}" for d in names))

g = nx.karate_club_graph()
print(g.number_of_nodes(), g.number_of_edges(), nx.shortest_path(g, 0, 33))
bc = nx.betweenness_centrality(g)
print(sorted(bc, key=lambda n: (-bc[n], n))[:3], round(bc[0], 6))
print(sorted(len(c) for c in nx.community.louvain_communities(g, seed=7)))

d = nx.DiGraph([("a", "b", {"w": 2}), ("b", "c", {"w": 1}), ("a", "c", {"w": 5})])
print(
    nx.dijkstra_path(d, "a", "c", weight="w"),
    list(nx.topological_sort(d)),
    nx.is_directed_acyclic_graph(d),
)
print(sorted(nx.minimum_spanning_tree(nx.Graph(d)).edges()))

frame = pd.DataFrame({"y": [1.0, 2, 3, 4], "x": [1.0, 0, 2, 3], "g": list("abab")})
y, X = patsy.dmatrices("y ~ x + C(g)", frame, return_type="dataframe")
print(X.design_info.column_names)
print(X.to_csv(index=False), end="")
beta, *_ = np.linalg.lstsq(X.values, y.values.ravel(), rcond=None)
print(np.round(beta, 6).tolist())
