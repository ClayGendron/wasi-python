"""How deep one call gets in the default 60 s deadline (a benchmark fact, not a check): the guest
reports every 250 levels on stderr. usage: p_deadline_depth.py TEMP (run inline for the .out)"""
import resource, sys, tempfile, time
resource.setrlimit(resource.RLIMIT_NOFILE, (8192, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
tempfile.tempdir = sys.argv[1]
import wasi_python
G = '''
import os
fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
for i in range(1, 100001):
    os.mkdir("a", dir_fd=fd)
    n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
    if i % 250 == 0: os.write(2, b"%d\\n" % i)
'''
t = time.monotonic()
d = wasi_python.run(["-c", G], root=True)
print(d.exit_code, d.trapped, "last depth", d.stderr.split()[-1:], "secs", round(time.monotonic() - t))
