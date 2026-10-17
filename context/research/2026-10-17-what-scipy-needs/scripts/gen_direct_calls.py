"""Append to a copy of an f2py module one function that calls every `extern ... F_FUNC(name,NAME)(...)`
directly, so wasm-ld's signature check sees what f2py's indirect calls hide until run time."""
import re, sys
src, dst, tag = sys.argv[1:]
text = open(src, encoding="utf-8").read()
pat = re.compile(r"^extern\s+(.+?)\s+(F_FUNC(?:_US)?)\((\w+),(\w+)\)\((.*)\);\s*$", re.M)
calls, seen = [], set()
for m in pat.finditer(text):
    ret, mac, name, up, args = m.groups()
    if name in seen:
        continue
    seen.add(name)
    depth, n = 0, 0 if args.strip() in ("", "void") else 1
    for ch in args:
        depth += ch == "("
        depth -= ch == ")"
        n += ch == "," and depth == 0
    calls.append(f"  (void){mac}({name},{up})({', '.join(['0'] * n)});")
with open(dst, "w", encoding="utf-8") as f:
    f.write(text + f"\nvoid direct_calls_{tag}(void) {{\n" + "\n".join(calls) + "\n}\n")
print(f"{tag}: {len(seen)} routines", file=sys.stderr)
