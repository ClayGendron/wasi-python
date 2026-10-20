"""One qualified line carries a trailing comment that takes it past 100 columns and that ruff
format cannot wrap: the comment moves to the line above (named in the landing notes)."""
from pathlib import Path

p = Path("src/wasi_python/_sessions.py")
t = p.read_text()
LONG = "    _private_dirs._flush_warnings()  # what the release's removals queued, outside every lock (spec 084)\n"
assert t.count(LONG) == 1
p.write_text(t.replace(LONG, "    # what the release's removals queued, outside every lock (spec 084)\n    _private_dirs._flush_warnings()\n"))
