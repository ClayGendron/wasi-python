"""Print each unpacked tree's pytest configuration (read as text, nothing imported).

    uv run --no-project python -I configs.py <trees>
"""

import configparser
import sys
import tomllib
from pathlib import Path

trees = Path(sys.argv[1])
for d in sorted(trees.iterdir()):
    root = next(d.iterdir())
    print(f"=== {d.name}  ({root.name})")
    pp = root / "pyproject.toml"
    if pp.is_file():
        t = tomllib.loads(pp.read_text())
        o = t.get("tool", {}).get("pytest", {})
        o = o.get("ini_options", o)
        if o:
            for k, v in o.items():
                print(f"  pyproject {k} = {v!r}"[:400])
    for name, sect in [("pytest.ini", "pytest"), ("setup.cfg", "tool:pytest"), ("tox.ini", "pytest")]:
        f = root / name
        if f.is_file():
            c = configparser.RawConfigParser()
            try:
                c.read_string(f.read_text())
            except Exception as e:  # noqa: BLE001
                print(f"  {name}: unreadable {e}")
                continue
            if c.has_section(sect):
                for k, v in c.items(sect):
                    print(f"  {name} {k} = {v!r}"[:400])
    confs = sorted(str(p.relative_to(root)) for p in root.rglob("conftest.py"))
    print("  conftests:", confs[:12], "…" if len(confs) > 12 else "")
