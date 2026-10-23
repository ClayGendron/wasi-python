"""Stream every Claude Code transcript for this project, one file at a time,
and write the compact facts the analysis needs (usage per API message, the
timeline of events per session, every tool call with its class) to a JSON
file. Never loads a transcript whole.

Usage: uv run --no-project python -I extract.py <projects-dir> <out.json>
"""
import json, os, sys, re, glob
from multiprocessing import Pool

SKIP_TYPES = ('"type":"api-request', '"type":"file-history', '"type":"attachment"',
              '"type":"mode"', '"type":"permission-mode"', '"type":"atis-latch"',
              '"type":"last-prompt"', '"type":"ai-title"', '"type":"bridge-session"')

def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for c in content or []:
        if isinstance(c, dict) and c.get('type') == 'text':
            out.append(c.get('text', ''))
    return '\n'.join(out)

def tool_cmd(name, inp):
    if not isinstance(inp, dict):
        return ''
    for k in ('command', 'prompt', 'description', 'file_path', 'pattern', 'query', 'url'):
        if k in inp and isinstance(inp[k], str):
            return inp[k][:600]
    return json.dumps(inp)[:300]

def one(path):
    sess = os.path.basename(path)[:-6]
    parent = None
    meta = {}
    if '/subagents/' in path:
        parent = path.split('/subagents/')[0].split('/')[-1]
        mp = path[:-6] + '.meta.json'
        if os.path.exists(mp):
            try:
                meta = json.load(open(mp))
            except Exception:
                pass
    usage = {}      # key -> [ts, model, in, out, cr, cw]
    events = []     # [ts, kind, ref]
    tools = {}      # tool_use_id -> [ts, name, cmd, background]
    humans = []     # [ts, text]
    with open(path, errors='replace') as f:
        for line in f:
            head = line[:400]
            if any(s in head for s in SKIP_TYPES):
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            t = r.get('type')
            ts = r.get('timestamp')
            if t == 'assistant':
                m = r.get('message') or {}
                model = m.get('model')
                u = m.get('usage') or {}
                key = (m.get('id') or '') + '|' + (r.get('requestId') or '')
                vals = [u.get('input_tokens') or 0, u.get('output_tokens') or 0,
                        u.get('cache_read_input_tokens') or 0, u.get('cache_creation_input_tokens') or 0]
                if model and model != '<synthetic>':
                    old = usage.get(key)
                    if old is None:
                        usage[key] = [ts, model] + vals
                    else:
                        for i in range(4):
                            old[2 + i] = max(old[2 + i], vals[i])
                events.append([ts, 'gen', key])
                for c in m.get('content') or []:
                    if isinstance(c, dict) and c.get('type') == 'tool_use':
                        inp = c.get('input') or {}
                        bg = bool(isinstance(inp, dict) and inp.get('run_in_background'))
                        tools[c.get('id')] = [ts, c.get('name'), tool_cmd(c.get('name'), inp), bg]
            elif t == 'user':
                m = r.get('message') or {}
                content = m.get('content')
                if isinstance(content, list) and any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content):
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'tool_result':
                            events.append([ts, 'result', c.get('tool_use_id')])
                    continue
                origin = r.get('origin') or {}
                kind = origin.get('kind') if isinstance(origin, dict) else None
                txt = text_of(content)
                if kind == 'task-notification' or txt.lstrip().startswith('<task-notification>'):
                    mm = re.search(r'<tool-use-id>([^<]+)</tool-use-id>', txt)
                    events.append([ts, 'notify', mm.group(1) if mm else None])
                elif kind == 'peer':
                    events.append([ts, 'peer', origin.get('from')])
                elif kind == 'human' or (not r.get('isMeta') and kind is None and txt and not txt.lstrip().startswith('<')
                                         and not txt.startswith('This session is being continued')
                                         and not txt.startswith('[Request interrupted')):
                    if parent is None:
                        humans.append([ts, txt[:400]])
                    events.append([ts, 'human', None])
                else:
                    events.append([ts, 'meta', txt[:60]])
            elif t == 'queue-operation' and r.get('operation') == 'enqueue':
                c = r.get('content')
                if parent is None and isinstance(c, str) and c and not c.lstrip().startswith('<'):
                    humans.append([ts, c[:400]])
                    events.append([ts, 'human', 'queued'])
            elif t == 'system':
                events.append([ts, 'system', r.get('subtype')])
    events = [e for e in events if e[0]]
    events.sort(key=lambda e: e[0])
    return {'session': sess, 'parent': parent, 'meta': meta, 'path': path,
            'usage': usage, 'events': events, 'tools': tools, 'humans': humans}

if __name__ == '__main__':
    root, out = sys.argv[1], sys.argv[2]
    files = [p for p in glob.glob(root + '/**/*.jsonl', recursive=True) if os.path.getsize(p) > 0]
    files.sort(key=os.path.getsize, reverse=True)
    with Pool(6) as pool:
        res = pool.map(one, files, chunksize=1)
    json.dump(res, open(out, 'w'))
    print(len(res), 'files')
