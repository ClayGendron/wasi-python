"""zip_hybrid.py <site-packages> <zip> <program> [args]: run <program> with the pure parts of
sklearn and statsmodels (and their pure dependencies) imported from <zip>, and their extension
modules loaded from <site-packages> by name, as the guest's builtins are: a model of the guest's
import path on the host."""
import importlib.abc, importlib.machinery, importlib.util, runpy, sys
from pathlib import Path

site, zpath, program = sys.argv[1], sys.argv[2], sys.argv[3]
PKGS = ("sklearn", "statsmodels")


class Native(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(PKGS):
            return None
        rel = Path(site, *fullname.split("."))
        for so in rel.parent.glob(rel.name + ".cpython-*.so"):
            loader = importlib.machinery.ExtensionFileLoader(fullname, str(so))
            return importlib.util.spec_from_file_location(fullname, so, loader=loader)
        return None


sys.meta_path.insert(0, Native())
sys.path.insert(0, zpath)
sys.argv = [program, *sys.argv[4:]]
runpy.run_path(program, run_name="__main__")
