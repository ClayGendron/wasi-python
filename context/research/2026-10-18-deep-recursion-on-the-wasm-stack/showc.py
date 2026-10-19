import json,sys
stack = int(sys.argv[2]) if len(sys.argv) > 2 else 524288
for l in open(sys.argv[1]):
    d=json.loads(l)
    try: n=int(d['stderr_last'] or 0)
    except ValueError: n=0
    sp=d.get('sp_used',0)
    t=d.get('trap') or d['stdout'][:60]
    trapped = 'trap' in d
    print(f"{d['case']:20} depth {n:5} native/lvl {(stack/max(n,1) if trapped else 0):6.0f} linear/lvl {sp/max(n,1):6.0f} ratio {(stack/sp if sp and trapped else 0):5.2f} fuel {d['fuel']:>11} | {t}")
