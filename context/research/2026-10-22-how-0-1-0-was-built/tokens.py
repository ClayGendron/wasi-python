"""Token totals from extract.py's JSON: deduplicated per API message
(message id + request id), by model, by day and hour (local time, UTC-4),
and by lead session versus subagent. Writes tokens.json.

Usage: uv run --no-project python -I tokens.py data.json tokens.json [exclude-session ...]
"""
import json, sys, collections
from datetime import datetime, timedelta, timezone
LOCAL = timezone(timedelta(hours=-4))
data = json.load(open(sys.argv[1])); exclude = set(sys.argv[3:])
data = [f for f in data if f['session'] not in exclude and f['parent'] not in exclude]
seen = {}
for f in data:
    role = 'subagent' if f['parent'] else 'lead'
    for k, (ts, model, i, o, cr, cw) in f['usage'].items():
        if k in seen:
            continue
        seen[k] = (ts, model, i, o, cr, cw, role, f['session'], f['parent'] or f['session'])
F = ('input', 'output', 'cache_read', 'cache_write')
def z(): return dict.fromkeys(F + ('calls',), 0)
tot = z(); by_model = collections.defaultdict(z); by_role = collections.defaultdict(z)
by_day = collections.defaultdict(z); by_hour = collections.defaultdict(z)
by_hod = collections.defaultdict(z); by_hour_model = collections.defaultdict(lambda: collections.defaultdict(int)); by_hour_out = collections.defaultdict(int)
by_lead = collections.defaultdict(z)
for k, (ts, model, i, o, cr, cw, role, s, root) in seen.items():
    t = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(LOCAL)
    for d in (tot, by_model[model], by_role[role], by_day[t.strftime('%Y-%m-%d')],
              by_hour[t.strftime('%Y-%m-%d %H')], by_hod[t.strftime('%H')], by_lead[root]):
        d['input'] += i; d['output'] += o; d['cache_read'] += cr; d['cache_write'] += cw; d['calls'] += 1
    by_hour_model[t.strftime('%Y-%m-%d %H')][model] += i + o + cr + cw
    by_hour_out[t.strftime('%Y-%m-%d %H')] += o
def all_(d): return d['input'] + d['output'] + d['cache_read'] + d['cache_write']
out = {'total': tot, 'by_model': by_model, 'by_role': by_role, 'by_day': by_day,
       'by_hour': by_hour, 'by_hour_of_day': by_hod, 'by_hour_model': by_hour_model, 'by_hour_output': by_hour_out, 'by_lead_tree': by_lead}
json.dump(out, open(sys.argv[2], 'w'), indent=1, sort_keys=True)
fmt = lambda n: f'{n/1e9:.3f}B' if n > 1e8 else f'{n/1e6:.2f}M'
print('messages', len(seen))
print('total', {k: fmt(v) for k, v in tot.items() if k != 'calls'}, 'all', fmt(all_(tot)), 'no cache read', fmt(all_(tot) - tot['cache_read']))
for name, d in (('model', by_model), ('role', by_role), ('day', by_day), ('lead tree', by_lead)):
    print('--', name)
    for k in sorted(d):
        v = d[k]; print(' ', k, 'calls', v['calls'], {f: fmt(v[f]) for f in F}, 'all', fmt(all_(v)))
hrs = sorted(by_hour.items(), key=lambda kv: -all_(kv[1]))[:5]
print('busiest hours', [(h, fmt(all_(v)), 'out', fmt(v['output'])) for h, v in hrs])
active = [h for h, v in by_hour.items() if v['calls']]
print('hours with tokens', len(active), 'mean per active hour', fmt(all_(tot) / len(active)))
print('by hour of day', {h: fmt(all_(v)) for h, v in sorted(by_hod.items())})
ho = sorted(by_hour_out.items(), key=lambda kv: -kv[1])[:3]
print('busiest output hours', [(h, fmt(v)) for h, v in ho])
print('output per active hour', fmt(tot['output'] / len(active)), 'cache-read share', f"{100*tot['cache_read']/all_(tot):.1f}%")
