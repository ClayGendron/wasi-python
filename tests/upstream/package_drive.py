"""Guest side of spec 066: run one compiled package's own tests, writing the outcome stream.

Runs inside the guest only, as `python -u /upstream-<package>/judge/package_drive.py <package>
<name>`, with the package's own read-only grant (the kit, this file, the configuration, the
staged tests under `tree/`) and a writable root. The grant is read from this file's own path, so
one driver serves every family. `judge/<name>.json` holds everything the run needs. The stream,
`/tmp/upstream/outcomes.txt`, is `drive.py`'s (spec 050), with three more lines:

    R skipped <collector> -- <reason>  a file that skips itself whole (a counted outcome)
    D <node id>                        an item lxml's own runner would not run, deselected
    K <n>                              the collected count before any -k deselects (a split)

`M` lines name every module loaded from the tree, and every module of the product's top-level
names (the zip's, from the JSON) loaded from outside the zip and not builtin. `drive.py`, which
numpy's and pandas' sessions run, is not changed by any of this.
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
# The kit after the product's zip, so every module the product carries comes from the product
# (its packaging is the kit's own pin, so pytest runs on the product's copy).
sys.path.append(GRANT + "/kit")
for pkg, folder in spec["package_paths"].items():
    importlib.import_module(pkg).__path__.append(TREE + folder)
for folder in spec["extra_sys_path"]:
    sys.path.append(TREE.rstrip("/") if folder == "." else TREE + folder)

os.makedirs(os.path.dirname(STREAM), exist_ok=True)
out = open(STREAM, "w", encoding="utf-8")  # noqa: SIM115 (open for the whole session)


def emit(line: str) -> None:
    out.write(line.replace("\n", " ").replace("\r", " ") + "\n")
    out.flush()


def first_line(text) -> str:
    for line in str(text).strip().splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


os.makedirs(spec["cwd"], exist_ok=True)
os.chdir(spec["cwd"])

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


class DoctestItem(pytest.Item):
    """One doctest run by the stdlib's runner with the flags lxml's own runner gives it
    (`DocFileSuite`, `DocTestSuite`): pytest's doctest checker breaks `lxml.usedoctest`."""

    def __init__(self, *, test, flags=0, **kw):
        super().__init__(**kw)
        self.dtest = test
        self.flags = flags

    def runtest(self):
        runner = doctest.DocTestRunner(optionflags=self.flags, verbose=False)
        report: list[str] = []
        runner.run(self.dtest, out=report.append)
        if runner.failures:
            raise AssertionError("doctest failed: " + first_line("".join(report)[-400:]))

    def reportinfo(self):
        return self.path, None, self.name


def _keep(items, config) -> None:
    keep = spec["keep_classes"]
    kept, dropped = [], []
    for it in items:
        cls = getattr(it, "cls", None)
        listed = keep.get(it.nodeid.split("::", 1)[0])
        if (
            isinstance(cls, type)
            and issubclass(cls, unittest.TestCase)
            and listed is not None
            and listed != "*"
            and cls.__name__ not in listed
        ):
            dropped.append(it)
        else:
            kept.append(it)
    for it in dropped:
        emit(f"D {it.nodeid}")
    if dropped:
        config.hook.pytest_deselected(items=dropped)
    items[:] = kept


def _doctests(session, items) -> None:
    for mod_name in spec["doctest_preimport"]:  # registers lxml's option flags
        importlib.import_module(mod_name)
    for rel, flags in spec["doctest_files"]:
        path = TREE + rel
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        test = doctest.DocTestParser().get_doctest(
            text, {"__file__": path}, os.path.basename(rel), path, 0
        )
        items.append(
            DoctestItem.from_parent(session, name=f"docfile:{rel}", test=test, flags=flags)
        )
    for mod_name in spec["docstring_modules"]:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:  # noqa: BLE001 (any import failure is a collection error)
            emit(f"X docstrings:{mod_name} -- {type(e).__name__}: {first_line(e)}")
            continue
        for test in doctest.DocTestFinder().find(mod, mod_name):
            if test.examples:  # flags 0, as DocTestSuite gives them
                items.append(
                    DoctestItem.from_parent(session, name=f"docstrings:{test.name}", test=test)
                )


class Stream:
    def pytest_configure(self, config):
        for marker in spec["markers"]:
            config.addinivalue_line("markers", marker)

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, session, config, items):
        if spec["split"]:
            emit(f"K {len(items)}")  # before -k deselects: every split group saw the same file
        if spec["keep_classes"]:
            _keep(items, config)
        _doctests(session, items)

    def pytest_collectstart(self, collector):
        emit(f"C {collector.nodeid}")

    def pytest_collectreport(self, report):
        if report.failed:
            emit(f"X {report.nodeid} -- {first_line(_last_line(report.longrepr))}")
        elif report.skipped and report.nodeid:
            reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
            emit(f"R skipped {report.nodeid} -- {first_line(reason)}")

    def pytest_collection_finish(self, session):
        s = hypothesis.settings.default
        emit(f"P derandomize={s.derandomize} database={s.database!r} max_examples={s.max_examples}")

    def pytest_runtest_logstart(self, nodeid, location):
        emit(f"S {nodeid}")

    def pytest_runtest_logreport(self, report):
        outcome = report.outcome
        if report.when != "call" and outcome == "passed":
            return  # a setup or teardown that passed is not an outcome
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


def _last_line(longrepr) -> str:
    lines = [line for line in str(longrepr).strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _abs(arg: str) -> str:
    """A path under the tree, absolute; an option as it is (`--ignore=` gets the tree too)."""
    if arg.startswith("--ignore="):
        return "--ignore=" + TREE + arg[len("--ignore=") :]
    return arg if arg.startswith("-") else TREE + arg


code = pytest.main(
    [
        "-p",
        "no:faulthandler",
        "--capture=sys",
        "-o",
        "log_file=/tmp/pytest.log",
        "--basetemp=/tmp/pytest",
        "-p",
        "no:cacheprovider",
        "--import-mode=importlib",
        "--strict-markers",
        "--strict-config",
        f"--rootdir={TREE.rstrip('/')}",
        "-c",
        f"{GRANT}/judge/{package}.ini",
        "--doctest-glob=no-file-matches-this",  # lxml's doctests are DoctestItems, run once
        "-q",
        "--tb=no",
        "--no-header",
        "-rN",
        *[_abs(a) for a in spec["args"]],
    ],
    plugins=[Stream()],
)
top = set(spec["top_names"])
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
