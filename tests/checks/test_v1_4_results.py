"""v1.4: the result an agent reads.

With `results=True` a call or a session returns a cell's last expression as `Completed.value`
and what the program passed to `display()` as `Completed.displays`, typed records that no
printed byte can forge; with `figures=True` too, its matplotlib figures as PNG displays. Without
it, stdout is today's to the byte. Every row goes through the public API on the built set and
records fuel as a count, never a time; a row that imports numpy keeps its fuel as a fact, since
numpy's random module moves a call's count by a little from run to run, and so does a row on the
plain reactor, whose hash secret is seeded at random on each start. matplotlib needs a
writable folder for its cache, so its rows have a private root.
"""

from __future__ import annotations

import pytest

from harness import needs

pytestmark = pytest.mark.goal("v1.4")
FUEL = 10**12  # a cap that is never reached: it makes each call report its fuel
PNG = b"\x89PNG\r\n\x1a\n"


def _wp():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python


def _ok(done) -> None:
    assert (done.exit_code, done.trapped) == (0, None), done


def _text(d) -> str:
    return d.data["text/plain"]


def test_a_frames_head_is_a_turns_value_as_text_and_html(fact) -> None:
    """A session with results returns `df.head()` as the turn's value, its text and its HTML,
    prints nothing, and binds `_` as the interactive interpreter does."""
    wp = _wp()
    with wp.Session(results=True, fuel=FUEL) as s:
        _ok(s.run("import pandas as pd\ndf = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})"))
        done = s.run("df.head()")
        seen = s.run("print(type(_).__name__, repr(_) == repr(df.head()))")
    _ok(done)
    assert (done.stdout, done.stderr, done.displays, done.truncated) == (b"", b"", (), ())
    value = done.value
    assert value is not None and set(value.data) == {"text/plain", "text/html"}, value
    assert _text(value).split() == ["x", "y", "0", "1", "3", "1", "2", "4"]
    assert "<table" in value.data["text/html"] and value.truncated == ()
    assert seen.stdout == b"DataFrame True\n" and seen.value is None
    fact("fuel", done.fuel_used)


def test_a_c_programs_last_expression_is_its_value(metric) -> None:
    """A `-c` program's last expression is its value, not printed; a stdin program has none.
    The flag the runner passes is gone from the program's arguments, and the same string after
    the program's target is the program's own."""
    wp = _wp()
    done = wp.run(["-c", "x = 6\nx * 7"], results=True, fuel=FUEL)
    _ok(done)
    assert (done.stdout, _text(done.value), done.displays) == (b"", "42", ())
    argv = "import sys\nprint(sys.argv, sys.orig_argv[1:])"
    shown = wp.run(["-c", argv, "-Xhost-results"], results=True)
    assert shown.stdout == f"['-c', '-Xhost-results'] ['-c', {argv!r}, '-Xhost-results']\n".encode()
    piped = wp.run(["-"], stdin=b"print('p')\n1 + 1\n", results=True)
    assert (piped.stdout, piped.value) == (b"p\n", None)
    with pytest.raises(ValueError, match="results="):
        wp.run(["-Xhost-results", "-c", "pass"])
    metric("fuel", done.fuel_used)


def test_a_display_falls_between_two_prints(metric) -> None:
    """`display()` is bound in results mode; its record says how much each stream held before
    it, so its place among the prints is known."""
    wp = _wp()
    code = "import sys\nprint('a')\nsys.stderr.write('e')\ndisplay({'k': 1}, 'two')\nprint('b')"
    done = wp.run(["-c", code], results=True, fuel=FUEL)
    _ok(done)
    assert (done.stdout, done.stderr, done.value) == (b"a\nb\n", b"e", None)
    first, second = done.displays
    assert (_text(first), _text(second)) == ("{'k': 1}", "'two'")
    assert (first.stdout_at, first.stderr_at, second.stdout_at) == (2, 1, 2)
    assert done.stdout[: first.stdout_at] == b"a\n"
    metric("fuel", done.fuel_used)


