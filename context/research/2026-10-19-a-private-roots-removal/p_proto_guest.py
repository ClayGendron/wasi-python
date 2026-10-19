"""A guest-built leftover (400 levels at soft 256, with links out), then the prototype removes it
under soft 32. usage: p_proto_guest.py TEMP CANARY"""
import os, resource, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
temp, canary = sys.argv[1], sys.argv[2]
hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
resource.setrlimit(resource.RLIMIT_NOFILE, (256, hard))
tempfile.tempdir = temp
import wasi_python
G = f"""
import os
try: os.symlink({canary!r}, "/abs")
except OSError as e: print("abs link refused:", e.errno)
os.symlink("../../../../../..", "/up")
fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
for i in range(400):
    os.mkdir("a", dir_fd=fd)
    n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
os.symlink("../" * 420 + "canary", "deep-up", dir_fd=fd)
print("built")
"""
d = wasi_python.run(["-c", G], root=True)
roots = [n for n in os.listdir(temp) if n.startswith("wasi-python-root-") and not n.endswith(".lock")]
print("call:", d.exit_code, d.stdout, d.stderr[-300:], "roots left:", roots)
import importlib
p = importlib.import_module(sys.argv[3] if len(sys.argv) > 3 else "proto_remove")
resource.setrlimit(resource.RLIMIT_NOFILE, (32, hard))
tfd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
for r in roots:
    print("prototype at soft 32:", r, "gone =", p.remove_tree(r, tfd), "peak fds", p.ops["open_peak"])
    os.unlink(os.path.join(temp, r + ".lock"))
print("canary:", sorted(os.listdir(canary)), "left:", sorted(n for n in os.listdir(temp) if "root" in n))
