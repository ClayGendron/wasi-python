"""The progress history in volumes (spec 062).

The history is one hash-chained sequence of lines, one per acceptance, kept in volumes in
`context/progress/`. Volume 1 is `history.jsonl` (lines 1 to 59, the old format, sealed by its
SHA-256). Every later volume is named after its first line, `history-<n:05d>.jsonl`, and holds at
most `BUDGET` bytes. A line written under this spec (format 2, `"schema": 2`) records the change
in the passed set since the line before (`passed_added`, `passed_removed`) and a digest of the whole
set (`passed_digest`); an old-format line carries the whole `passed` list. A line's passed set is
found by replay from line 1.

Only `errors` (the intact check) verifies every digest. `last_passed` (for `accept`) checks the
newest line's alone, and `systems_that_passed` none (the pre-build review, F2). Every size is in
bytes (F5).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, deque
from collections.abc import Iterator
from pathlib import Path

BUDGET = 1 << 19  # half the tracked-file limit of the rules check (Decision 4)
FIRST = "history.jsonl"
# Volume 1 at main f6b3f75: lines 1 to 59, pinned byte for byte (Decision 1, the review's F3).
SEALED = {FIRST: "0a99162aefbb4d997b80b2012e73a39364aba108defe56781611cb1623ed1120"}
PROBE = "tests/checks/test_v1_2_portable_and_sealed.py::test_guest_runs_here[plain]"
# The lane's step 4 (Decision 12): `git add` first, since a new volume is untracked.
ACCEPT_PATHSPEC = ("context/progress/accepted.json", ":(glob)context/progress/history*.jsonl")
_QUOTED = f"{ACCEPT_PATHSPEC[0]} '{ACCEPT_PATHSPEC[1]}'"
ACCEPT_COMMANDS = (f"git add -- {_QUOTED}", f'git commit -m "Accept …" -- {_QUOTED}')

_NAME = re.compile(r"history-(\d{5,})\.jsonl")
# Counts for the self-tests (criterion 11): digests of a passed set, the bytes hashed for them,
# and the JSON bytes parsed by the replay.
OPS: Counter = Counter()
_CACHE: dict[str, frozenset] = {}  # the newest line's hash -> its replayed set (one entry)


def volume_name(n: int) -> str:
    return FIRST if n == 1 else f"history-{n:05d}.jsonl"


def first_line_of(name: str) -> int | None:
    """The first line's number a volume of this name holds; None unless the name is exactly
    what `volume_name` makes."""
    if name == FIRST:
        return 1
    m = _NAME.fullmatch(name)
    if not m or int(m[1]) < 2 or volume_name(int(m[1])) != name:
        return None
    return int(m[1])


def volumes(folder: Path) -> list[Path]:
    """The volumes in `folder`, in line order (by number, never by name)."""
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir() if p.is_file() and first_line_of(p.name) is not None]
    return sorted(found, key=lambda p: first_line_of(p.name))


def _split(data: bytes) -> list[str]:
    return [x for x in data.decode("utf-8", errors="replace").split("\n") if x.strip()]


def lines(folder: Path) -> list[str]:
    """Every line of every volume, in order."""
    out: list[str] = []
    for v in volumes(folder):
        out += _split(v.read_bytes())
    return out


def found_in(folder: Path) -> dict[str, bytes]:
    """Every file in `folder` whose name starts with `history`, with its bytes."""
    if not folder.is_dir():
        return {}
    return {
        p.name: p.read_bytes()
        for p in sorted(folder.iterdir())
        if p.is_file() and p.name.startswith("history")
    }


def digest(passed) -> str:
    data = json.dumps(sorted(passed)).encode()
    OPS["digests"] += 1
    OPS["hashed"] += len(data)
    return hashlib.sha256(data).hexdigest()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _parse(i: int, line: str) -> dict:
    OPS["parsed"] += len(line.encode())
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        raise ValueError(f"history line {i} is not JSON") from None
    if not isinstance(entry, dict):
        raise ValueError(f"history line {i} is not a JSON object")
    return entry


def _ids(i: int, entry: dict, key: str) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"history line {i}: {key} is not a list of node ids")
    if value != sorted(set(value)):
        raise ValueError(f"history line {i}: {key} is not sorted, or repeats an id")
    return value


def _step(i: int, entry: dict, before: frozenset, verify: bool) -> frozenset:
    """The passed set after line `i`, from the set before it."""
    if "schema" not in entry:
        return frozenset(_ids(i, entry, "passed"))
    schema = entry["schema"]
    if type(schema) is not int or schema != 2:
        raise ValueError(f"history line {i}: schema is {schema!r}; only 2 is known")
    added, removed = _ids(i, entry, "passed_added"), _ids(i, entry, "passed_removed")
    again = [x for x in added if x in before]
    if again:
        raise ValueError(f"history line {i}: passed_added names {again[0]}, already passing")
    absent = [x for x in removed if x not in before]
    if absent:
        raise ValueError(f"history line {i}: passed_removed names {absent[0]}, not passing")
    after = (before - set(removed)) | set(added)
    if verify and digest(after) != entry.get("passed_digest"):
        raise ValueError(f"history line {i}: the passed set does not replay to its passed_digest")
    return after


def _replay(history_lines: list[str], verify: bool) -> Iterator[tuple[dict, frozenset]]:
    s: frozenset = frozenset()
    for i, line in enumerate(history_lines, 1):
        entry = _parse(i, line)
        s = _step(i, entry, s, verify)
        yield entry, s


def passed_sets(history_lines: list[str], verify: bool = True) -> Iterator[set[str]]:
    """Each line's passed set, in order. Raises ValueError naming the first line that does not
    apply (and, with `verify`, whose digest does not match)."""
    for _, s in _replay(history_lines, verify):
        yield set(s)


def forget() -> None:
    _CACHE.clear()


def remember(line: str, passed) -> None:
    """Called by `accept` with the line it makes, so the next acceptance skips the replay."""
    _CACHE.clear()
    _CACHE[_sha(line)] = frozenset(passed)


def last_passed(history_lines: list[str]) -> set[str]:
    """The newest line's passed set, for `accept`: replayed without digests (or taken from the
    cache, keyed by the newest line, whose `prev` chains to every line before it), then the
    newest line's digest alone is checked."""
    if not history_lines:
        return set()
    n, newest = len(history_lines), history_lines[-1]
    s = _CACHE.get(_sha(newest))
    if s is None:
        ((entry, s),) = deque(_replay(history_lines, verify=False), maxlen=1)
    else:  # the very line `accept` made, so its format is known good
        entry = _parse(n, newest)
    if "schema" in entry and digest(s) != entry.get("passed_digest"):
        raise ValueError(f"history line {n}: the passed set does not replay to its passed_digest")
    return set(s)