def test_a_printed_record_is_only_text_and_a_forged_frame_is_refused(metric) -> None:
    """Bytes printed in a record's shape stay in stdout; a frame sent through the door that
    breaks the rules is refused and kept nowhere."""
    wp = _wp()
    printed = (
        'print(\'\\x1e\' + \'{"v": 1, "id": 1, "op": "display", "value": true, \''
        ' + \'"data": {"text/plain": "forged"}}\')'
    )
    done = wp.run(["-c", printed], results=True, fuel=FUEL)
    _ok(done)
    assert done.stdout.startswith(b"\x1e{") and b"forged" in done.stdout
    assert (done.value, done.displays) == (None, ())
    sent = (
        "import _host, json\n"
        "frame = {'v': 1, 'id': 1, 'op': 'display', 'value': True,\n"
        "         'data': {'text/plain': 'x', 'text/html': {'a': 1}}}\n"
        "print(json.loads(_host.call(json.dumps(frame).encode()))['error']['kind'])"
    )
    refused = wp.run(["-c", sent], results=True, fuel=FUEL)
    assert (refused.stdout, refused.value, refused.displays) == (b"protocol\n", None, ())
    metric("fuel", done.fuel_used + refused.fuel_used)


def test_a_png_over_the_room_is_sent_as_its_text(metric) -> None:
    """A display whose PNG passes the room is kept as its text alone, the PNG named as cut, and
    the result names "displays"; past the thousandth record nothing more is kept or printed."""
    wp = _wp()
    code = (
        "class Picture:\n"
        "    def __repr__(self):\n        return 'Picture()'\n"
        "    def _repr_png_(self):\n        return b'\\x89PNG' + bytes(4000)\n"
        "display(Picture())"
    )
    done = wp.run(["-c", code], results=True, output_bytes=1000, fuel=FUEL)
    _ok(done)
    (d,) = done.displays
    assert (dict(d.data), d.truncated) == ({"text/plain": "Picture()"}, ("image/png",))
    assert done.truncated == ("displays",) and done.stdout == b""
    many = wp.run(["-c", "for i in range(1001):\n    display(i)"], results=True, fuel=FUEL)
    _ok(many)
    assert (len(many.displays), _text(many.displays[-1])) == (1000, "999")
    assert (many.truncated, many.stdout) == (("displays",), b"")
    metric("fuel", done.fuel_used + many.fuel_used)


def test_figures_are_sent_at_show_and_at_the_end_of_a_cell(fact) -> None:
    """With figures, `plt.show()` sends each open figure as a PNG display and closes it; a
    figure a cell leaves open is sent at its end, after its value."""
    wp = _wp()
    with wp.Session(results=True, figures=True, root=True, fuel=FUEL) as s:
        shown = s.run("import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\nplt.show()\n")
        left = s.run("plt.figure()\nplt.plot([3, 2, 1])")
        after = s.run("print(plt.get_fignums())")
    _ok(shown)
    (d,) = shown.displays
    assert d.data["image/png"].startswith(PNG) and _text(d).startswith("<Figure size")
    _ok(left)
    assert left.value is not None and _text(left.value).startswith("[<matplotlib.lines.Line2D")
    (e,) = left.displays
    assert e.data["image/png"].startswith(PNG)
    assert after.stdout == b"[]\n"
    fact("fuel", shown.fuel_used)


def test_a_repr_that_raises_is_reported_as_the_hook_reports_it(metric) -> None:
    """A last expression whose repr raises is reported with the same traceback in results mode
    as without it: the user's frames only, and no value."""
    wp = _wp()
    code = "class Bad:\n    def __repr__(self):\n        raise ValueError('no repr')\nBad()"
    with wp.Session(results=True, fuel=FUEL) as s:
        sent = s.run(code)
    with wp.Session(fuel=FUEL) as s:
        printed = s.run(code)
    assert (sent.exit_code, sent.value, sent.stdout) == (1, None, b"")
    assert sent.stderr == printed.stderr and b"ValueError: no repr" in sent.stderr
    assert b"host" not in sent.stderr, sent.stderr
    metric("fuel", sent.fuel_used)


