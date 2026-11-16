"""Golden job: orjson, fast JSON compiled from Rust.

Usage: orjson_json.py <data dir> <out dir> (both unused). Named `orjson_json`, not `orjson`, so
the script's own folder on sys.path cannot hide the package. It prints orjson's `dumps` with
sorted, indented, non-string-key, numpy and passthrough options over datetimes, UUIDs,
dataclasses, enums, integers to 2**64 and text from several scripts; `loads` of the same; a
`Fragment`; both depth limits; and both error types with their messages and positions. Each
result is printed as its length and SHA-256, and in full when it is short, so a change of one byte
shows on its own line. Both sides run orjson 3.13.0's own code, so the bytes must be equal.
"""

import dataclasses
import datetime
import enum
import hashlib
import json
import sys
import uuid

import numpy as np
import orjson


def show(label, f):
    try:
        out = f()
    except Exception as e:
        print(label, "-> RAISES", type(e).__name__, str(e)[:200])
        return
    if isinstance(out, bytes):
        digest = hashlib.sha256(out).hexdigest()
        text = out.decode() if len(out) <= 320 else "..."
        print(label, "->", len(out), digest, text.replace("\n", "\\n"))
    else:
        print(label, "->", repr(out)[:320])


class Colour(enum.Enum):
    RED = "red"
    GREEN = 2


class Level(enum.IntEnum):
    LOW = 1
    HIGH = 1 << 40


@dataclasses.dataclass
class Point:
    x: int
    y: float
    label: str = "p"


@dataclasses.dataclass(slots=True)
class Shape:
    name: str
    points: list
    colour: Colour
    made: datetime.datetime


IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
WHEN = datetime.datetime(2026, 11, 15, 12, 30, 45, 123456, tzinfo=IST)
NAIVE = datetime.datetime(1999, 12, 31, 23, 59, 59)
UTC = datetime.datetime(2000, 2, 29, 0, 0, 0, 1, tzinfo=datetime.UTC)
ID = uuid.UUID("7d444840-9dc0-11d1-b245-5ffdce74fad2")
TEXT = ["ascii", "é ü ß", "中文字符", "Ελληνικά", "👩‍💻 \U0001f600", "  ", '\x00\x1f"']
RECORD = {
    "id": ID,
    "when": WHEN,
    "naive": NAIVE,
    "utc": UTC,
    "date": datetime.date(2026, 1, 2),
    "time": datetime.time(7, 8, 9, 10),
    "point": Point(1, 2.5),
    "shape": Shape("tri", [Point(0, 0.0), Point(3, 4.0, "q")], Colour.RED, WHEN),
    "colour": Colour.GREEN,
    "level": Level.HIGH,
    "ints": [0, -1, 2**53, 2**60, -(2**60), 2**63 - 1, -(2**63), 2**64 - 1],
    "floats": [0.1, -0.0, 1e300, 5e-324, 1 / 3, 123456789.125, float("nan"), float("inf")],
    "text": TEXT,
    "nested": {"b": [True, False, None], "a": {"z": 1, "y": [{}], "x": []}},
}

print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} orjson={orjson.__version__}")
show("record", lambda: orjson.dumps(RECORD))
show(
    "sorted indented",
    lambda: orjson.dumps(RECORD, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2),
)
show(
    "naive utc z",
    lambda: orjson.dumps([NAIVE, UTC], option=orjson.OPT_NAIVE_UTC | orjson.OPT_UTC_Z),
)
show("omit microseconds", lambda: orjson.dumps([WHEN, UTC], option=orjson.OPT_OMIT_MICROSECONDS))
show("append newline", lambda: orjson.dumps(TEXT, option=orjson.OPT_APPEND_NEWLINE))
show("strict integer", lambda: orjson.dumps(2**53 + 1, option=orjson.OPT_STRICT_INTEGER))
show("too big an integer", lambda: orjson.dumps(2**64))
show(
    "passthrough datetime",
    lambda: orjson.dumps(
        {"when": WHEN, "date": RECORD["date"]},
        option=orjson.OPT_PASSTHROUGH_DATETIME,
        default=lambda o: o.strftime("%d %b %Y"),
    ),
)
show(
    "passthrough dataclass",
    lambda: orjson.dumps(Point(1, 2.0), option=orjson.OPT_PASSTHROUGH_DATACLASS, default=repr),
)
show(
    "default", lambda: orjson.dumps({"set": {3}, "c": 1j}, default=lambda o: str(sorted([str(o)])))
)
show("no default", lambda: orjson.dumps({1, 2}))
NON_STR = {
    3: "int",
    -1.5: "float",
    True: "bool",
    None: "none",
    ID: "uuid",
    WHEN: "datetime",
    datetime.date(2026, 1, 2): "date",
    Colour.RED: "enum",
    "s": "str",
}
show("non str keys", lambda: orjson.dumps(NON_STR, option=orjson.OPT_NON_STR_KEYS))
show(
    "non str keys sorted",
    lambda: orjson.dumps(NON_STR, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SORT_KEYS),
)
show("non str keys refused", lambda: orjson.dumps({3: "int"}))

