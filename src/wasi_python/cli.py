"""`wasi-python run`: run one program through `wasi_python.run` and print its result as one line
of JSON (spec 019). It adds no power `run` does not have: each option is one of `run`'s
arguments, and without an option the argument is `run`'s default.

    wasi-python run -- -c "print(1)"
    {"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\\n", "trapped": null,
     "truncated": []}    (one line)

Exit codes say whether there is a result, not how the program ended: 0, the call returned (the
JSON says how the program ended); 1, `run` raised (one JSON object with `error` and `kind`);
2, a usage error (argparse's message on standard error); 130, interrupted by Ctrl-C.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
from typing import Any

USAGE = "wasi-python run [OPTIONS] [--] ARG..."
VALUED = {
    "--env",
    "--stdin",
    "--deadline-s",
    "--memory-bytes",
    "--output-bytes",
    "--fuel",
    "--grant",
    "--grant-writable",
    "--root",
}


class _Once(argparse.Action):
    """An option that may be given once: a second `--root` is a usage error, never last-wins."""

    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore[override]
        if hasattr(namespace, self.dest):
            parser.error(f"argument {option_string}: given twice")
        setattr(namespace, self.dest, values)


def _limit(kind: type) -> Any:
    """`none` for no limit, else a value of `kind`; anything else is a usage error."""

    def parse(text: str) -> Any:
        if text == "none":
            return None
        try:
            return kind(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not {kind.__name__} or none: {text!r}") from None

    return parse


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wasi-python run",
        usage=USAGE,
        allow_abbrev=False,
        description="Run one program in a fresh sandboxed CPython and print its result as JSON.",
    )
    p.add_argument("--env", action="append", default=[], metavar="KEY[=VALUE]")
    p.add_argument("--stdin", metavar="PATH", help="a file, or - for this command's own input")
    # An option not given is absent from the result, so `run` keeps its own default.
    unset = argparse.SUPPRESS
    p.add_argument("--deadline-s", type=_limit(float), metavar="SECONDS", default=unset)
    p.add_argument("--memory-bytes", type=_limit(int), metavar="BYTES", default=unset)
    p.add_argument("--output-bytes", type=_limit(int), metavar="BYTES", default=unset)
    p.add_argument("--fuel", type=_limit(int), metavar="N", default=unset)
    p.add_argument("--no-snapshot", action="store_true")
    # Both grant options write to one list, each value tagged with its mode, so the order typed
    # is the order `run` numbers them in (spec 022).
    p.add_argument(
        "--grant", dest="grants", action="append", default=[], type=lambda v: ("ro", v),
        metavar="GUEST=HOST", help="a host folder the guest sees at GUEST, read-only",
    )  # fmt: skip
    p.add_argument(
        "--grant-writable", dest="grants", action="append", type=lambda v: ("rw", v),
        metavar="GUEST=HOST", help="a host folder the guest sees at GUEST, writable",
    )  # fmt: skip
    roots = p.add_mutually_exclusive_group()
    roots.add_argument(
        "--root", action=_Once, default=unset, metavar="HOST",
        help="the guest's /, writable; made if missing",
    )  # fmt: skip
    roots.add_argument(
        "--private-root", action="store_true",
        help="a fresh private /, writable, removed after the call",
    )  # fmt: skip
    roots.add_argument("--no-root", action="store_true", help="no / at all, the default")
    return p


def _grants(items: list[tuple[str, str]], parser: argparse.ArgumentParser) -> list[Any]:
    """GUEST=HOST, split at the first `=`: a host path may hold `=` or `C:\\`, a guest path
    starts with `/`. Whatever parses goes to `run()`, which judges it."""
    from .runner import Grant

    grants = []
    for mode, value in items:
        guest, sep, host = value.partition("=")
        if not sep:
            option = "--grant-writable" if mode == "rw" else "--grant"
            parser.error(f"{option} needs GUEST=HOST")
        grants.append(Grant(host, guest, writable=mode == "rw"))
    return grants


def _split(args: list[str]) -> tuple[list[str], list[str]]:
    """One left-to-right scan: `--` gives the rest to the guest; an argument starting with `-`
    (not `-` itself) is this command's option, and one of `VALUED` consumes the next argument
    unless written `--name=value`; anything else starts the guest's argv, `--` after it included."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            return args[:i], args[i + 1 :]
        if arg.startswith("-") and arg != "-":
            i += 2 if arg in VALUED else 1
            continue
        return args[:i], args[i:]
    return args, []


