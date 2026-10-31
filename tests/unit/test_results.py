"""Results, with no guest: the host's half (`_results._ResultHost`, `Display`, the keywords'
checks) driven with frames written here, and the guest's half (`recipes/guest/host/display.py`)
loaded on the host's Python with a fake `_host` whose door is a result host. One check per rule:
how a display frame is judged, how the mode reaches the guest, and the bounds. Nothing here
measures time."""

from __future__ import annotations

import base64
import importlib.util
import itertools
import json
import sys
import types
from typing import Any

import pytest

from harness import paths
from harness.calls import checked_call
from wasi_python import Display, _call, _outputs, runner
from wasi_python import _results as R
from wasi_python import _tool_host as H
from wasi_python.tools import tool

PACKAGE = paths.REPO / "recipes" / "guest" / "host"
_names = itertools.count()


def frame(data: Any = None, *, value: bool = False, truncated: Any = None, **over: Any) -> bytes:
    f = {"v": 1, "id": 7, "op": "display", "value": value, "data": data or {"text/plain": "1"}}
    if truncated is not None:
        f["truncated"] = truncated
    f.update(over)
    return json.dumps(f).encode()


def answer(raw: bytes) -> dict:
    return json.loads(raw)


def kind(raw: bytes) -> str | None:
    a = answer(raw)
    return None if a["ok"] else a["error"]["kind"]


class Streams:
    """Two streams whose counts a settle brings up to date, as the capture's does."""

    def __init__(self) -> None:
        self.out = _outputs._Stream("stdout", None)
        self.err = _outputs._Stream("stderr", None)
        self.owed: list[tuple[bytes, bytes]] = []
        self.settled = 0

    def settle(self) -> None:
        self.settled += 1
        for out, err in self.owed:
            self.out.write(out)
            self.err.write(err)
        self.owed.clear()


def result_host(room: int | None = 1 << 20, tools: Any = None) -> tuple[R._ResultHost, Streams]:
    s = Streams()
    return R._ResultHost(tools, room, (s.out, s.err), s.settle), s


@tool
def lookup(code: str) -> str:
    """Look something up."""
    return code


# -------------------------------------------------------------------------------------------------
# The record


def test_a_display_is_read_only_and_holds_what_it_was_given() -> None:
    given = {"text/plain": "1", "image/png": b"\x89PNG"}
    d = Display(given, ["image/png"], 3, 4)
    given["text/html"] = "<b>"
    assert dict(d.data) == {"text/plain": "1", "image/png": b"\x89PNG"}
    assert d.truncated == ("image/png",) and (d.stdout_at, d.stderr_at) == (3, 4)
    with pytest.raises(TypeError):
        d.data["text/html"] = "<i>"  # type: ignore[index]
    with pytest.raises(AttributeError):
        d.stdout_at = 9  # type: ignore[misc]


def test_a_completed_carries_the_value_and_the_displays_after_image_sha256() -> None:
    names = [f.name for f in _call.Completed.__dataclass_fields__.values()]
    assert names[-3:] == ["image_sha256", "value", "displays"]
    done = _call.Completed(0, b"", b"", None, None)
    assert (done.value, done.displays) == (None, ())


def test_the_result_names_displays_when_one_was_cut() -> None:
    host, s = result_host(room=0)
    host(frame())
    out, err, _ = _outputs._feed_for(None, "head", None, None, None)  # type: ignore[arg-type]
    done = _call._completed(out, err, None, 0, None, None, None, None, None, host)
    assert (done.truncated, done.value, done.displays) == (("displays",), None, ())


# -------------------------------------------------------------------------------------------------
# Decision 4: one more operation of the tool protocol, judged by the host whoever sent it.


def test_a_display_frame_is_kept_and_the_last_value_frame_is_the_value() -> None:
    host, s = result_host()
    png = base64.b64encode(b"\x89PNG").decode()
    a = answer(host(frame({"text/plain": "x", "image/png": {"$bytes": png}})))
    assert a == {"v": 1, "id": 7, "ok": True, "kept": True}
    host(frame({"text/plain": "first"}, value=True))
    host(frame({"text/plain": "last"}, value=True))
    assert [dict(d.data) for d in host.displays] == [{"text/plain": "x", "image/png": b"\x89PNG"}]
    assert host.value is not None and dict(host.value.data) == {"text/plain": "last"}
    assert host.cut is False


