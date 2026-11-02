"""Whether two run records give the same answer.

`differences(a, b)` lists every difference between two `latest.json` records in what a verdict is
made of: each check's `status`, `need`, `area`, `closer`, `facts`, the names of its metrics, its
`bytes`, `passes` and `ignores`; its `reason` where both records call it `gap` or `blocked`
(there the reason is deterministic: a gap's first line, a need); its `fuel` where the two differ
by more than the ratchet's tolerance, `abs(a - b) > FUEL_TOLERANCE * max(a, b)`, and so too each
value of its `fuel_facts` fact (fuel recorded, never ratcheted), both between records
of one platform (the ratchet keys fuel by platform too); and the run's `deselected`,
`collected_files` (one line per node or file), `suite` and `meta.foreign` (what steered the run
from outside the judge, which makes it red). A failure's reason is not compared: it may name a
temporary path, and the statuses already decide. A pass's reason, its note, is not compared
either: the plugin never compares a note, and one may print a fuel count, which carries the
residual serial runs show (the zip directory's zone-load check: 17 instructions in 8.7 million
between a serial and a parallel run, the build's evidence). The rest of `meta` is never compared.

Either record may be the release workflow's merged record (`release-record-1`, written by
`gather.merge`). It is read as the darwin run it contains: each check as its `source`
saw it (the darwin record that ran it, else the first other system's), with that source's
platform; a check no shard ran (deselected everywhere, or blocked by a need CI lacks) is not
compared, and `notes` names it; `suite` is the sum of the darwin runs' suites.

    uv run python tests/harness/sameness.py A.json B.json
    uv run python tests/harness/sameness.py --claims wave.toml [--except NNN] A.json B.json

    uv run python tests/harness/sameness.py --tier-rows release [--claims ledger/] A.json B.json

prints the differences, one per line, and exits 1 when there are any; with `--claims`, only those
no claim explains (a claim list, or a folder of them, is what B has that A lacks, by kind). Notes
go to stderr. A record or a claim list it cannot read exits 2.

Release-tier rows (a record's `release_checks`) are compared only when both records judged the
release tier: a normal record never ran them, so they are counted in a note. `--tier-rows
release` compares those rows alone, with their `deselected` entries, and neither the files nor
the unit suite: the comparison between two release acceptances, against the ledger of claims.
"""

from __future__ import annotations

import json
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):  # run as a script: the harness package lives one folder up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.gather import CI_NEEDS  # noqa: E402
from harness.scoreboard import FUEL_TOLERANCE  # noqa: E402

FIELDS = ("status", "need", "area", "closer")
FUEL_FACTS = "fuel_facts"  # a fact of fuel values, compared as fuel is
EXACT_METRICS = ("bytes", "passes", "ignores")  # counts that are equal on every system
REASONED = ("gap", "blocked")
SIDE = {0: "only in the first record", 1: "only in the second record"}
# The build shard runs in the x86_64 rebuild, on Linux: its blocks are Linux's, as are the
# release tier's shards'.
SYSTEMS = {"darwin": {"macos"}, "linux": {"linux", "build", "release"}, "win32": {"windows"}}
# Its run's unit tests are the lane's darwin units all the same: the lane runs them on darwin.
BUILD_RUN = "build/build"


class NotComparable(ValueError):
    """A record sameness cannot read (a release record older than the merged release record)."""


class ClaimError(ValueError):
    """A claim list that does not have the shape of `[[claim]]` tables."""


def fuel_differs(a: int, b: int) -> bool:
    return abs(a - b) > FUEL_TOLERANCE * max(a, b)


@dataclass(frozen=True)
class Diff:
    """One difference: its line, and what a claim must name to explain it."""

    text: str
    kind: str  # "only", "field", "deselected", "collected_files", "suite", "foreign"
    key: str = ""  # the node or file
    side: int = -1  # for "only", "deselected", "collected_files": which record has it
    name: str = ""  # for "field": the field or metric


