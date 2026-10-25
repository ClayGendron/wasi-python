"""private() reads only the mode bits: a macOS extended ACL that lets everyone write the cache
folder, and that every new file inherits, is not seen. One OS user; scratch only."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
from wasi_python import _platform

work = Path(sys.argv[1]).resolve()
shutil.rmtree(work, ignore_errors=True)
cache = work / "cache"
cache.mkdir(parents=True, mode=0o700)
os.chmod(cache, 0o700)
subprocess.run(["/bin/chmod", "+a",
    "everyone allow list,add_file,search,delete_child,read,write,append,file_inherit,directory_inherit",
    str(cache)], check=True)
fd, tmp = tempfile.mkstemp(prefix=".cwasm-", dir=cache)  # as the runner's _store makes it
os.close(fd)
f = cache / "x-wasmtime49.0.0-plain.cwasm"
os.replace(tmp, f)
print(subprocess.run(["/bin/ls", "-led", str(cache)], capture_output=True, text=True).stdout)
print(subprocess.run(["/bin/ls", "-le", str(f)], capture_output=True, text=True).stdout)
print("private(cache dir):", _platform.PLATFORM.private(cache, is_dir=True))
print("private(cwasm file):", _platform.PLATFORM.private(f, is_dir=False))
shutil.rmtree(work)
