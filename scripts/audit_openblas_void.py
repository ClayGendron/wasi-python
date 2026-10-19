"""Audit OpenBLAS's void-convention patches line by line (spec 037, Decision 5).

    audit_openblas_void.py <patch>...

Every run of removed lines must pair, one for one and in order, with the run of added lines that
follows it, and each pair must differ only by one of the convention's rewrites (the rules of
scripts/openblas_make_void.py):

  int->void     `int` before a subroutine's declarator becomes `void` (R1, R2, R4)
  return        `return 0;` becomes `return;` in a body that became void (R3)
  xerbla proto  `xerbla_(char *, integer *)` gains f2c's hidden `ftnlen` (R6), with or without R1;
                a prototype broken over lines gains it on its last line, before the `)`
  xerbla call   `xerbla_("NAME", x)` gains `(ftnlen)<len("NAME")>` (R6)
  xerbla.c      xerbla_'s own definition and its alias return void (R5)
  unchanged     a line removed and added back as it was (git's diff does this with blank lines
                inside a run of changed ones)

It prints the count of each kind and every line it cannot pair, and exits 1 if there is one. So a
review checks the script and its rules, and this shows the patches hold nothing else. Adapted from
the pre-build review's audit (context/reviews/037-scipy-spec-2026-10-17.md, finding 3).
"""

from __future__ import annotations

import re
import sys
from collections import Counter

INT_VOID = re.compile(r"\bint(\s+(?:BLASFUNC\(|NAME\(|__xerbla|[a-z][a-z0-9_]*_\s*\())")
RETURN0 = re.compile(r"\breturn\s+0\s*;")
XERBLA_PROTO = re.compile(r"(xerbla_\(\s*char\s*\*\s*,\s*integer\s*\*\s*)\)")
XERBLA_CALL = re.compile(r'xerbla_\("([A-Z0-9_]+)",\s*([^,()]+)\)')
HEADER = ("---", "+++", "diff ", "index ", "@@", "new file", "deleted file", "similarity")


def kind(old: str, new: str) -> str | None:
    """The rewrite that turns `old` into `new`, or None when none does."""
    if old == new:  # git's diff may remove and re-add a line it did not change (a blank one)
        return "unchanged"
    if INT_VOID.sub(r"void\1", old, count=1) == new:
        return "int->void"
    if RETURN0.sub("return;", old) == new:
        return "return"
    if XERBLA_PROTO.sub(r"\1, ftnlen)", old) == new:
        return "xerbla proto"
    if INT_VOID.sub(r"void\1", XERBLA_PROTO.sub(r"\1, ftnlen)", old), count=1) == new:
        return "xerbla proto"
    # A prototype broken over lines: its last line gains the length before its `)`.
    if new.replace(", ftnlen)", ")", 1) == old:
        return "xerbla proto"
    call = XERBLA_CALL.sub(lambda m: f'xerbla_("{m[1]}", {m[2]}, (ftnlen){len(m[1])})', old)
    if call == new:
        return "xerbla call"
    xerbla_c = old.replace("int __xerbla", "void __xerbla").replace(
        "return openblas_xerbla_dispatch(", "openblas_xerbla_dispatch("
    )
    if xerbla_c == new:
        return "xerbla.c"
    return None


def audit(text: str) -> tuple[Counter, list[str]]:
    """(each rewrite's count, every line no rewrite explains) for one patch's text."""
    kinds: Counter = Counter()
    bad: list[str] = []
    minus: list[str] = []
    plus: list[str] = []

    def flush() -> None:
        if len(minus) != len(plus):
            bad.extend(f"unpaired: -{m}" for m in minus)
            bad.extend(f"unpaired: +{p}" for p in plus)
        else:
            for old, new in zip(minus, plus, strict=True):
                k = kind(old, new)
                if k is None:
                    bad.append(f"-{old} / +{new}")
                else:
                    kinds[k] += 1
        minus.clear()
        plus.clear()

    for line in text.split("\n"):  # not splitlines: a CRLF source's \r stays in its line
        if line.startswith(HEADER):
            flush()
        elif line.startswith("-"):
            if plus:  # a removal after additions starts a new run
                flush()
            minus.append(line[1:])
        elif line.startswith("+"):
            plus.append(line[1:])
        else:
            flush()
    flush()
    return kinds, bad


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: audit_openblas_void.py <patch>...", file=sys.stderr)
        return 2
    total: Counter = Counter()
    unexplained: list[str] = []
    for path in argv:
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            kinds, bad = audit(f.read())
        total += kinds
        unexplained += [f"{path}: {b}" for b in bad]
    print(", ".join(f"{k} {v}" for k, v in sorted(total.items())), f"; unexplained {len(unexplained)}")
    for line in unexplained[:20]:
        print(line)
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