@dataclass
class View:
    """A record as sameness compares it."""

    names: set[str]  # every check the record holds, run or not
    checks: dict[str, dict]  # the checks compared
    platform: dict[str, str]  # each compared check's platform
    unrun: dict[str, str]  # release only: checks no shard ran, with their need or status
    deselected: list[str]
    collected_files: list[str]
    suite: dict
    foreign: list[str]
    unheld: set[str] = field(default_factory=set)  # release only: fuel no shard on darwin gave
    elsewhere: dict[str, str] = field(default_factory=dict)  # release only: a worse status
    tier: str = "normal"  # the tier the record judged
    release: set[str] = field(default_factory=set)  # its release-tier checks


def is_release(r: dict) -> bool:
    return "records" in (r.get("meta") or {})


def view(r: dict) -> View:
    meta = r.get("meta") or {}
    if not is_release(r):
        checks = r.get("checks", {})
        return View(
            names=set(checks),
            checks=checks,
            platform={n: str(meta.get("platform")) for n in checks},
            unrun={},
            deselected=r.get("deselected", []),
            collected_files=r.get("collected_files", []),
            suite=r.get("suite", {}),
            foreign=meta.get("foreign") or [],
            tier=meta.get("tier") or "normal",
            release=set(r.get("release_checks", [])),
        )
    missing = [k for k in ("runs", "deselected", "collected_files") if k not in r]
    missing += ["meta.foreign"] if "foreign" not in meta else []
    if any("worst_platform" not in c for c in r.get("checks", {}).values()):
        missing.append("worst_platform on every check")
    if missing:
        raise NotComparable(
            "a release record older than the merged release record (it has no "
            f"{', '.join(missing)}): "
            "download the record of a run on a commit whose gather.py writes the merged record"
        )
    checks, platform, unrun, unheld, elsewhere = {}, {}, {}, set(), {}
    for node, c in r.get("checks", {}).items():
        source = c.get("source")
        if source is None:
            if c.get("status") != "deselected" and not _ci_block(c):
                raise NotComparable(
                    f"{node}: {c.get('status')!r} with no source; gather.merge leaves out the "
                    "source only of a check every record deselected or blocked by a CI need"
                )
            unrun[node] = c.get("need") or c.get("status")
            continue
        if c.get("status") != source.get("status") and not _ci_block(c):
            elsewhere[node] = (
                f"{node}: status {source.get('status')!r} on {source.get('platform')}, "
                f"{c.get('status')!r} on {c.get('worst_platform')}"
            )
        checks[node] = {
            **{k: v for k, v in source.items() if k != "platform"},
            "metrics": c.get("metrics", {}),
        }
        platform[node] = str(source.get("platform"))
        if not platform[node].startswith("darwin-"):  # G5 holds darwin fuel only
            unheld.add(node)
    suite: dict[str, int] = {}
    for key, run in r["runs"].items():
        if key == BUILD_RUN or str(run.get("platform", "")).startswith("darwin-"):
            for k, n in (run.get("suite") or {}).items():
                if type(n) is not int or n < 0:
                    raise NotComparable(
                        f"runs: a suite count that is not a whole number: {k} {n!r}"
                    )
                suite[k] = suite.get(k, 0) + n
    return View(
        names=set(r.get("checks", {})),
        checks=checks,
        platform=platform,
        unrun=unrun,
        deselected=r["deselected"],
        collected_files=r["collected_files"],
        suite=suite,
        foreign=meta["foreign"],
        unheld=unheld,
        elsewhere=elsewhere,
        tier=meta.get("tier") or "normal",
        release=set(r.get("release_checks", [])),
    )


def _ci_block(c: dict) -> bool:
    """Whether a merged check's worst status is a block by a need CI lacks, on a system that lacks
    it (`worst_platform`; the descriptor limit lacks on Windows alone)."""
    need = c.get("need")
    if c.get("status") != "blocked" or not isinstance(need, str) or need not in CI_NEEDS:
        return False
    where = str(c.get("worst_platform")).split("-")[0]
    return bool(SYSTEMS.get(where, set()) & CI_NEEDS[need])


def _facts(record: dict) -> tuple[object, dict]:
    """(the facts compared exactly, the fuel facts compared within the tolerance)."""
    facts = record.get("facts")
    if not isinstance(facts, dict) or FUEL_FACTS not in facts:
        return facts, {}
    return {k: v for k, v in facts.items() if k != FUEL_FACTS}, facts[FUEL_FACTS] or {}


