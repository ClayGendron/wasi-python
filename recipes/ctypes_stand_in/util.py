# The `ctypes` stand-in's `ctypes.util` (spec 033, Decision 5): the guest has no shared library to
# find, so `find_library` answers None for every name. A query whose true wasm32 answer is known is
# answered (spec 039, Decision 5): the guest is one statically linked module and loads no shared
# library, so `dllist` (CPython 3.14's list of loaded libraries, which threadpoolctl reads) is empty.


def find_library(name):
    return None


def dllist():
    return []
