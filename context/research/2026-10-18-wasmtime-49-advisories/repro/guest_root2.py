import os, json
r=[]
os.chdir("/")
tgt="../wasi_canary_dir_19975"
try:
    os.symlink(tgt,"up"); r.append(("symlink "+tgt,"ok"))
except OSError as e: r.append(("symlink",f"errno {e.errno} {e.strerror}"))
try:
    os.rename("up/","stolen"); r.append(("rename up/->stolen","ok"))
except OSError as e: r.append(("rename",f"errno {e.errno} {e.strerror}"))
try:
    r.append(("listdir /stolen",sorted(os.listdir("/stolen"))))
except OSError as e: r.append(("listdir",f"errno {e.errno} {e.strerror}"))
try:
    r.append(("READ","/stolen/canary.txt="+open("/stolen/canary.txt").read().strip()))
except OSError as e: r.append(("read",f"errno {e.errno} {e.strerror}"))
print("RESULT "+json.dumps(r))
