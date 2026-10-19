"""Spec 085: forged shard records against today's gather (main a6dfc17). Each forgery should be
red; the verdict printed is what gather says today. Run from the worktree:
    uv run python <this> <scratch dir>
It uses tests/unit/test_gather.py's synthetic good set (the Case), edits it, and calls
gather.gather exactly as the unit tests do."""

import shutil
import sys
from pathlib import Path

sys.path[:0] = ["tests", "tests/unit"]
import test_gather as T  # noqa: E402

out = Path(sys.argv[1])
UPS = (("linux", "up-l"), ("windows", "up-w"))
OWN = [(s, "own-a") for s in ("macos", "linux", "windows")]
REST = [("macos", "own-rest"), ("linux", "own-rest")]
OTHER_SUMS = "f" * 64


def blocked(keys, node, need, drop_metrics=False):
    def edit(c):
        for k in keys:
            c.records[k]["checks"][node].update(status="blocked", need=need)
            if drop_metrics:
                c.records[k]["checks"][node]["metrics"] = {}
    return edit


def suite(key, value):
    def edit(c):
        c.records[key]["suite"] = value
    return edit


def drop_fuel(c):  # the accepted darwin-arm64 value stays; a linux record drops its fuel
    c.records[("linux", "up-l")]["checks"][T.SUITE]["metrics"] = {"passes": 5}


def drop_probe_fuel(c):  # a product check's fuel, accepted on darwin-arm64, dropped on win32
    c.accepted["checks"][T.PROBE]["metrics"] = {"darwin-arm64": {"fuel": 7, "wasmtime": "49.0.0"}}
    for k in OWN:
        c.records[k]["checks"][T.PROBE]["metrics"] = {"fuel": 7}
    c.records[("windows", "own-a")]["checks"][T.PROBE]["metrics"] = {}


def string_fuel(c):  # not compared on Linux, so never parsed as a number
    c.accepted["checks"][T.PROBE]["metrics"] = {"darwin-arm64": {"fuel": 7, "wasmtime": "49.0.0"}}
    for k in OWN:
        c.records[k]["checks"][T.PROBE]["metrics"] = {"fuel": 7}
    c.records[("linux", "own-a")]["checks"][T.PROBE]["metrics"] = {"fuel": "7"}


def fuel_unchecked(wasmtime):  # the review's F1: one meta field turns off the darwin ratchet
    def edit(c):
        c.accepted["checks"][T.PROBE]["metrics"] = {"darwin-arm64": {"fuel": 7, "wasmtime": "49.0.0"}}
        for k in OWN:
            c.records[k]["checks"][T.PROBE]["metrics"] = {"fuel": 7}
        c.records[("macos", "own-a")]["checks"][T.PROBE]["metrics"] = {"fuel": 70}
        c.records[("macos", "own-a")]["meta"]["wasmtime"] = wasmtime
    return edit


def newest(**fields):
    def edit(c):
        c.newest.update(fields)
    return edit


def meta(key, **fields):
    def edit(c):
        c.records[key]["meta"].update(fields)
    return edit


FORGERIES = [
    ("F6", "an accepted-pass class check blocked by 'oracle' in every record that runs it",
     blocked(UPS, T.CLASS, "oracle")),
    ("F6", "an upstream suite blocked by 'three systems' in every record, its metrics gone",
     blocked(UPS, T.SUITE, "three systems", drop_metrics=True)),
    ("F6", "a rule blocked by 'descriptor limit' on macOS and Linux, where the need is met",
     blocked(REST, T.RULE_NODE, "descriptor limit")),
    ("F7", "a record's suite is {} though its share has 2 unit tests",
     suite(("macos", "own-rest"), {})),
    ("F7", "a record's suite is all zeros though its share has 2 unit tests",
     suite(("macos", "own-rest"), {"passed": 0, "skipped": 0, "total": 0})),
    ("F7", "a record's suite counts one unit test fewer than its share (one dropped)",
     suite(("macos", "own-rest"), {"passed": 1, "skipped": 0, "total": 1})),
    ("F7", "a record's suite counts are not whole numbers",
     suite(("macos", "own-rest"), {"passed": "2", "skipped": 0, "total": "2"})),
    ("F7", "a record's suite counts a bool as a whole number",
     suite(("macos", "own-rest"), {"passed": True, "skipped": 1, "total": 2})),
    ("F7", "a Linux record drops an upstream suite's fuel (accepted on darwin-arm64)", drop_fuel),
    ("F7", "a Windows record drops a product check's fuel (accepted on darwin-arm64)",
     drop_probe_fuel),
    ("F7", "a Linux record's product-check fuel is a string (accepted on darwin-arm64)",
     string_fuel),
    ("F7", "a macOS record's fuel x10, its meta.wasmtime 49.0.0 (the control)", fuel_unchecked("49.0.0")),
    ("F7", "a macOS record's fuel x10, its meta.wasmtime 48.0.0", fuel_unchecked("48.0.0")),
    ("F7", "a macOS record's fuel x10, its meta.wasmtime null", fuel_unchecked(None)),
    ("F5", "the newest acceptance is on python.wasm but another set's SHA256SUMS",
     newest(set_sums=OTHER_SUMS)),
    ("F5", "the newest acceptance records no set at all (a line from before 085)",
     newest(set_sums=None)),
    ("F5", "a record judged another set (meta.set_sums) with the same python.wasm",
     meta(("linux", "own-a"), set_sums=OTHER_SUMS)),
]

green = 0
for finding, name, edit in [("--", "the good set", lambda c: None), *FORGERIES]:
    d = out / name.replace(" ", "_").replace("'", "")[:60]
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    c = T.Case(d)
    edit(c)
    try:
        v = c.run()
    except Exception as e:  # gather.py exits non-zero: it fails closed, with no reason line
        print(f"{finding} RAISE {name}: {type(e).__name__}: {e}")
        continue
    verdict = "RED  " if v.red else "GREEN"
    green += finding != "--" and not v.red
    print(f"{finding} {verdict} {name}" + (f": {v.red[:2]}" if v.red else ""))
print(f"{green} of {len(FORGERIES)} forgeries leave gather green")
