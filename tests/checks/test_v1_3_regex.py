"""v1.3: regex, built in (spec 047): native regex's answers in the guest, the five callbacks its
carried patch fixed among them, and a compiled pattern that pickles under its import name."""

from __future__ import annotations

import json

import pytest

from harness import jobs

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])


@pytest.mark.slow
@BINARY
def test_regex_features_job_matches_native(guest, which) -> None:
    """Fuzzy matching, Unicode properties from regex's own tables, graphemes, full case folding
    and the rest print native regex's output, then the five patched calls and a pickle round trip
    with the pickle's length and SHA-256 (spec 047, Decision 7)."""
    job = "regex_features"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.render(r.stdout, r.root / "out"))
    assert why is None, why


FIVE = """
import json, regex
p = regex.compile(r"(?P<a>\\w)(?P<b>\\d)+")
m = p.match("x12")
print(json.dumps({
    "groupindex": dict(p.groupindex),
    "pickled_data": type(p._pickled_data).__name__,
    "capturesdict": m.capturesdict(),
    "allcaptures": m.allcaptures(),
    "allspans": m.allspans(),
    "named sub": regex.sub(r"(?P<y>\\d{4})-(?P<m>\\d\\d)", r"\\g<m>/\\g<y>", "2026-10"),
}))
"""


@BINARY
def test_the_five_patched_callbacks_answer(guest, which) -> None:
    """The two getters and three no-argument methods carried patch 0001 gives the parameter
    CPython passes return native's values; without it each trapped the guest ("indirect call
    type mismatch"), and so did `regex.sub` with a named-group template, which reads
    `groupindex` (spec 047, Decision 3). Nothing writable is granted."""
    r = guest(which, ["-c", FIVE])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    want = {
        "groupindex": {"a": 1, "b": 2},
        "pickled_data": "tuple",
        "capturesdict": {"a": ["x"], "b": ["1", "2"]},
        "allcaptures": [["x12"], ["x"], ["1", "2"]],
        "allspans": [[[0, 3]], [[0, 1]], [[1, 2], [2, 3]]],
        "named sub": "10/2026",
    }
    assert json.loads(r.text) == want, r.text


PICKLE = """
import json, pickle, regex
p = regex.compile(r"(?P<word>\\w+)\\s(?P<num>\\d+)", regex.I | regex.V1)
data = pickle.dumps(p, protocol=5)
back = pickle.loads(data)
print(json.dumps({
    "names": b"regex._regex" in data,
    "pattern": back.pattern == p.pattern,
    "flags": back.flags == p.flags,
    "groupindex": dict(back.groupindex) == dict(p.groupindex),
    "match": back.match("Abc 12").groupdict(),
    "module": [regex._regex.__name__, regex._regex.compile.__module__],
}))
"""


@BINARY
def test_a_pickled_pattern_loads_back_equal(guest, which) -> None:
    """A compiled pattern pickles and loads back with its pattern, flags and groupindex. Its
    pickle names the reconstructor's module `regex._regex`: as a builtin the module keeps its
    import name only because the inittab calls its init function inside CPython's package
    context; without that, pickling raised PicklingError for a top-level `_regex` (Decision 4)."""
    r = guest(which, ["-c", PICKLE])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    want = {
        "names": True,
        "pattern": True,
        "flags": True,
        "groupindex": True,
        "match": {"word": "Abc", "num": "12"},
        "module": ["regex._regex", "regex._regex"],
    }
    assert json.loads(r.text) == want, r.text
