"""Classify every changed line of the OpenBLAS carried patches (data only, no target code run).

Each patch is split into hunks; within a hunk the removed text and the added text are each
joined and normalised: whitespace removed, the word 'int' made 'void', 'return <expr>;' made
'return;' or '<expr>;', the hidden Fortran length argument (', ftnlen' / ', (ftnlen)N') removed.
A hunk whose two sides then match is a pure signature/return change; anything else is printed.
Also lists file headers that are not plain modifications (mode, new, deleted, rename, binary).
"""
import re, sys, collections

def norm(s):
    s = re.sub(r"\bint\b", "void", s)
    s = re.sub(r"\bVOID\b|\bvoid\b", "void", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r",\(ftnlen\)\d+", "", s)
    s = re.sub(r",ftnlen\b", "", s)
    s = s.replace("(ftnlen)", "")
    s = re.sub(r"return0;", "return;", s)
    s = re.sub(r"returnret_val;", "return;", s)
    s = re.sub(r"return(?=[A-Za-z_])", "", s)
    s = s.replace("return;", "")
    return s

counts = collections.Counter()
residue = []
meta = []
files = []
for path in sys.argv[1:]:
    cur = None
    minus, plus = [], []
    def flush():
        global minus, plus
        if minus or plus:
            counts["hunks"] += 1
            if norm("".join(minus)) == norm("".join(plus)):
                counts["pure"] += 1
            else:
                residue.append((path, cur, minus, plus))
        minus, plus = [], []
    for line in open(path, encoding="utf-8", errors="surrogateescape"):
        line = line.rstrip("\n")
        if line.startswith("diff --git"):
            flush(); cur = line.split(" b/", 1)[1]; files.append(cur); continue
        if re.match(r"(new file mode|deleted file mode|old mode|new mode|rename |copy |similarity|Binary|GIT binary)", line):
            meta.append((path, cur, line)); continue
        if line.startswith(("--- ", "+++ ", "index ")):
            continue
        if line.startswith("@@"):
            flush(); continue
        if line.startswith("-"):
            minus.append(line[1:])
        elif line.startswith("+"):
            plus.append(line[1:])
        elif line.startswith(" ") or line == "":
            flush()
        elif line.startswith("\\"):
            continue
        else:
            meta.append((path, cur, "UNKNOWN LINE: " + line[:80]))
    flush()
print("files changed:", len(files), "distinct:", len(set(files)))
print("counts:", dict(counts))
print("meta lines:", meta[:20], len(meta))
print("paths with ..:", [f for f in files if ".." in f.split("/")])
print("non-.c/.h:", sorted({f for f in files if not f.endswith((".c", ".h"))}))
print("residue hunks:", len(residue))
for p, f, m, pl in residue:
    print("----", p.split("/")[-1][:6], f)
    for x in m: print("  -", x)
    for x in pl: print("  +", x)

# Second, stricter pass: the multiset of token-level edits across all hunks.
import difflib
edits = collections.Counter()
for path in sys.argv[1:]:
    minus, plus = [], []
    def flush2():
        global minus, plus
        if minus or plus:
            a = re.findall(r"\w+|[^\w\s]", " ".join(minus))
            b = re.findall(r"\w+|[^\w\s]", " ".join(plus))
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if op != "equal":
                    edits[(op, " ".join(a[i1:i2]), " ".join(b[j1:j2]))] += 1
        minus, plus = [], []
    for line in open(path, encoding="utf-8", errors="surrogateescape"):
        line = line.rstrip("\n")
        if line.startswith(("diff --git", "@@", "--- ", "+++ ", "index ")):
            flush2(); continue
        if line.startswith("-"): minus.append(line[1:])
        elif line.startswith("+"): plus.append(line[1:])
        else: flush2()
    flush2()
print("token-level edit kinds:", len(edits))
for k, v in edits.most_common():
    print(v, k)
