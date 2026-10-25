"""Print every suite's medians and minima from results/*.json, as the memo's tables read them.

    uv run --no-sync python context/research/2026-10-24-what-output-capture-costs/summarize.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def row(name: str, v: dict, indent: str) -> None:
    runs = ", ".join(f"{x:.1f}" for x in v["runs"])
    line = f"{indent}{name:30s} median {v['median_ms']:7.1f}  min {v['min_ms']:7.1f}  runs [{runs}]"
    print(line)
    for e in v.get("extra", [])[:1]:
        keep = ("callbacks", "inside_ms", "per_callback_us", "sizes", "first_four_thread_names", "os_threads")
        print(f"{indent}    {({k: e[k] for k in keep if k in e})}")


def main() -> None:
    for path in sorted(HERE.glob("results/*.json")):
        d = json.loads(path.read_text())
        meta = d.pop("_meta", {})
        print(f"== {path.stem}: repeats {meta.get('repeats')}, {meta.get('seconds')} s, {meta.get('python')} on {meta.get('platform')}")
        for k, v in d.items():
            if isinstance(v, dict) and "median_ms" in v:
                row(k, v, "  ")
            elif isinstance(v, dict):
                print(f"  [{k}]")
                for k2, v2 in v.items():
                    if isinstance(v2, dict) and "median_ms" in v2:
                        row(k2, v2, "    ")
                    else:
                        print(f"    {k2}: {v2}")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
