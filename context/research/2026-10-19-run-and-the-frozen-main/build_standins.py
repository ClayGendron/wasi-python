"""Spec 073's stand-ins: each one change to the branch's recipe, rebuilt (steps 60, 80, 90), the
named checks run, the recipe restored. Output: build/073/standin-<name>.log and one summary line."""
import shutil, subprocess, sys
from pathlib import Path

B, C = Path("recipes/reactor_bootstrap.py"), Path("recipes/reactor_main.c")
GOOD_B, GOOD_C = Path("build/073/reactor_bootstrap.py.good"), Path("build/073/reactor_main.c.good")
CHECKS = [
    "tests/checks/test_v1_4_embedding.py::test_run_keeps_unclosed_files_in_every_mode",
    "tests/checks/test_v1_4_embedding.py::test_every_program_runs_in_an_unfrozen_main",
    "tests/checks/test_v1_4_embedding.py::test_run_keeps_a_file_the_stdlib_reaches",
    "tests/checks/test_v1_4_embedding.py::test_module_and_directory_errors_read_as_native",
    "tests/checks/test_v1_4_embedding.py::test_run_keeps_an_unclosed_files_bytes",
    "tests/checks/test_v1_4_embedding.py::test_main_starts_as_native",
    "tests/checks/test_v1_3_data_stack.py::test_the_snapshot_starts_cheaper_than_plain",
]
STANDINS = {
    "S1": (B, "    try:\n        main = _fresh_main()\n",
           "    try:\n        main = sys.modules[\"__main__\"]\n        _fresh_main()\n"),
    "S2": (B, "            if pkgutil.get_importer(target) is None:  # a file, as runpy.run_path tells it\n                _run_file(target, main)\n            else:",
           "            if True:\n                import runpy\n\n                runpy.run_path(target, run_name=\"__main__\")\n            else:"),
    "S3": (B, "            runpy._run_module_as_main(target)  # CPython's own -m (spec 073, Decision 3)",
           "            runpy.run_module(target, run_name=\"__main__\", alter_sys=True)"),
    "S4": (B, "    main.__dict__.update(_MAIN_NAMES)\n", ""),
    "S5": (B, "    g[\"__loader__\"] = loader(\"__main__\", target)\n",
           "    g[\"__loader__\"] = None\n    g[\"__package__\"] = \"\"\n"),
    "S6": (C, "        PyObject *done = PyObject_CallNoArgs(unfreeze_function);\n        if (done == NULL) {\n            show_and_drop();\n        }\n        Py_XDECREF(done);\n    }\n    Py_CLEAR(unfreeze_function);\n    if (Py_FinalizeEx() < 0) {",
           "    }\n    Py_CLEAR(unfreeze_function);\n    if (Py_FinalizeEx() < 0) {"),
    "S7": (B, "    finally:\n        g.pop(\"__file__\", None)\n", "    finally:\n        pass\n"),
    "S8": (C, "        PyObject *done = PyObject_CallNoArgs(unfreeze_function);\n        if (done == NULL) {\n            show_and_drop();\n        }\n        Py_XDECREF(done);\n    }\n    Py_CLEAR(unfreeze_function);\n    if (Py_FinalizeEx() < 0) {",
           "        PyObject *gcm = PyImport_ImportModule(\"gc\");\n        PyObject *f = gcm != NULL ? PyObject_GetAttrString(gcm, \"unfreeze\") : NULL;\n        PyObject *done = f != NULL ? PyObject_CallNoArgs(f) : NULL;\n        if (done == NULL) {\n            show_and_drop();\n        }\n        Py_XDECREF(done);\n        Py_XDECREF(f);\n        Py_XDECREF(gcm);\n    }\n    Py_CLEAR(unfreeze_function);\n    if (Py_FinalizeEx() < 0) {"),
}

def restore():
    shutil.copy(GOOD_B, B); shutil.copy(GOOD_C, C)

for name in sys.argv[1:] or list(STANDINS):
    path, old, new = STANDINS[name]
    restore()
    text = path.read_text()
    assert text.count(old) == 1, (name, "anchor")
    path.write_text(text.replace(old, new))
    log = Path(f"build/073/standin-{name}.log")
    with log.open("w") as fh:
        b = subprocess.run(["scripts/build.sh", "--plain", "60", "80", "90"], stdout=fh, stderr=subprocess.STDOUT)
        if b.returncode:
            print(f"{name}: BUILD FAILED"); restore(); continue
        subprocess.run(["uv", "run", "pytest", "-n", "3", "-q", *CHECKS], stdout=fh, stderr=subprocess.STDOUT)
    lines = log.read_text().splitlines()
    fails = sorted({l.split(" ")[1].split("::")[1] for l in lines if l.startswith("FAIL ")})
    summary = [l for l in lines if " passed" in l or " failed" in l][-1:]
    print(f"{name}: fails {fails or 'none'} | {summary}")
    for l in lines:
        if l.startswith("FAIL "):
            print("   ", l[:300])
restore()
