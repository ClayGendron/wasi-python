"""The owner's own messages to the lead sessions (typed prompts, queued
messages and AskUserQuestion answers), deduplicated, per day.

Usage: uv run --no-project python -I owner.py data.json owner.json [exclude-session ...]
"""
import json, sys, collections
from datetime import datetime, timedelta, timezone
LOCAL = timezone(timedelta(hours=-4))
P = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
data = json.load(open(sys.argv[1])); exclude = set(sys.argv[3:])
msgs = []
for f in data:
    if f['parent'] or f['session'] in exclude:
        continue
    for ts, txt in f['humans']:
        msgs.append((P(ts), txt.strip(), f['session']))
msgs.sort()
out = []
for t, txt, s in msgs:
    if out and out[-1][1][:80] == txt[:80] and (t - out[-1][0]).total_seconds() < 120:
        continue
    if txt in ('login',) or txt.startswith('/') or txt.startswith('Lane heartbeat'):
        continue
    out.append((t, txt, s))
asks = []; answers = []
for f in data:
    if f['session'] in exclude or f['parent'] in exclude:
        continue
    res = {ref: ts for ts, k, ref in f['events'] if k == 'result'}
    for tid, (ts, name, cmd, bg) in f['tools'].items():
        if name == 'AskUserQuestion':
            asks.append(P(ts))
            if tid in res:
                answers.append(P(res[tid]))
per_day = collections.Counter(t.astimezone(LOCAL).strftime('%Y-%m-%d') for t, _, _ in out)
ask_day = collections.Counter(t.astimezone(LOCAL).strftime('%Y-%m-%d') for t in asks)
print('owner messages', len(out), dict(sorted(per_day.items())))
print('AskUserQuestion calls', len(asks), dict(sorted(ask_day.items())))
print('owner words', sum(len(x[1].split()) for x in out))
json.dump([(t.astimezone(LOCAL).isoformat(), txt, s) for t, txt, s in out], open(sys.argv[2], 'w'), indent=0)
# stretches of two hours or more with no message from the owner and no answer to a question, and the tokens the agents spent in them
seen = {}
for f in data:
    if f['session'] in exclude or f['parent'] in exclude:
        continue
    for k, v in f['usage'].items():
        seen.setdefault(k, (P(v[0]), sum(v[2:6]), v[3]))
touch = sorted([t for t, _, _ in out] + answers)
gaps = []
for a, b in zip(touch, touch[1:]):
    if (b - a).total_seconds() >= 7200:
        tok = sum(n for t, n, o in seen.values() if a <= t < b)
        gaps.append((a.astimezone(LOCAL).strftime('%a %d %H:%M'), b.astimezone(LOCAL).strftime('%a %d %H:%M'), round((b - a).total_seconds() / 3600, 1), round(tok / 1e9, 2)))
alltok = sum(n for t, n, o in seen.values())
print('owner silent >= 2 h:', len(gaps), 'stretches,', round(sum(g[2] for g in gaps), 1), 'hours,', round(sum(g[3] for g in gaps), 2), 'B tokens of', round(alltok / 1e9, 2))
for g in gaps:
    print('  ', g)
