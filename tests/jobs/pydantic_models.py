"""Golden job: pydantic, with its core compiled from Rust.

Usage: pydantic_models.py <data dir> <out dir> (both unused). Named `pydantic_models`, not
`pydantic`, so the script's own folder on sys.path cannot hide the package. It validates nested
models with `Annotated` constraints from annotated-types, field and model validators, a
discriminated union, datetimes, UUIDs and `Decimal`; a `TypeAdapter` and a dataclass; dumps to
Python and to JSON, floats among them (0.1, 1e16, 1e-7, the smallest subnormal, negative zero and
a large float with an integer value); the JSON schema; and a `ValidationError` as JSON. Each
result is printed as its length and SHA-256, and in full when it is short, so a change of one byte
shows on its own line. Both sides run pydantic 2.14.3 over pydantic-core 2.50.4's own code, so
the bytes must be equal.
"""

import dataclasses
import datetime
import decimal
import hashlib
import json
import sys
import uuid
from typing import Annotated, Literal

import annotated_types
import pydantic
import pydantic_core
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


def show(label, f):
    try:
        out = f()
    except ValidationError as e:
        out = e.json().encode()
        label += " (ValidationError)"
    except Exception as e:
        print(label, "-> RAISES", type(e).__name__, str(e)[:200])
        return
    if isinstance(out, str):
        out = out.encode()
    if isinstance(out, bytes):
        digest = hashlib.sha256(out).hexdigest()
        text = out.decode() if len(out) <= 320 else "..."
        print(label, "->", len(out), digest, text.replace("\n", "\\n"))
    else:
        print(label, "->", repr(out)[:320])


Port = Annotated[int, annotated_types.Ge(1), annotated_types.Le(65535)]
Name = Annotated[str, annotated_types.MinLen(1), annotated_types.MaxLen(16)]


class Address(BaseModel):
    host: Name
    port: Port = 443


class Cat(BaseModel):
    kind: Literal["cat"]
    lives: Annotated[int, annotated_types.Interval(ge=0, le=9)] = 9


class Dog(BaseModel):
    kind: Literal["dog"]
    good: bool = True


class Service(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: uuid.UUID
    name: Name
    started: datetime.datetime
    timeout: datetime.timedelta
    price: Annotated[decimal.Decimal, Field(max_digits=8, decimal_places=2)]
    tags: list[str] = []
    upstream: list[Address]
    pet: Annotated[Cat | Dog, Field(discriminator="kind")]

    @pydantic.field_validator("tags")
    @classmethod
    def lower_tags(cls, v):
        return sorted(t.lower() for t in v)

    @pydantic.model_validator(mode="after")
    def ports_differ(self):
        ports = [a.port for a in self.upstream]
        if len(ports) != len(set(ports)):
            raise ValueError("upstream ports repeat")
        return self


class Floats(BaseModel):
    values: list[float]


@dataclasses.dataclass
class Point:
    x: int
    y: float
    label: str = "p"


GOOD = {
    "id": "12345678-1234-5678-1234-567812345678",
    "name": "  api  ",
    "started": "2026-11-15T12:34:56.789+01:00",
    "timeout": "PT1M30S",
    "price": "1234.50",
    "tags": ["B", "a", "C"],
    "upstream": [{"host": "one"}, {"host": "two", "port": "8080"}],
    "pet": {"kind": "cat", "lives": 3},
}
BAD = {
    "id": "not-a-uuid",
    "name": "",
    "started": "yesterday",
    "timeout": "PT1M",
    "price": "123456789.123",
    "upstream": [{"host": "one", "port": 0}, {"host": "x" * 17}],
    "pet": {"kind": "fish"},
    "extra": 1,
}


def main() -> None:
    print("versions", pydantic.VERSION, pydantic_core.__version__)
    s = Service.model_validate(GOOD)
    show("python dump", lambda: json.dumps(s.model_dump(mode="json"), sort_keys=True))
    show("json dump", lambda: s.model_dump_json())
    show("json dump indented", lambda: s.model_dump_json(indent=2, exclude={"timeout"}))
    show("from json", lambda: Service.model_validate_json(s.model_dump_json()) == s)
    dog = dict(GOOD, pet={"kind": "dog"})
    show("the union's other arm", lambda: Service.model_validate(dog).pet.model_dump_json())
    show("errors", lambda: Service.model_validate(BAD))
    repeat = dict(GOOD, upstream=[{"host": "a"}, {"host": "b"}])
    show("a model validator", lambda: Service.model_validate(repeat))
    strict = TypeAdapter(int, config=ConfigDict(strict=True))
    show("strict int", lambda: strict.validate_python("1"))
    floats = [0.1, 1e16, 1e-7, 5e-324, -0.0, 2.0**60, 1.5, 123456789.0]
    show("floats", lambda: Floats(values=floats).model_dump_json())
    show("floats back", lambda: Floats.model_validate_json(Floats(values=floats).model_dump_json()))
    ta = TypeAdapter(list[Point])
    points = ta.validate_python([{"x": 1, "y": "2.5"}, Point(3, 4.0, "q")])
    show("dataclasses", lambda: ta.dump_json(points))
    dates = TypeAdapter(dict[str, datetime.date])
    show("dates", lambda: dates.dump_json(dates.validate_json('{"b": "2026-02-28", "a": 0}')))
    show("schema", lambda: json.dumps(Service.model_json_schema(), sort_keys=True))
    show("adapter schema", lambda: json.dumps(ta.json_schema(), sort_keys=True))
    show("core json", lambda: pydantic_core.to_json({"a": [1, 2.5, None, "é"]}))
    show("core from json", lambda: pydantic_core.from_json(b'{"a": [1, 2.5e3, null]}'))


if __name__ == "__main__":
    main()
    sys.stdout.flush()
