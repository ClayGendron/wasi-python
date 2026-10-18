"""Print the Version: header of PKG-INFO in the current directory: meson runs this from the
source tree's top, where the sdist keeps it. Anything else stops the build in one line."""

import sys
from pathlib import Path

for line in Path("PKG-INFO").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        break  # the headers end at the first blank line
    if line.startswith("Version: "):
        print(line.split(": ", 1)[1].strip())
        break
else:
    sys.exit("setuptools_scm stand-in: no Version: header in PKG-INFO")