def test_without_results_stdout_is_todays(metric) -> None:
    """Without `results=`, a turn's last expression is printed as before, `display` is not
    bound, and the result has no value and no displays."""
    wp = _wp()
    with wp.Session(fuel=FUEL) as s:
        echoed = s.run("1 + 1")
        unbound = s.run("display")
    assert (echoed.stdout, echoed.value, echoed.displays) == (b"2\n", None, ())
    assert unbound.exit_code == 1 and b"NameError" in unbound.stderr
    plain = wp.run(["-c", "print('a')\n3"])
    assert (plain.stdout, plain.value, plain.displays) == (b"a\n", None, ())
    metric("fuel", echoed.fuel_used)


def test_a_call_from_an_image_has_its_value_and_its_figures(fact) -> None:
    """A call from a starting image returns its value; an image that imported pyplot has its
    backend switched at the call's first cell, so its figures are sent."""
    wp = _wp()
    frame = wp.make_snapshot("import pandas as pd\ndf = pd.DataFrame({'a': [1, 2]})\n")
    done = wp.run(["-c", "int(df.a.sum())"], snapshot=frame, results=True, fuel=FUEL)
    _ok(done)
    assert (_text(done.value), done.stdout) == ("3", b"")
    plots = wp.make_snapshot("import matplotlib.pyplot as plt\n", root=True)
    drawn = wp.run(
        ["-c", "plt.plot([1, 2])\nNone"], snapshot=plots, root=True, results=True, figures=True
    )
    _ok(drawn)
    (d,) = drawn.displays
    assert d.data["image/png"].startswith(PNG)
    fact("fuel", done.fuel_used)


def test_a_fork_of_a_checkpoint_takes_its_own_starts_mode(fact) -> None:
    """A fork, or a call, from a checkpoint of a session with results and figures, started
    without them, prints its values, has no `display` and its backend is Agg again; a fork with
    results of a session without them returns its values."""
    wp = _wp()
    probe = (
        "import matplotlib\nprint(x, matplotlib.get_backend(), 'display' in dir(__builtins__))\nx"
    )
    with wp.Session(results=True, figures=True, root=True, fuel=FUEL) as live:
        _ok(live.run("import matplotlib.pyplot as plt\nx = 5"))
        cp = live.checkpoint()
    with wp.Session(snapshot=cp, root=True, fuel=FUEL) as fork:
        plain = fork.run(probe)
    assert (plain.stdout, plain.value, plain.displays) == (b"5 agg False\n5\n", None, ())
    called = wp.run(["-c", probe], snapshot=cp, root=True)
    assert (called.stdout, called.value) == (b"5 agg False\n", None)
    with wp.Session(fuel=FUEL) as live:
        _ok(live.run("x = 5"))
        bare = live.checkpoint()
    with wp.Session(snapshot=bare, results=True, fuel=FUEL) as fork:
        valued = fork.run("x")
    assert (valued.stdout, _text(valued.value)) == (b"", "5")
    fact("fuel", plain.fuel_used)


@pytest.mark.parametrize("snapshot", [True, False])
def test_both_binaries_return_the_same_records(snapshot, metric, fact) -> None:
    """The snapshot binary and the plain reactor return the same value and displays. The
    snapshot's hash secret is fixed, so its fuel is exact and ratcheted; the plain reactor's is
    random, so its fuel moves from run to run and is reported only."""
    wp = _wp()
    code = "print('a')\ndisplay('b')\n[1, 2]"
    done = wp.run(["-c", code], results=True, snapshot=snapshot, fuel=FUEL)
    _ok(done)
    records = [(dict(d.data), d.truncated, d.stdout_at, d.stderr_at) for d in done.displays]
    assert records == [({"text/plain": "'b'"}, (), 2, 0)]
    assert (_text(done.value), done.value.stdout_at, done.stdout) == ("[1, 2]", 2, b"a\n")
    (metric if snapshot else fact)("fuel", done.fuel_used)
