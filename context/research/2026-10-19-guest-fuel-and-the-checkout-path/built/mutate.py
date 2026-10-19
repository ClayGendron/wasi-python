import sys
from pathlib import Path
p = Path("tests/checks/test_v1_3_lxml.py"); s = p.read_text()
M = {
 "m1": ('outside = guest(which, ["-c", OUTSIDE, host], preopens=preopens, record=False)',
        'outside = guest(which, ["-c", OUTSIDE, host], preopens=[*preopens, (host.rsplit("/", 1)[0], ro, False)], record=False)'),
 "m2": ('case("entity by guest path, outside run", "file:///ro/secret.txt")',
        'case("entity by guest path, outside run", "file:///ro/elsewhere.txt")'),
 "m3": ('    host = str(ro / "secret.txt")\n', '    host = "/nonexistent/secret.txt"\n'),
 "m4": ('NET = "http://127.0.0.1:9/x"\n', 'case("entity outside grants", lambda: entity("file:///nope", resolve_entities=True))\nNET = "http://127.0.0.1:9/x"\n'),
}
old, new = M[sys.argv[1]]
assert s.count(old) == 1, sys.argv[1]
p.write_text(s.replace(old, new))
