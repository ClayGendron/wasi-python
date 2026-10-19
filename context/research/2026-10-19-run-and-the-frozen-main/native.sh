#!/bin/sh
# Spec 073: native CPython 3.15.0 (the build's pinned host Python, build/tools/python in the main
# tree) on the gap's program in each mode, and on files whose last references are garbage.
# Usage: sh native.sh <python3.15> <empty work folder>
PY=$1; cd "$2" || exit 1
printf "f = open('out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n" > prog.py
"$PY" -V
t() { rm -f out.txt; "$PY" -I -X dev -c "$2" 2>err.txt
      echo "$1: $(cat out.txt 2>/dev/null | wc -c | tr -d ' ')  $(grep -o 'unclosed file <[^ ]*' err.txt | head -1)"; }
rm -f out.txt; "$PY" -I prog.py; echo "python prog.py: $(wc -c < out.txt | tr -d ' ')"
rm -f out.txt; "$PY" -E -s -m prog; echo "python -m prog: $(wc -c < out.txt | tr -d ' ')"
t "python -c <the program>" "$(cat prog.py)"
t "runpy.run_path (a temporary module)" "import runpy; runpy.run_path('prog.py', run_name='__main__')"
t "runpy.run_path, collector disabled" "import gc; gc.disable(); import runpy; runpy.run_path('prog.py', run_name='__main__')"
t "a fresh __main__, ended with the interpreter" "
import sys, types
m = types.ModuleType('__main__'); sys.modules['__main__'] = m
exec(open('prog.py').read(), m.__dict__)
del m"
t "a module dropped mid-run, gc.collect()" "
import types, gc
m = types.ModuleType('m'); exec(open('prog.py').read(), m.__dict__); del m; gc.collect()"
t "a file in a cycle, collected at exit" "
class Box: pass
b = Box(); b.me = b; b.f = open('out.txt', 'w'); b.f.write('x' * 100); del b"
t "the wrapper in its own cycle, gc.collect()" "
f = open('out.txt', 'w'); f.write('x' * 100); f.me = f; del f
import gc; gc.collect()"
