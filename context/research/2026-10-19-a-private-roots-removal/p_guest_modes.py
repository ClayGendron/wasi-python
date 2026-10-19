"""Can a guest make a folder (or file) unwritable or unreadable on the host through WASI preview1
and wasmtime? Every way Python in the guest offers, in a caller's root (so the tree stays), then
the host's modes, and whether the host's shutil.rmtree can remove it. usage: p_guest_modes.py ROOT"""
import os, stat, sys, shutil, tempfile
root = sys.argv[1]
tempfile.tempdir = os.path.dirname(root)
import wasi_python
G = r'''
import os, stat
def attempt(label, f):
    try:
        f(); print(label, "ok")
    except Exception as e:
        print(label, type(e).__name__, getattr(e, "errno", ""))
print("has", {n: hasattr(os, n) for n in ("chmod", "fchmod", "lchmod", "umask", "chflags", "mkfifo", "mknod")})
attempt("mkdir mode 0o500", lambda: os.mkdir("/d500", 0o500))
attempt("mkdir mode 0o000", lambda: os.mkdir("/d000", 0o000))
attempt("open O_CREAT mode 0o400", lambda: os.close(os.open("/f400", os.O_CREAT | os.O_WRONLY, 0o400)))
os.mkdir("/dc"); open("/dc/x", "w").close()
attempt("chmod dir 0o500", lambda: os.chmod("/dc", 0o500))
attempt("chmod file 0o000", lambda: os.chmod("/dc/x", 0o000))
attempt("fchmod dir", lambda: os.fchmod(os.open("/dc", os.O_RDONLY | os.O_DIRECTORY), 0o500))
attempt("umask 0o777 then mkdir", lambda: (os.umask(0o777), os.mkdir("/dumask")))
attempt("mkfifo", lambda: os.mkfifo("/fifo"))
attempt("utime (the only setter left)", lambda: os.utime("/dc", (0, 0)))
for p in ("/d500", "/d000", "/f400", "/dc", "/dc/x", "/dumask"):
    try: print("guest sees", p, oct(stat.S_IMODE(os.stat(p).st_mode)))
    except Exception as e: print("guest sees", p, type(e).__name__)
'''
d = wasi_python.run(["-c", G], root=root)
print(d.stdout.decode(), d.stderr.decode()[-400:])
print("host umask", oct(os.umask(0o022)))
for dp, dirs, files in os.walk(root):
    for n in dirs + files:
        p = os.path.join(dp, n)
        if "usr" in p or ".home-" in p: continue
        print("host", os.path.relpath(p, root), oct(stat.S_IMODE(os.lstat(p).st_mode)))
errs = []
shutil.rmtree(root, onexc=lambda f, p, e: errs.append((f.__name__, p, e)))
print("host rmtree errors:", errs, "left:", os.path.exists(root))
