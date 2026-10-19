"""Spec 083 probe: CPython's own tests that spec 065's `stepped-clock` class admits (test_os's
utime "current" pair, test_logging's timed rotation), run in the snapshot through a driver, with
CPython's Lib/test granted read-only at /cpython. Usage:
uv run python -I probe_cpython_tests.py <tests dir> <work> <Python-3.15.0 tree>"""
import atexit, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8")
tree = Path(sys.argv[3])
code = r"""
import sys, unittest, os
os.makedirs('/tmp', exist_ok=True)
os.chdir('/tmp')
sys.path.insert(0, '/cpython')
names = ['test.test_os.test_os.UtimeTests.test_utime_current',
         'test.test_os.test_os.UtimeTests.test_utime_current_old',
         'test.test_logging.TimedRotatingFileHandlerTest']
suite = unittest.defaultTestLoader.loadTestsFromNames(names)
r = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
print('ran', r.testsRun, 'failures', len(r.failures), 'errors', len(r.errors), 'skipped', len(r.skipped))
for t, tb in r.failures + r.errors:
    print('FAIL', t.id(), tb.strip().splitlines()[-1][:160])
"""
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work,
              python_version="3.15", stdlib=SET / "python-stdlib.zip", env={"TMPDIR": "/tmp", "HOME": "/tmp"},
              preopens=[("/cpython", tree / "Lib", False)], fuel=10**12)
print(r.describe())
print("\n".join(l for l in r.text.splitlines() if l.startswith(("ran", "FAIL"))))
