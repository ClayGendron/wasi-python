"""The two tiers of an upstream family: which tests each tier runs, and the rules that keep every
test in a tier.

The normal tier runs at every check; the release tier only before a publication. Together they
are every test the family selects, and nothing is left out of both. A pytest family says which
tests are release-tier in two ways, each with its reason in the family's TOML:

- by upstream's markers: `release_marker` is the `-m` expression its marker release groups run,
  beside the normal groups' `marker`. Over every assignment of true and false to the names the
  expressions use, the two never hold together, and one of them always holds unless the test is
  excluded by `excluded_marker`, which may name only capabilities the guest lacks (`EXCLUDABLE`);
- by the project's keyword selections, `[[release_select]]`: within the named files, a test that
  is not marker-selected and matches the keyword is release-tier. A normal group over such a file
  runs `-k "not (K)"`, a keyword release group `-k "K"`, K being the OR of the entries naming
  that file, so within the normal marker each test matches K or does not, never both.

A third way is a package's whole suite: a **smoke family** keeps, in the normal tier, a small
smoke group per package (each normal group says why in its `smoke` key) and runs every other
staged test file in path release groups, whole, with no `-m`, ignoring the smoke files under their
paths (the owner, 2026-10-21: "we need to have fast tests and slow tests. We only run slow tests
when we are trying to publish to pypi"). Every staged test file is under exactly one smoke path or
one path release group.

CPython's family says it by regrtest's resources (`regrtest.py`): its release lists name every
test a normal group skips for the `cpu` or `largefile` resource, and its normal groups prove the
lists on every run.
"""

from __future__ import annotations

import itertools
import re

from harness import scoreboard

# The markers a family may leave out of both tiers: each a capability the guest does not have
# (no network, no database server), as README.md says. Any other name is a test left out, which
# the owner ruled out: every test runs in one tier or the other.
EXCLUDABLE = ("network", "db")
KINDS = ("marker", "keyword", "path")
# A smoke family's smoke groups are small by rule, so the normal tier cannot grow a second suite
# unnoticed: their measured fuel sums to at most this. A larger selection is a judge change.
SMOKE_BUDGET = 500 * 10**9
TEST_FILE = re.compile(r"(?:.*/)?(?:test_[^/]*|[^/]*_test)\.py")
# pytest's identifier, as its expression scanner reads one
IDENT = re.compile(r"(?:\w|:|\+|-|\.|\[|\]|\\|/)+")
OPERATORS = frozenset({"and", "or", "not", "True", "False"})
MAX_NAMES = 12  # 4,096 assignments: far more than a marker expression uses


def names(expr: str) -> set[str]:
    return {n for n in IDENT.findall(expr) if n not in OPERATORS}


def _compile(expr: str):
    from _pytest.mark.expression import Expression

    return Expression.compile(expr)


def _truth(pkg: str, exprs: dict[str, str]) -> tuple[dict, list[str]]:
    """Each expression compiled, or the errors that stop the table."""
    compiled, errors = {}, []
    for key, expr in exprs.items():
        if not expr:
            continue
        if re.search(r"\w\s*\(", expr):
            errors.append(f"{pkg}: {key} {expr!r} uses a marker with keyword arguments")
            continue
        try:
            compiled[key] = _compile(expr)
        except Exception as e:  # noqa: BLE001 (pytest's ParseError, whatever its module)
            errors.append(f"{pkg}: {key} {expr!r} does not parse: {str(e).splitlines()[0]}")
    return compiled, errors


