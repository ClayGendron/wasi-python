"""Summarize the survey's streams: per group, outcomes, fuel, collection errors, deselections,
guard lines, and failures sorted into the draft's classes by their one-line reasons."""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
CLASSES = [
    ("no-processes", r"wasi does not support processes|does not support processes"),
    ("no-threads", r"can't start new thread|start new thread"),
    ("no-dup", r"Errno 58\]|Not supported"),
    ("no-mmap", r"mmap is unavailable"),
    ("shallow-recursion", r"Stack overflow \(used|RecursionError"),
    ("zip-no-source", r"could not get source code|source code not available"),
    ("wasm32-memory", r"MemoryError"),
    ("pillow-zlib-only", r"(decoder|encoder) \w+ not available"),
    ("wasi-iconv", r"unknown encoding|[Uu]nsupported encoding|LookupError"),
]


def classify(reason: str) -> str:
    for name, rx in CLASSES:
        if re.search(rx, reason):
            return name
    return "unclassified"


def main(groups):
    report = {}
    for g in groups:
        d = OUT / g
        res = json.loads((d / "result.json").read_text()) if (d / "result.json").is_file() else {}
        lines = (d / "stream.txt").read_text().splitlines() if (d / "stream.txt").is_file() else []
        counts = Counter()
        fails = defaultdict(list)
        xerr, desel, guard, last_s = [], [], [], None
        for line in lines:
            if line.startswith("R "):
                _, outcome, rest = line.split(" ", 2)
                node, _, reason = rest.partition(" -- ")
                counts[outcome] += 1
                if outcome in ("failed", "error"):
                    fails[classify(reason)].append((node, reason))
            elif line.startswith("X "):
                xerr.append(line[2:])
            elif line.startswith("D "):
                desel.append(line[2:])
            elif line.startswith("M "):
                guard.append(line[2:])
            elif line.startswith("S "):
                last_s = line[2:]
        ended = any(x.startswith("E ") for x in lines)
        report[g] = dict(
            fuel=res.get("fuel"), trapped=res.get("trapped"), trap_cause=res.get("trap_cause"),
            exit=res.get("exit_code"), ended=ended, last_started=None if ended else last_s,
            counts=dict(counts), collect_errors=xerr, deselected=len(desel),
            guard=[m for m in guard if "/tests/" not in m and "/Tests/" not in m
                   and "/testing/" not in m and "/doc/" not in m],
            classes={k: len(v) for k, v in fails.items()},
            unclassified_reasons=Counter(r[:90] for _, r in fails.get("unclassified", [])).most_common(25),
            members={k: sorted(n for n, _ in v) for k, v in fails.items()},
        )
    return report


if __name__ == "__main__":
    groups = sys.argv[1:] or sorted(p.name for p in OUT.iterdir() if (p / "result.json").is_file())
    r = main(groups)
    full = OUT.parent / "summary.json"
    full.write_text(json.dumps(r, indent=1))
    for g, v in r.items():
        print(f"== {g}: fuel {v['fuel']:,} exit {v['exit']} trapped {v['trapped']} ended {v['ended']}"
              if v["fuel"] else f"== {g}: no result")
        print("   counts", v["counts"], "deselected", v["deselected"])
        if v["last_started"]:
            print("   last started:", v["last_started"], v["trap_cause"])
        print("   classes", v["classes"])
        for e in v["collect_errors"][:12]:
            print("   X", e[:170])
        for m in v["guard"][:8]:
            print("   M", m[:170])
        for reason, n in v["unclassified_reasons"]:
            print(f"   ? {n:4d} {reason}")
