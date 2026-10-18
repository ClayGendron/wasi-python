# The `ctypes` stand-in's `ctypes.util` (spec 033, Decision 5): the guest has no shared library to
# find, so `find_library` answers None for every name.


def find_library(name):
    return None
