"""Golden job: time zones with pytz.

Usage: time_zones.py <data dir> <out dir> (both unused). pytz localizes and normalizes local
times across the changes of Paris, New York and Lord Howe, whose summer time is half an hour,
on both sides of each change and with `is_dst` either way; a time in a gap and one in an overlap
raise as pytz says. It lists its zones and New Zealand's, and a localized time survives a pickle
round trip with its zone the same object. pandas takes a pytz zone for a `Timestamp` and converts
it, since it imports pytz whenever it is there.
"""

import pickle
from datetime import datetime, timedelta
from importlib.metadata import version

import pandas as pd
import pytz

print("versions", f"pytz={version('pytz')}", f"pandas={version('pandas')}")


def show(dt):
    return f"{dt.isoformat()} {dt.tzname()} {dt.utcoffset()} {dt.dst()}"


paris = pytz.timezone("Europe/Paris")
new_york = pytz.timezone("America/New_York")
lord_howe = pytz.timezone("Australia/Lord_Howe")
CHANGES = (
    (paris, datetime(2026, 3, 29, 1, 30)),
    (paris, datetime(2026, 10, 25, 2, 30)),
    (new_york, datetime(2026, 3, 8, 1, 30)),
    (new_york, datetime(2026, 11, 1, 1, 30)),
    (lord_howe, datetime(2026, 4, 5, 1, 45)),
    (lord_howe, datetime(2026, 10, 4, 1, 45)),
)
for zone, naive in CHANGES:
    for is_dst in (True, False):
        local = zone.localize(naive, is_dst=is_dst)
        later = zone.normalize(local + timedelta(hours=1))
        print(zone.zone, is_dst, show(local), "->", show(later))
for naive in (datetime(2026, 3, 29, 2, 30), datetime(2026, 10, 25, 2, 30)):
    try:
        paris.localize(naive, is_dst=None)
    except pytz.exceptions.InvalidTimeError as e:
        print("refused", naive.isoformat(), type(e).__name__, e)
print("zones", len(pytz.all_timezones), len(pytz.common_timezones))
print("nz", pytz.country_timezones("nz"), pytz.country_names["nz"])
noon = paris.localize(datetime(2026, 7, 1, 12))
print("utc", noon.astimezone(pytz.utc).isoformat(), pytz.utc.localize(datetime(2026, 1, 1)))
again = pickle.loads(pickle.dumps(noon))
print("pickle", again.isoformat(), again == noon, again.tzinfo is noon.tzinfo)
stamp = pd.Timestamp("2026-07-01 12:00", tz=paris)
print("pandas", stamp.isoformat(), stamp.tz_convert(new_york).isoformat())
index = pd.date_range("2026-03-28", periods=4, freq="D", tz=paris)
print("range", [t.isoformat() for t in index], str(index.tz))
