- **Project:** regex (https://github.com/mrabarnett/mrab-regex)
- **Against:** 2026.9.29 (the pinned tarball)
- **Status:** drafted
- **Title:** Give five callbacks the signatures CPython calls them with
- **Files:** src/_regex.c
- **Why we carry it:** on `wasm32-wasip1` a call through a function pointer of the wrong type traps, so `Pattern.groupindex`, pickling a compiled pattern, `Match.capturesdict()`, `Match.allcaptures()` and `Match.allspans()` each kill the guest ("bad signature").

**This is a facts sheet, not a pull request** (question 80 in
`context/questions-for-the-owner.md`). The regex repository has no contributor guide and no
rule on AI-written changes that the agent could find (READ, 2026-10-18: the 2026.9.29 sdist and
the repository's top folder on its default branch `hg`). Under question 80's recommendation,
if you send it, you write the issue or pull request yourself from these facts. Nothing has
been posted, and no agent will post anything to the project.

When spec 047 is built, this file moves unchanged to
`context/upstream/patches/regex-2026.9.29/0001-callback-signatures.md`, and `fix.patch` is
copied byte for byte to `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch`. The
evidence stays in `context/upstream/9-regex-callback-signatures/evidence/`, so every link below
is a path from the repository's top.

**Checked for you** (2026-10-18): `src/_regex.c` on the default branch is byte-identical to the
2026.9.29 release's, so the five definitions are unchanged there; GitHub's issue search in the
repository finds nothing for "wasi" or for "signature wasm".

## The facts

**What fails.** CPython calls a getter as `PyObject *(*)(PyObject *, void *)` and a
`METH_NOARGS` method as `PyObject *(*)(PyObject *, PyObject *)`. Five functions in
`src/_regex.c` are defined with one parameter and cast into those tables:

| table entry | function | defined as |
|---|---|---|
| `Pattern.groupindex` (getset) | `pattern_groupindex` | `(PyObject* self_)` |
| `Pattern._pickled_data` (getset) | `pattern_pickled_data` | `(PyObject* self_)` |
| `Match.capturesdict` (`METH_NOARGS`) | `match_capturesdict` | `(MatchObject* self)` |
| `Match.allcaptures` (`METH_NOARGS`) | `match_allcaptures` | `(MatchObject* self)` |
| `Match.allspans` (`METH_NOARGS`) | `match_allspans` | `(MatchObject* self)` |

C calling conventions on the usual platforms ignore the extra argument, so these work there.
WebAssembly checks the exact type of every indirect call, and a mismatch traps. Under WASI
there is no trampoline to hide it (Emscripten's CPython calls these through one, which is why
Pyodide never saw it). Each of the five, called alone in a guest built without the change,
traps (`context/upstream/9-regex-callback-signatures/evidence/unpatched-guest.txt`):

```
## p.groupindex
EXIT None ... 'trapped': 'bad signature'
```

`pickle.dumps(pattern)` traps too, because regex's `copyreg` hook reads `_pickled_data`.

**The change** (`fix.patch`, 5 lines changed): each of the five gains the second parameter
CPython passes, unused and marked `Py_UNUSED`. No caller changes; no behaviour changes on any
platform.

**How the five were found.** A scan of `src/_regex.c` matched every `(getter)` and
`(PyCFunction)` table entry to its definition's parameter count (`METH_NOARGS` and `METH_O`
want two, `METH_VARARGS | METH_KEYWORDS` three, getters two). These five were the only
mismatches; the type slots are assigned without casts, so the compiler checks them.

**How it was tested** (EXECUTED 2026-10-18 in a scratch folder: regex 2026.9.29 built for
`wasm32-wasip1` with wasi-sdk 33's clang and linked into this project's CPython 3.15 reactor,
under wasmtime 49): with the change, a program exercising fuzzy matching, Unicode properties,
graphemes, full case folding, named lists, captures, overlapped and reverse searches, partial
matches, set operations, recursion, possessive quantifiers, branch reset, variable lookbehind,
POSIX matching, `subf`, splitting and named-group replacement prints exactly what native regex
prints (`evidence/regex_probe.py`, `evidence/native.txt`, `evidence/guest.txt`), and the five
calls give native's results (`evidence/regex_five.py`).

**One more thing we found, which is ours, not regex's.** In this project regex's module is
linked into the interpreter as a builtin. CPython gives a builtin no package context, so a
single-phase module created as `"_regex"` keeps that name, and pickle then looks for a
top-level `_regex`. We fix that in our own build, for every builtin at once: the generated
inittab sets the package context around each init function, as CPython does when it loads a
shared library. It needs nothing from upstream.
