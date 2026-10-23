"""Work done per day, from the repository and GitHub Actions: commits,
specifications drafted and landed, reviews, research memos, accepted judge
records, and release-workflow runs with their outcomes and durations.

Usage (from the repository root):
  gh run list --limit 1000 --json databaseId,createdAt,updatedAt,startedAt,conclusion,status,headBranch,event,workflowName,displayTitle > gh_all.json
  uv run --no-project python -I work.py <repo> gh_all.json work.json
"""
import json, sys, re, os, glob, subprocess, collections
from datetime import datetime, timedelta, timezone
LOCAL = timezone(timedelta(hours=-4))
P = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
repo, runs_path, out = sys.argv[1:4]
git = lambda *a: subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, check=True).stdout
day = lambda dt: dt.astimezone(LOCAL).strftime('%Y-%m-%d')
res = {}
# commits per day on this branch's history
commits = collections.Counter(day(P(l.strip())) for l in git('log', '--format=%cI').splitlines() if l.strip())
res['commits_per_day'] = dict(sorted(commits.items())); res['commits'] = sum(commits.values())
# specifications: drafted = first commit adding the file; landed = the date after "landed" in its Status line
specs = sorted(glob.glob(os.path.join(repo, 'context/specifications/[0-9][0-9][0-9]-*.md')))
drafted = collections.Counter(); landed = collections.Counter(); status = collections.Counter()
for p in specs:
    rel = os.path.relpath(p, repo)
    first = git('log', '--diff-filter=A', '--follow', '--format=%cI', '--', rel).split()
    if first:
        drafted[day(P(first[-1]))] += 1
    st = next((l for l in open(p) if l.startswith('- **Status')), '')
    m = re.search(r'landed[^0-9]{0,20}(2026-10-\d\d)', st)
    word = re.sub(r'[*:]', '', st.split('Status')[1]).strip().split()[0].rstrip(',') if st else '?'
    status[word] += 1
    if m:
        landed[m.group(1)] += 1
res['spec_files'] = len(specs); res['spec_status'] = status
res['spec_numbers_max'] = max(int(os.path.basename(p)[:3]) for p in specs)
res['specs_drafted_per_day'] = dict(sorted(drafted.items())); res['specs_landed_per_day'] = dict(sorted(landed.items()))
# reviews and memos, dated by file name
rv = collections.Counter(); kinds = collections.Counter()
for p in glob.glob(os.path.join(repo, 'context/reviews/*.md')):
    m = re.search(r'(2026-10-\d\d)', os.path.basename(p))
    if m:
        rv[m.group(1)] += 1
        b = os.path.basename(p)
        kinds['specification' if '-spec-' in b else 'security' if 'security' in b else 'structural' if 'structural' in b
              else 'integration' if ('wave' in b or 'integration' in b) else 'build or other'] += 1
res['reviews_per_day'] = dict(sorted(rv.items())); res['reviews'] = sum(rv.values()); res['review_kinds'] = kinds
memos = collections.Counter(os.path.basename(p)[:10] for p in glob.glob(os.path.join(repo, 'context/research/2026-*.md')))
res['memos_per_day'] = dict(sorted(memos.items())); res['memos'] = sum(memos.values())
# accepted judge records
acc = collections.Counter()
hist = sorted(glob.glob(os.path.join(repo, 'context/progress/history*.jsonl')))
for h in hist:
    for l in open(h):
        if l.strip():
            acc[day(P(json.loads(l)['at']))] += 1
res['acceptances_per_day'] = dict(sorted(acc.items())); res['acceptances'] = sum(acc.values())
# CI runs
runs = [r for r in json.load(open(runs_path)) if r['workflowName'] in ('release', 'set-cache')]
ci = collections.defaultdict(collections.Counter); durs = []
for r in runs:
    d = day(P(r['createdAt'])); ci[d][(r['workflowName'], r['conclusion'])] += 1
    if r.get('startedAt') and r.get('updatedAt'):
        durs.append(((P(r['updatedAt']) - P(r['startedAt'])).total_seconds(), r['databaseId'], r['workflowName'], r['conclusion'], r['headBranch'], r['createdAt']))
durs.sort(reverse=True)
rel = [x for x in durs if x[2] == 'release']
res['ci_per_day'] = {d: {f'{w} {c}': n for (w, c), n in sorted(v.items())} for d, v in sorted(ci.items())}
res['ci_runs'] = len(runs)
res['ci_release_outcomes'] = collections.Counter(x[3] for x in rel)
res['ci_release_hours_total'] = round(sum(x[0] for x in rel) / 3600, 1)
res['ci_release_median_min'] = round(sorted(x[0] for x in rel)[len(rel) // 2] / 60, 1)
res['ci_release_success_median_min'] = round(sorted(x[0] for x in rel if x[3] == 'success')[sum(1 for x in rel if x[3] == 'success') // 2] / 60, 1)
res['ci_longest'] = [(round(s / 60, 1), i, w, c, b, t) for s, i, w, c, b, t in durs[:5]]
res['ci_branches'] = collections.Counter('main' if x[4] == 'main' else 'tag' if x[4].startswith('v0') else 'branch' for x in rel)
json.dump(res, open(out, 'w'), indent=1)
for k, v in res.items():
    print(k, v)