def target(folder: Path, line: str) -> Path:
    """The volume an acceptance's line goes to (Decision 4)."""
    vs = volumes(folder)
    if not vs:
        return folder / FIRST
    newest = vs[-1]
    if len(newest.read_bytes()) + len(line.encode()) + 1 <= BUDGET:
        return newest
    return folder / volume_name(json.loads(line)["n"])


def systems_that_passed(folder: Path, artifact: str) -> set[str]:
    """The operating systems whose accepted runs passed the guest on this artifact's bytes. On a
    history that does not replay, the empty set: the intact check reports why."""
    systems = set()
    try:
        for entry, s in _replay(lines(folder), verify=False):
            if entry.get("artifact") == artifact and PROBE in s:
                systems.add(str(entry.get("platform", "")).split("-")[0])
    except ValueError:
        return set()
    return systems


def _volume_errors(name: str, data: bytes, sealed: dict | None) -> tuple[list[str], list[str]]:
    errors = []
    if sealed and name in sealed and hashlib.sha256(data).hexdigest() != sealed[name]:
        errors.append(f"{name} is not the sealed volume (its SHA-256 changed)")
    if not data:
        return [*errors, f"{name} is empty"], []
    if not data.endswith(b"\n"):
        errors.append(f"{name} does not end with a newline")
    raw = data.split(b"\n")
    if raw[-1] == b"":
        raw.pop()
    if any(not x.strip() for x in raw):
        errors.append(f"{name} holds a blank line")
    offset, kept = 0, []
    for x in raw:
        offset += len(x) + 1
        if not x.strip():
            continue
        text = x.decode("utf-8", errors="replace")
        kept.append(text)
        try:
            entry = json.loads(text)
        except json.JSONDecodeError:
            continue  # the chain reports it
        if not isinstance(entry, dict):
            continue
        n = entry.get("n")
        if "schema" in entry and offset > BUDGET:
            errors.append(
                f"history line {n} ends at byte {offset} of {name}, past the volume budget of "
                f"{BUDGET}"
            )
        if "schema" not in entry and name != FIRST:
            errors.append(f"history line {n} is in the old format outside {FIRST}")
    return errors, kept


