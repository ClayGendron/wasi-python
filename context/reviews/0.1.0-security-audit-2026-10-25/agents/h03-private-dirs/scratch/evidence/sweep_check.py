"""Bounded local check of the sweep and the no-follow remover, in a temporary folder under
scratch (TMPDIR points there). Same-user fixtures only: another OS user cannot be staged here.

Fixtures, each named as the runner names its private folders:
  dead:    an unlocked lock with this kernel's identity, and a folder holding a link to a file
           outside, a link to a folder outside, a nested tree, and a FIFO;
  live:    a lock held by flock on another open file description, and its folder;
  foreign: an unlocked lock naming another kernel, and its folder;
  lone:    an unlocked lock with this kernel's identity and no folder;
  linkdir: an unlocked lock with this identity, where the folder is a link to a folder outside.
"""

import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path

from wasi_python import _platform, _private_dirs

temp = Path(tempfile.gettempdir())
outside = Path(sys.argv[1]) / "work" / "outside"
outside.mkdir(parents=True, exist_ok=True)
(outside / "keep.txt").write_text("keep")
(outside / "sub").mkdir(exist_ok=True)
(outside / "sub" / "keep2.txt").write_text("keep")
identity = _platform.PLATFORM.kernel_identity()


def lock(name, text, hold=False):
    p = temp / f"{name}.lock"
    fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, text)
    if hold:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    os.close(fd)
    return None


names = {k: f"wasi-python-root-{os.urandom(8).hex()}" for k in ("dead", "live", "foreign", "lone", "linkdir")}
ident = (identity or "").encode() + b"\n"
lock(names["dead"], ident)
d = temp / names["dead"]
d.mkdir(mode=0o700)
(d / "a" / "b" / "c").mkdir(parents=True)
(d / "a" / "b" / "c" / "f.txt").write_text("x")
os.symlink(outside / "keep.txt", d / "link_to_file")
os.symlink(outside / "sub", d / "a" / "link_to_dir")
os.mkfifo(d / "fifo")
held = lock(names["live"], ident, hold=True)
(temp / names["live"]).mkdir(mode=0o700)
(temp / names["live"] / "data").write_text("live")
lock(names["foreign"], b"another-kernel\n")
(temp / names["foreign"]).mkdir(mode=0o700)
lock(names["lone"], ident)
lock(names["linkdir"], ident)
os.symlink(outside / "sub", temp / names["linkdir"])

_private_dirs._sweep_once()

state = {
    "kernel_identity_known": identity is not None,
    "dead_folder_exists": os.path.lexists(temp / names["dead"]),
    "dead_lock_exists": os.path.lexists(temp / f"{names['dead']}.lock"),
    "live_folder_exists": os.path.lexists(temp / names["live"]),
    "live_lock_exists": os.path.lexists(temp / f"{names['live']}.lock"),
    "foreign_folder_exists": os.path.lexists(temp / names["foreign"]),
    "lone_lock_exists": os.path.lexists(temp / f"{names['lone']}.lock"),
    "linkdir_link_exists": os.path.lexists(temp / names["linkdir"]),
    "outside_file_kept": (outside / "keep.txt").read_text() == "keep",
    "outside_subdir_file_kept": (outside / "sub" / "keep2.txt").read_text() == "keep",
}
os.close(held)
Path(sys.argv[1], "evidence", "sweep_result.json").write_text(json.dumps(state, indent=1))
print(json.dumps(state, indent=1))
