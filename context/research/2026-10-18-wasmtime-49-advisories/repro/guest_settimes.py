import os, json
r=[]
os.chdir("/")
open("f.txt","w").write("x")
for ns in (2**63-1, -(2**63), 2**64-1, 10**30, -(10**30)):
    try:
        os.utime("f.txt", ns=(ns, ns)); r.append((str(ns),"ok"))
    except OverflowError as e: r.append((str(ns),f"OverflowError {e}"))
    except OSError as e: r.append((str(ns),f"errno {e.errno} {e.strerror}"))
    except Exception as e: r.append((str(ns),f"{type(e).__name__} {e}"))
print("RESULT "+json.dumps(r))
