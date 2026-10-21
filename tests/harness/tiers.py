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
KINDS = ("marker", "keyword")
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


def kind_of(cfg, group) -> str:
    """A pytest release group's kind: `release_by`, or the family's one kind."""
    if group.release_by:
        return group.release_by
    if cfg.release_marker and not cfg.release_select:
        return "marker"
    if cfg.release_select and not cfg.release_marker:
        return "keyword"
    return ""


def marker_of(cfg, group) -> str:
    """The `-m` expression a group runs."""
    if group.tier == "release" and kind_of(cfg, group) == "marker":
        return cfg.release_marker
    return cfg.marker


def tier_filter(cfg, group) -> str | None:
    """The `-k` expression the tier adds: `not (K)` for a normal group over an entry's file, K for
    a keyword release group, None otherwise."""
    k = keyword_of(cfg, group)
    if k is None:
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


def rule_errors(pkg: str, cfg) -> list[str]:
    errors: list[str] = []
    groups = list(cfg.groups.values())
    release = [g for g in groups if g.tier == "release"]
    for g in groups:
        if g.tier not in scoreboard.TIERS:
            errors.append(f"{pkg}: group {g.name}: tier {g.tier!r} is neither normal nor release")
        if g.release_by and (g.tier != "release" or g.release_by not in KINDS):
            errors.append(f"{pkg}: group {g.name}: release_by {g.release_by!r} on a {g.tier} group")
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
        if not kind and cfg.release_marker and cfg.release_select:
            errors.append(f"{pkg}: release group {g.name} names no release_by; its family has both")
        elif not kind or (kind == "marker" and not cfg.release_marker):
            errors.append(f"{pkg}: release group {g.name} is of no named kind")
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
