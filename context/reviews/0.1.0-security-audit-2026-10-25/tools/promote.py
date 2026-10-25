"""Trusted parent-side promotion of allowlisted scratch files into an agent's artifacts/ (SKILL.md procedure).

Usage: promote.py <agent_id>
Allowlist: regular files directly under scratch/evidence/ named *.txt|*.json|*.log|*.py, <=24 files, <=512 KiB each, <=8 MiB total.
"""
import os, stat, sys, json
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
PER_FILE = 512 * 1024; TOTAL = 8 * 1024 * 1024; MAX_FILES = 24
EXTS = (".txt", ".json", ".log", ".py")

def open_dir_nofollow(dirfd, name):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirfd)
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode):
        os.close(fd); raise RuntimeError(f"{name} not a directory")
    return fd

def main(aid):
    root = os.path.join(OUT, "agents", aid)
    # retained trusted descriptors for scratch root and artifacts root
    base = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    scratch = open_dir_nofollow(base, "scratch")
    arts = open_dir_nofollow(base, "artifacts")
    promoted = []; rejected = []; total = 0
    try:
        ev = open_dir_nofollow(scratch, "evidence")
    except FileNotFoundError:
        print(json.dumps({"agent": aid, "promoted": [], "rejected": ["no scratch/evidence"]})); return
    names = sorted(os.listdir(ev))
    if len(names) > MAX_FILES:
        rejected.append(f"more than {MAX_FILES} entries; promoting none")
        names = []
    # destination evidence dir: create exclusively if missing, then open no-follow
    try:
        os.mkdir("evidence", 0o700, dir_fd=arts)
    except FileExistsError:
        pass
    dst_dir = open_dir_nofollow(arts, "evidence")
    for name in names:
        if "/" in name or name in (".", "..") or not name.endswith(EXTS) or name.startswith("."):
            rejected.append(f"{name}: not allowlisted"); continue
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=ev)
        except OSError as e:
            rejected.append(f"{name}: open failed ({e.strerror})"); continue
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                rejected.append(f"{name}: not a regular file with one link"); continue
            if st.st_size > PER_FILE or total + st.st_size > TOTAL:
                rejected.append(f"{name}: over size bound"); continue
            data = b""; remaining = st.st_size
            while remaining > 0:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk: break
                data += chunk; remaining -= len(chunk)
                if len(data) > PER_FILE: break
            st2 = os.fstat(fd)
            if len(data) != st.st_size or (st2.st_ino, st2.st_dev, st2.st_size, st2.st_nlink, stat.S_IFMT(st2.st_mode)) != (st.st_ino, st.st_dev, st.st_size, st.st_nlink, stat.S_IFMT(st.st_mode)):
                rejected.append(f"{name}: changed during read"); continue
            try:
                dfd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dst_dir)
            except FileExistsError:
                rejected.append(f"{name}: destination exists"); continue
            try:
                dst = os.fstat(dfd)
                if not stat.S_ISREG(dst.st_mode) or dst.st_nlink != 1:
                    rejected.append(f"{name}: destination not a fresh regular file"); continue
                off = 0
                while off < len(data):
                    off += os.write(dfd, data[off:])
            finally:
                os.close(dfd)
            total += len(data)
            promoted.append(f"agents/{aid}/artifacts/evidence/{name}")
        finally:
            os.close(fd)
    print(json.dumps({"agent": aid, "promoted": promoted, "rejected": rejected, "bytes": total}, indent=1))

if __name__ == "__main__":
    main(sys.argv[1])
