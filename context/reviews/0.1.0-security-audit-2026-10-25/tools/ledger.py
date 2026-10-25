"""Parent-side ledger helpers: coverage_id derivation per RECONNAISSANCE.md, and unit construction.

Usage: import from a driver script. Units are given as dicts with canonical_refs and labels;
make_unit() fills the bookkeeping fields in the 'planned' state.
"""
import json
import unicodedata
import sys

UNRESERVED = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _check_ref(s: str) -> str:
    if s != unicodedata.normalize("NFC", s):
        raise ValueError(f"not NFC: {s!r}")
    if s != s.strip() or not s:
        raise ValueError(f"empty or surrounding whitespace: {s!r}")
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Zl", "Zp") or ch in "​‌‍﻿":
            raise ValueError(f"forbidden code point in {s!r}")
    return s


def enc(s: str) -> str:
    _check_ref(s)
    out = []
    for b in s.encode("utf-8"):
        if b in UNRESERVED:
            out.append(chr(b))
        else:
            out.append("%%%02X" % b)
    return "".join(out)


def coverage_id(refs: dict) -> str:
    parts = [enc(refs["surface"]), enc(refs["boundary"]), enc(refs["subsystem"]), enc(refs["attack_class"])]
    if "lifecycle" in refs:
        parts.append(enc(refs["lifecycle"]))
    return "::".join(parts)


def make_unit(refs, surface, boundary, subsystem, attack_class, starting_paths,
              ordinary_block, companion_blocks, excluded_blocks, lifecycle=None):
    u = {
        "coverage_id": coverage_id(refs),
        "canonical_refs": refs,
        "surface": surface,
        "boundary": boundary,
        "subsystem": subsystem,
        "attack_class": attack_class,
        "starting_paths": starting_paths,
        "ordinary_attack_class_block": ordinary_block,
        "selected_companion_blocks": companion_blocks,
        "excluded_blocks": excluded_blocks,
        "prior_status": "none",
        "attempts": [],
        "wave": 1,
        "status": "planned",
        "agent_id": None,
        "reviewed_paths": [],
        "local_checks": [],
        "result_fingerprints": [],
        "unresolved": [],
    }
    if lifecycle:
        u["lifecycle"] = lifecycle
    return u


def write(units, path):
    ids = [u["coverage_id"] for u in units]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate coverage ids: {dupes}")
    units = sorted(units, key=lambda u: u["coverage_id"])
    with open(path, "w") as f:
        json.dump(units, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {len(units)} units to {path}")
