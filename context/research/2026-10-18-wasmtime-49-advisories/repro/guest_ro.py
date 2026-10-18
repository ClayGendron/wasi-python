import os, json
r=[]
os.chdir("/work")
try:
    os.symlink("../outside","up"); r.append(("symlink","ok"))
except OSError as e: r.append(("symlink",f"errno {e.errno} {e.strerror}"))
print("RESULT "+json.dumps(r))
