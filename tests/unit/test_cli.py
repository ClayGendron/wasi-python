"""`wasi-python run` (spec 019): parsing, the output line and the exit codes, with a fake `run`
that records its arguments. Real calls are in tests/checks/test_v1_4_embedding.py."""

from __future__ import annotations

import base64
import json
import threading

import pytest

from wasi_python import cli, runner
from wasi_python.runner import Completed


@pytest.fixture
def fake(monkeypatch):
    calls: list[tuple[list[str], dict]] = []
    result = {"done": Completed(0, b"1\n", b"", None, None, ())}

    def run(argv, **kw):
        calls.append((list(argv), kw))
        done = result["done"]
        if isinstance(done, BaseException):
            raise done
        return done

    monkeypatch.setattr(runner, "run", run)
    return calls, result


def _main(capsysbinary, *args: str) -> tuple[int, bytes, bytes]:
    code = cli.main(list(args))
    out, err = capsysbinary.readouterr()
    return code, out, err


def test_each_option_reaches_run_as_its_argument(fake, capsysbinary, tmp_path) -> None:
    calls, _ = fake
    (tmp_path / "in").write_bytes(b"input")
    code, out, _ = _main(
        capsysbinary,
        "run",
        "--env", "A=1",
        "--stdin", str(tmp_path / "in"),
        "--deadline-s", "2.5",
        "--memory-bytes", "none",
        "--output-bytes", "100",
        "--fuel", "7",
        "--no-snapshot",
        "--", "-c", "print(1)",
    )  # fmt: skip
    assert code == 0 and out.endswith(b"\n")
    (argv, kw), cancel = calls[0], calls[0][1].pop("cancel")
    assert argv == ["-c", "print(1)"]
    assert kw == {
        "env": {"A": "1"},
        "stdin": b"input",
        "deadline_s": 2.5,
        "memory_bytes": None,
        "output_bytes": 100,
        "fuel": 7,
        "snapshot": False,
    }
    assert isinstance(cancel, threading.Event) and not cancel.is_set()


def test_an_option_not_given_is_not_passed(fake, capsysbinary) -> None:
    calls, _ = fake
    assert _main(capsysbinary, "run", "--", "-c", "1")[0] == 0
    assert set(calls[0][1]) == {"cancel"}


@pytest.mark.parametrize(
    ("args", "guest"),
    [
        (["--", "-c", "x"], ["-c", "x"]),
        (["--", "--fuel", "5"], ["--fuel", "5"]),
        (["x.py", "--fuel", "5"], ["x.py", "--fuel", "5"]),
        (["x.py", "--", "y"], ["x.py", "--", "y"]),
        (["--fuel=5", "x.py"], ["x.py"]),
        (["--fuel", "5", "x.py"], ["x.py"]),
        (["-"], ["-"]),  # a lone `-`: the program on standard input
        (["--grant=/d=x", "x.py"], ["x.py"]),
        (["--no-root", "x.py"], ["x.py"]),
        ([], []),
    ],
)
def test_the_guests_argv_is_split_off_in_one_scan(fake, capsysbinary, args, guest) -> None:
    calls, _ = fake
    assert _main(capsysbinary, "run", *args)[0] == 0
    assert calls[0][0] == guest


def test_env(fake, capsysbinary, monkeypatch) -> None:
    calls, _ = fake
    monkeypatch.setenv("SECRET_FOR_THE_GUEST", "s3")
    assert _main(capsysbinary, "run", "--env", "SECRET_FOR_THE_GUEST", "--env", "K=a=b",
                 "--env", "K=c", "--", "-c", "1")[0] == 0  # fmt: skip
    assert calls[0][1]["env"] == {"SECRET_FOR_THE_GUEST": "s3", "K": "c"}
    monkeypatch.delenv("SECRET_FOR_THE_GUEST")
    code, out, err = _main(capsysbinary, "run", "--env", "SECRET_FOR_THE_GUEST", "--", "-c", "1")
    assert (code, out) == (2, b"") and b"no such name" in err


@pytest.mark.parametrize(
    "args",
    [
        ["run", "--dead", "1", "--", "-c", "1"],  # an abbreviation is never taken
        ["run", "--dead=1", "--", "-c", "1"],
        ["run", "--no", "--", "-c", "1"],
        ["run", "--fuel", "ten", "--", "-c", "1"],
        ["run", "-c", "x"],  # an unknown option before any program
        ["walk"],
        [],
    ],
)
def test_a_usage_error_exits_2_with_nothing_on_stdout(fake, capsysbinary, args) -> None:
    code, out, err = _main(capsysbinary, *args)
    assert (code, out) == (2, b"") and err
    assert fake[0] == []


def test_stdin_dash_is_this_commands_input(fake, capsysbinary, monkeypatch) -> None:
    import io

    calls, _ = fake
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"from the caller")))
    assert _main(capsysbinary, "run", "--stdin", "-", "--", "-")[0] == 0
    assert calls[0][1]["stdin"] == b"from the caller"
    monkeypatch.setattr("sys.stdin", None)  # closed, as under a detached process
    code, out, _ = _main(capsysbinary, "run", "--stdin", "-", "--", "-")
    assert code == 1 and "standard input is closed" in json.loads(out)["error"]