def _check(node: str, a: dict, b: dict, same_platform: bool) -> list[Diff]:
    def d(name: str, text: str) -> Diff:
        return Diff(f"{node}: {text}", "field", node, name=name)

    found = [d(f, f"{f} {a.get(f)!r} != {b.get(f)!r}") for f in FIELDS if a.get(f) != b.get(f)]
    (fa, xa), (fb, xb) = _facts(a), _facts(b)
    if fa != fb:
        found.append(d("facts", f"facts {fa!r} != {fb!r}"))
    if set(xa) != set(xb):
        found.append(d("facts", f"{FUEL_FACTS} {sorted(xa)} != {sorted(xb)}"))
    for name in sorted(set(xa) & set(xb)) if same_platform else []:
        if fuel_differs(xa[name], xb[name]):
            text = f"{FUEL_FACTS} {name} {xa[name]} != {xb[name]} (beyond {FUEL_TOLERANCE})"
            found.append(d("fuel", text))
    if a.get("status") == b.get("status") in REASONED and a.get("reason") != b.get("reason"):
        found.append(d("reason", f"reason {a.get('reason')!r} != {b.get('reason')!r}"))
    ma, mb = a.get("metrics") or {}, b.get("metrics") or {}
    if set(ma) != set(mb):
        found.append(d("metrics", f"metrics {sorted(ma)} != {sorted(mb)}"))
    for name in EXACT_METRICS:
        if name in ma and name in mb and ma[name] != mb[name]:
            found.append(d(name, f"{name} {ma[name]} != {mb[name]}"))
    if same_platform and "fuel" in ma and "fuel" in mb and fuel_differs(ma["fuel"], mb["fuel"]):
        found.append(d("fuel", f"fuel {ma['fuel']} != {mb['fuel']} (beyond {FUEL_TOLERANCE})"))
    return found


def _tally(suite: dict) -> tuple[int, int]:
    """A unit suite's total and its failing count."""
    total = suite.get("total", 0)
    return total, total - suite.get("passed", 0) - suite.get("skipped", 0)


def _items(name: str, a: list[str], b: list[str]) -> list[Diff]:
    sa, sb = set(a), set(b)
    return [
        Diff(f"{name}: {x} {SIDE[side]}", name, x, side)
        for side, xs in ((0, sa - sb), (1, sb - sa))
        for x in sorted(xs)
    ]


def compare(a: dict, b: dict, rows: str = "all") -> tuple[list[Diff], list[str]]:
    """Every difference between two records that could change a verdict, and the notes: what
    was not compared, and why. With `rows="release"`, the release-tier rows alone."""
    va, vb = view(a), view(b)
    release = va.release | vb.release
    # A record of the normal tier never ran a release-tier row: nothing to compare it with.
    untiered = release if "normal" in (va.tier, vb.tier) else set()
    keep = (lambda n: n in release) if rows == "release" else (lambda n: True)  # noqa: E731
    found: list[Diff] = []
    unrun: Counter[str] = Counter()
    across: Counter[str] = Counter()
    unheld: Counter[str] = Counter()
    not_tiered = 0
    for node in sorted(va.names | vb.names):
        if not keep(node):
            continue
        if node in untiered:
            not_tiered += 1
        elif node not in vb.names:
            found.append(Diff(f"{node}: {SIDE[0]}", "only", node, 0))
        elif node not in va.names:
            found.append(Diff(f"{node}: {SIDE[1]}", "only", node, 1))
        elif node in va.unrun or node in vb.unrun:
            unrun[va.unrun.get(node) or vb.unrun[node]] += 1
        else:
            ca, cb = va.checks[node], vb.checks[node]
            pa, pb = va.platform[node], vb.platform[node]
            fuel_both = "fuel" in (ca.get("metrics") or {}) and "fuel" in (cb.get("metrics") or {})
            held = node not in va.unheld and node not in vb.unheld
            if fuel_both and not held:
                unheld[pa if node in va.unheld else pb] += 1
            elif fuel_both and pa != pb:
                across[f"{pa} against {pb}"] += 1
            found += _check(node, ca, cb, held and pa == pb)
    for node, text in sorted({**vb.elsewhere, **va.elsewhere}.items()):
        if not keep(node) or node in untiered:
            continue
        found.append(Diff(text, "elsewhere", node))  # no claim explains it
        if node in va.elsewhere and node in vb.elsewhere and vb.elsewhere[node] != text:
            found.append(Diff(vb.elsewhere[node], "elsewhere", node))
    shown = [n for n in va.deselected if keep(n) and n not in untiered]
    found += _items(
        "deselected", shown, [n for n in vb.deselected if keep(n) and n not in untiered]
    )
    notes = []
    if not_tiered:
        notes.append(
            f"release-tier rows not compared: {not_tiered} (one record judged the normal tier)"
        )
    if rows == "release":
        pass  # rows alone: the files and the unit suite belong to the whole run
    elif va.suite != vb.suite:
        # A release ran on other hosts: a unit test may skip there and pass here.
        if is_release(a) != is_release(b) and _tally(va.suite) == _tally(vb.suite):
            notes.append(
                f"unit tests skipped on one host and passed on the other: {va.suite!r} against "
                f"{vb.suite!r} (the same total, the same failing)"
            )
        else:
            found.append(Diff(f"suite: {va.suite!r} != {vb.suite!r}", "suite"))
    if rows != "release":
        found += _items("collected_files", va.collected_files, vb.collected_files)
    if sorted(va.foreign) != sorted(vb.foreign):  # the one meta field that decides a verdict
        found.append(Diff(f"meta.foreign: {va.foreign!r} != {vb.foreign!r}", "foreign"))
    if unrun:
        why = ", ".join(f"{k} {n}" for k, n in sorted(unrun.items()))
        notes.append(f"not run on any system in the release: {sum(unrun.values())} ({why})")
    if unheld:
        why = ", ".join(f"{k} {n}" for k, n in sorted(unheld.items()))
        notes.append(f"release fuel not from darwin, not compared: {sum(unheld.values())} ({why})")
    if across:
        why = "; ".join(sorted(across))
        notes.append(f"fuel not compared across platforms: {sum(across.values())} ({why})")
    return found, notes


