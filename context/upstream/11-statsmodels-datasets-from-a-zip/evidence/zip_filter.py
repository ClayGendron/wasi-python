"""zip_filter.py <in.zip> <out.zip> <prefix>...: copy a zip without the members under any prefix (a folder ending in / or an exact name)."""
import sys, zipfile
src, out, prefixes = sys.argv[1], sys.argv[2], sys.argv[3:]
def gone(n):
    return any(n.startswith(p) if p.endswith("/") else n == p for p in prefixes)
with zipfile.ZipFile(src) as a, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as b:
    for i in a.infolist():
        if not gone(i.filename):
            b.writestr(i, a.read(i))
