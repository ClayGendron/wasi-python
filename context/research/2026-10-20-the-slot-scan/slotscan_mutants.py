"""Spec 096: the drafting scanner sees a void clear in each table kind it reads. Each mutant
rewrites one word of the parsed image (the binary on disk is not touched): a static type's
tp_clear, a static type's nb_bool, and a module definition's m_clear, each pointed at a function
of type (i32) -> () (the table index of a tp_dealloc, a destructor). Run as slotscan.py is."""

import contextlib
import io
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slotscan as s  # noqa: E402

from harness import callbacks, wasm  # noqa: E402


def poke(mod, addr, value):
    for i, (off, body) in enumerate(mod.data):
        if off <= addr < off + len(body):
            b = bytearray(body)
            struct.pack_into("<I", b, addr - off, value)
            mod.data[i] = (off, bytes(b))
            return
    raise SystemExit(f"{addr:#x} is not in the image")


def run(mod):
    out = io.StringIO()
    orig = wasm.parse_file
    wasm.parse_file = lambda _p: mod
    try:
        with contextlib.redirect_stdout(out):
            s.main("-")
    finally:
        wasm.parse_file = orig
    return [ln for ln in out.getvalue().splitlines() if ln.startswith("FINDING")]


def find_type(mod, name):
    image = callbacks._Image(mod.data)
    for addr in range(image.base, image.base + len(image.mem) - s.TYPE_SIZE, 4):
        w = image.words(addr, s.TYPE_SIZE // 4)
        if w[0] == s.STATIC_REFCNT and s.cstring(image, w[3]) == name:
            return addr, w
    raise SystemExit(f"no static type {name}")


def find_module(mod, name):
    image = callbacks._Image(mod.data)
    for addr in range(image.base, image.base + len(image.mem) - 52, 4):
        w = image.words(addr, 13)
        if w[0] == s.STATIC_REFCNT and not any(w[1:5]) and s.cstring(image, w[5]) == name:
            return addr, w
    raise SystemExit(f"no module definition {name}")


def find_spec(mod, name):
    image = callbacks._Image(mod.data)
    for addr in range(image.base, image.base + len(image.mem) - 20, 4):
        w = image.words(addr, 5)
        if s.cstring(image, w[0]) == name and w[4] and image.has(w[4], 8):
            return addr, w
    raise SystemExit(f"no spec {name}")


def report(label, found, key):
    """The mutated record's findings, and the total, so nothing else new can hide (L6)."""
    print(f"{label}: total {len(found)}; {[f for f in found if key in f]}")


path = sys.argv[1]
base = run(wasm.parse_file(path))
print("findings unmutated:", len(base))

mod = wasm.parse_file(path)
addr, w = find_type(mod, "numpy.ndarray")
poke(mod, addr + 96, w[6])  # tp_clear := its own tp_dealloc (a destructor)
report("ndarray tp_clear := tp_dealloc", run(mod), "type numpy.ndarray")

mod = wasm.parse_file(path)
addr, w = find_type(mod, "ImagingCore")
_, ndw = find_type(mod, "numpy.ndarray")
poke(mod, addr + 96, ndw[6])
report("ImagingCore tp_clear := a destructor", run(mod), "type ImagingCore")

mod = wasm.parse_file(path)
addr, w = find_type(mod, "int")
poke(mod, w[48 // 4] + 9 * 4, w[6])  # nb_bool := int's tp_dealloc
report("int nb_bool := tp_dealloc", run(mod), "type int.")

mod = wasm.parse_file(path)
addr, w = find_module(mod, "_regex")
_, ndw = find_type(mod, "numpy.ndarray")
poke(mod, addr + 44, ndw[6])  # m_clear := a destructor
report("_regex m_clear := a destructor", run(mod), "module _regex")

# F2: kiwisolver.Term's spec loses its slot array (its slots word zeroed). The minimums stay
# green (453 specs >= 380); only the named record turns the check red.
mod = wasm.parse_file(path)
addr, w = find_spec(mod, "kiwisolver.Term")
poke(mod, addr + 16, 0)
report("kiwisolver.Term spec slots := 0", run(mod), "kiwisolver.Term")

# F1: a referenced type whose tp_name points into the image but at no C string: numpy.ndarray's
# tp_name pointed at its own ob_type word, which holds 0, an empty string. The named record goes
# unread too.
mod = wasm.parse_file(path)
addr, w = find_type(mod, "numpy.ndarray")
poke(mod, addr + 12, addr + 4)  # its ob_type word: not a C string
report("ndarray tp_name := a non-string", run(mod), "does not read as a type (tp_name)")
