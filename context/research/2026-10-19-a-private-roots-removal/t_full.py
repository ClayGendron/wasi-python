"""On a full volume: a deep tree, then fill every block, then each prototype removes it.
usage: t_full.py MNT MODULE"""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mnt, mod = sys.argv[1], sys.argv[2]
p = importlib.import_module(mod)
mfd = os.open(mnt, os.O_RDONLY | os.O_DIRECTORY)
os.mkdir("t", dir_fd=mfd)
fd = os.open("t", os.O_RDONLY | os.O_DIRECTORY, dir_fd=mfd)
for i in range(300):
    os.mkdir("a", dir_fd=fd); n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
os.close(fd)
k = 0
try:  # fill the volume: files, then empty folders, until ENOSPC on both
    with open(os.path.join(mnt, "t", "fill"), "wb") as f:
        while True:
            f.write(b"x" * 65536)
except OSError as e:
    print("fill stopped:", e.errno)
try:
    while True:
        os.mkdir(os.path.join(mnt, "t", f"d{k}")); k += 1
except OSError as e:
    print("mkdir stopped after", k, "folders:", e.errno)
st = os.statvfs(mnt); print("free blocks:", st.f_bavail)
print(mod, "gone =", p.remove_tree("t", mfd), {k: v for k, v in p.ops.items() if v})
print("left:", os.listdir(mnt))
