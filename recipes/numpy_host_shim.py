# Host-side stand-in for the numpy package during the pandas cross build (spec 003, Decision 6).
# pandas' meson asks the target Python for numpy.get_include(); the build-Python must not import a
# native numpy (its _numpyconfig.h would say sizeof(long double) == 8). Step 40 installs this file as
# build/numpy-host/numpy/__init__.py beside the WASI build's headers. (The spike's file, brought in.)
import os

__version__ = "2.5.2"


def get_include():
    return os.path.join(os.path.dirname(__file__), "_core", "include")