@pytest.mark.parametrize(
    ("data", "over"),
    [
        ({"text/plain": "1", "text/rtf": "x"}, {}),  # not one of the six
        ({"text/plain": "1", "text/html": {"a": [1]}}, {}),  # not a string
        ({"text/plain": "1", "image/png": "eA=="}, {}),  # PNG as text, not $bytes
        ({"text/plain": {"$bytes": "eA=="}}, {}),  # text as bytes
        ({"text/html": "<b>"}, {}),  # no text/plain
        (None, {"truncated": ["text/rtf"]}),  # truncated names a seventh type
        (None, {"truncated": "text/html"}),  # truncated is not a list
        (None, {"value": 1}),  # value is not a JSON boolean
        (None, {"value": None}),
        (None, {"data": ["text/plain"]}),  # data is not an object
    ],
)
def test_a_display_frame_that_breaks_the_rules_is_refused_and_kept_nowhere(data, over) -> None:
    host, _ = result_host()
    f = json.loads(frame(data))
    f.update(over)
    raw = host(json.dumps(f).encode())
    assert kind(raw) == "protocol" and answer(raw)["id"] == 7
    assert (host.value, host.displays, host.cut) == (None, [], False)


def test_a_frame_that_is_not_json_or_of_another_version_is_refused() -> None:
    host, _ = result_host()
    assert kind(host(b"{not json")) == "protocol"
    assert kind(host(frame(v=2))) == "protocol"
    assert kind(host(frame(op="batch"))) == "protocol"
    assert host.displays == []


def test_without_tools_list_and_call_are_refused_so_the_guest_has_no_tools() -> None:
    host, _ = result_host()
    for op in ({"op": "list"}, {"op": "call", "tool": "lookup", "args": {}}):
        raw = host(json.dumps({"v": 1, "id": 3, **op}).encode())
        assert kind(raw) == "protocol" and "no tools" in answer(raw)["error"]["message"]


def test_with_tools_list_and_call_go_to_the_tool_host_which_alone_keeps_the_record() -> None:
    tools = H._ToolHost([lookup])
    host, _ = result_host(tools=tools)
    listed = answer(host(json.dumps({"v": 1, "id": 1, "op": "list"}).encode()))
    assert [t["name"] for t in listed["tools"]] == ["lookup"]
    call = {"v": 1, "id": 2, "op": "call", "tool": "lookup", "args": {"code": "EMEA"}}
    assert answer(host(json.dumps(call).encode()))["value"] == "EMEA"
    assert answer(host(frame()))["kept"] is True
    assert kind(host(b"{not json")) == "protocol"  # not a display: the tool host's refusal
    assert tools.record.frames == 3  # list, call and the bad frame; never the display
    assert [o.op for o in tools.record.outcomes] == ["list", "call", None]


def test_the_guests_tools_import_still_fails_without_tools(load) -> None:
    host, _ = result_host()
    package, _display = load(host)
    with pytest.raises(ImportError, match="no tools"):
        importlib.import_module(f"{package.__name__}.tools")


def test_an_old_host_or_no_host_gets_the_text_printed(load, capsys) -> None:
    _, display = load(H._ToolHost([lookup]))  # a host that serves list and call only
    display._on = True
    display.display([1, 2])
    _, display = load(None)
    display._on = True
    display.display("x")
    assert capsys.readouterr().out == "[1, 2]\n'x'\n"


# -------------------------------------------------------------------------------------------------
# Decision 2: the record the guest builds.


class Rich:
    def __repr__(self) -> str:
        return "Rich()"

    def _repr_mimebundle_(self, include=None, exclude=None):
        return {"text/html": "<b>bundle</b>", "text/plain": "ignored", "text/x-other": "no"}

    def _repr_html_(self) -> str:
        return "<b>method</b>"

    def _repr_markdown_(self) -> str:
        raise ValueError("skipped")

    def _repr_svg_(self) -> bytes:
        return b"<svg/>"  # the wrong type: skipped

    def _repr_json_(self) -> dict:
        return {"a": [1, 2]}

    def _repr_png_(self) -> bytes:
        return b"\x89PNG"