def test_a_missing_env_name_is_never_echoed(fake, capsysbinary) -> None:
    code, out, err = _main(capsysbinary, "run", "--env", "s3cr3t-value-typed-by-mistake", "--", "-")
    assert (code, out) == (2, b"") and b"s3cr3t" not in err and b"--env number 1" in err


def test_ctrl_c_while_parsing_is_130(fake, capsysbinary, monkeypatch) -> None:
    def interrupted(args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_split", interrupted)
    assert _main(capsysbinary, "run", "--", "-c", "1")[:2] == (130, b"")


def test_help_exits_0(fake, capsysbinary) -> None:
    assert _main(capsysbinary, "run", "--help")[0] == 0
    assert _main(capsysbinary, "--help")[0] == 0


def test_what_run_refuses_exits_1_with_one_error_line(fake, capsysbinary, tmp_path) -> None:
    _, result = fake
    result["done"] = ValueError("deadline_s must be finite and above 0")
    code, out, _ = _main(capsysbinary, "run", "--deadline-s", "-1", "--", "-c", "1")
    assert code == 1 and out.count(b"\n") == 1 and out.endswith(b"\n")
    assert json.loads(out) == {
        "error": "deadline_s must be finite and above 0",
        "kind": "ValueError",
    }
    assert list(json.loads(out)) == ["error", "kind"]  # sorted keys
    code, out, _ = _main(capsysbinary, "run", "--stdin", str(tmp_path / "missing"), "--", "-")
    assert code == 1 and json.loads(out)["kind"] == "FileNotFoundError"


def test_ctrl_c_exits_130_with_nothing_on_stdout(fake, capsysbinary) -> None:
    _, result = fake
    result["done"] = KeyboardInterrupt()
    assert _main(capsysbinary, "run", "--", "-c", "1")[:2] == (130, b"")


def test_the_result_line(fake, capsysbinary) -> None:
    _, result = fake
    result["done"] = Completed(3, "é\n".encode(), b"\xff\xfe", "deadline", None, ("stderr",))
    code, out, _ = _main(capsysbinary, "run", "--", "-c", "1")
    assert code == 0 and out.isascii() and out.count(b"\n") == 1
    line = json.loads(out)
    assert list(line) == sorted(line)
    assert line == {
        "exit_code": 3,
        "trapped": "deadline",
        "fuel_used": None,
        "truncated": ["stderr"],
        "stdout": "é\n",
        "stderr_base64": base64.b64encode(b"\xff\xfe").decode(),
    }
    assert base64.b64decode(line["stderr_base64"]) == b"\xff\xfe"


# Grants on the command line (spec 022).


def test_grants_reach_run_in_the_order_typed_with_their_modes(fake, capsysbinary) -> None:
    from wasi_python import Grant

    calls, _ = fake
    args = ["--grant", "/a=ha", "--grant-writable", "/b=hb", "--grant", "/c=h=c"]
    assert _main(capsysbinary, "run", *args, "--", "-c", "1")[0] == 0
    assert calls[0][1]["grants"] == [
        Grant("ha", "/a"),
        Grant("hb", "/b", writable=True),
        Grant("h=c", "/c"),  # the split is at the first `=`: the host keeps the rest
    ]


@pytest.mark.parametrize(
    ("args", "root"), [(["--root", "r"], "r"), (["--no-root"], False), (["--root", ""], "")]
)
def test_root_reaches_run(fake, capsysbinary, args, root) -> None:
    calls, _ = fake
    assert _main(capsysbinary, "run", *args, "--", "-c", "1")[0] == 0
    assert calls[0][1]["root"] == root  # `--root ""` too: run() refuses it, exit 1


def test_a_windows_host_path_passes_whole(fake, capsysbinary) -> None:
    calls, _ = fake
    assert _main(capsysbinary, "run", r"--grant=/d=C:\data", "--", "-c", "1")[0] == 0
    assert calls[0][1]["grants"][0].host == r"C:\data"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--grant", "/d"], b"--grant needs GUEST=HOST"),
        (["--grant-writable", "/d"], b"--grant-writable needs GUEST=HOST"),
        (["--root", "a", "--root", "b"], b"--root: given twice"),
        (["--root", "a", "--no-root"], b"not allowed with argument"),
        (["--grant-writabl", "/d=x"], b"unrecognized arguments"),
    ],
)
def test_a_grant_usage_error_exits_2_and_says_why(fake, capsysbinary, args, message) -> None:
    code, out, err = _main(capsysbinary, "run", *args, "--", "-c", "1")
    assert (code, out) == (2, b"") and message in err, err
    assert fake[0] == []


@pytest.mark.parametrize(
    ("value", "grant"), [("/d=", ("", "/d")), ("=x", ("x", "")), ("==", ("=", ""))]
)
def test_an_empty_side_reaches_run_which_refuses_it(fake, capsysbinary, value, grant) -> None:
    """Exit 2 is only for what cannot be parsed; an empty side parses, so `run()` judges it."""
    calls, _ = fake
    assert _main(capsysbinary, "run", "--grant", value, "--", "-c", "1")[0] == 0
    g = calls[0][1]["grants"][0]
    assert (g.host, g.guest) == grant
