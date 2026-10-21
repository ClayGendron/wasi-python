"""Guest side, survey only: run the inline test_* functions of every patsy module the product
ships (patsy's setup.cfg collects *.py under patsy/), writing drive.py-style R lines."""

import importlib
import os
import sys
import traceback
import zipfile

sys.path.append("/upstream-patsy/kit")
sys.dont_write_bytecode = True
os.makedirs("/tmp/upstream", exist_ok=True)
out = open("/tmp/upstream/outcomes.txt", "w")  # noqa: SIM115
zip_path = next(p for p in sys.path if p.endswith(".zip"))
with zipfile.ZipFile(zip_path) as z:
    mods = sorted(n.removesuffix(".pyc").replace("/", ".") for n in z.namelist()
                  if n.startswith("patsy/") and n.endswith(".pyc"))
for m in mods:
    m = m.removesuffix(".__init__")
    name = m.rsplit(".", 1)[-1]
    if name.startswith("test_"):
        continue
    try:
        mod = importlib.import_module(m)
    except Exception as e:  # noqa: BLE001
        out.write(f"X {m} -- {type(e).__name__}: {e}\n")
        continue
    for attr in sorted(vars(mod)):
        fn = getattr(mod, attr)
        if attr.startswith("test_") and callable(fn) and getattr(fn, "__module__", "") == m:
            try:
                fn()
                out.write(f"R passed ::functions:{m}.{attr} -- \n")
            except BaseException as e:  # noqa: BLE001 (pytest's Skipped is a BaseException)
                tb = traceback.format_exception_only(type(e), e)[-1].strip()[:150]
                kind = "skipped" if type(e).__name__ == "Skipped" else "failed"
                out.write(f"R {kind} ::functions:{m}.{attr} -- {tb}\n")
    out.flush()
out.write("E 0\n")
out.close()
