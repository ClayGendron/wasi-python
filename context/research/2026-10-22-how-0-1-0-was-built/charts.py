"""Draw the three SVG charts from rollup.json and tokens.json. Each SVG
carries its own light and dark colours (a prefers-color-scheme query).

Usage: uv run --no-project python -I charts.py rollup.json tokens.json <out-dir>
"""
import json, sys, os
from datetime import datetime, timedelta
rollup = json.load(open(sys.argv[1])); tokens = json.load(open(sys.argv[2])); outdir = sys.argv[3]
CLASSES = [('generate', 'Model generating'), ('build', 'Building'), ('judge', 'Judge and test runs'),
           ('ci', 'Waiting on CI'), ('other', 'Other tool calls'), ('owner', 'Waiting on the owner'),
           ('idle', 'Idle')]
FOLD = {'subagent': 'other'}
STYLE = """<style>
svg{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--c-generate:#2a78d6;--c-build:#eb6834;--c-judge:#1baf7a;--c-ci:#eda100;--c-other:#e87ba4;--c-owner:#008300;--c-idle:#ebeae6;--c-none:transparent;
--m-opus:#2a78d6;--m-fable:#eb6834;--m-other:#1baf7a}
@media (prefers-color-scheme: dark){svg{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--c-generate:#3987e5;--c-build:#d95926;--c-judge:#199e70;--c-ci:#c98500;--c-other:#d55181;--c-owner:#008300;--c-idle:#2e2e2b;
--m-opus:#3987e5;--m-fable:#d95926;--m-other:#199e70}}
text{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;fill:var(--ink2);font-size:12px}
.t{fill:var(--ink);font-size:15px;font-weight:600}.s{fill:var(--ink2);font-size:12px}.m{fill:var(--muted);font-size:11px}
.bg{fill:var(--bg)}.grid{stroke:var(--grid);stroke-width:1}.axis{stroke:var(--axis);stroke-width:1}
""" + ''.join(f'.f-{k}{{fill:var(--c-{k})}}' for k, _ in CLASSES) + """.f-opus{fill:var(--m-opus)}.f-fable{fill:var(--m-fable)}.f-mo{fill:var(--m-other)}
</style>"""
def svg(w, h, body, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-labelledby="title desc"><title id="title">{title}</title><desc id="desc">{desc}</desc>{STYLE}'
            f'<rect class="bg" width="{w}" height="{h}" rx="8"/>{body}</svg>')
def legend(x, y, items, gap=16):
    out = []; cx = x
    for k, label in items:
        out.append(f'<rect x="{cx}" y="{y-9}" width="10" height="10" rx="2" class="f-{k}"/><text x="{cx+14}" y="{y}">{label}</text>')
        cx += 14 + len(label) * 6.4 + gap
    return ''.join(out)