ARRAYS = {
    "i64": np.arange(-6, 6, dtype=np.int64).reshape(3, 4),
    "f64": np.array([0.1, -0.0, 1e300, np.pi, np.nan]),
    "f32": np.array([0.1, 1.5, -2.25], dtype=np.float32),
    "f16": np.array([0.5, 65504.0], dtype=np.float16),
    "u8": np.array([0, 255], dtype=np.uint8),
    "bool": np.array([[True, False], [False, True]]),
    "dt64": np.array(["2026-11-15T12:30:45", "1970-01-01"], dtype="datetime64[s]"),
    "scalars": [np.float64(1.5), np.int8(-8), np.uint64(2**64 - 1), np.bool_(True)],
    "empty": np.zeros((0, 3)),
}
show(
    "numpy", lambda: orjson.dumps(ARRAYS, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SORT_KEYS)
)
big = np.arange(20_000, dtype=np.float64) / 7
show("numpy big", lambda: orjson.dumps(big, option=orjson.OPT_SERIALIZE_NUMPY))
show(
    "numpy fortran",
    lambda: orjson.dumps(np.asfortranarray(ARRAYS["i64"]), option=orjson.OPT_SERIALIZE_NUMPY),
)
show("numpy without the option", lambda: orjson.dumps(ARRAYS["u8"]))

ROWS = [
    {
        "n": i,
        "id": uuid.UUID(int=i * 7919),
        "when": UTC + datetime.timedelta(minutes=i),
        "name": TEXT[i % len(TEXT)],
        "score": i / 9,
        "tags": [Colour.RED, Level.LOW][: i % 3],
    }
    for i in range(2_000)
]
show("records", lambda: orjson.dumps(ROWS))
show(
    "records indented",
    lambda: orjson.dumps(ROWS, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
)

show(
    "fragment",
    lambda: orjson.dumps({"pre": orjson.Fragment(b'{"made":[1,2]}'), "s": orjson.Fragment("[]")}),
)

encoded = orjson.dumps(RECORD, option=orjson.OPT_SORT_KEYS)
show("loads", lambda: orjson.loads(encoded))
show("loads then dumps", lambda: orjson.dumps(orjson.loads(encoded), option=orjson.OPT_SORT_KEYS))
show("loads str", lambda: orjson.loads('{"é":[1,2.5,"\\u00e9\\ud83d\\ude00"]}'))
show("loads bytearray", lambda: orjson.loads(bytearray(b"[1e2,-0.0,1.7976931348623157e308]")))
show("loads memoryview", lambda: orjson.loads(memoryview(b'{"a":null}')))
show(
    "loads big ints",
    lambda: orjson.loads(b"[9223372036854775807,18446744073709551615,-9223372036854775808]"),
)
show("loads too big an int", lambda: orjson.loads(b"18446744073709551616"))
show("loads records", lambda: len(orjson.loads(orjson.dumps(ROWS))))
show("loads numpy", lambda: orjson.loads(orjson.dumps(big, option=orjson.OPT_SERIALIZE_NUMPY))[-3:])


def nested_list(depth):
    value = []
    for _ in range(depth - 1):
        value = [value]
    return value


for depth in (254, 255, 256):
    show(f"dumps depth {depth}", lambda d=depth: orjson.dumps(nested_list(d)))
for depth in (1024, 1025):
    show(f"loads depth {depth}", lambda d=depth: len(str(orjson.loads(b"[" * d + b"]" * d))))


def errors():
    try:
        orjson.dumps(object())
    except orjson.JSONEncodeError as e:
        print("encode error", type(e).__name__, orjson.JSONEncodeError is TypeError, e)
    for bad in (b"", b"[1,]", b'"\xff"', b"NaN", b'{"a" 1}', b"[1]\n[2]", '"\ud800"'):
        try:
            orjson.loads(bad)
        except orjson.JSONDecodeError as e:
            parents = (isinstance(e, json.JSONDecodeError), isinstance(e, ValueError))
            print("decode error", repr(bad), parents, (e.msg, e.pos, e.lineno, e.colno))


errors()