class Halts:
    def _repr_html_(self) -> str:
        raise SystemExit(3)


class BadRepr:
    def __repr__(self) -> str:
        raise RuntimeError("no repr")


def test_the_guest_reads_the_bundle_then_the_methods_and_skips_what_fails(load) -> None:
    host, _ = result_host()
    _, display = load(host)
    display._on = True
    display.display(Rich())
    (d,) = host.displays
    assert dict(d.data) == {
        "text/plain": "Rich()",
        "text/html": "<b>bundle</b>",
        "application/json": '{"a": [1, 2]}',
        "image/png": b"\x89PNG",
    }
    with pytest.raises(SystemExit):
        display.display(Halts())  # a BaseException from a method propagates
    with pytest.raises(RuntimeError, match="no repr"):
        display.display(BadRepr())  # as sys.displayhook reports it: no record
    assert len(host.displays) == 1


def test_out_of_results_mode_display_prints_the_text(load, capsys) -> None:
    host, _ = result_host()
    _, display = load(host)
    display.display(Rich(), "s")
    assert capsys.readouterr().out == "Rich()\n's'\n" and host.displays == []


# -------------------------------------------------------------------------------------------------
# Decision 5: the mode, by the keywords and the guest's first argument.


@pytest.mark.parametrize(
    ("kw", "error", "match"),
    [
        ({"results": 1}, TypeError, "results must be True or False"),
        ({"figures": "yes"}, TypeError, "figures must be True or False"),
        ({"figures": True}, TypeError, "figures= without results="),
        ({"results": True, "host": lambda b: b}, TypeError, "results= needs the runner's door"),
    ],
)
def test_the_keywords_are_checked_before_any_work(kw, error, match) -> None:
    with pytest.raises(error, match=match):
        runner.run(["-c", "pass"], **kw)


@pytest.mark.parametrize("flag", [R.FLAG, R.FIGURES_FLAG])
def test_the_flag_before_the_target_is_refused_and_after_it_is_the_programs(flag) -> None:
    for argv in ([flag, "-c", "pass"], ["-u", flag, "x.py"], ["-X", "utf8", flag, "-m", "m"]):
        with pytest.raises(ValueError, match="results="):
            R._check_results(False, False, None, tuple(argv))
    for argv in (["-c", "pass", flag], ["x.py", flag], ["-", flag], ["-X", flag, "-c", "1"]):
        assert R._check_results(False, False, None, tuple(argv)) is None


def test_the_mode_is_one_argument_first_after_the_programs_name() -> None:
    assert R._check_results(True, False, None, ()) == "results"
    assert R._check_results(True, True, None, ()) == "figures"
    assert (R._flag(None), R._flag("results"), R._flag("figures")) == (
        [],
        ["-Xhost-results"],
        ["-Xhost-results=figures"],
    )
    assert checked_call(results="figures").results == "figures"


# -------------------------------------------------------------------------------------------------
# Decision 7: the bounds.


def test_admit_refuses_unread_past_six_times_the_room_and_counts_it() -> None:
    tools = H._ToolHost([lookup])
    host, _ = result_host(room=100)
    bound = R.ESCAPE * 100 + R.ENVELOPE
    assert host.admit(bound) is None
    a = answer(host.admit(bound + 1))
    assert (a["id"], a["error"]["kind"], a["room"]) == (None, "too_large", 100)
    assert host.cut is True and host._records == 1
    with_tools, _ = result_host(room=100, tools=tools)
    assert with_tools.admit(H._TOOL_REQUEST_BYTES) is None  # a tool frame the tool host reads
    assert kind(with_tools.admit(H._TOOL_REQUEST_BYTES + 1)) == "too_large"
    unbounded, _ = result_host(room=None)
    assert unbounded.admit(1 << 40) is None
    assert tools.record.frames == 0  # the tool host's admit is never asked


