#!/bin/sh
# Spec 073, revised (the pre-build review's F1 and F3): native CPython 3.15.0's __main__ globals
# for a script (source and .pyc), a directory and -m, during the run and in an atexit handler.
# Usage: sh native_atexit.sh <python3.15> <empty work folder>
PY=$1; cd "$2" || exit 1
cat > atx.py <<'PROG'
import atexit, sys
class C: pass
def at():
    m = sys.modules['__main__']
    print('atexit: __file__', getattr(m, '__file__', None), 'C', hasattr(m, 'C'), 'loader', type(m.__loader__).__name__, 'package', repr(m.__package__))
atexit.register(at)
print('run: __file__', __file__, 'loader', type(__loader__).__name__, 'package', repr(__package__), 'spec', getattr(__spec__, 'name', None))
PROG
echo "== script"; "$PY" -I atx.py
echo "== script.pyc"; "$PY" -I -c "import py_compile; py_compile.compile('atx.py', cfile='atxc.pyc')"; "$PY" -I atxc.pyc
echo "== directory"; mkdir -p app && cp atx.py app/__main__.py && "$PY" -I app
echo "== -m"; mkdir -p code && cp atx.py code/atx.py && (cd code && "$PY" -E -s -m atx)
