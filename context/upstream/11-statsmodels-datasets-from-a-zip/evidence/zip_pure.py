"""zip_pure.py <site-packages> <out.zip> <pkg>...: the packages' files without native or source files."""
import os, sys, zipfile
site, out, pkgs = sys.argv[1], sys.argv[2], sys.argv[3:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for pkg in pkgs:
        for dp, dn, fn in os.walk(os.path.join(site, pkg)):
            dn[:] = sorted(d for d in dn if d not in ("__pycache__", "tests", "test", ".dylibs"))
            for f in sorted(fn):
                if f.endswith((".so", ".pyx", ".pxd", ".c", ".h", ".cpp", ".pyc")):
                    continue
                p = os.path.join(dp, f)
                z.write(p, os.path.relpath(p, site))
