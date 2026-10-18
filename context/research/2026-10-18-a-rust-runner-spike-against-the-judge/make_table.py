"""Write comparison-table.txt from the result files in results/ (plain python3, no imports beyond
the stdlib)."""

import json
from pathlib import Path

HERE = Path(__file__).parent
R = HERE / "results"


def load(name):
    return json.loads((R / name).read_text())


def judge_table(name, title):
    d = load(name)
    lines = [title, f"  ({d['repeats']} runs per side per job; Rust binary {Path(d['binary']).name})", ""]
    head = f"  {'job':26} {'outputs':8} {'golden':7} {'exit/trap':12} {'fuel exact':10} {'py fuel (each run)':40} rust fuel (each run)"
    lines += [head, "  " + "-" * (len(head) + 10)]
    for r in d["rows"]:
        g = r["golden"]
        gold = "-" if g[0] is None else ("yes" if all(g) else "NO")
        how = r["trapped"][0] or f"exit {r['exit'][0]}"
        py = ",".join(str(x) for x in r["fuel_py"])
        rs = ",".join(str(x) for x in r["fuel_rs"])
        lines.append(
            f"  {r['job']:26} {'same' if r['outputs_match'] else 'DIFF':8} {gold:7} {how:12} "
            f"{'yes' if r['fuel_exact'] else 'no':10} {py:40} {rs}"
        )
    n = len(d["rows"])
    lines += ["", f"  outputs equal {sum(r['outputs_match'] for r in d['rows'])}/{n}; "
              f"fuel equal on every run {sum(r['fuel_exact'] for r in d['rows'])}/{n}", ""]
    return lines


def runner_table():
    d = load("runner-rs-49.0.3.json")
    lines = ["Table 3. Runner mode: the Rust spike (49.0.3) against wasi_python.run (wasmtime-py 49.0.0)",
             "  (wasmtime's own random and clocks; 2 runs per side; fuel cannot repeat exactly here)", ""]
    head = f"  {'job':28} {'outputs':8} {'exit/trap':12} {'py fuel':24} {'rust fuel':24} spread ppm (all / py / rust)"
    lines += [head, "  " + "-" * len(head)]
    for r in d["rows"]:
        how = r["trapped"][0] or f"exit {r['exit'][0]}"
        f = lambda xs: ",".join("-" if x is None else str(x) for x in xs)  # noqa: E731
        spread = (f"{r.get('fuel_spread_ppm')} / {r.get('fuel_spread_py_ppm')} / {r.get('fuel_spread_rs_ppm')}"
                  if r.get("fuel_spread_ppm") is not None else "- (fuel is None after a deadline)")
        lines.append(f"  {r['job']:28} {'same' if r['outputs_match'] else 'DIFF':8} {how:12} "
                     f"{f(r['fuel_py']):24} {f(r['fuel_rs']):24} {spread}")
    lines += ["", f"  outputs equal {sum(r['outputs_match'] for r in d['rows'])}/{len(d['rows'])}", ""]
    return lines


def same_root_table():
    rows = load("same-root-rs-49.0.0-drc.json")
    lines = ["Table 4. One root, three runs: judge driver, then the Rust spike (49.0.0, drc) twice on the same folder",
             ""]
    lines.append(f"  {'trial':5} {'job':22} {'py':12} {'rust 1st':12} {'rust 2nd':12} equal")
    for r in rows:
        lines.append(f"  {r['trial']:<5} {r['job']:22} {r['py']:<12} {r['rs_first']:<12} {r['rs_second']:<12} "
                     f"{'yes' if r['exact'] else 'no'}")
    lines += ["", f"  equal {sum(r['exact'] for r in rows)}/{len(rows)}", ""]
    return lines


def cwasm_table():
    lines = ["Table 5. Serialized modules (.cwasm): wasmtime-py 49.0.0 against the Rust spike", ""]
    for name, title in (("cwasm-default-collector.json", "crate-default collector (copying)"),
                        ("cwasm-drc-collector.json", "collector set to deferred reference counting (drc)")):
        d = load(name)
        lines.append(f"  Rust Config: {title}")
        lines.append(f"  {'side':10} {'config':12} {'module':9} {'compile ms':>10} {'bytes':>11}  sha256[:16]")
        for r in d["compiles"]:
            lines.append(f"  {r['side']:10} {r['cfg']:12} {r['which']:9} {r['ms']:>10} {r['bytes']:>11}  {r['sha']}")
        for r in d["loads"]:
            res = r.get("error") or f"exit {r['exit_code']}, fuel {r['fuel_used']}, stdout {r['stdout']!r}, load {r['module_ms']:.0f} ms"
            lines.append(f"  {r['side']} loads {r['loads']}: {res}")
        lines.append("")
    return lines


def probe_table():
    lines = ["Table 6. Probes for the plot_line gap on 49.0.3 (drc; 2 runs per side)", ""]
    for name in ("judge-rs-49.0.3-probe.json", "judge-rs-49.0.3-mpl-probe.json"):
        for r in load(name)["rows"]:
            lines.append(f"  {r['job']:24} py {r['fuel_py']}  rust {r['fuel_rs']}  rust - py {r['cross_delta']}")
    return lines + [""]


out = []
out += judge_table("judge-rs-49.0.3.json",
                   "Table 1. Judge mode: tests/harness/guest.py (wasmtime-py 49.0.0) against the Rust spike on wasmtime 49.0.3")
out += judge_table("judge-rs-49.0.0.json",
                   "Table 2a. Judge mode: the same, the Rust spike on wasmtime 49.0.0 (crate-default collector)")
out += judge_table("judge-rs-49.0.0-drc.json",
                   "Table 2b. Judge mode: the same, the Rust spike on wasmtime 49.0.0 with the drc collector")
out += judge_table("judge-rs-49.0.0-epoch.json",
                   "Table 2c. Judge mode, the Rust side with epoch_interruption on (the runner's Config), 49.0.0")
out += runner_table()
out += same_root_table()
out += cwasm_table()
out += probe_table()
(HERE / "comparison-table.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
