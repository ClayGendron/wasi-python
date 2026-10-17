# Runs inside the guest: python.wasm -c <this file's text> <data dir> <a spelling of it that does
# not match the preopen's name string>. One line per operation: "ok" and the value, or "err" and errno.
import errno
import hashlib
import os
import sys
from pathlib import Path

P, ALT = sys.argv[1], sys.argv[2]
RC = P + "/matplotlibrc"


def t(name, f):
    try:
        r = f()
        print("ok ", name, repr(r)[:90])
    except OSError as e:
        print("err", name, type(e).__name__, e.errno, errno.errorcode.get(e.errno))


def stat(p):
    s = os.stat(p)
    return oct(s.st_mode), s.st_size, s.st_mtime, s.st_ino, s.st_nlink


def read_all():
    h, n, count = hashlib.sha256(), 0, 0
    for d, dirs, files in os.walk(P):
        dirs.sort()
        for f in sorted(files):
            with open(os.path.join(d, f), "rb") as fh:
                b = fh.read()
            h.update(b)
            n += len(b)
            count += 1
    return count, n, h.hexdigest()[:16]


def write_root():
    with open("/probe.txt", "w") as f:
        f.write("hi")
    with open("/probe.txt") as f:
        return f.read()


def plant():
    os.makedirs(ALT, exist_ok=True)
    with open(ALT + "/matplotlibrc", "w") as f:
        f.write("## PLANTED\n")
    return "planted"


print("-- reads")
t("readline", lambda: open(RC).readline().strip())
t("listdir", lambda: sorted(os.listdir(P)))
t("isfile", lambda: os.path.isfile(RC))
t("isdir", lambda: os.path.isdir(P))
t("Path.is_dir", lambda: Path(P).is_dir())
t("stat", lambda: stat(RC))
t("stat dir", lambda: stat(P))
t("walk", read_all)
print("-- writes")
t("create", lambda: open(P + "/new", "w").write("x"))
t("open w existing", lambda: open(RC, "w").close())
t("size after open w", lambda: os.path.getsize(RC))


def write_close(mode):
    f = open(RC, mode)
    try:
        f.write("x")
    finally:
        f.close()


def write_raw():
    fd = os.open(RC, os.O_RDWR)
    try:
        return os.write(fd, b"x")
    finally:
        os.close(fd)


t("append", lambda: write_close("a"))
t("r+ write", lambda: write_close("r+"))
t("os.write O_RDWR", write_raw)
t("unlink", lambda: os.remove(RC))
t("mkdir", lambda: os.mkdir(P + "/d"))
t("rmdir", lambda: os.rmdir(P + "/sample_data/axes_grid"))
t("rename inside", lambda: os.rename(RC, P + "/x"))
t("rename to root", lambda: os.rename(RC, "/moved"))
t("symlink", lambda: os.symlink("/etc", P + "/l"))
t("hard link to root", lambda: os.link(RC, "/hl"))
t("utime", lambda: os.utime(RC, (0, 0)))
t("truncate", lambda: os.truncate(RC, 0))
t("escape ..", lambda: open(P + "/../../../../../../etc/passwd").read(10))
print("-- after")
t("readline", lambda: open(RC).readline().strip())
t("walk", read_all)
print("-- the root and the zip")
t("import decimal", lambda: __import__("decimal").__file__)
t("import json", lambda: __import__("json").__file__)
t("write root", write_root)
t("listdir /", lambda: sorted(os.listdir("/")))
t("zip isfile", lambda: os.path.isfile("/usr/local/lib/python314.zip"))
print("-- shadow")
t("plant at " + ALT, plant)
t("readline", lambda: open(RC).readline().strip())
t("readline alt", lambda: open(ALT + "/matplotlibrc").readline().strip())
