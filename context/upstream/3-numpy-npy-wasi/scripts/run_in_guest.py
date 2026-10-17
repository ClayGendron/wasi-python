"""Host side: build the guest program from the patched numpy tree and run it
through wasi_python.run. Usage: run_in_guest.py <numpy-clone> <guest_check.py>"""
import ast
import sys
import textwrap
import types

from wasi_python import run

numpy_dir, guest_path = sys.argv[1], sys.argv[2]
impl = open(f"{numpy_dir}/numpy/lib/_format_impl.py").read()
tests = open(f"{numpy_dir}/numpy/lib/tests/test_format.py").read()


def function_source(src, name):
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = src.splitlines()[node.lineno - 1:node.end_lineno]
            return "\n".join(l for l in lines)
    raise LookupError(name)


# The patched isfileobj, without its decorator (set_module only renames it).
patched = function_source(impl, "isfileobj")
assert 'sys.platform == "wasi"' in patched, "the clone is not patched"
# The test's arrays: the module's top-level code from `scalars = [` to `record_arrays`.
tree = ast.parse(tests)
start = next(n for n in tree.body if isinstance(n, ast.Assign)
             and n.targets[0].id == "scalars").lineno
end = next(n for n in tree.body if isinstance(n, ast.Assign)
           and n.targets[0].id == "record_arrays").end_lineno
arrays = "\n".join(tests.splitlines()[start - 1:end])
test = function_source(tests, "test_save_load_without_dup")
test = "\n".join(l for l in test.splitlines() if not l.startswith("@pytest"))

program = "\n".join([
    "import errno, os, sys",
    "import numpy as np",
    "from numpy.testing import assert_array_equal",
    f"PATCHED_ISFILEOBJ = {patched!r}",
    arrays,
    test,
    open(guest_path).read(),
])
done = run(["-c", program], deadline_s=300)
sys.stdout.write(done.stdout.decode())
sys.stderr.write(done.stderr.decode()[-3000:])
print(f"[host] exit_code={done.exit_code} trapped={done.trapped}")
