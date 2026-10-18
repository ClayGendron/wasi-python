"""Guest side: run numpy's or pandas' own tests from a read-only grant at /t, streaming outcomes."""
import importlib
import sys

sys.path.insert(0, "/t/kit")
sys.dont_write_bytecode = True
which = sys.argv[1]
args = sys.argv[2:]
PKGS = {
    "numpy": ["numpy", "numpy._core", "numpy.lib", "numpy.linalg", "numpy.fft", "numpy.random",
              "numpy.ma", "numpy.polynomial", "numpy.matrixlib", "numpy.testing", "numpy.typing"],
    "pandas": ["pandas"],
}
for name in PKGS[which]:
    importlib.import_module(name).__path__.append("/t/tests/" + name.replace(".", "/"))

import hypothesis  # noqa: E402

hypothesis.settings.register_profile(
    "judge", database=None, derandomize=True, deadline=None, print_blob=True,
    suppress_health_check=list(hypothesis.HealthCheck),
)
hypothesis.settings.load_profile("judge")
import pytest  # noqa: E402

out = sys.stdout


def emit(*parts):
    out.write("\n@@" + " ".join(parts) + "\n")
    out.flush()


class Stream:
    def pytest_runtest_logstart(self, nodeid, location):
        emit("S", nodeid)

    def pytest_runtest_logreport(self, report):
        o = report.outcome
        if report.when == "call" or o != "passed":
            if report.when != "call" and o == "passed":
                return
            if hasattr(report, "wasxfail"):
                o = "xfailed" if report.skipped else "xpassed"
            elif report.when != "call" and o == "failed":
                o = "error"
            why = ""
            if o in ("failed", "error"):
                rc = getattr(report.longrepr, "reprcrash", None)
                text = rc.message if rc is not None and rc.message else str(report.longrepr)
                why = (text.strip().splitlines() or [""])[0][:200]
            elif o == "skipped" and isinstance(report.longrepr, tuple):
                why = str(report.longrepr[2])[:160]
            emit("R", o, report.nodeid, "--", why.replace("\n", " "))

    def pytest_collectreport(self, report):
        if report.failed:
            emit("R", "collect-error", report.nodeid, "--",
                 str(report.longrepr).strip().splitlines()[-1][:200])

    def pytest_configure(self, config):
        for m in ["slow", "valgrind_error", "leaks_references", "parallel_threads(n)",
                  "iterations(n)", "thread_unsafe", "xslow", "limit_memory"]:
            config.addinivalue_line("markers", m + ": upstream marker")


code = pytest.main(
    ["-q", "-p", "no:cacheprovider", "-p", "no:faulthandler", "--capture=sys",
     "--import-mode=importlib", "--rootdir=/t/tests", "-c", f"/t/tests/_judge/{which}.ini",
     "-o", "log_file=/tmp/pytest.log", "--basetemp=/tmp/pytest", "--tb=no", "--no-header",
     "-rN", *args],
    plugins=[Stream()],
)
emit("END", str(int(code)))
