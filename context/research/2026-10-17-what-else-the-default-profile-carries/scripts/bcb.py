import json, sys, glob, ast, collections, sys as _s
std = set(_s.stdlib_module_names)
c = collections.Counter(); n=0
for f in sorted(glob.glob(sys.argv[1]+"/rows_*.json")):
    for r in json.load(open(f))["rows"]:
        libs = r["row"]["libs"]
        if isinstance(libs,str): libs = ast.literal_eval(libs)
        n+=1
        for l in set(libs): c[l]+=1
print("tasks", n, "distinct libs", len(c))
ext = [(k,v) for k,v in c.most_common() if k not in std]
print("TOP stdlib:", [(k,v) for k,v in c.most_common() if k in std][:15])
print("ALL external:", ext)
