import sys,json
for l in open(sys.argv[1]):
    try: d=json.loads(l)
    except Exception: print(l[:200]); continue
    print(d['case'], '|', d.get('trap') or ('exit %s'%d.get('exit')), '|', d['stdout'][:90], '| fuel', d['fuel'], '| cstack', d['c_stack_used'], '| last', d['stderr_last'][:40])
