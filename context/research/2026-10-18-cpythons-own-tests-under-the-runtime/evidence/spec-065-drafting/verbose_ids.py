"""Every failed or errored test, by the id the driver's stream would write, from the research's
verbose reruns (build/cpython-suite-research/runs-verbose/<module>.out, regrtest -v).

uv run --no-project python verbose_ids.py <runs-verbose dir>  ->  module, outcome, id, reason (TSV)

unittest prints `FAIL: <name> (<id or module>) <subtest description>`; the id a stream writes is
the test's id(), then the subtest's description ([msg] and/or (params)), as _SubTest.id() does.
"""
import re
import sys
from pathlib import Path

HEAD = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]*)\)(.*)$")
for out in sorted(Path(sys.argv[1]).glob("*.out")):
    module = out.stem
    lines = out.read_text(errors="replace").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if not m or i == 0 or not lines[i - 1].startswith("====="):
            continue
        kind, name, paren, suffix = m.groups()
        tid = paren if paren.endswith("." + name) else f"{paren}.{name}"
        sid = (tid + " " + suffix.strip()).strip()
        reason = ""
        for nxt in lines[i + 2 :]:
            if nxt.startswith("=====") or nxt.startswith("-----"):
                break
            if nxt and not nxt.startswith(" ") and not nxt.startswith("Traceback"):
                reason = nxt
        key = (kind, sid)
        if key in seen:
            continue
        seen.add(key)
        print(f"{module}\t{'failed' if kind == 'FAIL' else 'error'}\t{sid}\t{reason[:160]}")
