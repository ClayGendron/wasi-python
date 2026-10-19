"""Guest side: run CPython's own regrtest on the arguments given, in this one process.

Runs inside the guest only, as `python -u /cpy/judge/drive.py <regrtest args>`, with the read-only
grant /cpy (lib/test from the pinned tarball, this file) and a writable root. The test package
joins sys.path at its end, so every module the product has still comes from the product.
"""

import os
import sys

# Adaptation A2: the guest's fresh root is empty; TMPDIR=/tmp must exist, or regrtest's work
# directory and tempfile fall back to the root itself.
os.makedirs("/tmp", exist_ok=True)
sys.dont_write_bytecode = True
sys.path.append("/cpy/lib")
sys.argv = ["regrtest", *sys.argv[1:]]

# Adaptation A1: the snapshot pre-imports numpy, numpy imports the product's ctypes stand-in, and
# regrtest's clear_caches() calls ctypes._reset_cache() on whatever `ctypes` is in sys.modules.
# The stand-in has no such function; give it a no-op so each test's teardown can run.
ctypes = sys.modules.get("ctypes")
if ctypes is not None and "_reset_cache" not in vars(ctypes):
    ctypes._reset_cache = lambda: None

from test.libregrtest import results  # noqa: E402
from test.libregrtest.main import main  # noqa: E402

# Adaptation A4: in one process, test_xml_etree and test_xml_etree_c swap ElementTree's C and
# Python classes, so regrtest's --junit-xml writer later fails ("append() argument 1 must be
# xml.etree.ElementTree.Element, not xml.etree.ElementTree.Element") and the whole record is lost.
# Keep each module's XML as text and write the text (regrtest's workers do this in fresh
# processes, so upstream never meets it).


def _add_junit(self, xml_data):
    self.testsuite_xml.extend(xml_data)


def _write_junit(self, filename):
    if self.testsuite_xml:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("<testsuites>" + "".join(self.testsuite_xml) + "</testsuites>")


results.TestResults.add_junit = _add_junit
results.TestResults.write_junit = _write_junit

main()
