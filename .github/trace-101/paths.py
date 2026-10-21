"""Temporary: every repository path a traced build touches, outside build/ and downloads/.

Reads `strace -f -y -s 65535` output on stdin (pid-prefixed lines). Each process's working folder
is followed: a child takes its parent's at clone, fork or vfork; chdir and fchdir change it.
A path a syscall names is resolved against its dirfd (shown by -y) or the working folder. Lines
of a process whose parent is not yet known wait until the clone's return names it. Writes one
line per path: the path relative to the root, the syscalls with their results, a count, and the
first program that touched it.
"""

import json
import os
import re
import sys

ROOT = os.path.realpath(sys.argv[1])
OUT = sys.argv[2]
SKIP = (os.path.join(ROOT, "build"), os.path.join(ROOT, "downloads"))
LINE = re.compile(r"^(\d+)\s+(.*)$")
CALL = re.compile(r"^([a-z0-9_]+)\((.*)$")
RESUMED = re.compile(r"^<\.\.\. ([a-z0-9_]+) resumed>(.*)$")
STRING = re.compile(r'"((?:[^"\\]|\\.)*)"(\.\.\.)?')
FD = re.compile(r"^(-?\d+|AT_FDCWD)<([^>]*)>")
RESULT = re.compile(r"\)\s+=\s+(-?\d+|\?)(?:<([^>]*)>)?(?:\s+(E[A-Z0-9]+))?")
TWO_PATHS = {"rename", "renameat", "renameat2", "link", "linkat"}
FORKS = {"clone", "clone3", "fork", "vfork"}

cwd = {}
prog = {}
pending = {}
unfinished = {}
touched = {}
stats = {"lines": 0, "unknown_pid_lines": 0, "unresolved": 0}
first_pid = None


def unescape(s):
    return s.encode("latin-1", "backslashreplace").decode("unicode_escape", "replace")


def resolve(base, p):
    if not p:
        return None
    if not os.path.isabs(p):
        if base is None:
            return None
        p = os.path.join(base, p)
    return os.path.normpath(p)


def note(path, call, result, pid):
    if path is None:
        stats["unresolved"] += 1
        return
    if not (path == ROOT or path.startswith(ROOT + os.sep)):
        return
    if any(path == s or path.startswith(s + os.sep) for s in SKIP):
        return
    rel = os.path.relpath(path, ROOT)
    e = touched.setdefault(rel, {"calls": {}, "count": 0, "first": prog.get(pid, "?")})
    key = f"{call}:{result}"
    e["calls"][key] = e["calls"].get(key, 0) + 1
    e["count"] += 1


def handle(pid, call, args_and_result):
    base = cwd.get(pid)
    at = args_and_result.rfind(") = ")
    m = RESULT.match(args_and_result[at:]) if at >= 0 else None
    ret, retpath, err = (m.group(1), m.group(2), m.group(3)) if m else ("?", None, None)
    result = err or "ok"
    if call in FORKS and ret not in ("?",) and not ret.startswith("-"):
        child = int(ret)
        cwd[child] = base
        prog[child] = prog.get(pid, "?")
        for c, a in pending.pop(child, []):
            handle(child, c, a)
        return
    if call == "chdir" and result == "ok":
        s = STRING.search(args_and_result)
        if s:
            cwd[pid] = resolve(base, unescape(s.group(1)))
            note(cwd[pid], call, result, pid)
        return
    if call == "fchdir" and result == "ok":
        f = FD.match(args_and_result)
        if f:
            cwd[pid] = f.group(2)
        return
    if call in ("execve", "execveat"):
        s = STRING.search(args_and_result)
        if s and result == "ok":
            prog[pid] = os.path.basename(unescape(s.group(1)))
    dirbase = base
    f = FD.match(args_and_result)
    if f:
        dirbase = f.group(2)
    strings = [unescape(s.group(1)) for s in STRING.finditer(args_and_result)]
    if not strings:
        return
    if retpath and result == "ok" and not retpath.startswith(("pipe:", "socket:", "anon_inode")):
        note(os.path.normpath(retpath), call, result, pid)
        if call not in TWO_PATHS:
            return
    names = strings[:2] if call in TWO_PATHS else strings[:1]
    for n in names:
        note(dirbase if n == "" else resolve(dirbase, n), call, result, pid)


for raw in sys.stdin.buffer:
    stats["lines"] += 1
    line = raw.decode("utf-8", "surrogateescape").rstrip("\n")
    m = LINE.match(line)
    if not m:
        continue
    pid, rest = int(m.group(1)), m.group(2)
    if first_pid is None:
        first_pid = pid
        cwd[pid] = ROOT
        prog[pid] = "build.sh"
    if rest.endswith("<unfinished ...>"):
        c = CALL.match(rest)
        if c:
            unfinished[pid] = (c.group(1), c.group(2)[: -len("<unfinished ...>")])
        continue
    r = RESUMED.match(rest)
    if r:
        call, tail = r.group(1), r.group(2)
        head = unfinished.pop(pid, (call, ""))[1]
        rest_args = head + tail
    else:
        c = CALL.match(rest)
        if not c:
            continue
        call, rest_args = c.group(1), c.group(2)
    if pid not in cwd:
        stats["unknown_pid_lines"] += 1
        pending.setdefault(pid, []).append((call, rest_args))
        continue
    handle(pid, call, rest_args)

orphans = 0
while pending:
    pid, events = pending.popitem()
    cwd.setdefault(pid, None)
    for call, a in events:
        orphans += 1
        handle(pid, call, a)
stats["orphan_lines_resolved_without_a_cwd"] = orphans
stats["paths"] = len(touched)
with open(OUT, "w") as out:
    for rel in sorted(touched):
        e = touched[rel]
        calls = ",".join(f"{k}x{v}" for k, v in sorted(e["calls"].items()))
        out.write(f"{rel}\t{calls}\t{e['count']}\t{e['first']}\n")
json.dump(stats, sys.stdout)
print()
