"""Golden job: pandas read_csv, groupby, to_csv, a seeded synthetic frame, and time zones (which
exercise tzdata and dateutil). Usage: pandas_csv.py <data dir> <out dir>. Its output must be
byte-identical natively and in the guest."""

import os
import sys

import dateutil
import dateutil.parser
import numpy as np
import pandas as pd
import six
import tzdata


def f(x):
    return format(round(float(x), 9) + 0.0, ".9g")


data_dir, out_dir = sys.argv[1], sys.argv[2]
print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} numpy={np.__version__}"
    f" pandas={pd.__version__} python-dateutil={dateutil.__version__}"
    f" tzdata={tzdata.__version__} six={six.__version__}"
)
df = pd.read_csv(os.path.join(data_dir, "sales.csv"))
summary = df.groupby("region")["sales"].agg(["sum", "mean", "max", "count"])
print("rows", len(df), "regions", list(summary.index))
print(summary.round(6).to_string())
summary.to_csv(os.path.join(out_dir, "summary.csv"), float_format="%.9g", lineterminator="\n")

rng = np.random.default_rng(0)
n = 20_000
big = pd.DataFrame({"k": rng.integers(0, 50, n, dtype=np.int64), "v": rng.random(n)})
groups = big.groupby("k")["v"].agg(["sum", "mean", "max", "count"])
groups.to_csv(os.path.join(out_dir, "groups.csv"), float_format="%.9g", lineterminator="\n")
print("groups", len(groups), "total", f(groups["sum"].sum()), "rows", int(groups["count"].sum()))

months = pd.to_datetime(df["month"].map(lambda m: f"2026-{m:02d}-15 12:00"))
utc = months.dt.tz_localize("Europe/Paris").dt.tz_convert("UTC")
print("tz", utc.iloc[0].isoformat(), utc.iloc[-1].isoformat())
print("dateutil", dateutil.parser.parse("2026-10-16T12:00:00+02:00").isoformat())
