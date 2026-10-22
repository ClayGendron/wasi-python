import json
ff=json.load(open('filefuel.json')); g={x['name']:x for gs in json.load(open('groups.json')).values() for x in gs}
bad=0
for n,v in ff.items():
    f=v['first'].split('::')[0]
    ps=g[n]['paths'] if n in g else None
    if ps is None: print('nogroup',n); continue
    if not any(f==p or f.startswith(p.rstrip('/')+'/') for p in ps): bad+=1; print('MISMATCH',n,f)
    tot=v['start']+sum(v['files'].values())
    if abs(tot-v['fuel'])>1: print('sum',n,round(tot),round(v['fuel']))
print(len(ff),'bad',bad)
