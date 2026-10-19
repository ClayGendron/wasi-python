"""A guest given a caller's root builds 256 levels under its fresh HOME at soft 128; what is left
in root/tmp? usage: p_home.py ROOT TEMP (run inline as `python -I -c` for p_home.out)"""
import os, resource, sys, tempfile
resource.setrlimit(resource.RLIMIT_NOFILE, (128, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
tempfile.tempdir = sys.argv[2]
import wasi_python
G = '''
import os
fd = os.open(os.environ["HOME"], os.O_RDONLY | os.O_DIRECTORY)
for i in range(256):
    os.mkdir("a", dir_fd=fd)
    n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
print("built in", os.environ["HOME"])
'''
d = wasi_python.run(["-c", G], root=sys.argv[1])
print(d.exit_code, d.stdout, "root/tmp holds:", os.listdir(os.path.join(sys.argv[1], "tmp")))