def differences(a: dict, b: dict, rows: str = "all") -> list[str]:
    """Every difference between two run records that could change a verdict."""
    return [d.text for d in compare(a, b, rows)[0]]


def notes(a: dict, b: dict) -> list[str]:
    return compare(a, b)[1]


# ---------------------------------------------------------------------------------------------
# Claim lists

LISTS = ("new", "retired", "changed", "passes", "grows")
KEYS = frozenset({"spec", "growth", "units", *LISTS})


@dataclass
class Claim:
    spec: str
    new: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    grows: list[str] = field(default_factory=list)
    growth: str = ""
    units: int = 0


def load_claims(path: Path) -> list[Claim]:
    """The claims of a claim list, or of every .toml file in a folder of them, by file name."""
    if Path(path).is_dir():
        return [c for p in sorted(Path(path).glob("*.toml")) for c in load_claims(p)]
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise ClaimError(f"{path}: not a readable TOML file ({e})") from e
    if set(data) - {"claim"} or not isinstance(data.get("claim", []), list):
        raise ClaimError(f"{path}: only [[claim]] tables, found {sorted(data)}")
    out = []
    for n, c in enumerate(data.get("claim", []), 1):
        where = f"{path}: claim {n}"
        unknown = sorted(set(c) - KEYS)
        if unknown:
            raise ClaimError(f"{where}: keys the shape does not name: {', '.join(unknown)}")
        if not isinstance(c.get("spec"), str) or not c["spec"]:
            raise ClaimError(f"{where}: spec, a string, is required")
        for k in LISTS:
            v = c.get(k, [])
            if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
                raise ClaimError(f"{where} ({c['spec']}): {k} is a list of strings")
        if not isinstance(c.get("growth", ""), str):
            raise ClaimError(f"{where} ({c['spec']}): growth is a string")
        if c.get("grows") and not c.get("growth"):
            raise ClaimError(f"{where} ({c['spec']}): grows needs growth, its reason")
        if type(c.get("units", 0)) is not int:
            raise ClaimError(f"{where} ({c['spec']}): units is a whole number")
        out.append(Claim(**c))
    return out


def _names(entry: str, key: str) -> bool:
    """Whether a claimed entry names a check or file: exactly, as the check's file, or by a
    trailing `*` prefix."""
    if entry.endswith("*"):
        return key.startswith(entry[:-1])
    return key == entry or ("::" not in entry and key.split("::", 1)[0] == entry)


