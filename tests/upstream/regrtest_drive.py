"""Guest side of CPython's own tests in the guest (spec 065). Runs inside the guest only:

    python -u /cpython/judge/regrtest_drive.py <id>

with the read-only grant /cpython (lib/test from the pinned tarball's members; this file; one
<id>.json per group and trap entry) and a writable root. It runs regrtest's own main() in this one
process and writes the outcome stream (Decision 13) to /judge/outcomes.txt, flushing every line:

    L <module>                      every module regrtest's own discovery names
    C <module>                      a module starts
    S <test id>                     a test starts
    R <outcome> <id> -- <reason>    every test outcome; a failing subtest under its own id
    X <module> -- <reason>          a module failed to load, or raised outside any test
    D <module> <state> <env>[ <w>]  a module ends: regrtest's state, altered or kept, and after
                                    altered the first line of each print_warning, |-separated
    Z <module> -- <reason>          a module denied a resource as a whole, and which: before
                                    its D line
    M <module> <file> <kind>        at the end: each module whose __file__ is under /cpython/,
                                    `product` when the product provides that name, else `test`
    E <exit code>                   last

The adaptations, each with its reason (Decisions 4 and 8):
- A2: the guest's root is empty, so /tmp (TMPDIR) is made.
- A1: regrtest's clear_caches() calls ctypes._reset_cache() on whatever `ctypes` is in
  sys.modules; the product's stand-in has none. single.clear_caches (regrtest calls it by that
  name) is wrapped to give the stand-in a no-op first. The driver never imports ctypes.
- -W error: the warnings half of CPython CI's `-W error -bb`, set before regrtest imports
  anything (the guest's bootstrap refuses -W; -bb cannot be set at run time).
"""

import json
import os
import sys
import warnings

GRANT = "/cpython"
STREAM = "/judge/outcomes.txt"

spec = json.loads(open(f"{GRANT}/judge/{sys.argv[1]}.json", encoding="utf-8").read())
if spec.get("warnings") == "error":
    sys.warnoptions[:] = ["error"]
    warnings.simplefilter("error")

os.makedirs("/tmp", exist_ok=True)  # A2
os.makedirs(os.path.dirname(STREAM), exist_ok=True)
sys.dont_write_bytecode = True
PRODUCT_PATH = list(sys.path)  # before the test package joins: the product's own import path
sys.path.append(f"{GRANT}/lib")

out = open(STREAM, "w", encoding="utf-8", buffering=1)


def emit(line: str) -> None:
    out.write(line.replace("\n", " ").replace("\r", " ") + "\n")
    out.flush()


def first_line(text: str) -> str:
    for line in str(text).splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


def reason_of(err) -> str:
    import traceback

    if err is None:
        return ""
    etype, value, _ = err
    return first_line("".join(traceback.format_exception_only(etype, value)))


from test import support  # noqa: E402
from test.libregrtest import main as regrtest_main  # noqa: E402
from test.libregrtest import single, testresult  # noqa: E402
from test.libregrtest.findtests import findtests  # noqa: E402

# ---- the warnings regrtest prints for an altered environment (Decision 5) -------------------
# Every cause goes through support.print_warning (libregrtest.utils.print_warning calls it by
# attribute). The original reads `print_warning.orig_stderr` off its own global name, which is
# now this wrapper, and single._runtest sets that attribute on it: so the wrapper carries
# orig_stderr from the start (the confirmation's C1 hazard).
_warnings_now: list[str] = []
_original_print_warning = support.print_warning


def _print_warning(msg):
    _warnings_now.append(first_line(msg).replace("|", "/"))
    return _original_print_warning(msg)


_print_warning.orig_stderr = _original_print_warning.orig_stderr
support.print_warning = _print_warning

# ---- A1 -------------------------------------------------------------------------------------
_original_clear_caches = single.clear_caches


def _clear_caches():
    stand_in = sys.modules.get("ctypes")
    if stand_in is not None and not hasattr(stand_in, "_reset_cache"):
        stand_in._reset_cache = lambda: None
    return _original_clear_caches()


single.clear_caches = _clear_caches

# ---- each test's outcome --------------------------------------------------------------------
R = testresult.RegressionTestResult


