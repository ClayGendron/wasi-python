"""Derived figures and the results table, from results-*.json (EXECUTED) plus instances.py's RSS lines."""
import json, pathlib
S = pathlib.Path(__file__).resolve().parent.parent
R = {v: json.load(open(S / f"results-{v}.json")) for v in ["plain", "A", "D", "B", "C"]}
rss = {"plain": 7.9, "A": 9.6, "D": 24.0, "B": 41.3, "C": 58.1}           # MiB per live instance, instances.py
mods = {"plain": 36, "A": 70, "D": 186, "B": 588, "C": 772}               # modules.py
names = {"plain": "plain python.wasm", "A": "A stdlib only", "D": "D + numpy", "B": "B today (numpy, pandas)", "C": "C every package"}
jobs = ["pass", "hard_exit", "pure", "numpy", "pandas", "plot_fresh_cache", "plot_kept_cache"]
out = ["# Results: one snapshot per pre-import rule (EXECUTED, darwin-arm64, 2026-10-18)", "",
       "Fuel is wasmtime's guest instruction count through tests/harness/guest.py; the stdlib zip is the frozen set's",
       "(16ee747c…). Resident memory is ps RSS growth per live instance after `-c pass`, 8 instances (instances.py).", "",
       "| variant | pre-imported modules at start | snapshot bytes | deflated (level 6, as the wheel) | data section (heap+static) | memory min (pages / MiB) | resident per live instance (MiB) |", "|---|---|---|---|---|---|---|"]
for v in ["plain", "A", "D", "B", "C"]:
    r = R[v]
    out.append(f"| {names[v]} | {mods[v]} | {r['bytes']:,} | {r['deflated_level6']:,} | {r['data_section_bytes']:,} | {r['memory_min_pages']} / {r['memory_min_mib']} | {rss[v]} |")
out += ["", "| job (fuel) | " + " | ".join(names[v] for v in ["plain", "A", "D", "B", "C"]) + " |", "|---|---|---|---|---|---|"]
for j in jobs:
    out.append(f"| {j} | " + " | ".join(f"{R[v]['jobs'][j]['fuel']:,}" for v in ["plain", "A", "D", "B", "C"]) + " |")
out += ["", "| job (wall s, benchmark fact, one run) | " + " | ".join(names[v] for v in ["plain", "A", "D", "B", "C"]) + " |", "|---|---|---|---|---|---|"]
for j in jobs:
    out.append(f"| {j} | " + " | ".join(f"{R[v]['jobs'][j]['wall_s']}" for v in ["plain", "A", "D", "B", "C"]) + " |")
# per-module costs
def d(a, b, k): return R[b][k] - R[a][k]
rows = [("numpy (D - A)", "A", "D"), ("numpy + pandas (B - A)", "A", "B"), ("pandas alone (B - D)", "D", "B"), ("plot stack and the rest (C - B)", "B", "C")]
out += ["", "## Per pre-imported module (EXECUTED differences)", "", "| step | modules | heap bytes / module | `pass` fuel / module | resident KiB / module | snapshot bytes / module |", "|---|---|---|---|---|---|"]
for name, a, b in rows:
    m = mods[b] - mods[a]
    out.append(f"| {name} | {m} | {d(a,b,'data_section_bytes')/m:,.0f} | {(R[b]['jobs']['pass']['fuel']-R[a]['jobs']['pass']['fuel'])/m:,.0f} | {(rss[b]-rss[a])*1024/m:,.0f} | {d(a,b,'bytes')/m:,.0f} |")
out += ["", "## What a run pays or saves (EXECUTED differences)", ""]
pa, pb, pc = (R[v]['jobs']['pass']['fuel'] for v in "ABC")
out.append(f"- Pre-importing numpy and pandas (B over A) costs every run {pb-pa:,} fuel and {rss['B']-rss['A']:.1f} MiB resident; it saves a pandas run {R['A']['jobs']['pandas']['fuel']-R['B']['jobs']['pandas']['fuel']:,} and a numpy run {R['A']['jobs']['numpy']['fuel']-R['B']['jobs']['numpy']['fuel']:,}. Fuel break-even: pandas in more than {100*(pb-pa)/(R['A']['jobs']['pandas']['fuel']-R['B']['jobs']['pandas']['fuel']):.1f}% of runs.")
out.append(f"- Pre-importing the plot stack (C over B) costs every run {pc-pb:,} fuel and {rss['C']-rss['B']:.1f} MiB resident; it saves a plot run {R['B']['jobs']['plot_fresh_cache']['fuel']-R['C']['jobs']['plot_fresh_cache']['fuel']:,} (fresh font cache) or {R['B']['jobs']['plot_kept_cache']['fuel']-R['C']['jobs']['plot_kept_cache']['fuel']:,} (kept). Fuel break-even: a plot in more than {100*(pc-pb)/(R['B']['jobs']['plot_fresh_cache']['fuel']-R['C']['jobs']['plot_fresh_cache']['fuel']):.2f}% of runs.")
for v in "ABCD":
    h, p = R[v]['jobs']['hard_exit']['fuel'], R[v]['jobs']['pass']['fuel']
    out.append(f"- {names[v]}: `-c pass` {p:,}; the same with `os._exit(0)` {h:,}: finalization is {100*(p-h)/p:.1f}% of a bare run.")
out.append(f"- A over plain: `pass` {R['plain']['jobs']['pass']['fuel']/R['A']['jobs']['pass']['fuel']:.1f}x cheaper, pure script {R['plain']['jobs']['pure']['fuel']/R['A']['jobs']['pure']['fuel']:.2f}x, pandas {R['plain']['jobs']['pandas']['fuel']/R['A']['jobs']['pandas']['fuel']:.2f}x, numpy {R['plain']['jobs']['numpy']['fuel']/R['A']['jobs']['numpy']['fuel']:.2f}x.")
out.append(f"- A against B on a pandas run: {R['A']['jobs']['pandas']['fuel']/R['B']['jobs']['pandas']['fuel']:.0f}x the fuel; on a numpy run {R['A']['jobs']['numpy']['fuel']/R['B']['jobs']['numpy']['fuel']:.0f}x; on the pure script {R['B']['jobs']['pure']['fuel']/R['A']['jobs']['pure']['fuel']:.2f}x (B pays more).")
(S / "results.md").write_text("\n".join(out) + "\n"); print("\n".join(out))