def table_errors(pkg: str, marker: str, release: str, excluded: str) -> list[str]:
    """The truth table: `marker and release` never holds; `marker or release` holds exactly when
    `excluded` does not (always, without one)."""
    exprs = {"marker": marker, "release_marker": release, "excluded_marker": excluded}
    compiled, errors = _truth(pkg, exprs)
    for n in sorted(names(excluded) - set(EXCLUDABLE)):
        errors.append(f"{pkg}: excluded_marker names {n}, which is not one of {EXCLUDABLE}")
    if errors:
        return errors
    used = sorted(set().union(*(names(e) for e in exprs.values())))
    if len(used) > MAX_NAMES:
        return [f"{pkg}: the markers use {len(used)} names, more than {MAX_NAMES}"]

    def holds(key: str, value: dict) -> bool:
        if key not in compiled:  # an empty expression selects every test, or excludes none
            return key != "excluded_marker"

        def match(name: str, **kwargs) -> bool:
            if kwargs:
                raise ValueError(name)
            return value.get(name, False)

        return compiled[key].evaluate(match)

    for bits in itertools.product((False, True), repeat=len(used)):
        value = dict(zip(used, bits, strict=True))
        m, r = holds("marker", value), holds("release_marker", value)
        x = holds("excluded_marker", value)
        shown = ", ".join(f"{k}={v}" for k, v in value.items()) or "no names"
        if m and r:
            return [f"{pkg}: marker and release_marker overlap ({shown})"]
        if (m or r) == x:
            what = "is not every test" if not x else "selects an excluded test"
            return [f"{pkg}: marker or release_marker {what} ({shown})"]
    return []


# ---------------------------------------------------------------------------------------------
# What a group runs


def _covers(path: str, file: str) -> bool:
    return file == path or file.startswith(path.rstrip("/") + "/")


def keyword_of(cfg, group) -> str | None:
    """K for a group's files: the OR of the keywords of the entries naming them, or None."""
    entries = [e for e in cfg.release_select if any(f in group.paths for f in e.files)]
    if not entries:
        return None
    if len(entries) == 1:
        return entries[0].keyword
    return " or ".join(f"({e.keyword})" for e in entries)


def is_smoke_family(cfg) -> bool:
    return any(g.smoke is not None for g in cfg.groups.values())


def smoke_paths(cfg) -> list[str]:
    return [p for g in cfg.groups.values() if g.smoke is not None for p in g.paths]


def kind_of(cfg, group) -> str:
    """A pytest release group's kind: `release_by`, or the family's one kind."""
    if group.release_by:
        return group.release_by
    if is_smoke_family(cfg):
        return "" if cfg.release_marker else "path"
    if cfg.release_marker and not cfg.release_select:
        return "marker"
    if cfg.release_select and not cfg.release_marker:
        return "keyword"
    return ""


def marker_of(cfg, group) -> str:
    """The `-m` expression a group runs: a path release group runs every test of its paths."""
    if group.tier == "release" and kind_of(cfg, group) == "marker":
        return cfg.release_marker
    if group.tier == "release" and kind_of(cfg, group) == "path":
        return ""
    return cfg.marker


def is_node(path: str) -> bool:
    """A node-id group's path: a file and one test in it (`file.py::test`)."""
    return "::" in path


def node_deselects(cfg, group) -> list[str]:
    """The node ids other groups run alone (a test too big for any group) that lie under this path
    release group's paths: it deselects them, so each runs once."""
    if group.tier != "release" or kind_of(cfg, group) != "path":
        return []
    return [
        p
        for g in cfg.groups.values()
        if g.name != group.name
        for p in g.paths
        if is_node(p)
        and not any(is_node(q) for q in group.paths)
        and any(_covers(q, p.split("::", 1)[0]) for q in group.paths)
    ]


def is_test_file(cfg, member: str) -> bool:
    """A staged test file: upstream's own `python_files` patterns where the family's .ini names
    them, else pytest's default (`test_*.py`, `*_test.py`)."""
    import fnmatch

    patterns = getattr(getattr(cfg, "keys", None), "python_files", ())
    if not patterns:
        return bool(TEST_FILE.fullmatch(member))
    name = member.rsplit("/", 1)[-1]
    if name in ("conftest.py", "__init__.py"):
        return False  # pytest collects neither as a test module, whatever the patterns
    return any(fnmatch.fnmatch(name, p) for p in patterns if p.endswith(".py"))


def smoke_ignores(cfg, group) -> list[str]:
    """The smoke paths under a path release group's paths, which it leaves to the normal tier."""
    if group.tier != "release" or kind_of(cfg, group) != "path":
        return []
    return [s for s in smoke_paths(cfg) if any(_covers(p, s) and p != s for p in group.paths)]


