"""3.11's rmtree recurses: a deep private root under a high soft limit. usage: p311.py SOFT DEPTH TEMP"""
import os, resource, sys, tempfile, traceback
soft, depth, temp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
resource.setrlimit(resource.RLIMIT_NOFILE, (soft, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
tempfile.tempdir = temp
import wasi_python
G = f"""
import os
fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
for i in range({depth}):
    os.mkdir("a", dir_fd=fd)
    n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
print("built", {depth})
"""
try:
    d = wasi_python.run(["-c", G], root=True)
    print(sys.version.split()[0], soft, depth, "returned", d.exit_code, d.stdout)
except BaseException as e:
    print(sys.version.split()[0], soft, depth, "raised", type(e).__name__, str(e)[:100])
    tb = traceback.extract_tb(e.__traceback__)
    print("  frames:", len(tb), "first:", [f"{f.name}:{f.lineno}" for f in tb[:6]])
print("  left:", sorted(os.listdir(temp)))