DAYS = ['2026-10-16', '2026-10-17', '2026-10-18', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22']
DAYNAME = {d: datetime.strptime(d, '%Y-%m-%d').strftime('%a %d') for d in DAYS}
# chart 1: the week as a band per day, hour by hour, coloured by the class with the most minutes
ph = rollup['per_hour']
W, left, top, cw, ch = 760, 70, 112, 26, 30
body = [f'<text class="t" x="20" y="30">The week, hour by hour</text>',
        f'<text class="s" x="20" y="50">Each cell is one clock hour, coloured by what took most of its minutes across every agent (UTC-4).</text>',
        legend(20, 74, CLASSES[:4]), legend(20, 94, CLASSES[4:])]
for r, d in enumerate(DAYS):
    y = top + r * (ch + 4)
    body.append(f'<text x="{left-10}" y="{y+ch/2+4}" text-anchor="end">{DAYNAME[d]}</text>')
    for h in range(24):
        key = f'{d} {h:02d}'
        mins = ph.get(key)
        x = left + h * (cw + 2)
        if not mins:
            body.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="3" fill="none" class="axis" stroke-dasharray="2 3"/>')
            continue
        folded = {}
        for k, v in mins.items():
            folded[FOLD.get(k, k)] = folded.get(FOLD.get(k, k), 0) + v
        dom = max(folded, key=folded.get)
        tip = ', '.join(f'{lbl} {folded[k]} min' for k, lbl in CLASSES if folded.get(k))
        body.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="3" class="f-{dom}"><title>{DAYNAME[d]} {h:02d}:00. {tip}</title></rect>')
yb = top + 7 * (ch + 4) + 14
for h in range(0, 24, 3):
    body.append(f'<text class="m" x="{left + h*(cw+2) + cw/2}" y="{yb}" text-anchor="middle">{h:02d}:00</text>')
body.append(f'<text class="m" x="{left}" y="{yb+20}">Dashed cells are outside the week (it began 12:53 on the 16th and ended 14:31 on the 22nd).</text>')
H1 = yb + 34
open(os.path.join(outdir, 'how-it-was-built-timeline.svg'), 'w').write(svg(W, H1, ''.join(body), 'The week, hour by hour',
     'A grid of seven days by twenty-four hours. Almost every hour is coloured: the model generating dominates the first three days, judge and test runs and waiting on CI dominate the last three.'))
# chart 2: tokens per hour, small multiples: all tokens by model, then output tokens
bhm = tokens['by_hour_model']; bho = tokens['by_hour_output']
start = datetime(2026, 10, 16, 12); hours = [start + timedelta(hours=i) for i in range(147)]
W2, L2, R2 = 760, 70, 20
pw = W2 - L2 - R2; bw = pw / len(hours)
def panel(y0, hgt, vals_fn, vmax, ticks, fmt, label):
    out = [f'<text class="s" x="20" y="{y0-10}">{label}</text>']
    for t in ticks:
        yy = y0 + hgt - hgt * t / vmax
        out.append(f'<line class="grid" x1="{L2}" x2="{W2-R2}" y1="{yy:.1f}" y2="{yy:.1f}"/><text class="m" x="{L2-6}" y="{yy+4:.1f}" text-anchor="end">{fmt(t)}</text>')
    for i, hr in enumerate(hours):
        key = hr.strftime('%Y-%m-%d %H'); x = L2 + i * bw
        ybase = y0 + hgt
        for cls, v in vals_fn(key):
            if v <= 0: continue
            hh = hgt * v / vmax
            out.append(f'<rect x="{x+0.4:.2f}" y="{ybase-hh:.2f}" width="{max(bw-0.8,0.5):.2f}" height="{hh:.2f}" class="{cls}"><title>{hr.strftime("%a %d %H:00")}: {fmt(v)}</title></rect>')
            ybase -= hh
    out.append(f'<line class="axis" x1="{L2}" x2="{W2-R2}" y1="{y0+hgt}" y2="{y0+hgt}"/>')
    return ''.join(out)
def by_model(key):
    d = bhm.get(key, {})
    opus = d.get('claude-opus-5-5', 0); fable = d.get('claude-fable-5-1', 0)
    return [('f-opus', opus), ('f-fable', fable), ('f-mo', sum(d.values()) - opus - fable)]
body = ['<text class="t" x="20" y="30">Tokens per hour</text>',
        '<text class="s" x="20" y="50">Every API call of every agent, by the hour it was made (UTC-4). Cache reads are most of the top panel.</text>',
        legend(20, 74, [('opus', 'Claude Opus'), ('fable', 'Fable'), ('mo', 'Other models')])]
body.append(panel(110, 150, by_model, 350e6, [0, 100e6, 200e6, 300e6], lambda v: f'{v/1e6:.0f}M', 'All tokens (input, output, cache read and cache write)'))
body.append(panel(310, 90, lambda k: [('f-opus', bho.get(k, 0))], 270e3, [0, 100e3, 200e3], lambda v: f'{v/1e3:.0f}K', 'Output tokens only (what the models wrote)'))
for i, hr in enumerate(hours):
    if hr.hour == 0 or i == 0:
        x = L2 + i * bw
        body.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" y1="100" y2="406"/><text class="m" x="{x+3:.1f}" y="422">{hr.strftime("%a %d")}</text>')
H2 = 440
open(os.path.join(outdir, 'how-it-was-built-tokens.svg'), 'w').write(svg(W2, H2, ''.join(body), 'Tokens per hour',
     'Bar charts of tokens per hour across the week. All tokens peak at about 337 million in the hour from 22:00 on 18 October; output tokens peak at about 260 thousand an hour.'))
# chart 3: hours per class, per day and the whole week (wall clock, dominant class per minute)
pd_ = rollup['per_day']
rows = [(DAYNAME[d], pd_[d]) for d in DAYS]
tot = {}
for _, v in rows:
    for k, m in v.items():
        tot[k] = tot.get(k, 0) + m
W3, L3, bh = 760, 110, 22
scale = (W3 - L3 - 60) / (24 * 60)
body = ['<text class="t" x="20" y="30">Where the hours went</text>',
        '<text class="s" x="20" y="50">Wall-clock hours per day, each minute given to the activity that took most agent time in it.</text>',
        legend(20, 74, CLASSES[:4]), legend(20, 94, CLASSES[4:])]
y = 116
for h in range(0, 25, 6):
    x = L3 + h * 60 * scale
    body.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{y-4}" y2="{y + 7*(bh+8)}"/><text class="m" x="{x:.1f}" y="{y + 7*(bh+8) + 14}" text-anchor="middle">{h} h</text>')
for name, v in rows:
    body.append(f'<text x="{L3-10}" y="{y+bh/2+4}" text-anchor="end">{name}</text>')
    x = L3
    folded = {}
    for k, m in v.items():
        folded[FOLD.get(k, k)] = folded.get(FOLD.get(k, k), 0) + m
    for k, lbl in CLASSES:
        m = folded.get(k, 0)
        if not m: continue
        w = m * scale
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w-2,0.5):.1f}" height="{bh}" rx="3" class="f-{k}"><title>{name}: {lbl} {m/60:.1f} h</title></rect>')
        x += w
    body.append(f'<text class="m" x="{x+4:.1f}" y="{y+bh/2+4}">{sum(folded.values())/60:.1f} h</text>')
    y += bh + 8
# the week as shares
y += 48
total = sum(tot.values())
body.append(f'<text class="s" x="20" y="{y-8}">The whole week, {total/60:.0f} hours</text>')
x = 20; wtot = W3 - 40
ft = {}
for k, m in tot.items():
    ft[FOLD.get(k, k)] = ft.get(FOLD.get(k, k), 0) + m
for k, lbl in CLASSES:
    m = ft.get(k, 0)
    if not m: continue
    w = wtot * m / total
    body.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w-2,0.5):.1f}" height="{bh+6}" rx="3" class="f-{k}"><title>{lbl}: {m/60:.1f} h ({100*m/total:.0f}%)</title></rect>')
    if w > 52:
        body.append(f'<text class="m" x="{x+2:.1f}" y="{y+bh+22}">{m/60:.0f} h</text>')
    x += w
H3 = y + bh + 36
open(os.path.join(outdir, 'how-it-was-built-hours.svg'), 'w').write(svg(W3, H3, ''.join(body), 'Where the hours went',
     'Stacked bars of wall-clock hours per day by activity, and one bar for the whole week: the model generating about a third, judge and test runs about a quarter, waiting on CI about a seventh, idle under a twentieth.'))
print({k: round(v/60, 1) for k, v in ft.items()}, round(total/60, 1))
