"""Pure CPython: does a zipimporter still have the private `_files` dict?

Run: uv run --no-project --python 3.12 python -I zipimporter_files.py
     uv run --no-project --python 3.13 python -I zipimporter_files.py
Makes a one-file zip in a temporary folder; needs nothing but the standard library.
"""

import os
import sys
import tempfile
import zipfile
import zipimport

with tempfile.TemporaryDirectory() as d:
    archive = os.path.join(d, "pkg.zip")
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("pkg/__init__.py", "")
        z.writestr("pkg/data.txt", "hello\n")
    sys.path.insert(0, archive)
    import pkg

    ldr = pkg.__loader__
    print("python", sys.version.split()[0])
    print("loader is zipimporter:", isinstance(ldr, zipimport.zipimporter))
    print("hasattr(ldr, '_files'):", hasattr(ldr, "_files"))
    print("hasattr(ldr, '_get_files'):", hasattr(ldr, "_get_files"))
    # What reportlab.lib.utils.zipImported does, verbatim in effect:
    try:
        result = ldr if isinstance(ldr, zipimport.zipimporter) and len(ldr._files) else None
    except Exception as e:  # reportlab uses a bare except
        result = None
        print("len(ldr._files) raised:", type(e).__name__, e)
    print("zipImported-style test:", "zip-imported" if result else "None (treated as files)")
    print("public API sees the member:", ldr.get_data("pkg/data.txt") == b"hello\n")