def _file_named(entry: str, file: str) -> bool:
    """Whether a claimed entry names a collected file: the file, a check in it, or a prefix."""
    if entry.endswith("*"):
        return file.startswith(entry[:-1])
    return entry.split("::", 1)[0] == file


def _explains(c: Claim, d: Diff) -> list[str]:
    """The claimed entries of `c` that explain `d` (empty when none does)."""
    if d.kind == "only":
        kind = "new" if d.side == 1 else "retired"
        return [f"{kind} {e}" for e in getattr(c, kind) if _names(e, d.key)]
    if d.kind == "collected_files":
        kind = "new" if d.side == 1 else "retired"
        return [f"{kind} {e}" for e in getattr(c, kind) if _file_named(e, d.key)]
    if d.kind == "deselected":
        return [f"changed {e}" for e in c.changed if _names(e, d.key)]
    if d.kind == "field":
        kinds = {"fuel": ("grows",), "bytes": ("grows",), "ignores": ("grows",)}
        kinds["passes"] = ("passes",)
        kinds["facts"] = ("changed", "passes")
        for kind in kinds.get(d.name, ("changed",)):
            hit = [f"{kind} {e}" for e in getattr(c, kind) if _names(e, d.key)]
            if hit:
                return hit
    return []


def _suite_explained(a: dict, b: dict, units: int) -> bool:
    (ta, fa), (tb, fb) = _tally(a), _tally(b)
    return tb - ta == units and fa == fb


def explain(
    a: dict,
    b: dict,
    claims: list[Claim],
    drop: frozenset[str] | set[str] = frozenset(),
    rows: str = "all",
) -> tuple[list[str], list[str]]:
    """(the differences no claim explains, the notes: the counts per spec, the unseen claims)."""
    claims = [c for c in claims if c.spec not in drop]
    found, notes_ = compare(a, b, rows)
    seen: set[tuple[str, str]] = set()
    per_spec: Counter[str] = Counter()
    left = []
    units = sum(c.units for c in claims)
    for d in found:
        if d.kind == "suite":
            hit = [(c.spec, "units") for c in claims if c.units]
            if not _suite_explained(view(a).suite, view(b).suite, units):
                hit = []
        else:
            hit = [(c.spec, e) for c in claims for e in _explains(c, d)]
        if not hit:
            left.append(d.text)
        seen.update(hit)
        per_spec.update({spec for spec, _ in hit})
    unseen = [
        f"{c.spec} {kind} {e}"
        for c in claims
        for kind in LISTS
        for e in getattr(c, kind)
        if (c.spec, f"{kind} {e}") not in seen
    ]
    if per_spec:
        counts = " · ".join(f"{s} {n}" for s, n in sorted(per_spec.items()))
        notes_.append(f"explained by claims: {counts}")
    notes_ += [f"claimed, not seen: {u}" for u in unseen]
    return left, notes_


def unexplained(
    a: dict,
    b: dict,
    claims: list[Claim],
    drop: frozenset[str] | set[str] = frozenset(),
    rows: str = "all",
) -> list[str]:
    return explain(a, b, claims, drop, rows)[0]


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="sameness.py")
    ap.add_argument("--claims", type=Path, help="a claim list, or a folder of them")
    ap.add_argument("--except", dest="drop", action="append", default=[], metavar="SPEC")
    ap.add_argument("--tier-rows", choices=["release"], help="compare the release-tier rows alone")
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args(argv)
    if args.drop and not args.claims:
        ap.error("--except drops a spec's claims, so it needs --claims")
    try:
        a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (args.a, args.b))
        claims = load_claims(args.claims) if args.claims else None
        rows = args.tier_rows or "all"
        if claims is None:
            found, notes_ = compare(a, b, rows)
            lines = [d.text for d in found]
        else:
            lines, notes_ = explain(a, b, claims, set(args.drop), rows)
    except (OSError, ValueError) as e:  # NotComparable, ClaimError, and JSON errors are ValueError
        print(f"sameness.py: {e}", file=sys.stderr)
        return 2
    for line in notes_:
        print(f"note: {line}", file=sys.stderr)
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
