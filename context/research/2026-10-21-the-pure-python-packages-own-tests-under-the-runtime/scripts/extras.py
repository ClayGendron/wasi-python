"""Fetch the survey's candidate kit-extra wheels (pure, py3-none-any) from PyPI into one folder
each, check each against PyPI's SHA-256, and print name, version, requires_dist.

    uv run --no-project python -I extras.py <out> name[==version] ...
"""

import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

out = Path(sys.argv[1])
for spec in sys.argv[2:]:
    name, _, ver = spec.partition("==")
    url = f"https://pypi.org/pypi/{name}/{ver + '/' if ver else ''}json"
    with urllib.request.urlopen(url) as r:
        meta = json.load(r)
    v = meta["info"]["version"]
    wheels = [u for u in meta["urls"] if u["packagetype"] == "bdist_wheel"
              and u["filename"].endswith("-none-any.whl")]
    if not wheels:
        print(f"NOWHEEL {name} {v}")
        continue
    w = wheels[0]
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    f = d / w["filename"]
    if not f.exists():
        subprocess.run(["curl", "-sSfL", "-o", str(f), w["url"]], check=True)
    ok = hashlib.sha256(f.read_bytes()).hexdigest() == w["digests"]["sha256"]
    req = [x for x in (meta["info"]["requires_dist"] or []) if "extra ==" not in x]
    print(("OK  " if ok else "BAD ") + f"{w['filename']} {w['digests']['sha256']} {w['url']}")
    print(f"    requires: {req}")