def test_a_display_frame_spends_no_tool_frame_and_a_tool_frame_spends_as_today() -> None:
    tools = H._ToolHost([lookup], max_calls=1, max_bytes=10_000)
    host, _ = result_host(tools=tools)
    for _ in range(3):
        assert host.admit(len(frame())) is None
        assert answer(host(frame()))["kept"] is True
    call = json.dumps({"v": 1, "id": 2, "op": "call", "tool": "lookup", "args": {"code": "a"}})
    assert host.admit(len(call)) is None
    assert answer(host(call.encode()))["value"] == "a"
    assert kind(host(call.encode())) == "budget_exceeded"  # max_calls=1, as without results
    assert (tools.record.frames, len(host.displays)) == (2, 3)


def test_over_the_room_the_frame_is_refused_with_the_room_and_its_text_then_fits() -> None:
    host, _ = result_host(room=10)
    raw = host(frame({"text/plain": "x" * 11}))
    assert (kind(raw), answer(raw)["room"]) == ("too_large", 10)
    data = {"text/plain": "x" * 10}
    assert answer(host(frame(data, truncated=["text/plain", "image/png"])))["kept"] is True
    assert host.displays[0].truncated == ("text/plain", "image/png") and host.cut is True
    assert answer(host(frame({"text/plain": "y"})))["kept"] is False  # no room left


def test_the_thousand_and_first_record_is_not_kept() -> None:
    host, _ = result_host(room=None)
    for _ in range(R.RECORDS):
        assert answer(host(frame()))["kept"] is True
    assert host.cut is False
    a = answer(host(frame()))
    assert (a["ok"], a["kept"], host.cut, len(host.displays)) == (True, False, True, R.RECORDS)


def test_the_guest_cuts_the_text_at_a_character_and_names_the_rest(load) -> None:
    host, _ = result_host(room=5)
    _, display = load(host)
    display._on = True

    class Wide:
        def __repr__(self) -> str:
            return "abééé"  # 8 bytes: the cut falls inside the second é

        def _repr_html_(self) -> str:
            return "<b>"

    display.display(Wide())
    (d,) = host.displays
    assert dict(d.data) == {"text/plain": "abé"} and d.truncated == ("text/plain", "text/html")


def test_once_the_host_keeps_no_more_the_cell_sends_and_prints_nothing(load, capsys) -> None:
    host, _ = result_host(room=1)
    _, display = load(host)
    display._on = True
    sent = []
    door = sys.modules["_host"].call

    def counted(raw: bytes) -> bytes:
        sent.append(raw)
        return door(raw)

    sys.modules["_host"].call = counted
    display.display("x")  # 3 bytes: cut to "'" (1 byte), kept
    display.display("y")  # no room: not kept
    display.display("z")
    display._value("w")
    assert (len(sent), capsys.readouterr().out, display._stopped) == (3, "", True)
    display._begin()  # the next cell may send again
    display.display("v")
    assert len(sent) == 4


def test_a_display_falls_after_what_printed_before_it() -> None:
    host, s = result_host()
    s.owed.append((b"before\n", b"e"))
    host(frame())
    s.owed.append((b"after\n", b""))
    host(frame(value=True))
    assert (host.displays[0].stdout_at, host.displays[0].stderr_at) == (7, 1)
    assert host.value is not None and host.value.stdout_at == 13 and s.settled == 2


# -------------------------------------------------------------------------------------------------
# The guest package, loaded on the host's Python.


@pytest.fixture
def load(monkeypatch):
    """`load(door)` imports the package and its `display` under a fresh private name, with
    `door` as `_host`; it returns (package, display). A door of None stands for no host."""
    loaded: list[str] = []

    def run(door: Any) -> tuple[types.ModuleType, types.ModuleType]:
        fake = types.ModuleType("_host")

        def call(raw: bytes) -> bytes:
            if door is None:
                raise ConnectionRefusedError("no host is bound to the door")
            return door(raw)

        fake.call = call  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "_host", fake)
        name = f"_guest_host_{next(_names)}"
        spec = importlib.util.spec_from_file_location(
            name, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)]
        )
        assert spec is not None and spec.loader is not None
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        loaded.append(name)
        spec.loader.exec_module(package)
        return package, importlib.import_module(f"{name}.display")

    yield run
    for name in loaded:
        for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
            del sys.modules[key]