def _id(test) -> str:
    try:
        return test.id()
    except Exception:
        return str(test)


def _wrap(name, outcome_of):
    original = getattr(R, name)

    def method(self, test, *args):
        try:
            outcome_of(test, *args)
        except Exception as exc:  # the stream must never change what the test run does
            emit(f"R error {_id(test)} -- the driver could not record this outcome: {exc!r}")
        return original(self, test, *args)

    setattr(R, name, method)


_original_start = R.startTest


def _start(self, test):
    emit(f"S {_id(test)}")
    return _original_start(self, test)


R.startTest = _start
_wrap("addSuccess", lambda test: emit(f"R passed {_id(test)} -- "))
_wrap("addError", lambda test, err: emit(f"R error {_id(test)} -- {reason_of(err)}"))
_wrap("addFailure", lambda test, err: emit(f"R failed {_id(test)} -- {reason_of(err)}"))
_wrap("addSkip", lambda test, why: emit(f"R skipped {_id(test)} -- {first_line(why)}"))
_wrap("addExpectedFailure", lambda test, err: emit(f"R xfailed {_id(test)} -- {reason_of(err)}"))
_wrap("addUnexpectedSuccess", lambda test: emit(f"R xpassed {_id(test)} -- unexpected success"))


def _subtest(test, subtest, err):
    if err is None:
        return  # passing subtests are not written
    failed = issubclass(err[0], test.failureException)
    emit(f"R {'failed' if failed else 'error'} {_id(subtest)} -- {reason_of(err)}")


_wrap("addSubTest", _subtest)

# ---- each module ----------------------------------------------------------------------------
_load_error: list[str] = []
_denied: list[str] = []  # why a module was denied a resource as a whole
_original_load_run = single._load_run_test


def _load_run_test(result, runtests):
    try:
        return _original_load_run(result, runtests)
    except BaseException as exc:
        if isinstance(exc, support.ResourceDenied):
            _denied.append(first_line(str(exc)))
        if not isinstance(exc, (support.TestFailed, support.ResourceDenied, support.TestDidNotRun)):
            import unittest

            if not isinstance(exc, unittest.SkipTest):
                _load_error.append(first_line(f"{type(exc).__name__}: {exc}"))
        raise


single._load_run_test = _load_run_test
_original_run_single = regrtest_main.run_single_test


def _run_single_test(test_name, runtests):
    del _warnings_now[:], _load_error[:], _denied[:]
    emit(f"C {test_name}")
    result = _original_run_single(test_name, runtests)
    state = getattr(result.state, "name", str(result.state)) if result.state else "NONE"
    if state == "UNCAUGHT_EXC":
        emit(f"X {test_name} -- {_load_error[0] if _load_error else 'uncaught exception'}")
    if state == "RESOURCE_DENIED" and _denied:
        emit(f"Z {test_name} -- {_denied[0]}")
    env = "altered" if support.environment_altered else "kept"
    line = f"D {test_name} {state} {env}"
    if env == "altered" and _warnings_now:
        line += " " + "|".join(_warnings_now)
    emit(line)
    return result


regrtest_main.run_single_test = _run_single_test

# ---- the universe, then the run --------------------------------------------------------------
for name in findtests():
    emit(f"L {name.removeprefix('test.')}")

argv = ["regrtest", "-u", spec["resources"], *spec.get("options", [])]
for test_id in spec.get("ignore", []):
    argv += ["-i", test_id]
for test_id in spec.get("match", []):
    argv += ["-m", test_id]
argv += spec["modules"]
sys.argv = argv

code = 0
try:
    regrtest_main.main()
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)


# ---- the guard: product modules come from the product (Decision 13) -------------------------
def _product_provides(name: str) -> bool:
    import importlib.machinery

    top = name.partition(".")[0]
    if top in sys.builtin_module_names:
        return True
    try:
        return importlib.machinery.PathFinder.find_spec(top, PRODUCT_PATH) is not None
    except Exception:
        return False


for name, module in sorted(sys.modules.items()):
    f = getattr(module, "__file__", None)
    if isinstance(f, str) and f.startswith(GRANT + "/"):
        emit(f"M {name} {f} {'product' if _product_provides(name) else 'test'}")
emit(f"E {code}")
out.close()
sys.exit(0)
