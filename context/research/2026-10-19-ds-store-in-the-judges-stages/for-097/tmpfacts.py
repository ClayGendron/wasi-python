import os
import pathlib
import tempfile

t = tempfile.gettempdir()
print("gettempdir", t, "realpath", os.path.realpath(t))
p = pathlib.Path(os.path.realpath(t))
for q in [p, *p.parents]:
    st = os.lstat(q)
    print(oct(st.st_mode), st.st_uid, q, "link" if os.path.islink(q) else "")
print("/var ->", os.readlink("/var"))
print("dev temp", os.stat(t).st_dev, "dev home", os.stat(os.path.expanduser("~")).st_dev)
print("home", pathlib.Path.home(), pathlib.Path.home().resolve())
