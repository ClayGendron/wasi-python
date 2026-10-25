"""Bounded local check for h01-fs-paths: a hostile guest through wasi_python.run against the
local artifact set. Fixtures live only under this script's scratch folder. Prints JSON."""

import json
import os
import shutil
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent
FX = SCRATCH / "fx"

sys.path.insert(0, "./src")
import wasi_python  # noqa: E402
from wasi_python import Errno, Grant, Mount, Stat, run  # noqa: E402

GUEST_GRANTS = r'''
import os, json
out = {}
def t(name, fn):
    try:
        r = fn()
        out[name] = "ok:" + repr(r)
    except OSError as e:
        out[name] = "err:%s:%s" % (type(e).__name__, e.errno)
os.symlink("../outside", "/w/up")
os.symlink("../outside_empty", "/w/e")
os.symlink("../outside/newdir", "/w/dang")
os.symlink("../outside/newfile", "/w/dangf")
t("open_through_link", lambda: open("/w/up/canary").read())
t("rename_slash", lambda: os.rename("/w/up/", "/w/stolen"))
t("rename_double_slash", lambda: os.rename("/w/up//", "/w/stolen2"))
t("rename_slash_dot", lambda: os.rename("/w/up/.", "/w/stolen3"))
t("rename_target_slash", lambda: os.rename("/w/e", "/w/moved/"))
t("rmdir_slash", lambda: os.rmdir("/w/e/"))
t("unlink_slash", lambda: os.unlink("/w/up/"))
t("link_ro_to_rw", lambda: os.link("/r/secret.txt", "/w/hl"))
t("link_through_up", lambda: os.link("/w/up/canary", "/w/hl2"))
t("link_slash", lambda: os.link("/w/up/", "/w/hl3"))
t("symlink_at_slash", lambda: os.symlink("x", "/w/up/"))
t("mkdir_dangling_slash", lambda: os.mkdir("/w/dang/"))
t("mkdir_dangling", lambda: os.mkdir("/w/dang"))
t("create_through_dangling", lambda: open("/w/dangf", "w").write("x"))
t("utime_slash", lambda: os.utime("/w/up/", (1, 1)))
t("readlink_slash", lambda: os.readlink("/w/up/"))
t("stat_slash", lambda: os.stat("/w/up/").st_ino)
t("write_ro_grant", lambda: open("/r/secret.txt", "a").write("x"))
t("rename_ro_to_rw", lambda: os.rename("/r/secret.txt", "/w/moved"))
t("dotdot_out_of_w", lambda: open("/w/../r/secret.txt").read())
t("listdir_w", lambda: sorted(os.listdir("/w")))
print(json.dumps(out))
'''

GUEST_MOUNTS = r'''
import os, json
out = {}
def t(name, fn):
    try:
        r = fn()
        out[name] = "ok:" + repr(r)
    except OSError as e:
        out[name] = "err:%s:%s" % (type(e).__name__, e.errno)
t("plain", lambda: open("/m/a.txt").read())
t("climb_abs", lambda: open("/m/../m/a.txt").read())
t("climb_sub", lambda: open("/m/d/../../x").read())
t("nested_via_mount", lambda: open("/m/d/../g/secret.txt").read())
t("nested_direct", lambda: open("/m/g/secret.txt").read())
t("backslash", lambda: open("/m/..\\..\\x").read())
fd = os.open("/m/d", os.O_RDONLY | os.O_DIRECTORY)
t("dirfd_climb", lambda: os.open("../a.txt", os.O_RDONLY, dir_fd=fd))
t("dirfd_abs", lambda: os.open("/etc/passwd", os.O_RDONLY, dir_fd=fd))
t("write_ro_mount", lambda: open("/m/a.txt", "a").write("x"))
t("rename_mount_to_grant", lambda: os.rename("/m/a.txt", "/m/g/a.txt"))
t("mkdir_ro_mount", lambda: os.mkdir("/m/new"))
print(json.dumps(out))
'''


class Files:
    def __init__(self, tree):
        self.tree, self.seen = tree, []

    def stat(self, path):
        self.seen.append(("stat", path))
        if path == "/" or self.tree.get(path, b"") is None:
            return Stat("dir")
        return Stat("file", len(self.tree[path])) if path in self.tree else Errno.ENOENT

    def list(self, path):
        self.seen.append(("list", path))
        prefix = path.rstrip("/") + "/"
        return [
            (p[len(prefix) :], "dir" if v is None else "file")
            for p, v in self.tree.items()
            if p.startswith(prefix) and "/" not in p[len(prefix) :]
        ]

    def read(self, path):
        self.seen.append(("read", path))
        if path == "/" or self.tree.get(path, b"") is None:
            return Errno.EISDIR
        return self.tree.get(path, Errno.ENOENT)


def fixtures():
    if FX.exists():
        shutil.rmtree(FX)
    for d in ("outside", "outside_empty", "w", "r", "g"):
        (FX / d).mkdir(parents=True)
    (FX / "outside" / "canary").write_text("CANARY")
    (FX / "r" / "secret.txt").write_text("RO")
    (FX / "g" / "secret.txt").write_text("GRANT")


def host_state():
    return {
        "outside": sorted(os.listdir(FX / "outside")) if (FX / "outside").exists() else None,
        "outside_empty_exists": (FX / "outside_empty").is_dir(),
        "w": sorted(os.listdir(FX / "w")),
        "r_secret": (FX / "r" / "secret.txt").read_text(),
        "canary_nlink": os.stat(FX / "outside" / "canary").st_nlink
        if (FX / "outside" / "canary").exists()
        else None,
    }


def main():
    import importlib.metadata as _md
    report = {"wasmtime_py": _md.version("wasmtime"), "platform": sys.platform}
    fixtures()
    done = run(
        ["-c", GUEST_GRANTS],
        grants=[Grant(FX / "w", "/w", writable=True), Grant(FX / "r", "/r")],
        deadline_s=60,
    )
    report["grants"] = {
        "exit": done.exit_code,
        "trapped": done.trapped,
        "guest": done.stdout.decode(errors="replace").strip(),
        "stderr_tail": done.stderr.decode(errors="replace")[-600:],
        "host_after": host_state(),
    }
    files = Files({"/a.txt": b"A", "/d": None, "/x": b"X"})
    done = run(
        ["-c", GUEST_MOUNTS],
        mounts=[Mount(files, "/m")],
        grants=[Grant(FX / "g", "/m/g")],
        deadline_s=60,
    )
    report["mounts"] = {
        "exit": done.exit_code,
        "trapped": done.trapped,
        "guest": done.stdout.decode(errors="replace").strip(),
        "stderr_tail": done.stderr.decode(errors="replace")[-600:],
        "provider_saw": files.seen,
    }
    # A read-only grant over the module cache, and a writable one.
    cache = Path(os.environ["WASI_PYTHON_CACHE"])
    for writable in (False, True):
        key = "cache_grant_writable" if writable else "cache_grant_readonly"
        try:
            done = run(
                ["-c", "import os; print(sorted(os.listdir('/c'))[:5])"],
                grants=[Grant(cache, "/c", writable=writable)],
                cache_dir=True,
                deadline_s=60,
            )
            report[key] = {"exit": done.exit_code, "guest": done.stdout.decode().strip()}
        except ValueError as e:
            report[key] = {"refused": str(e)[:300]}
    shutil.rmtree(FX)
    print(json.dumps(report, indent=1))


main()
