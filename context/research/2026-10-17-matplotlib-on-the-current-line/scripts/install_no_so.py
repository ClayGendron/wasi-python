"""Copy a meson build's installed files (meson introspect --installed) into DEST, skipping the
extension archives (they are linked into python.wasm, not installed)."""
import json, shutil, subprocess, sys
from pathlib import Path
build, dest, hp = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
out = subprocess.run([hp, "-m", "mesonbuild.mesonmain", "introspect", build, "--installed"],
                     check=True, capture_output=True, text=True).stdout
n = 0
for src, dst in json.loads(out).items():
    if dst.endswith(".so"):
        continue
    marker = "site-packages/"
    if marker not in dst:
        continue
    target = dest / dst.split(marker, 1)[1]
    target.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).is_dir():
        shutil.copytree(src, target, dirs_exist_ok=True)
    else:
        shutil.copyfile(src, target)
    n += 1
print(build, n, "files")
