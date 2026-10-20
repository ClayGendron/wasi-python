"""Spec 099 phase 1 smoke compile: four real numpy compiles from main's compile records, each run
again with the worktree's npy_fenv_flags.h force-included (as the new cross file adds it), into a
scratch folder; dependency-file flags dropped so nothing is written into main's build tree. Then
llvm-nm on each object: the weak word, and no call left to the C library's fe* functions."""

import json
import os
import shlex
import subprocess
import sys

MAIN = "/Users/claygendron/Git/Repos/wasi_python"
WT = sys.argv[1]
OUT = sys.argv[2]
SDK = f"{MAIN}/build/tools/wasi-sdk-34.0-arm64-macos"
WANT = ("ieee754.c", "halffloat.cpp", "umath_linalg.cpp", "loops_arithmetic.dispatch.c")

records = json.load(open(f"{MAIN}/build/numpy-build/compile_commands.json"))
env = dict(os.environ, WASI_SDK_PATH=SDK)
for e in records:
    if not e["file"].endswith(WANT):
        continue
    argv = shlex.split(e["command"])
    kept, skip = [], 0
    for a in argv:
        if skip:
            skip -= 1
            continue
        if a in ("-MD",):
            continue
        if a in ("-MQ", "-MF", "-o"):
            skip = 1
            continue
        kept.append(a)
    name = os.path.basename(e["file"]) + ".o"
    wrapper = kept[0].replace(f"{MAIN}/scripts/", f"{WT}/scripts/")
    inc = [] if os.environ.get("NO_HEADER") else ["-include", f"{WT}/recipes/npy_fenv_flags.h"]
    cmd = [wrapper, *inc, *kept[1:], "-o", f"{OUT}/{name}"]
    r = subprocess.run(cmd, cwd=e["directory"], env=env, capture_output=True, text=True)
    nm = subprocess.run([f"{SDK}/bin/llvm-nm", f"{OUT}/{name}"], capture_output=True, text=True)
    lines = [ln for ln in nm.stdout.splitlines() if "fe_flags" in ln or "fetestexcept" in ln
             or "feraiseexcept" in ln or "feclearexcept" in ln]
    warned, failed = r.stderr.count("warning:"), r.stderr.count("error:")
    print(f"{name}: exit {r.returncode}; warnings {warned}; errors {failed}")
    print("   ", "; ".join(" ".join(ln.split()) for ln in lines) or "(no fe symbol)")
    if r.returncode:
        print(r.stderr[-1500:])
