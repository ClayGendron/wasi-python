# A stand-in for the stdlib `ctypes` on wasm32-wasip1, packed as `ctypes/` (spec 033, Decision 5).
#
# The guest has no `_ctypes`: wasi-sdk has no libffi. numpy and pandas import `ctypes` anyway
# (numpy/_core/_internal.py, pandas/errors/__init__.py), and other importers name C types at import.
# This package names and sizes wasm32's C types and gives numpy the dtype it gives a real one. It
# loads no library and calls nothing: every such use raises OSError, as a missing library does.
#
# Only the names below exist at import. The first lookup of any other public name imports
# `ctypes._types`, which builds them all; they are then stored here, so later lookups are plain
# reads.
# `import numpy` and `import pandas` never build them.
# (Comments, not a docstring: this module loads on every `import numpy`.)

_MSG = "ctypes is unavailable on wasm32-wasi"
DEFAULT_MODE = RTLD_LOCAL = 0
RTLD_GLOBAL = 256


def WinError(code=None, descr=None):
    raise OSError(_MSG)


_BUILT = (
    "c_bool", "c_char", "c_wchar", "c_byte", "c_ubyte", "c_short", "c_ushort", "c_int", "c_uint",
    "c_long", "c_ulong", "c_longlong", "c_ulonglong", "c_size_t", "c_ssize_t", "c_float",
    "c_double", "c_longdouble", "c_char_p", "c_wchar_p", "c_void_p", "c_int8", "c_int16",
    "c_int32", "c_int64", "c_uint8", "c_uint16", "c_uint32", "c_uint64", "c_time_t",
    "Structure", "Union", "POINTER", "CFUNCTYPE", "PYFUNCTYPE", "sizeof",
    "CDLL", "PyDLL", "LibraryLoader", "cdll", "pydll",
    "byref", "pointer", "cast", "addressof", "memmove", "memset", "string_at", "wstring_at",
    "create_string_buffer", "create_unicode_buffer", "resize", "get_errno", "set_errno",
)  # fmt: skip
__all__ = ["DEFAULT_MODE", "RTLD_GLOBAL", "RTLD_LOCAL", "WinError", *_BUILT]
# Private names C code reads (spec 037): scipy's QUADPACK checks every integrand against
# ctypes._CFuncPtr, the base of the function types, before it calls back into Python.
_PRIVATE = ("_CFuncPtr",)


def __getattr__(name):
    if name in _BUILT or name in _PRIVATE:
        from . import _types

        here = globals()
        for built in (*_BUILT, *_PRIVATE):
            here[built] = getattr(_types, built)
        return here[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted({*globals(), *__all__})
