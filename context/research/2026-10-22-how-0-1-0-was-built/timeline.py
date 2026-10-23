"""Classify every second each Claude Code session spent, from extract.py's
JSON, and roll it up per minute of wall clock (local time, UTC-4).

Rules (stated in the README beside this script):
- A gap ending at an assistant record is the model generating (capped at
  10 minutes; the rest is idle).
- A gap ending at a foreground tool's result is that tool's class.
- A gap ending at anything else (a background task's notification, a
  subagent's hand-back, a heartbeat, the owner's prompt) is waiting: on the
  outstanding background task of highest class (build > judge > CI >
  subagent > other), or idle when nothing is outstanding.
Classes: generate, build, judge, ci, other, subagent (a session waiting on
its subagents), owner (a session blocked on an AskUserQuestion), idle.

Usage: uv run --no-project python -I timeline.py data.json timeline.json [exclude-session ...]
"""
import json, sys, re, collections
from datetime import datetime, timedelta, timezone
LOCAL = timezone(timedelta(hours=-4))
P = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
GEN_CAP = 600
CI = re.compile(r'\bgh (run|pr checks|workflow run)|gh api [^|]*actions|(wait|watch)[-_]?run|run_done|wait_ci|dispatch|\b3[89]\d{9}\b')
BUILD_STRONG = re.compile(r'build\.sh|scripts/steps|scripts/0\d_|docker (run|build|exec)|podman|container build')
JUDGE = re.compile(r'pytest|mutant|/survey/|measure|streams/|poll-|logs/jobs|plan-run|upstream|accept\.sh|fast\.sh|fast-tier|judge|lane\.lock|scoreboard|--tier')
BUILD = re.compile(r'build[-_. ]?(log|exit|\d)|rebuild|\bmake\b|ninja|cmake|clang\b|wasm-ld|configure\b')
SLEEP = re.compile(r'^\s*(sleep \d+\s*;?\s*)+$')
RANK = {'build': 0, 'judge': 1, 'ci': 2, 'subagent': 3, 'other': 4}

def classify(name, cmd):
    if name == 'Agent':
        return 'subagent'
    if name == 'AskUserQuestion':
        return 'owner'
    if name not in ('Bash', 'Monitor'):
        return 'other'
    raw = cmd.lower()
    if CI.search(raw):
        return 'ci'
    # quoted strings (acceptance reasons, commit messages) are prose, not commands
    c = re.sub(r'"[^"]{40,}"', '""', raw)
    if BUILD_STRONG.search(c):
        return 'build'
    if JUDGE.search(c):
        return 'judge'
    if BUILD.search(c):
        return 'build'
    if SLEEP.match(c):
        return 'sleep'
    return 'other'

data = json.load(open(sys.argv[1]))
exclude = set(sys.argv[3:])
data = [f for f in data if f['session'] not in exclude and (f['parent'] not in exclude)]
# end time of every subagent, keyed by the parent's Agent tool-use id
agent_end = {}
for f in data:
    tid = (f['meta'] or {}).get('toolUseId')
    if tid and f['events']:
        agent_end[tid] = P(f['events'][-1][0])
minute = collections.defaultdict(lambda: collections.defaultdict(float))   # minute -> class -> agent-seconds
minute_sessions = collections.defaultdict(set)    # minute -> sessions working (generate or a foreground tool)
agent_secs = collections.Counter(); per_session = {}
tool_durations = []   # (secs, class, cmd, session, start)
def add(sess, cls, t0, t1, working):
    if t1 <= t0:
        return
    agent_secs[cls] += t1 - t0
    t = t0
    while t < t1:
        m = int(t // 60); e = min(t1, (m + 1) * 60)
        minute[m][cls] += e - t
        if working:
            minute_sessions[m].add(sess)
        t = e
for f in data:
    ev = f['events']; tools = f['tools']; sess = f['session']
    if not ev:
        continue
    # classify tools; a bare sleep takes CI's class when a gh run call is within 15 minutes in this session
    cls = {tid: classify(v[1], v[2]) for tid, v in tools.items()}
    ci_times = sorted(P(v[0]) for tid, v in tools.items() if cls[tid] == 'ci')
    import bisect
    for tid, v in tools.items():
        if cls[tid] == 'sleep':
            t = P(v[0]); i = bisect.bisect_left(ci_times, t - 900)
            cls[tid] = 'ci' if i < len(ci_times) and ci_times[i] <= t + 900 else 'other'
    # background intervals
    first_notify = {}; last_notify = {}
    for ts, k, ref in ev:
        if k == 'notify' and ref:
            first_notify.setdefault(ref, P(ts)); last_notify[ref] = P(ts)
    bg = []
    for tid, (ts, name, cmd, isbg) in tools.items():
        t0 = P(ts)
        if name == 'Agent' and tid in agent_end and agent_end[tid] - t0 > 120:
            bg.append((t0, agent_end[tid], 'subagent'))
        elif (isbg or name == 'Monitor') and tid in last_notify:
            end = first_notify[tid] if name != 'Monitor' else last_notify[tid]
            bg.append((t0, end, cls[tid] if cls[tid] != 'owner' else 'other'))
            if name != 'Monitor':
                tool_durations.append((end - t0, cls[tid], cmd, sess, ts, 'bg'))
    results = {}
    for ts, k, ref in ev:
        if k == 'result' and ref not in results:
            results[ref] = P(ts)
    for tid, (ts, name, cmd, isbg) in tools.items():
        if tid in results and not isbg:
            tool_durations.append((results[tid] - P(ts), cls[tid], cmd, sess, ts, 'fg'))
    ss = collections.Counter()
    for (ta, ka, ra), (tb, kb, rb) in zip(ev, ev[1:]):
        a, b = P(ta), P(tb)
        if b <= a:
            continue
        if kb == 'gen':
            g = min(b, a + GEN_CAP)
            add(sess, 'generate', a, g, True); ss['generate'] += g - a
            if b > g:
                ss['idle'] += b - g
        elif kb == 'result' and rb in tools and not tools[rb][3]:
            c = cls[rb]
            add(sess, c, a, b, c not in ('subagent', 'owner')); ss[c] += b - a
        else:
            out = [x for x in bg if x[0] <= a and x[1] > a]
            if out:
                c = min((x[2] for x in out), key=lambda c: RANK.get(c, 9))
                add(sess, c, a, b, False); ss[c] += b - a
            else:
                ss['idle'] += b - a
    per_session[sess] = {'parent': f['parent'], 'desc': (f['meta'] or {}).get('description'),
                         'start': ev[0][0], 'end': ev[-1][0], 'secs': dict(ss)}
# per-minute dominant class; a session waiting on its subagents counts only when nothing else ran
dom = {}
for m, d in minute.items():
    d2 = {k: v for k, v in d.items() if k not in ('subagent', 'owner', 'idle')} or {k: v for k, v in d.items() if k != 'idle'}
    if d2:
        dom[m] = max(d2, key=d2.get)
out = {'agent_secs': agent_secs, 'per_session': per_session,
       'minutes': {m: dict(d) for m, d in minute.items()}, 'dominant': dom,
       'working_sessions': {m: len(s) for m, s in minute_sessions.items()},
       'longest': sorted(tool_durations, key=lambda x: -x[0])[:400]}
json.dump(out, open(sys.argv[2], 'w'))
print({k: round(v / 3600, 1) for k, v in agent_secs.most_common()})
