SINK = r'''
import io, json, csv, re, pickle, sqlite3, zipfile, decimal, fractions, statistics, textwrap, difflib, ast, os
import numpy as np, pandas as pd
a = np.random.default_rng(1).normal(size=(200, 200))
np.linalg.inv(a); np.linalg.svd(a[:50, :50]); np.fft.fft(a[0]); np.sort(a, axis=None); np.einsum("ij,jk->ik", a, a)
df = pd.DataFrame({"k": np.arange(5000) % 37, "v": np.arange(5000.0), "s": [str(i) for i in range(5000)]})
g = df.groupby("k").agg({"v": ["sum", "mean"], "s": "count"})
m = df.merge(df.head(100), on="k")
buf = io.StringIO(); df.to_csv(buf); buf.seek(0); d2 = pd.read_csv(buf)
pd.to_datetime(pd.Series(["2024-01-01"] * 100)); df.pivot_table(index="k", values="v")
con = sqlite3.connect(":memory:"); con.execute("create table t(x)"); con.executemany("insert into t values (?)", [(i,) for i in range(1000)])
con.execute("select sum(x), avg(x) from t where x % 3 = 0").fetchall()
json.loads(json.dumps({"a": [list(range(100))] * 50})); pickle.loads(pickle.dumps(df))
re.findall(r"(\w+)@(\w+)\.com", "a@b.com c@d.com " * 200); re.compile("|".join(f"x{i}y" for i in range(500)))
src = "\n".join(f"def f{i}(x):\n    return [y * {i} for y in range(x) if y % 2]" for i in range(300))
exec(compile(src, "s", "exec")); ast.parse(src)
z = io.BytesIO(); zf = zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED); zf.writestr("a", "x" * 100000); zf.close()
decimal.getcontext().prec = 50; decimal.Decimal(2).sqrt(); statistics.median(range(1001))
difflib.unified_diff(src.splitlines(), src.upper().splitlines()); textwrap.fill(src[:2000])
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(); ax.plot(np.arange(100), np.sin(np.arange(100))); ax.set_title("t"); ax.legend(["sin"])
fig.savefig(io.BytesIO(), format="png"); fig.savefig(io.BytesIO(), format="svg"); fig.savefig(io.BytesIO(), format="pdf")
print("sink ok")
'''
CASES = {"sink": SINK}
