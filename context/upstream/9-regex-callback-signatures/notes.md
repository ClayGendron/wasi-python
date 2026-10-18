# How the regex callback signatures were found and checked

- **Found** while drafting spec 047 (2026-10-18): a scratch guest with regex built in ran a
  feature program; it stopped with the trap "bad signature" at `regex.sub` with a named-group
  template. Narrowed to `Pattern.groupindex`, which regex's Python side reads to expand
  `\g<name>`. The getter `pattern_groupindex` takes one parameter; CPython calls getters with
  two.
- **Scanned** `src/_regex.c` for every getter and `PyCFunction` table entry against its
  definition: five mismatches (the table in `pr.md`). Pyodide builds the same file unpatched
  (`context/prior_art/pyodide-recipes/packages/regex/meta.yaml`) because CPython's Emscripten
  build calls these through a trampoline; WASI's does not.
- **Seen failing first** (EXECUTED): each of the five calls alone in a guest built without the
  change traps (`evidence/unpatched-guest.txt`); `m.groups()` in the same guest works.
- **Checked** (EXECUTED): with `fix.patch`, `evidence/regex_probe.py` equals native byte for
  byte (`evidence/native.txt`, `evidence/guest.txt`), and `evidence/regex_five.py` prints
  native's five results. The patched file compiles with `-Wall` and no warning.
- **The module name** (not part of the patch): without a fix, `pickle.dumps` of a compiled
  pattern raised `PicklingError: Can't pickle <built-in function compile>: No module named
  '_regex'` in the guest, because the builtin kept the name `"_regex"`. The draft fixed it with
  a forced-include header; after the spec review (finding 3) spec 047 instead has
  `scripts/gen_inittab.py` set CPython's package context around every builtin's init function,
  as `_PyImport_RunModInitFunction` does for a shared library. EXECUTED on a scratch binary
  whose inittab wraps all 61 builtins (no header): every dotted builtin's `__name__` equals its
  import name, the pickled bytes equal native's (117 bytes, the same SHA-256), and numpy and
  pandas give native's results.
- **Tests upstream.** regex's CI has no WebAssembly job. The change alters no behaviour, so its
  existing tests cover it on every platform.
