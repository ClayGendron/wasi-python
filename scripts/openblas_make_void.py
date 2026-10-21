"""One return convention for every subroutine in OpenBLAS C_LAPACK builds: all `void`. Moved from
the evidence folder of the research on OpenBLAS's return convention (a copy is kept there as
evidence) unchanged but for this header and R4 and R5 run as functions, so that no module-level name
is bound twice (the repository's rules). scripts/make_openblas_void_patch.sh runs it on a fresh
unpack of the pinned OpenBLAS 0.3.34 tarball and writes the three carried patches from what it
changes. usage: openblas_make_void.py <tree> [--no-xerbla-length] [--keep-xerbla-int]

Rules (each counted and printed):
  R1  f2c sources (lapack-netlib/SRC, SRC/DEPRECATED, INSTALL, TESTING/MATGEN): a declaration or definition
      whose return type is `int` and whose declarator is a Fortran subroutine name (`name_(`) becomes `void`.
      The subroutine names are every `name_` f2c marked `/* Subroutine */` anywhere in those sources, plus the
      OpenBLAS-defined LAPACK routines of R2 and xerbla_. f2c writes INTEGER functions as `integer`, never `int`,
      so `int` before such a name means a subroutine.
  R2  OpenBLAS's own LAPACK routines (interface/lapack/*.c): `int NAME(` becomes `void NAME(`.
  R3  in every definition R1 or R2 turned to void, `return 0;` becomes `return;`.
  R4  common_interface.h: the prototypes of xerbla and of the LAPACK routines that OpenBLAS or netlib define
      (`int BLASFUNC(?getrf)` ...) become `void`.
  R5  driver/others/xerbla.c: xerbla_ (and its ELF alias __xerbla) return void.
  R6  (argument count, not a return type; skipped with --no-xerbla-length) a `xerbla_(char *, integer *)`
      prototype that lacks f2c's hidden string length gets `ftnlen`, and its calls `xerbla_("NAME", &x)` get
      `(ftnlen)len("NAME")`, as every other f2c file in the tree already does.
"""
import pathlib
import re
import sys

tree = pathlib.Path(sys.argv[1])
do_r6 = "--no-xerbla-length" not in sys.argv[2:]
keep_xerbla_int = "--keep-xerbla-int" in sys.argv[2:]  # variant C: xerbla_ stays int, as OpenBLAS 0.3.34 defines it
F2C_DIRS = ["lapack-netlib/SRC", "lapack-netlib/SRC/DEPRECATED", "lapack-netlib/INSTALL", "lapack-netlib/TESTING/MATGEN"]
f2c_files = sorted(p for d in F2C_DIRS for p in (tree / d).glob("*.c"))
iface_files = sorted((tree / "interface/lapack").glob("*.c"))
count = {k: 0 for k in ["R1-decl", "R1-def", "R2", "R3", "R4", "R5", "R6-proto", "R6-call"]}
files_changed = set()

# The subroutine names: everything f2c marked as a subroutine.
SUB_MARK = re.compile(r"/\*\s*Subroutine\s*\*/\s*(?:int|void)\s+([a-z][a-z0-9_]*_)\s*\(")
GROUP_TAIL = re.compile(r"\)\s*,\s*([a-z][a-z0-9_]*_)\s*\(")
subs = set()
for p in f2c_files:
    subs.update(SUB_MARK.findall(p.read_text(errors="surrogateescape")))
IFACE_FAMILIES = ["gesv", "getf2", "getrf", "getrs", "laswp", "lauu2", "lauum", "potf2", "potrf", "potri",
                  "trti2", "trtri", "trtrs", "laed3", "potrs"]
subs.update(f"{p}{f}_" for p in "sdcz" for f in IFACE_FAMILIES)
if not keep_xerbla_int:
    subs.add("xerbla_")
else:
    subs.discard("xerbla_")

# R1: `int` as the return type of a subroutine declarator. `extern`, the f2c comment and a line break may sit
# between; a grouped declaration (`int a_(...), b_(...)`) shares the one `int`, so it changes once.
DECL = re.compile(r"(^|[;{}]\s*|\n\s*)((?:extern\s+)?(?:/\*\s*Subroutine\s*\*/\s*)?)int(\s+)([a-z][a-z0-9_]*_)(\s*\()")
DEF_LINE = re.compile(r"^(?:/\*\s*Subroutine\s*\*/\s*)?int\s+([a-z][a-z0-9_]*_)\s*\(", re.M)


