"""Guest side of spec 050: run numpy's or pandas' own tests, writing the outcome stream.

Runs inside the guest only, as `python -u /upstream/judge/drive.py <package> <name>`, with the
read-only grant `/upstream` (the kit, this file, the configuration, the staged tests) and a
writable root. `/upstream/judge/<name>.json` holds everything the run needs; the guest parses no
argument list of its own. The stream, `/tmp/upstream/outcomes.txt`, is flushed line by line:

    C <collector>                     a collector starts
    S <node id>                       a test starts
    R <outcome> <node id> -- <reason> every outcome, passes included
    X <node id> -- <reason>           a collection error
    P derandomize=… database=… max_examples=…   collection ended (the active hypothesis settings)
    M <module> <file>                 at the end, each module loaded from /upstream/tests/
    E <pytest exit code>              last
"""

import importlib
import json
import os
import sys

GRANT = "/upstream"
TESTS = GRANT + "/tests/"
STREAM = "/tmp/upstream/outcomes.txt"

package, name = sys.argv[1], sys.argv[2]
with open(f"{GRANT}/judge/{name}.json") as f:
    spec = json.load(f)

sys.dont_write_bytecode = True
sys.path.insert(0, GRANT + "/kit")
# The test folders join the product's packages (spec 050, Decision 4): appended, so every module
# the product has still comes from the product.
for pkg in spec["path_packages"]:
    importlib.import_module(pkg).__path__.append(TESTS + pkg.replace(".", "/"))

os.makedirs(os.path.dirname(STREAM), exist_ok=True)
out = open(STREAM, "w", encoding="utf-8")  # noqa: SIM115 (open for the whole session)


def emit(line: str) -> None:
    out.write(line.replace("\n", " ").replace("\r", " ") + "\n")
    out.flush()


def first_line(text: str) -> str:
    for line in str(text).strip().splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


import hypothesis  # noqa: E402

# numpy's own "np.test() profile" values (numpy/conftest.py), loaded before pytest starts, so a
# profile a conftest registers later (pandas' `pandas_ci`) inherits them (spec 050, Decision 6).
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


class Stream:
    def pytest_configure(self, config):
        for marker in spec.get("markers", []):
            config.addinivalue_line("markers", marker)

    def pytest_collectstart(self, collector):
        emit(f"C {collector.nodeid}")

    def pytest_collectreport(self, report):
        if report.failed:
            emit(f"X {report.nodeid} -- {first_line(_last_line(report.longrepr))}")

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
        f"--rootdir={GRANT}/tests",
        "-c",
        f"{GRANT}/judge/{package}.ini",
        "-q",
        "--tb=no",
        "--no-header",
        "-rN",
        *spec["args"],
    ],
    plugins=[Stream()],
)
for mod_name, mod in sorted(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if isinstance(f, str) and f.startswith(TESTS):
        emit(f"M {mod_name} {f}")
emit(f"E {int(code)}")
out.close()
