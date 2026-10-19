"""Golden job: the utility libraries (spec 039, Decisions 9 and 11).

Usage: utilities.py <data dir> <out dir>. attrs (a validated, ordered class, asdict, evolve, a
validator's ValueError); more-itertools and toolz; tqdm counting into a StringIO and formatting
a meter with a fixed elapsed time; typing_extensions' TypedDict with NotRequired; joblib's
Parallel with one and two jobs (the guest runs both serially, with the same result), Memory
caching in the writable data folder, hash, dump and load through a buffer; cloudpickle with a
closure and a class; a narwhals group-by over a pandas frame.
"""

import io
import sys
from importlib.metadata import version

import attrs
import cloudpickle
import joblib
import more_itertools as mi
import narwhals as nw
import pandas as pd
import toolz
import toolz.curried
import tqdm
import typing_extensions as te

data_dir = sys.argv[1]
names = (
    "attrs",
    "more-itertools",
    "toolz",
    "tqdm",
    "typing-extensions",
    "joblib",
    "cloudpickle",
    "narwhals",
    "pandas",
)
print("versions", " ".join(f"{d}={version(d)}" for d in names))


@attrs.define(order=True)
class P:
    x: int
    y: int = attrs.field(default=0, validator=attrs.validators.ge(0))


print(P(1), sorted([P(2), P(1, 3)]), attrs.asdict(P(4, 5)), attrs.evolve(P(1), y=9))
try:
    P(1, -1)
except ValueError as e:
    print("attrs:", type(e).__name__)

print(
    list(mi.chunked(range(7), 3)),
    list(mi.windowed("abcd", 2)),
    mi.first([], default="none"),
    list(mi.unique_everseen("abacb")),
)
print(
    toolz.groupby(len, ["a", "bb", "cc", "d"]),
    toolz.pipe(range(5), toolz.curried.map(lambda v: v * v), list),
    toolz.frequencies("abca"),
)

bar = tqdm.tqdm(range(50), file=io.StringIO(), mininterval=0)
print(sum(bar), bar.n, tqdm.tqdm.format_meter(n=25, total=100, elapsed=12.5, ncols=60))


class TD(te.TypedDict):
    a: int
    b: te.NotRequired[str]


print(te.get_type_hints(TD), te.is_typeddict(TD), te.Literal["x"])

serial = joblib.Parallel(n_jobs=1)(joblib.delayed(pow)(i, 2) for i in range(5))
two = joblib.Parallel(n_jobs=2)(joblib.delayed(pow)(i, 3) for i in range(5))
print(serial, two)
memory = joblib.Memory(location=data_dir, verbose=0)
square = memory.cache(lambda v: v * v)
print(square(4), square(4), joblib.hash([1, 2, 3]))
buf = io.BytesIO()
joblib.dump({"a": [1, 2]}, buf)
buf.seek(0)
print(joblib.load(buf))

k = 3
add_k = cloudpickle.loads(cloudpickle.dumps(lambda v: v + k))
print(add_k(4), cloudpickle.loads(cloudpickle.dumps(P))(2, 1))

df = nw.from_native(pd.DataFrame({"g": ["a", "b", "a"], "v": [1, 2, 3]}), eager_only=True)
print(df.group_by("g").agg(nw.col("v").sum()).sort("g").to_native().to_csv(index=False), end="")
