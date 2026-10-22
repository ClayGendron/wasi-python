"""Pass 3: repack every release group past the bound, and rebuild every split whose groups
pytest's substring -k does not give the tests they were meant to have, by a packer that
simulates -k over the file's known tests (ksim.py), so each planned group is exactly the set
pytest selects, none is empty, and each is under the target unless it is one test.

    uv run python pass3.py [--target G] [--dry]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SP = Path(__file__).parent
sys.argv, _argv = sys.argv[:1], sys.argv[1:]
import kdepth_host  # noqa: E402
import ksim  # noqa: E402
import pass2  # noqa: E402

TARGET = float(_argv[_argv.index("--target") + 1]) if "--target" in _argv else 380.0
DRY = "--dry" in _argv
BOUND = 480.0
UNKNOWN = 20.0  # a test no session reached: its estimate
FULL = 0.6  # a bin this full closes rather than take finer keys
groups = json.loads((SP / "groups.json").read_text())
splits = json.loads((SP / "splits.json").read_text())
ff = json.loads((SP / "filefuel.json").read_text())
measured = json.loads((SP / "measured.json").read_text())
inv = json.loads((SP / "inventory.json").read_text())
START = pass2.START
KNOWN = ksim.known_tests()
_m = KNOWN["scipy/special/tests/test_mpmath.py"]
_i = _m.index("scipy/special/tests/test_mpmath.py::TestSystematic::test_betainc")
if "scipy/special/tests/test_mpmath.py::TestSystematic::test_betaincc" not in _m:
    _m.insert(_i + 1, "scipy/special/tests/test_mpmath.py::TestSystematic::test_betaincc")
EST: dict[str, float] = {}
for v in ff.values():
    for ts in v["tests"].values():
        for n, g in ts:
            EST[n] = g
EST["scipy/special/tests/test_mpmath.py::TestSystematic::test_betainc"] = 63.3 - 20.1
EST["scipy/special/tests/test_mpmath.py::TestSystematic::test_betaincc"] = 26.8 - 20.1
OK_KEY = re.compile(r"[\w:+\-.\[\]\\/]+")
CLOCK = {  # a group with a clock step holds exactly one test
    "scipy-special-mpmath-betainc": "TestSystematic and test_betainc and not test_betaincc",
    "scipy-special-mpmath-betaincc": "TestSystematic and test_betaincc",
}


def ok(key: str) -> bool:
    return bool(key) and key not in pass2.NOT_IDENT and bool(OK_KEY.fullmatch(key)) and pass2.parses(key)


FNAMES: dict[str, set[str]] = {
    f: {t.split("::")[-1].split("[")[0] for t in ts} for f, ts in KNOWN.items()
}


def exact(name: str, file: str) -> str:
    """A key that takes the function `name` and no other function of the file whose name holds
    it (pytest's -k matches substrings)."""
    others = sorted(o for o in FNAMES.get(file, ()) if name in o and o != name)
    return f"{name} and not ({' or '.join(others)})" if others else name


def keys_of(node: str) -> list[str]:
    """Candidate -k keys for a test, coarse to fine: its classes, its function, its parameters'
    leading dash-separated parts, the whole name; where a part holds a character -k cannot
    name, the characters before it."""
    parts = node.split("::")[1:]
    name, _, param = parts[-1].partition("[")
    file = node.split("::")[0]
    out = [c for c in parts[:-1] if ok(c)] + ([exact(name, file)] if ok(name) else [])
    if not param:
        if len(parts) > 1 and ok(parts[-2]) and out:
            out.append(f"{parts[-2]} and ({out[-1]})")
        return out
    param = param[:-1]
    bits = param.split("-")
    for d in range(1, len(bits) + 1):
        head = "-".join(bits[: d - 1]) + ("-" if d > 1 else "")
        for c in range(1, len(bits[d - 1])):
            k = f"{name}[" + head + bits[d - 1][:c]
            if ok(k) and k not in out:
                out.append(k)
        k = f"{name}[" + "-".join(bits[:d]) + ("]" if d == len(bits) else "")
        if ok(k):
            if k not in out:
                out.append(k)
            continue
        m = re.match(r"[\w:+\-.\\/]*", "-".join(bits[:d]))
        k = f"{name}[" + m[0]
        if m[0] and ok(k) and k not in out:
            out.append(k)
        break
    return out


class Sim:
    def __init__(self, tests: list[str]):
        self.tests = tests
        self.low = {t: [n.lower() for n in ksim.names(t)] for t in tests}

    def matches(self, key: str, among: list[str]) -> list[str]:
        e = ksim.Expression.compile(key)
        out = []
        for t in among:
            ns = self.low[t]
            if e.evaluate(lambda s, **_k: any(s.lower() in n for n in ns)):
                out.append(t)
        return out


def est(t: str) -> float:
    return EST.get(t, UNKNOWN)


def pack(tests: list[str], first: list[tuple[str, str]], room0: float) -> list[tuple[list[str], list[str]]]:
    """Bins (keys, tests) over `tests` in order, each bin's tests exactly what its keys take
    from the tests no earlier bin took; `first` are (group, keyword) bins of one test placed
    first. The last bin's keys are not used: it is the split's remainder."""
    sim = Sim(tests)
    left = list(tests)
    bins: list[tuple[list[str], list[str]]] = []

    def take(got: list[str]) -> None:
        gone = set(got)
        left[:] = [u for u in left if u not in gone]

    for _, k in first:
        got = sim.matches(k, left)
        assert len(got) == 1, (k, got)
        bins.append(([k], got))
        take(got)
    cur_keys: list[str] = []
    cur: list[str] = []
    fuel = 0.0
    while left:
        t = left[0]
        ks = keys_of(t)
        if not ks:
            raise SystemExit(f"no key names {t}")
        close = False
        for k in ks:
            got = sim.matches(k, left)
            g = sum(est(u) for u in got)
            if t in got and fuel + g <= room0:
                cur_keys.append(k)
                cur += got
                fuel += g
                take(got)
                break
            if cur and g <= room0 and fuel >= FULL * room0:
                close = True  # a fuller bin with finer keys only costs -k terms
                break
        else:
            close = True
        if close:
            if cur:
                bins.append((cur_keys, cur))
                cur_keys, cur, fuel = [], [], 0.0
                continue
            got = sim.matches(ks[-1], left)
            bins.append(([ks[-1]], got))
            take(got)
    if cur:
        bins.append((cur_keys, cur))
    return bins


def check(file: str, gnames: list[str], kws: list[str], planned: dict[str, list[str]]) -> None:
    got = ksim.assign(KNOWN[file], gnames, kws)
    for g in gnames:
        if g in planned and sorted(got[g]) != sorted(planned[g]):
            raise SystemExit(f"{file}: {g} would take {len(got[g])} tests, planned {len(planned[g])}")
        if not got[g]:
            raise SystemExit(f"{file}: {g} would take no test")


def group_entry(old: dict, name: str, tests: list[str], fam: str, file: str) -> dict:
    e = sum(est(t) for t in tests) + START[fam]
    d = {k: v for k, v in old.items() if k not in ("name", "est", "cap", "comment", "clock")}
    d |= {"name": name, "paths": [file], "est": round(e, 1), "cap": int(max(3 * e, 300) * 1e9)}
    if len(tests) == 1 and e > BOUND:
        d["comment"] = f"One test past the 480 G bound, about {e:.0f} G estimated: {tests[0].split('::', 1)[1]}"
    return d


def base_of(names: list[str]) -> str:
    return re.sub(r"-\d+$", "", names[0])


def rebuild_split(fam: str, s: dict, j: int, old: dict | None = None) -> list[dict]:
    """Rebuild split `s` of family `fam` from its group index j; returns the new group entries
    (the caller replaces the old ones from j on)."""
    file = s["file"]
    tests = KNOWN[file]
    kept_names, kept_kws = s["groups"][:j], s["keywords"][:j]
    taken = ksim.assign(tests, kept_names + ["_rest"], kept_kws) if kept_names else {"_rest": tests}
    rest = taken["_rest"]
    first = [(g, CLOCK[g]) for g in s["groups"][j:] if g in CLOCK]
    bins = pack(rest, first, TARGET - START[fam])
    base = base_of([g for g in s["groups"] if g not in CLOCK])
    names, n = [], j
    for keys, _ in bins:
        if keys and keys[0] in CLOCK.values():
            names.append(next(g for g, k in CLOCK.items() if k == keys[0]))
        else:
            n += 1
            names.append(f"{base}-{n}")
    kws = kept_kws + [" or ".join(dict.fromkeys(k)) for k, _ in bins[:-1]]
    gnames = kept_names + names
    check(file, gnames, kws, {g: b[1] for g, b in zip(names, bins)})
    terms = kdepth_host.split_depth({"file": file, "groups": gnames, "keywords": kws})
    if terms > 150:
        raise SystemExit(f"{file}: -k depth {terms}")
    old = old or next(x for x in groups[fam] if x["name"] in s["groups"])
    entries = []
    for g, (_, ts) in zip(names, bins):
        d = group_entry(old, g, ts, fam, file)
        if g in CLOCK:
            d["clock"] = 100_000
            d["cap"] = 200_000_000_000
        entries.append(d)
    for keys, ts in bins:
        if sum(est(t) for t in ts) + START[fam] > BOUND:
            print(f"   past the bound: {len(ts)} test(s), keys {keys[:3]}, {ts[0].split('::', 1)[1][:90]}")
    print(f"{file}: from group {j + 1}, {len(bins)} groups, {terms} -k depth; est "
          f"{[round(sum(est(t) for t in b[1])) for b in bins]}")
    s["groups"], s["keywords"] = gnames, kws
    return entries


FRESH: set[str] = set()


def subdivide(fam: str, s: dict, g: str) -> list[dict]:
    """Split one group of a split past the bound into bins of its own tests: each bin but the
    last runs `(e) and (keys)`, the last keeps e (or stays the remainder), so no other group of
    the split changes."""
    file = s["file"]
    i = s["groups"].index(g)
    got = ksim.assign(KNOWN[file], s["groups"], s["keywords"])
    bins = pack(got[g], [], TARGET - START[fam])
    if len(bins) == 1:
        return []
    last = i == len(s["groups"]) - 1
    e = None if last else s["keywords"][i]
    kws = []
    for keys, _ in bins[:-1]:
        k = " or ".join(dict.fromkeys(keys))
        kws.append(k if last else f"({e}) and ({k})")
    names = [f"{g}-{chr(ord('a') + j)}" for j in range(len(bins))]
    gnames = s["groups"][:i] + names + s["groups"][i + 1 :]
    kw_all = s["keywords"][:i] + kws + ([] if last else [e]) + s["keywords"][i + 1 :]
    if last:
        kw_all = s["keywords"] + kws
    check(file, gnames, kw_all, {n: b[1] for n, b in zip(names, bins)})
    depth = kdepth_host.split_depth({"file": file, "groups": gnames, "keywords": kw_all})
    if depth > 150:
        raise SystemExit(f"{file}: -k depth {depth}")
    old = next(x for x in groups[fam] if x["name"] == g)
    entries = [group_entry(old, n, b[1], fam, file) for n, b in zip(names, bins)]
    print(f"{g}: {measured.get(g, 0) / 1e9:.0f} G -> {len(bins)} groups, depth {depth}, est "
          f"{[round(sum(est(t) for t in b[1])) for b in bins]}")
    s["groups"], s["keywords"] = gnames, kw_all
    return entries


def bad_index(fam: str, s: dict) -> int | None:
    tests = KNOWN.get(s["file"], [])
    got = ksim.assign(tests, s["groups"], s["keywords"])
    for i, g in enumerate(s["groups"]):
        n = len(got[g])
        m = measured.get(g)
        if n == 0 or (g in CLOCK and n != 1):
            return i
        if m is None and g not in CLOCK and g not in FRESH:
            return i
    return None


def over(fam: str, s: dict) -> list[str]:
    tests = KNOWN.get(s["file"], [])
    got = ksim.assign(tests, s["groups"], s["keywords"])
    return [g for g in s["groups"] if measured.get(g, 0) / 1e9 > BOUND and len(got[g]) > 1]


def main() -> None:
    for fam, ss in splits.items():
        for s in ss:
            for g in over(fam, s):
                entries = subdivide(fam, s, g)
                if entries:
                    FRESH.update(e["name"] for e in entries)
                    gs = groups[fam]
                    pos = next(k for k, x in enumerate(gs) if x["name"] == g)
                    gs[pos : pos + 1] = entries
                    measured.pop(g, None)
            j = bad_index(fam, s)
            if j is None:
                continue
            old_names = list(s["groups"])
            entries = rebuild_split(fam, s, j)
            gs = groups[fam]
            pos = min(k for k, x in enumerate(gs) if x["name"] in old_names[j:])
            gs[:] = [x for x in gs if x["name"] not in old_names[j:]]
            gs[pos:pos] = entries
            for g in old_names[j:]:
                measured.pop(g, None)
            for e in entries:
                measured.pop(e["name"], None)
    in_split = {g for ss in splits.values() for s in ss for g in s["groups"]}
    for fam, gs in groups.items():
        out = []
        for g in gs:
            name, m = g["name"], measured.get(g["name"], 0) / 1e9
            if name in in_split or m <= BOUND:
                out.append(g)
                continue
            info = ff[name]
            files = []
            for p in g["paths"]:
                files += [f for f in inv[fam]["files"]
                          if (f == p or f.startswith(p.rstrip("/") + "/")) and not pass2.left_out(fam, f)]
            fe = {f: sum(est(t) for t in KNOWN.get(f, [])) or info["files"].get(f, 1.0) for f in files}
            pack_f, pack_g, k = [], 0.0, 0
            new = []
            for f in files:
                if fe[f] + START[fam] > TARGET and len(KNOWN.get(f, [])) > 1:
                    s = {"file": f, "groups": [f"{name}-{pass2.short(f)}-1"], "keywords": []}
                    entries = rebuild_split(fam, s, 0, g)
                    splits.setdefault(fam, []).append(s)
                    new += entries
                    continue
                if pack_f and pack_g + fe[f] > TARGET - START[fam]:
                    k += 1
                    new.append({**{x: y for x, y in g.items() if x not in ("name", "est", "cap", "comment")},
                                "name": f"{name}-{k}", "paths": pack_f, "est": round(pack_g + START[fam], 1),
                                "cap": int(max(3 * (pack_g + START[fam]), 300) * 1e9)})
                    pack_f, pack_g = [], 0.0
                pack_f.append(f)
                pack_g += fe[f]
            if pack_f:
                k += 1
                new.append({**{x: y for x, y in g.items() if x not in ("name", "est", "cap", "comment")},
                            "name": f"{name}-{k}", "paths": pack_f, "est": round(pack_g + START[fam], 1),
                            "cap": int(max(3 * (pack_g + START[fam]), 300) * 1e9)})
            measured.pop(name, None)
            print(f"{name}: {m:.0f} G -> {len(new)} groups, est {[x['est'] for x in new]}")
            out += new
        groups[fam] = out
    names = [x["name"] for gs in groups.values() for x in gs]
    assert len(names) == len(set(names)), "duplicate group names"
    if not DRY:
        (SP / "groups.json").write_text(json.dumps(groups, indent=1))
        (SP / "splits.json").write_text(json.dumps(splits, indent=1))
        (SP / "measured.json").write_text(json.dumps(measured, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
