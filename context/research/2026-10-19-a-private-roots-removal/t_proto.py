"""Tests the prototype on host-built trees in a child under a low soft limit.
usage: t_proto.py WORK  (prints one line per case)"""

import os
import resource
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402
p = importlib.import_module(sys.argv[2] if len(sys.argv) > 2 else "proto_remove")

work = sys.argv[1]
os.makedirs(work, exist_ok=True)
resource.setrlimit(resource.RLIMIT_NOFILE, (64, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
wfd = os.open(work, os.O_RDONLY | os.O_DIRECTORY)


def deep(name, depth, filler=True):
    os.mkdir(name, dir_fd=wfd)
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=wfd)
    for i in range(depth):
        if filler:
            os.close(os.open("f", os.O_CREAT | os.O_WRONLY, dir_fd=fd))
        os.mkdir("a", dir_fd=fd)
        n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
        os.close(fd)
        fd = n
    os.close(fd)


def case(label, name, entries):
    for k in p.ops:
        p.ops[k] = 0
    gone = p.remove_tree(name, wfd)
    total = sum(v for k, v in p.ops.items() if k not in ("open_now", "open_peak"))
    print(f"{label}: gone={gone} entries={entries} ops={total} peak_fds={p.ops['open_peak']} "
          f"{ {k: v for k, v in p.ops.items() if v and k not in ('open_now',)} }")


# 1. deep beyond the soft limit: 2,000 levels, a file at each
deep("d", 2000)
r = shutil.rmtree.__wrapped__ if hasattr(shutil.rmtree, "__wrapped__") else shutil.rmtree
errs = []
shutil.rmtree(os.path.join(work, "d"), onexc=lambda f, x, e: errs.append(type(e).__name__))
print("shutil.rmtree on 2,000 levels at soft 64:", "left" if os.path.exists(os.path.join(work, "d")) else "gone", errs[:2], len(errs))
case("deep 2,000 + files", "d", 4000)

# 2. links out of the root are never followed
canary = os.path.join(work, "canary")
os.mkdir(canary)
open(os.path.join(canary, "keep"), "w").write("keep")
os.mkdir("s", dir_fd=wfd)
sfd = os.open("s", os.O_RDONLY | os.O_DIRECTORY, dir_fd=wfd)
os.symlink(canary, "out", dir_fd=sfd)
os.symlink(os.path.join(canary, "keep"), "outfile", dir_fd=sfd)
os.symlink("../../..", "up", dir_fd=sfd)
os.mkdir("sub", dir_fd=sfd)
os.symlink(canary, "sub/out2", dir_fd=sfd)
os.close(sfd)
case("links", "s", 5)
print("  canary intact:", open(os.path.join(canary, "keep")).read() == "keep",
      sorted(os.listdir(canary)))

# 3. read-only folders: 0o500 with a file, 0o000 empty, a 0o500 chain 300 deep
os.mkdir("r", dir_fd=wfd)
rp = os.path.join(work, "r")
os.makedirs(os.path.join(rp, "ro", "inner"))
open(os.path.join(rp, "ro", "inner", "x"), "w").write("x")
open(os.path.join(rp, "ro", "y"), "w").write("y")
os.chmod(os.path.join(rp, "ro", "inner"), 0o500)
os.chmod(os.path.join(rp, "ro"), 0o500)
os.mkdir(os.path.join(rp, "none"))
os.chmod(os.path.join(rp, "none"), 0o000)
os.chmod(rp, 0o500)
case("read-only", "r", 6)

# 4. wide: 5,000 files and 300 empty folders in one folder
os.mkdir("w", dir_fd=wfd)
wp = os.path.join(work, "w")
for i in range(5000):
    open(os.path.join(wp, f"f{i}"), "w").close()
for i in range(300):
    os.mkdir(os.path.join(wp, f"d{i}"))
case("wide", "w", 5300)
print("left in work:", sorted(os.listdir(work)))