def tier_filter(cfg, group) -> str | None:
    """The `-k` expression the tier adds: `not (K)` for a normal group over an entry's file, K for
    a keyword release group, None otherwise."""
    k = keyword_of(cfg, group)
    if k is None or kind_of(cfg, group) == "path":
        return None
    if group.tier == "release":
        return k if kind_of(cfg, group) == "keyword" else None
    return f"not ({k})"


def keyword_arg(cfg, group, split_keyword: str | None) -> str | None:
    """The one `-k` a group's argv carries: the tier's filter joined to its split's expression."""
    f = tier_filter(cfg, group)
    if f is None:
        return split_keyword
    if split_keyword is None:
        return f
    return f"({f}) and ({split_keyword})"


# ---------------------------------------------------------------------------------------------
# The rules


def rule_errors(pkg: str, cfg, members: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    errors += smoke_errors(pkg, cfg, members)
    errors += item_errors(pkg, cfg)
    errors += node_errors(pkg, cfg)
    groups = list(cfg.groups.values())
    release = [g for g in groups if g.tier == "release"]
    for g in groups:
        if g.tier not in scoreboard.TIERS:
            errors.append(f"{pkg}: group {g.name}: tier {g.tier!r} is neither normal nor release")
        if g.release_by and (g.tier != "release" or g.release_by not in KINDS):
            errors.append(f"{pkg}: group {g.name}: release_by {g.release_by!r} on a {g.tier} group")
    for g in groups:
        if g.selects_nothing and (g.tier != "release" or kind_of(cfg, g) != "marker"):
            errors.append(f"{pkg}: group {g.name}: only a marker release group may select nothing")
    for g in release:
        if g.measured is None:
            errors.append(f"{pkg}: release group {g.name} records no measured fuel")
        else:
            from harness import packages

            if g.fuel > packages.rule_cap(g.measured):
                errors.append(
                    f"{pkg}: release group {g.name}'s cap {g.fuel:,} is above 1.5 times its "
                    f"measured {g.measured:,} ({packages.rule_cap(g.measured):,})"
                )
    if release:
        errors += [
            f"{pkg}: trap {t.id} names no group of its family"
            for t in cfg.traps
            if t.group not in cfg.groups
        ]
    if cfg.runner == "regrtest":
        errors += [
            f"{pkg}: release group {g.name} is of no named kind (no list of ids)"
            for g in release
            if not [e for e in cfg.release_entries if e.release_group == g.name]
        ]
        return errors
    if cfg.release_marker or cfg.excluded_marker:
        errors += table_errors(pkg, cfg.marker, cfg.release_marker, cfg.excluded_marker)
    if cfg.excluded_marker and not (cfg.excluded_reason.strip() and cfg.excluded_closes_with):
        errors.append(f"{pkg}: excluded_marker needs excluded_reason and excluded_closes_with")
    errors += _select_errors(pkg, cfg)
    for g in release:
        kind = kind_of(cfg, g)
        if not kind and cfg.release_marker and (cfg.release_select or is_smoke_family(cfg)):
            errors.append(f"{pkg}: release group {g.name} names no release_by; its family has both")
        elif not kind or (kind == "marker" and not cfg.release_marker):
            errors.append(f"{pkg}: release group {g.name} is of no named kind")
        elif kind == "path" and not is_smoke_family(cfg):
            errors.append(
                f"{pkg}: release group {g.name} is of no named kind (a path group "
                "belongs to a smoke family)"
            )
        elif kind == "keyword" and not cfg.release_select:
            errors.append(f"{pkg}: release group {g.name} is of no named kind")
    normal_paths = {p for g in groups if g.tier == "normal" for p in g.paths}
    by_kind = {k: [g for g in release if kind_of(cfg, g) == k] for k in KINDS}
    if cfg.release_marker:
        have = {p for g in by_kind["marker"] for p in g.paths}
        if have != normal_paths:
            errors.append(
                f"{pkg}: the marker release groups' paths are not the normal groups' paths "
                f"(+{len(have - normal_paths)} -{len(normal_paths - have)})"
            )
    if cfg.release_select:
        files = {f for e in cfg.release_select for f in e.files}
        have = {p for g in by_kind["keyword"] for p in g.paths}
        if have != files:
            errors.append(
                f"{pkg}: the keyword release groups' paths are not the entries' files "
                f"(+{len(have - files)} -{len(files - have)})"
            )
    if getattr(cfg, "keys", None) is not None:
        errors += split_tier_errors(pkg, cfg)
    split_of = getattr(getattr(cfg, "keys", None), "split_of", lambda _: None)
    for kind, mine in by_kind.items():
        seen: dict[str, str] = {}
        for g in mine:
            for p in g.paths:
                other = seen.get(p)
                split = split_of(g.name)
                if other and not (split and split.file == p and other in split.groups):
                    errors.append(f"{pkg}: {p} is in two {kind} release groups: {other}, {g.name}")
                seen[p] = g.name
    return errors


def smoke_errors(pkg: str, cfg, members: set[str] | None) -> list[str]:
    """A smoke family's rules: every normal group says why it is the smoke, no path group lies in
    a smoke path, the smoke stays small, and (with the tarball) every staged test file is in
    exactly one tier."""
    errors: list[str] = []
    for g in cfg.groups.values():
        if g.smoke is not None and g.tier != "normal":
            errors.append(f"{pkg}: group {g.name}: smoke on a {g.tier} group")
    if not is_smoke_family(cfg):
        return errors
    for g in cfg.groups.values():
        if g.tier != "normal":
            continue
        if g.smoke is None:
            errors.append(f"{pkg}: normal group {g.name} carries no smoke, in a smoke family")
        elif not g.smoke.strip():
            errors.append(f"{pkg}: group {g.name}: smoke is empty; it says why in words")
    if cfg.release_select:
        errors.append(f"{pkg}: a smoke family has no [[release_select]]; it moves whole paths")
    smoke = smoke_paths(cfg)
    total = sum(g.measured or 0 for g in cfg.groups.values() if g.smoke is not None)
    if total > SMOKE_BUDGET:
        errors.append(
            f"{pkg}: the smoke groups measure {total / 1e9:.1f} G, past the 500 G smoke budget"
        )
    path_groups = [
        g for g in cfg.groups.values() if g.tier == "release" and kind_of(cfg, g) == "path"
    ]
    split_of = getattr(getattr(cfg, "keys", None), "split_of", lambda _: None)
    for g in path_groups:
        for p in g.paths:
            if any(_covers(s, p) for s in smoke):
                errors.append(f"{pkg}: path release group {g.name}: {p} lies in a smoke path")
    if members is None:
        return errors
    out = {
        f for n in cfg.not_selected for f in n.files if "::" not in f
    }  # a test alone leaves its file
    keys = getattr(cfg, "keys", None)
    folders = (*getattr(keys, "stage_folders", ()), *getattr(keys, "support_files", ()))
    staged = sorted(
        m
        for m in members
        if is_test_file(cfg, m)
        and any(_covers(f, m) for f in folders)
        and not any(_covers(o, m) for o in out)
    )
    for s in smoke:
        if not any(_covers(s, m) for m in staged):
            errors.append(f"{pkg}: smoke path {s} holds no staged test file")
    for m in staged:
        if any(_covers(s, m) for s in smoke):
            continue
        holders = {g.name for g in path_groups if any(_covers(p, m) for p in g.paths)}
        split = {split_of(n) for n in holders}
        if not holders:
            errors.append(f"{pkg}: {m} is in no tier: under no smoke path or path release group")
        elif len(holders) > 1 and not (len(split) == 1 and None not in split):
            errors.append(
                f"{pkg}: {m} is under two path release groups: {', '.join(sorted(holders))}"
            )
    return errors


def _select_errors(pkg: str, cfg) -> list[str]:
    errors = []
    covered = [p for g in cfg.groups.values() for p in g.paths]
    entry_files: dict[str, set[int]] = {}
    for n, e in enumerate(cfg.release_select):
        where = f"{pkg}: release_select {e.keyword!r}"
        if not e.reason.strip():
            errors.append(f"{where} has no reason")
        if not e.keyword.strip():
            errors.append(f"{where}: an empty keyword")
        else:
            from harness import packages

            if (why := packages._keyword_errors(e.keyword)) is not None:
                errors.append(f"{where}: the keyword does not parse: {why}")
        if not e.files:
            errors.append(f"{where} names no file")
        for f in e.files:
            entry_files.setdefault(f, set()).add(n)
            if not any(_covers(p, f) for p in covered):
                errors.append(f"{where} names {f}, a file no group covers")
    # A group over an entry's file names it exactly, and only files with the same entries: the
    # group's one -k must mean the same in each of its files.
    for g in cfg.groups.values():
        held = [f for f in entry_files if any(_covers(p, f) for p in g.paths)]
        if not held:
            continue
        if g.tier == "release" and kind_of(cfg, g) == "marker":
            continue  # it runs the release marker over the whole family, with no -k
        if (
            any(p not in entry_files for p in g.paths)
            or len({frozenset(entry_files[p]) for p in g.paths}) != 1
        ):
            errors.append(
                f"{pkg}: group {g.name} holds an entry's file beside others: a group over such a "
                "file names only files with the same entries"
            )
    return errors


def split_tier_errors(pkg: str, cfg) -> list[str]:
    """A split's groups share one tier and one kind; a file carries at most one split per tier
    and kind."""
    errors = []
    seen: set[tuple[str, str, str]] = set()
    for s in cfg.keys.splits:
        tiers_ = {
            (
                cfg.groups[g].tier,
                kind_of(cfg, cfg.groups[g]) if cfg.groups[g].tier == "release" else "",
            )
            for g in s.groups
            if g in cfg.groups
        }
        if len(tiers_) > 1:
            errors.append(f"{pkg}: split of {s.file} mixes tiers or kinds")
            continue
        for tier, kind in tiers_:
            if (s.file, tier, kind) in seen:
                errors.append(f"{pkg}: {s.file} carries two splits of one tier and kind")
            seen.add((s.file, tier, kind))
    return errors


def item_errors(pkg: str, cfg) -> list[str]:
    """An item group's units are in exactly one group: no doctest file, module of
    `module_functions` or docstring module (a named module, or one a named package covers) is
    run by two groups."""
    items = getattr(getattr(cfg, "keys", None), "items", {})
    errors = []
    seen: dict[tuple[str, str], str] = {}
    for name, it in items.items():
        units = [("file", f) for f, _ in it.doctest_files]
        units += [("functions", m) for m in it.module_functions]
        for kind, u in units:
            other = seen.get((kind, u))
            if other is not None:
                errors.append(f"{pkg}: {u} is in two item groups: {other}, {name}")
            seen[(kind, u)] = name
    docs = [(name, m, False) for name, it in items.items() for m in it.docstring_modules]
    docs += [(name, m, True) for name, it in items.items() for m in it.docstring_packages]

    def covers(entry: str, is_package: bool, other: str) -> bool:
        return other == entry or (is_package and other.startswith(entry + "."))

    for i, (a, ea, pa) in enumerate(docs):
        for b, eb, pb in docs[i + 1 :]:
            if a != b and (covers(ea, pa, eb) or covers(eb, pb, ea)):
                errors.append(f"{pkg}: the docstrings of {ea} and {eb} are in two groups: {a}, {b}")
    for name in items:
        g = cfg.groups.get(name)
        if g is not None and g.tier == "release" and kind_of(cfg, g) != "path":
            errors.append(f"{pkg}: item group {name} is a release group of no named kind")
    return errors


def node_errors(pkg: str, cfg) -> list[str]:
    """A node-id group runs one test too big for any group: its file lies in exactly one path
    release group's paths, and that group deselects exactly it."""
    errors = []
    path_groups = [
        g
        for g in cfg.groups.values()
        if g.tier == "release"
        and kind_of(cfg, g) == "path"
        and not any(is_node(p) for p in g.paths)
    ]
    for g in cfg.groups.values():
        for p in g.paths:
            if not is_node(p):
                continue
            if g.tier != "release" or any(not is_node(q) for q in g.paths):
                errors.append(
                    f"{pkg}: group {g.name}: a node id runs in a release group of node ids"
                )
            file = p.split("::", 1)[0]
            holders = [h.name for h in path_groups if any(_covers(q, file) for q in h.paths)]
            if len(holders) != 1:
                errors.append(
                    f"{pkg}: node id {p} lies in {len(holders)} path release groups' paths, not one"
                )
    return errors
