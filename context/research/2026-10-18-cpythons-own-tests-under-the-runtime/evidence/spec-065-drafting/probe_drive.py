"""Guest side, spec 065's drafting probes: the research's driver (A1, A2, A4) plus two switches.

python -u /cpy/judge/drive.py [--exe-empty] [--werror] -- <regrtest args>

--exe-empty  sets sys.executable and sys._base_executable to "" before regrtest imports anything:
             what the product would show if it reported its executable as unknown (decision 2).
--werror     the warnings half of CPython CI's `-W error -bb`: sys.warnoptions and the filter set
             to "error" before regrtest imports anything (decision 8). `-bb` cannot be set here.
"""

import os
import sys
import warnings

args = sys.argv[1:]
sep = args.index("--")
flags, rest = set(args[:sep]), args[sep + 1 :]

if "--exe-empty" in flags:
    sys.executable = ""
    sys._base_executable = ""
if "--werror" in flags:
    sys.warnoptions[:] = ["error"]
    warnings.simplefilter("error")

os.makedirs("/tmp", exist_ok=True)  # A2
sys.dont_write_bytecode = True
sys.path.append("/cpy/lib")
sys.argv = ["regrtest", *rest]

ctypes = sys.modules.get("ctypes")  # A1
if ctypes is not None and "_reset_cache" not in vars(ctypes):
    ctypes._reset_cache = lambda: None

from test.libregrtest import results  # noqa: E402
from test.libregrtest.main import main  # noqa: E402


def _add_junit(self, xml_data):  # A4
    self.testsuite_xml.extend(xml_data)


def _write_junit(self, filename):
    if self.testsuite_xml:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("<testsuites>" + "".join(self.testsuite_xml) + "</testsuites>")


results.TestResults.add_junit = _add_junit
results.TestResults.write_junit = _write_junit

print("PROBE sys.executable=%r bytes_warning=%d warnoptions=%r" % (
    sys.executable, sys.flags.bytes_warning, sys.warnoptions), flush=True)
main()