def r3_bodies(text, starts, end_of):
    """Turn `return 0;` into `return;` from each start offset to the end of its function body."""
    out, last = [], 0
    for s in sorted(starts):
        e = end_of(text, s)
        body = text[s:e]
        n = len(re.findall(r"\breturn\s+0\s*;", body))
        count["R3"] += n
        out.append(text[last:s])
        out.append(re.sub(r"\breturn\s+0\s*;", "return;", body))
        last = e
    out.append(text[last:])
    return "".join(out)


def f2c_end(text, s):
    name = re.match(r"(?:/\*\s*Subroutine\s*\*/\s*)?int\s+([a-z0-9_]+)", text[s:]).group(1)
    m = re.compile(r"^\}\s*/\*\s*" + re.escape(name) + r"\s*\*/", re.M).search(text, s)
    if not m:
        raise SystemExit(f"no end marker for {name}")
    return m.end()


def brace_end(text, s):
    m = re.compile(r"^\}", re.M).search(text, s)
    return m.end()


unknown = set()
for p in f2c_files:
    t0 = p.read_text(errors="surrogateescape")
    # definitions first (their offsets are taken before any edit)
    defs = [m.start() for m in DEF_LINE.finditer(t0) if m.group(1) in subs]
    t = r3_bodies(t0, defs, f2c_end) if defs else t0
    count["R1-def"] += len(defs)

    def rep(m):
        name = m.group(4)
        if name not in subs:
            unknown.add((p.name, name))
            return m.group(0)
        count["R1-decl"] += 1
        return f"{m.group(1)}{m.group(2)}void{m.group(3)}{name}{m.group(5)}"

    t = DECL.sub(rep, t)
    count["R1-decl"] -= len(defs)  # DECL also matched the definitions; count them once, as definitions
    if do_r6:
        proto = re.compile(r"(xerbla_\(\s*char\s*\*\s*,\s*integer\s*\*\s*)\)")
        n1 = len(proto.findall(t))
        t = proto.sub(r"\1, ftnlen)", t)
        if n1:
            def call(m):
                count["R6-call"] += 1
                return f'xerbla_("{m.group(1)}", {m.group(2)}, (ftnlen){len(m.group(1))})'
            t = re.sub(r'xerbla_\("([A-Z0-9_]+)",\s*([^,()]+)\)', call, t)
            count["R6-proto"] += n1
    if t != t0:
        p.write_text(t, errors="surrogateescape")
        files_changed.add(str(p.relative_to(tree)))

# R2 + R3 for OpenBLAS's own LAPACK routines
for p in iface_files:
    t0 = p.read_text()
    starts = [m.start() for m in re.finditer(r"^int NAME\(", t0, re.M)]
    if not starts:
        continue
    t = r3_bodies(t0, starts, brace_end)
    t, n = re.subn(r"^int NAME\(", "void NAME(", t, flags=re.M)
    count["R2"] += n
    p.write_text(t)
    files_changed.add(str(p.relative_to(tree)))

# R4: the prototypes in common_interface.h
def rule_r4():
    p = tree / "common_interface.h"
    t0 = p.read_text()
    fams = "|".join(IFACE_FAMILIES)
    xer = "" if keep_xerbla_int else "xerbla|"
    t, n = re.subn(r"^(\s*)int(\s+BLASFUNC\((?:" + xer + r"[sdqcxz](?:" + fams + r"))\))", r"\1void\2", t0, flags=re.M)
    count["R4"] += n
    if t != t0:
        p.write_text(t)
        files_changed.add(str(p.relative_to(tree)))


rule_r4()

# R5: xerbla's definition
def rule_r5():
    p = tree / "driver/others/xerbla.c"
    t0 = p.read_text()
    t = t0
    for old, new in [] if keep_xerbla_int else [
        ("int __xerbla(char *message, blasint *info, blasint length) {\n  return openblas_xerbla_dispatch(",
         "void __xerbla(char *message, blasint *info, blasint length) {\n  openblas_xerbla_dispatch("),
        ("int BLASFUNC(xerbla)(char *, blasint *, blasint)\n", "void BLASFUNC(xerbla)(char *, blasint *, blasint)\n"),
        ("int BLASFUNC(xerbla)(char *message, blasint *info, blasint length) {\n  return openblas_xerbla_dispatch(",
         "void BLASFUNC(xerbla)(char *message, blasint *info, blasint length) {\n  openblas_xerbla_dispatch("),
    ]:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
        count["R5"] += 1
    if t != t0:
        p.write_text(t)
        files_changed.add(str(p.relative_to(tree)))


rule_r5()

print(f"subroutine names known: {len(subs)}")
for k, v in count.items():
    print(f"{k}: {v}")
print(f"files changed: {len(files_changed)}")
if unknown:
    print(f"int declarators left alone (not known subroutines): {len(unknown)}")
    for f, n in sorted(unknown)[:40]:
        print(f"  {f}: {n}")
