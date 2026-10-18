"""Golden job: pandas time zones read from the tzdata package (spec 035). Usage: pandas_tz.py
<data dir> <out dir>. `zoneinfo.reset_tzpath(to=[])` makes native and guest alike read their zones
from `tzdata` through `importlib.resources`, never from a system zone folder; in the guest that
read is the reactor's own resource reader on the zip. Its output must be byte-identical natively
and in the guest."""

import sys
import zoneinfo

zoneinfo.reset_tzpath(to=[])

import pandas as pd  # noqa: E402
import tzdata  # noqa: E402

print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} pandas={pd.__version__}"
    f" tzdata={tzdata.__version__}"
)
paris = pd.Timestamp("2026-07-01 12:00", tz="Europe/Paris")
print("paris", paris.isoformat(), paris.utcoffset())
tokyo = pd.date_range("2026-03-01", periods=2, freq="D", tz="Asia/Tokyo")
print("tokyo", [t.strftime("%Y-%m-%d %z") for t in tokyo])
print("utc", paris.tz_convert("UTC").isoformat())