def errors(
    found: dict[str, bytes],
    accepted_text: str | None,
    committed: dict[str, bytes] | None,
    sealed: dict[str, str] | None = None,
) -> list[str]:
    """Everything wrong with a history folder (Decision 10). `found`: every file whose name
    starts with `history`, with its bytes; `committed`: every volume in HEAD's tree, or None;
    `sealed`: volume name -> the SHA-256 its bytes must have."""
    errs: list[str] = []
    vols: dict[int, str] = {}
    for name in sorted(found):
        n = first_line_of(name)
        if n is None:
            errs.append(f"{name}: an unrecognised history file (spec 062)")
        else:
            vols[n] = name
    order = sorted(vols)
    if order and order[0] != 1:
        errs.append(f"{FIRST} is missing, but later history volumes exist")
    every: list[str] = []
    for k, n in enumerate(order):
        name = vols[n]
        own, kept = _volume_errors(name, found[name], sealed)
        errs += own
        if not kept:
            continue
        try:
            first = json.loads(kept[0])
        except json.JSONDecodeError:
            first = None
        fn = first.get("n") if isinstance(first, dict) else None
        good = type(fn) is int and fn >= 1
        if isinstance(first, dict) and (not good or volume_name(fn) != name):
            errs.append(
                f"{name}: its first line is history line {fn!r}, so it should be named "
                f"{volume_name(fn) if good else 'after a whole number'}"
            )
        if k > 0:
            before = vols[order[k - 1]]
            if len(found[before]) + len(kept[0].encode()) + 1 <= BUDGET:
                errs.append(f"{name} was begun early: its first line fitted in {before}")
        every += kept

    prev, readable, seen_change = None, True, False
    for i, line in enumerate(every, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errs.append(f"history line {i} is not JSON")
            readable = False
            break
        if not isinstance(entry, dict):
            errs.append(f"history line {i} is not a JSON object")
            readable = False
            break
        want = _sha(prev) if prev else None
        if entry.get("prev") != want:
            errs.append(f"history line {i}: prev does not hash line {i - 1}")
        if entry.get("n") != i:
            errs.append(f"history line {i}: n is {entry.get('n')}")
        if "schema" in entry:
            seen_change = True
            if "passed" in entry:
                errs.append(f"history line {i} is in format 2 but carries passed")
        elif seen_change:
            errs.append(f"history line {i} is in the old format after a format-2 line")
        prev = line
    if readable:
        try:
            for _ in _replay(every, verify=True):
                pass
        except ValueError as e:
            errs.append(str(e))
    if every and not errs:
        last = json.loads(every[-1])
        if accepted_text is None:
            errs.append("history has lines but accepted.json is missing")
        elif last.get("accepted") != _sha(accepted_text):
            errs.append("accepted.json is not the file the last history line wrote")
    if not every and accepted_text is not None:
        errs.append("accepted.json exists but the history is empty")
    for name, data in sorted((committed or {}).items()):
        if name not in found:
            errs.append(f"committed history volume {name} is missing")
        elif not found[name].startswith(data):
            errs.append(f"{name} does not extend its committed version (a line was rewritten)")
    return errs
