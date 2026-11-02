"""Golden job: labelled arrays with xarray.

Usage: labelled_arrays.py <data dir> <out dir> (both unused). A daily series at three sites,
made by plain arithmetic (no random numbers, and no function each libm rounds its own way), goes
through what an analysis does with xarray: alignment of two arrays on their labels, a monthly
`groupby`, a centred `rolling` mean, a monthly `resample`, a cubic `interp` (through scipy), a
pandas DataFrame round trip, and netCDF3 bytes written in memory (through scipy's writer), printed
as length and SHA-256, and read back. The HTML view reads its stylesheet and icons from the
package's files; each element id it draws is a fresh random UUID, so each is replaced by a fixed
token before the HTML is hashed. An engine and the tutorial data whose packages are not installed
fail by name, as they do natively without them.
"""

import hashlib
import io
import re
from importlib.metadata import version

import numpy as np
import pandas as pd
import xarray as xr

print("versions", f"xarray={version('xarray')}")

times = pd.date_range("2026-01-01", periods=120, freq="D")
day = np.arange(120, dtype=float)
values = np.stack([(day % 17) * 1.5 - (day % 5) / 4 + day / 10 + k for k in (0, 2.5, -1)], axis=1)
da = xr.DataArray(
    values,
    dims=("time", "site"),
    coords={"time": times, "site": ["a", "b", "c"]},
    name="temp",
    attrs={"units": "degC"},
)
print(da)


def show(label, arr):
    print(label, arr.dims, arr.shape, np.round(np.nansum(arr.values), 6))


other = da.isel(time=slice(10, 50)).sel(site=["b", "c"]) * 2
show("sum", da + other)
a, b = xr.align(da, other, join="outer")
print("outer", a.shape, b.shape, int(b.isnull().sum()))
a, b = xr.align(da, other, join="inner")
print("inner", a.shape, a.site.values.tolist(), str(a.time.values[0])[:10])

monthly = da.groupby("time.month").mean()
print(monthly.round(4).to_pandas().to_string())
rolled = da.rolling(time=7, center=True).mean()
show("rolling", rolled)
print("rolling nans", int(rolled.isnull().sum()))
print(da.resample(time="MS").max().round(4).to_pandas().to_string())

at = pd.date_range("2026-01-01T12:00", periods=5, freq="17D")
print(da.sel(site="b").interp(time=at, method="cubic").round(6).values.tolist())
print(da.interp(time=at[:2]).round(6).values.tolist())

ds = da.to_dataset()
ds["count"] = ("time", day % 5)  # float: the guest's default integer is 32-bit
df = ds.to_dataframe()
print(df.shape, list(df.columns))
print(df.head(4).to_string())
back = xr.Dataset.from_dataframe(df)
print(
    "dataframe round trip",
    back["temp"].transpose("time", "site").equals(ds["temp"]),
    back["count"].dims,
)

data = bytes(ds.to_netcdf())
print("netcdf3", len(data), data[:4], hashlib.sha256(data).hexdigest()[:16])
with xr.open_dataset(io.BytesIO(data)) as read:
    print("read", sorted(read.data_vars), read["temp"].attrs, read.time.dtype)
    print("netcdf round trip", read.load().identical(ds))

html = ds._repr_html_()
ids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html)
fixed = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "ID", html)
print("html", len(fixed), len(ids) > 0, hashlib.sha256(fixed.encode()).hexdigest()[:16])
print("html has the icons and the stylesheet", "icon-database" in html, "--xr-font-color0" in html)

try:
    xr.open_dataset(io.BytesIO(data), engine="h5netcdf")
except Exception as e:
    print("h5netcdf", type(e).__name__)
try:
    xr.tutorial.load_dataset("air_temperature")
except Exception as e:
    print("tutorial", type(e).__name__)