def _env(items: list[str], parser: argparse.ArgumentParser) -> dict[str, str] | None:
    """KEY=VALUE, or KEY alone for this command's own value, which keeps a secret off the command
    line; a repeated key keeps its last value."""
    if not items:
        return None
    env: dict[str, str] = {}
    for i, item in enumerate(items, 1):
        key, sep, value = item.partition("=")
        if not sep:
            if key not in os.environ:
                # Never echo what was typed: a value given by mistake as a name is a secret.
                parser.error(f"--env number {i}: no such name in this command's environment")
            value = os.environ[key]
        env[key] = value
    return env


def _stream(name: str, data: bytes) -> dict[str, str]:
    try:
        return {name: data.decode("utf-8")}
    except UnicodeDecodeError:
        return {f"{name}_base64": base64.b64encode(data).decode("ascii")}


def _write(obj: dict[str, Any]) -> None:
    line = json.dumps(obj, sort_keys=True, ensure_ascii=True) + "\n"
    sys.stdout.buffer.write(line.encode("ascii"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    """The command; Ctrl-C at any point is exit 130 with nothing on standard output."""
    try:
        return _main(list(sys.argv[1:] if argv is None else argv))
    except KeyboardInterrupt:
        return 130


def _main(args: list[str]) -> int:
    if args[:1] in (["-h"], ["--help"]):
        print(f"usage: {USAGE}\n\nRun `wasi-python run --help` for the options.")
        return 0
    if args[:1] != ["run"]:
        print(f"usage: {USAGE}\nwasi-python: the one command is `run`", file=sys.stderr)
        return 2
    options, guest = _split(args[1:])
    parser = _parser()
    try:
        ns = parser.parse_args(options)
        env = _env(ns.env, parser)
        grants = _grants(ns.grants, parser)
    except SystemExit as e:  # usage errors exit 2; --help exits 0
        return int(e.code or 0)
    given: dict[str, Any] = {"cancel": threading.Event()}  # set by no one: lets Ctrl-C stop it
    for name in ("deadline_s", "memory_bytes", "output_bytes", "fuel"):
        if hasattr(ns, name):
            given[name] = getattr(ns, name)
    if env is not None:
        given["env"] = env
    if ns.no_snapshot:
        given["snapshot"] = False
    if grants:
        given["grants"] = grants
    if hasattr(ns, "root"):
        given["root"] = ns.root
    elif ns.private_root:
        given["root"] = True
    elif ns.no_root:
        given["root"] = False
    try:
        if ns.stdin is not None:
            if ns.stdin == "-":
                if sys.stdin is None or sys.stdin.closed:
                    raise OSError("--stdin -: this command's standard input is closed")
                given["stdin"] = sys.stdin.buffer.read()
            else:
                with open(ns.stdin, "rb") as f:
                    given["stdin"] = f.read()
        from . import runner

        done = runner.run(guest, **given)
    except Exception as e:
        _write({"error": str(e), "kind": type(e).__name__})
        return 1
    _write(
        {
            "exit_code": done.exit_code,
            "trapped": done.trapped,
            "fuel_used": done.fuel_used,
            "truncated": list(done.truncated),
            **_stream("stdout", done.stdout),
            **_stream("stderr", done.stderr),
        }
    )
    return 0
