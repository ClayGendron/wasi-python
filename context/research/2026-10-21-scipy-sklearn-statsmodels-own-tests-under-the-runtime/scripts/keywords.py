"""Write the three SCIPY_XSLOW keyword entries from scipy's own parameter lists, read as data
(ast.literal_eval of the sdist's _distr_params.py, nothing imported), and check each id exists in
a collection's output. Usage: keywords.py <scipy tree> <collected ids file>"""

import ast
import sys
from pathlib import Path

tree, ids_file = Path(sys.argv[1]), Path(sys.argv[2])
src = (tree / "scipy/stats/_distr_params.py").read_text()
mod = ast.parse(src)
lists = {}
for node in mod.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in ("distcont", "distdiscrete"):
            lists[name] = ast.literal_eval(node.value)
cont, disc = lists["distcont"], lists["distdiscrete"]
ids = set(Path(ids_file).read_text().split())

SLOW = {"argus", "exponpow", "exponweib", "genexpon", "gompertz", "johnsonsb", "kappa4", "ksone",
        "kstwo", "kstwobign", "norminvgauss", "powerlognorm", "powernorm", "recipinvgauss",
        "studentized_range", "vonmises_line"}
rv = [f"test_rv_generic[{i}-distdata{i}]" for i, d in enumerate(cont + disc) if d[0] in SLOW]
acc = sorted({f"test_accuracy[numpy-case{i}-" for i, d in enumerate(cont)
              if d[0] in ("studentized_range", "levy_stable")})
P = "scipy/stats/tests/test_continuous.py::TestMakeDistribution::"
T = "scipy/integrate/tests/test_tanhsinh.py::TestTanhSinh::"
for k in rv:
    assert P + k in ids, k
acc_ids = sorted(i for i in ids if any((T + a) in i for a in acc))
print("test_rv_generic cases:", len(rv))
print("test_accuracy ids:", len(acc_ids))
print("K continuous:", " or ".join(rv))
acc_k = []
for a in acc:
    acc_k += [a + "0.5]", a + "ref1]"]
for k in acc_k:
    assert T + k in ids, k
print("K tanhsinh:", " or ".join(acc_k))
print("K axis_nan_policy: test_axis_nan_policy_full or kruskal or friedmanchisquare")
