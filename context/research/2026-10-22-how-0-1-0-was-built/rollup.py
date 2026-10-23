"""Wall-clock rollup of timeline.py's per-minute classes over the week:
hours per dominant class (overall and per day), hours with any activity,
idle stretches, and parallel sessions. Writes rollup.json for the charts.

Usage: uv run --no-project python -I rollup.py data.json timeline.json rollup.json gh_all.json [exclude-session ...]
"""
import json, sys, collections
from datetime import datetime, timedelta, timezone
LOCAL = timezone(timedelta(hours=-4))
P = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
data = json.load(open(sys.argv[1])); tl = json.load(open(sys.argv[2])); runs = json.load(open(sys.argv[4])); exclude = set(sys.argv[5:])
files = [f for f in data if f['events'] and f['session'] not in exclude and f['parent'] not in exclude]
t0 = min(P(f['events'][0][0]) for f in files); t1 = max(P(f['events'][-1][0]) for f in files)
m0, m1 = int(t0 // 60), int(t1 // 60)
dom = {int(k): v for k, v in tl['dominant'].items()}
# a minute with no session at work but a CI run in progress is time spent waiting on CI
ci_min = set()
for r in runs:
    if r.get('startedAt') and r.get('updatedAt'):
        for m in range(int(P(r['startedAt']) // 60), int(P(r['updatedAt']) // 60) + 1):
            ci_min.add(m)
filled = 0
for m in ci_min:
    if m not in dom and m0 <= m <= m1:
        dom[m] = 'ci'; filled += 1
print('idle minutes filled by a CI run in progress', filled)
mins = {int(k): v for k, v in tl['minutes'].items()}
work = {int(k): v for k, v in tl['working_sessions'].items()}
CL = ['generate', 'build', 'judge', 'ci', 'other', 'subagent', 'owner', 'idle']
tot = collections.Counter(); per_day = collections.defaultdict(collections.Counter)
per_hour = collections.defaultdict(collections.Counter); agent_hour = collections.defaultdict(collections.Counter)
for m in range(m0, m1 + 1):
    c = dom.get(m, 'idle')
    lt = datetime.fromtimestamp(m * 60, LOCAL)
    tot[c] += 1; per_day[lt.strftime('%Y-%m-%d')][c] += 1; per_hour[lt.strftime('%Y-%m-%d %H')][c] += 1
    for k, v in mins.get(m, {}).items():
        agent_hour[lt.strftime('%Y-%m-%d %H')][k] += v
span_h = (m1 - m0 + 1) / 60
print('window', datetime.fromtimestamp(t0, LOCAL), '->', datetime.fromtimestamp(t1, LOCAL), f'{span_h:.1f} h')
print('wall-clock hours by dominant class', {k: round(tot[k] / 60, 1) for k in CL}, 'shares', {k: f'{100*tot[k]/(m1-m0+1):.1f}%' for k in CL})
for d in sorted(per_day):
    print(' ', d, {k: round(per_day[d][k] / 60, 1) for k in CL if per_day[d][k]})
hours = sorted(per_hour)
active = [h for h in hours if per_hour[h]['idle'] < 60]
busy30 = [h for h in hours if per_hour[h]['idle'] <= 30]
print('clock hours in window', len(hours), 'with any activity', len(active), 'with activity >=30 min', len(busy30))
# idle stretches (no session generating or running a tool or waiting on a background task)
stretches = []; cur = None
for m in range(m0, m1 + 1):
    if dom.get(m) is None:
        cur = cur or m
    elif cur:
        stretches.append((m - cur, cur)); cur = None
stretches.sort(reverse=True)
print('longest idle stretches (min, start)', [(n, datetime.fromtimestamp(s * 60, LOCAL).strftime('%m-%d %H:%M')) for n, s in stretches[:8]])
print('idle minutes in stretches >= 15 min', sum(n for n, s in stretches if n >= 15))
# parallelism: sessions working (generating or a foreground tool) in the same minute
peak = max(work.values()); pm = max(work, key=work.get)
print('peak sessions working in one minute', peak, datetime.fromtimestamp(pm * 60, LOCAL))
dist = collections.Counter(work.get(m, 0) for m in range(m0, m1 + 1))
print('minutes by working-session count', sorted(dist.items()))
# sessions alive: first..last event
iv = [(P(f['events'][0][0]), P(f['events'][-1][0]), f['parent'] is None) for f in files]
best = 0; bt = None
for s, e, lead in iv:
    n = sum(1 for a, b, _ in iv if a <= s <= b)
    if n > best: best, bt = n, s
print('peak sessions open at once (first..last event)', best, datetime.fromtimestamp(bt, LOCAL))
leads = [f for f in files if f['parent'] is None]; subs = [f for f in files if f['parent']]
print('sessions: lead', len(leads), 'subagents', len(subs))
ag = {k: round(v / 3600, 1) for k, v in tl['agent_secs'].items()}
print('agent-hours by class', ag, 'sum', round(sum(tl['agent_secs'].values()) / 3600, 1))
json.dump({'ci_minutes': len(ci_min & set(range(m0, m1 + 1))), 't0': t0, 't1': t1, 'per_hour': per_hour, 'per_day': per_day, 'total': tot,
           'agent_hour': agent_hour, 'agent_secs': tl['agent_secs']}, open(sys.argv[3], 'w'))
