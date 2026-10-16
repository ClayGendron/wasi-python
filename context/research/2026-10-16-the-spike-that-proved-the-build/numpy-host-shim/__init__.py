# host-side stand-in for the numpy package during the pandas cross build (spike s12):
# the headers are the WASI build's (sizeof(long double) == 16), assembled next to this file.
import os
__version__ = "2.5.2"
def get_include():
    return os.path.join(os.path.dirname(__file__), "_core", "include")
