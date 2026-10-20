"""How the drafting `.out` files were made (the pre-build review's L4). A guest run's JSON (from
`wasi-python run`, as `run_checks.sh` writes it) becomes `<name>-guest-<which>.out`: one header line
`# main set SHA256SUMS f12cd25c, <which> binary: exit <n>, trapped <t>, stderr <repr>`, then the
`stdout` field unchanged. With `--crosstab NATIVE.out GUEST.out` it pairs singular_probe.py's case
lines and counts each (native, guest) outcome pair, with the cases of each pair.

Usage: uv run python to_out.py RUN.json OUT.out WHICH
       uv run python to_out.py --crosstab NATIVE.out GUEST.out
"""

import json
import sys


def to_out(src: str, dst: str, which: str, label: str = "main set SHA256SUMS f12cd25c") -> None:
    run = json.load(open(src))
    head = (
        f"# {label}, {which} binary: exit {run['exit_code']}, "
        f"trapped {run['trapped']}, stderr {run['stderr']!r}\n"
    )
    open(dst, "w").write(head + run["stdout"])


def cases(path: str) -> dict[str, str]:
    out = {}
    for line in open(path):
        if line.startswith(("case ", "named ")):
            key, _, got = line.rstrip().rpartition(" ")
            out[key] = got
    return out


def crosstab(native: str, guest: str) -> None:
    n, g = cases(native), cases(guest)
    pairs: dict[tuple[str, str], list[str]] = {}
    for key in n:
        pairs.setdefault((n[key], g[key]), []).append(key)
    for (a, b), keys in sorted(pairs.items()):
        print(f"native {a:7} guest {b:8} {len(keys):3d}  e.g. {', '.join(keys[:4])}")


if __name__ == "__main__":
    if sys.argv[1] == "--crosstab":
        crosstab(sys.argv[2], sys.argv[3])
    else:
        to_out(*sys.argv[1:5])  # RUN.json OUT.out WHICH [LABEL, for another set than main's]
