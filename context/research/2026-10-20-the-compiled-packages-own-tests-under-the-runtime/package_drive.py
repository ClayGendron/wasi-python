"""Stand-in guest driver for spec 066's survey (Decision 1): a scratch copy, never committed as
judge code. Derived from tests/upstream/drive.py: the same stream, plus `R skipped <collector>`
for a skipped collection report and `D <node id>` for an item lxml's selection deselects.

Runs in the guest as `python -u /upstream-<pkg>/judge/package_drive.py <pkg> <group>`.
"""

import doctest
import importlib
import json
import os
import sys
import unittest

GRANT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = GRANT + "/tree/"
STREAM = "/tmp/upstream/outcomes.txt"

package, name = sys.argv[1], sys.argv[2]
with open(f"{GRANT}/judge/{name}.json") as f:
    spec = json.load(f)

sys.dont_write_bytecode = True
sys.path.append(GRANT + "/kit")  # after the product's zip: the product's modules win
for pkg, folder in spec.get("package_paths", {}).items():
    importlib.import_module(pkg).__path__.append(TREE + folder)
for folder in spec.get("extra_sys_path", []):
    sys.path.append((TREE + folder).rstrip("/") if folder != "." else TREE.rstrip("/"))

os.makedirs(os.path.dirname(STREAM), exist_ok=True)
out = open(STREAM, "w", encoding="utf-8")  # noqa: SIM115


def emit(line):
    out.write(line.replace("\n", " ").replace("\r", " ") + "\n")
    out.flush()


def first_line(text):
    for line in str(text).strip().splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


cwd = spec.get("cwd")
if cwd:
    os.makedirs(cwd, exist_ok=True)
    os.chdir(cwd)

import hypothesis  # noqa: E402

hypothesis.settings.register_profile(
    "judge",
    database=None,
    derandomize=True,
    deadline=None,
    print_blob=True,
    suppress_health_check=list(hypothesis.HealthCheck),
)
hypothesis.settings.load_profile("judge")

import pytest  # noqa: E402


class DocstringItem(pytest.Item):
    """One doctest run by the stdlib's runner, as lxml's own test.py runs it (DocFileSuite,
    DocTestSuite), with the flags lxml gives it."""

    def __init__(self, *, test, flags=0, **kw):
        super().__init__(**kw)
        self.dtest = test
        self.flags = flags

    def runtest(self):
        runner = doctest.DocTestRunner(optionflags=self.flags, verbose=False)
        msgs = []
        runner.run(self.dtest, out=msgs.append)
        if runner.failures:
            raise AssertionError("doctest failed: " + first_line("".join(msgs)[-400:]))

    def reportinfo(self):
        return self.path, None, self.name


class Stream:
    def pytest_configure(self, config):
        for marker in spec.get("markers", []):
            config.addinivalue_line("markers", marker)

    def pytest_collectstart(self, collector):
        emit(f"C {collector.nodeid}")

    def pytest_collectreport(self, report):
        if report.failed:
            emit(f"X {report.nodeid} -- {first_line(_last_line(report.longrepr))}")
        elif report.skipped:
            reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
            emit(f"R skipped {report.nodeid} -- {first_line(reason)}")

    def pytest_collection_modifyitems(self, session, config, items):
        keep = spec.get("keep_classes")
        if keep is not None:
            kept, dropped = [], []
            for it in items:
                cls = getattr(it, "cls", None)
                f = it.nodeid.split("::", 1)[0]
                if cls is not None and isinstance(cls, type) and issubclass(cls, unittest.TestCase):
                    allowed = keep.get(f)
                    if allowed is not None and allowed != "*" and cls.__name__ not in allowed:
                        dropped.append(it)
                        continue
                kept.append(it)
            for it in dropped:
                emit(f"D {it.nodeid}")
            if dropped:
                config.hook.pytest_deselected(items=dropped)
            items[:] = kept
        for rel, flags in spec.get("doctest_files", []):
            path = TREE + rel
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            name = os.path.basename(rel)
            t = doctest.DocTestParser().get_doctest(text, {"__file__": path}, name, path, 0)
            items.append(DocstringItem.from_parent(session, name=f"docfile:{rel}", test=t,
                                                   flags=flags))
        for mod_name in spec.get("docstring_modules", []):
            try:
                mod = importlib.import_module(mod_name)
            except Exception as e:  # noqa: BLE001
                emit(f"X docstrings:{mod_name} -- {type(e).__name__}: {first_line(e)}")
                continue
            for t in doctest.DocTestFinder().find(mod, mod_name):
                if t.examples:
                    items.append(
                        DocstringItem.from_parent(session, name=f"docstrings:{t.name}", test=t)  # flags 0, as DocTestSuite
                    )

    def pytest_collection_finish(self, session):
        s = hypothesis.settings.default
        emit(f"P derandomize={s.derandomize} database={s.database!r} max_examples={s.max_examples}")

    def pytest_runtest_logstart(self, nodeid, location):
        emit(f"S {nodeid}")

    def pytest_runtest_logreport(self, report):
        outcome = report.outcome
        if report.when != "call" and outcome == "passed":
            return
        if hasattr(report, "wasxfail"):
            outcome = "xfailed" if report.skipped else "xpassed"
        elif report.when != "call" and outcome == "failed":
            outcome = "error"
        reason = ""
        if outcome in ("failed", "error"):
            crash = getattr(report.longrepr, "reprcrash", None)
            text = crash.message if crash is not None and crash.message else report.longrepr
            reason = first_line(text)
        elif outcome == "skipped" and isinstance(report.longrepr, tuple):
            reason = first_line(report.longrepr[2])
        elif outcome in ("xfailed", "xpassed"):
            reason = first_line(report.wasxfail)
        emit(f"R {outcome} {report.nodeid} -- {reason}")


def _abs(arg):
    if arg.startswith("--ignore="):
        return "--ignore=" + TREE + arg[len("--ignore="):]
    if arg.startswith("-"):
        return arg
    return TREE + arg


def _last_line(longrepr):
    lines = [line for line in str(longrepr).strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


code = pytest.main(
    [
        "-p", "no:faulthandler",
        "--capture=sys",
        "-o", "log_file=/tmp/pytest.log",
        "--basetemp=/tmp/pytest",
        "-p", "no:cacheprovider",
        "--import-mode=importlib",
        "--strict-markers",
        "--strict-config",
        f"--rootdir={TREE.rstrip('/')}",
        "-c", f"{GRANT}/judge/{package}.ini",
        "-q", "--tb=no", "--no-header", "-rN",
        "--continue-on-collection-errors",  # the survey: measure past a collection error
        *[_abs(a) for a in spec["args"]],
    ],
    plugins=[Stream()],
)
top = set(spec.get("top_names", []))
for mod_name, mod in sorted(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if not isinstance(f, str):
        continue
    if f.startswith(TREE):
        emit(f"M {mod_name} {f}")
    elif mod_name.split(".")[0] in top and ".zip/" not in f and f != "built-in":
        emit(f"M {mod_name} {f}")
emit(f"E {int(code)}")
out.close()
