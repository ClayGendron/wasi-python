"""Zip a package's non-native files from a site-packages folder: zip_pkg.py <site> <pkg> <out.zip>"""
import os, sys, zipfile
site, pkg, out = sys.argv[1:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for dp, dn, fn in os.walk(os.path.join(site, pkg)):
        dn[:] = sorted(d for d in dn if d not in ("__pycache__", "tests", "test"))
        for f in sorted(fn):
            if f.endswith((".so", ".pyx", ".pxd", ".c", ".h")):
                continue
            p = os.path.join(dp, f)
            z.write(p, os.path.relpath(p, site))
