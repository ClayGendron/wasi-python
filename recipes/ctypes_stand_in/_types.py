"""The `ctypes` stand-in's types, factories, libraries and memory functions (spec 033, Decision 5).

Imported by `ctypes.__getattr__` on the first lookup of a type name, never at `import ctypes`.

The rule: a name exists so that an import succeeds. Declaring a type works (a simple type, a
`Structure` or `Union` subclass with `_fields_`, `POINTER(t)`, `CFUNCTYPE(...)`, `t * n`), and
`sizeof` answers where the answer is a true fact on wasm32. Anything that would load a library,
touch memory or make an instance raises OSError with the message `import ctypes` raises today.
Two exceptions:
- (spec 037, Revised at build) `cast(address, F)`, an int (or None) to a function type F, gives an
  F that holds the integer and cannot be called. scipy's `_lib._ccallback_c` makes three at import,
  of its own test callbacks, so `import scipy` needs it; calling one raises OSError.
- (spec 038, Decision 3) The numeric simple types and `c_void_p` hold values: an instance's
  `.value` is stored as wasm32 C stores it (an integer wraps to the type's width and signedness,
  `c_float` rounds to single precision, `c_bool` is a bool, `c_void_p` an unsigned 32-bit integer
  or None for NULL), and `cast(x, c_void_p)` of an int, None or a `c_void_p` is a new `c_void_p`.
  Nothing has an address: `byref`, `pointer`, `addressof` and the `from_*` methods still refuse,
  so numpy's `ndarray.ctypes.data_as(c_void_p)` and scipy's `LowLevelCallable` user data work and
  no foreign call can be made.

The aliases follow CPython's own rule (Lib/ctypes/__init__.py), from `struct.calcsize` in the
guest, so on wasm32 `c_int is c_long`, `c_size_t is c_ulong` and `c_int32 is c_long`.
"""

import struct
import sys

from . import _MSG

_MODULE = __name__.rpartition(".")[0]
_POINTER_SIZE = struct.calcsize("P")
_WCHAR_SIZE = 4  # WASI's wchar_t is 32-bit; `struct` has no code for it
_LONGDOUBLE_SIZE = 16  # wasm32's long double is 128-bit; `struct` has no code for it


def _refuse(*args, **kwargs):
    raise OSError(_MSG)


class _Refused:
    """A class attribute that raises the OSError when read."""

    def __get__(self, obj, cls=None):
        raise OSError(_MSG)


class _NumpyDtype:
    """A simple type's dtype, as numpy computes it for a real one (numpy/_core/_dtype_ctypes.py,
    `_from_ctypes_scalar`). Without it numpy would treat the type as a plain class: dtype('O')."""

    def __get__(self, obj, cls=None):
        if cls is _SimpleCData:  # the abstract base, read by help() and np.info: no dtype
            return self
        numpy = sys.modules.get("numpy")
        if numpy is None:  # only numpy asks, and numpy is loaded then
            raise AttributeError("__numpy_dtype__")
        return numpy.dtype(cls._numpy_code_)


class _CType(type):
    """The stand-in types' metaclass: `t * n` and `n * t` declare an array type."""

    def __mul__(cls, length):
        if not isinstance(length, int) or length < 0:
            return NotImplemented
        return _array_type(cls, length)

    __rmul__ = __mul__


class _CData(metaclass=_CType):
    """Every stand-in type: no instance, no foreign call."""

    _size_ = None  # None: no layout is computed (Structure, Union)
    from_buffer = from_buffer_copy = from_address = from_param = in_dll = classmethod(_refuse)

    def __new__(cls, *args, **kwargs):
        raise OSError(_MSG)


class _SimpleCData(_CData):
    """A simple type. Those of spec 038's Decision 3 set `_store_`, which turns a value into what
    wasm32 C would store, and so hold values; for the others it is None and an instance refuses."""

    __numpy_dtype__ = _NumpyDtype()
    _store_ = None
    _zero_ = 0  # the value of an instance made with none

    def __new__(cls, *args, **kwargs):
        if cls._store_ is None:
            raise OSError(_MSG)
        return object.__new__(cls)

    def __init__(self, *value):
        if len(value) > 1:
            raise TypeError(f"{type(self).__name__}() takes at most one value")
        self.value = value[0] if value else self._zero_

    @property
    def value(self):
        return self._value_

    @value.setter
    def value(self, value):
        self._value_ = type(self)._store_(value)

    def __repr__(self):
        return f"{type(self).__name__}({self._value_!r})"


class _NoLayout(_CData):
    """Structure, Union, array, pointer and function types. numpy reads `__numpy_dtype__` first;
    without it numpy would make dtype('O'), so it refuses. It sits here, not on _CData, so that
    help() and np.info, which read every base class, still document the module and the simple
    types."""

    __numpy_dtype__ = _Refused()


def _simple(name, code, size, numpy_code=None):
    return _CType(
        name,
        (_SimpleCData,),
        {"_type_": code, "_size_": size, "_numpy_code_": numpy_code or code, "__module__": _MODULE},
    )


_arrays = {}


def _array_type(element, length):
    key = (element, length)
    if key not in _arrays:
        size = None if element._size_ is None else element._size_ * length
        _arrays[key] = _CType(
            f"{element.__name__}_Array_{length}",
            (_NoLayout,),
            {"_type_": element, "_length_": length, "_size_": size, "__module__": _MODULE},
        )
    return _arrays[key]


def _size(code):
    return struct.calcsize(code)


# The simple types CPython makes as classes everywhere.
c_bool = _simple("c_bool", "?", _size("?"))
c_char = _simple("c_char", "c", _size("c"))
c_wchar = _simple("c_wchar", "u", _WCHAR_SIZE)
c_byte = _simple("c_byte", "b", _size("b"))
c_ubyte = _simple("c_ubyte", "B", _size("B"))
c_short = _simple("c_short", "h", _size("h"))
c_ushort = _simple("c_ushort", "H", _size("H"))
c_long = _simple("c_long", "l", _size("l"))
c_ulong = _simple("c_ulong", "L", _size("L"))
c_float = _simple("c_float", "f", _size("f"))
c_double = _simple("c_double", "d", _size("d"))
c_char_p = _simple("c_char_p", "z", _POINTER_SIZE)
c_wchar_p = _simple("c_wchar_p", "Z", _POINTER_SIZE)
c_void_p = _simple("c_void_p", "P", _POINTER_SIZE)

# CPython's aliases: one class where two C types have one size.
if _size("i") == _size("l"):
    c_int, c_uint = c_long, c_ulong
else:
    c_int, c_uint = _simple("c_int", "i", _size("i")), _simple("c_uint", "I", _size("I"))
if _size("q") == _size("l"):
    c_longlong, c_ulonglong = c_long, c_ulong
else:
    c_longlong = _simple("c_longlong", "q", _size("q"))
    c_ulonglong = _simple("c_ulonglong", "Q", _size("Q"))
if _LONGDOUBLE_SIZE == _size("d"):
    c_longdouble = c_double
else:
    c_longdouble = _simple("c_longdouble", "g", _LONGDOUBLE_SIZE)
for _unsigned, _signed in ((c_uint, c_int), (c_ulong, c_long), (c_ulonglong, c_longlong)):
    if _unsigned._size_ == _POINTER_SIZE:
        c_size_t, c_ssize_t = _unsigned, _signed
        break
_widths = {}  # the last of c_short, c_int, c_long, c_longlong of each size, as in CPython
for _signed, _unsigned in ((c_short, c_ushort), (c_int, c_uint), (c_long, c_ulong),
                           (c_longlong, c_ulonglong)):  # fmt: skip
    _widths[_signed._size_] = (_signed, _unsigned)
c_int8, c_uint8 = c_byte, c_ubyte
c_int16, c_uint16 = _widths[2]
c_int32, c_uint32 = _widths[4]
c_int64, c_uint64 = _widths[8]
c_time_t = c_int64  # WASI's time_t is 8 bytes (SIZEOF_TIME_T in the build's _sysconfigdata)

def _index(value):
    """`operator.index` without importing `operator` (spec 038, Decision 6: the first lookup
    imports nothing a start has not): an object's `__index__`, or TypeError, as CPython says."""
    try:
        index = type(value).__index__
    except AttributeError:
        raise TypeError(f"an integer is required, not {type(value).__name__}") from None
    result = index(value)
    if not isinstance(result, int):
        raise TypeError(f"__index__ returned non-int (type {type(result).__name__})")
    return int(result)


def _storer(code, bits):
    """What wasm32 C stores for a value given to a numeric simple type (spec 038, Decision 3)."""
    if code == "?":
        return bool
    if code == "f":
        return _single
    if code in "dg":
        return _double
    size, signed = 1 << bits, code.islower()

    def wrap(value):
        n = _index(value) % size  # TypeError for a float or a str, as CPython's ctypes
        return n - size if signed and n >= size >> 1 else n

    return wrap


def _double(value):
    if isinstance(value, (str, bytes, bytearray)):  # float() would parse them; ctypes refuses
        raise TypeError(f"must be real number, not {type(value).__name__}")
    return float(value)


def _single(value):
    value = _double(value)
    try:
        return struct.unpack("f", struct.pack("f", value))[0]
    except OverflowError:  # beyond float's range: C's conversion gives the infinity of that sign
        return float("inf") if value > 0 else float("-inf")


def _address(value):
    """c_void_p's value: an unsigned pointer-width integer, or None for NULL (CPython's ctypes
    reads a zero pointer as None)."""
    if value is None:
        return None
    if isinstance(value, _CData) or not hasattr(type(value), "__index__"):
        raise TypeError(f"cannot be converted to pointer: {type(value).__name__}")
    return _index(value) % (1 << 8 * _POINTER_SIZE) or None


c_void_p._store_, c_void_p._zero_ = staticmethod(_address), None

# Byte order, as numpy's _from_ctypes_scalar and as_ctypes_type read it: on little-endian wasm32
# each numeric type is its own __ctype_le__; its __ctype_be__ is itself when one byte wide, else a
# big-endian twin.
_numeric = (c_bool, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, c_long, c_ulong,
            c_longlong, c_ulonglong, c_float, c_double, c_longdouble)  # fmt: skip
for _t in dict.fromkeys(_numeric):  # an alias once
    _t._store_ = staticmethod(_storer(_t._type_, 8 * _t._size_))
    _t.__ctype_le__ = _t
    if _t._size_ == 1:
        _t.__ctype_be__ = _t
    else:
        _twin = _simple(_t.__name__ + "_be", _t._type_, _t._size_, ">" + _t._type_)
        _twin.__ctype_be__, _twin.__ctype_le__ = _twin, _t
        _t.__ctype_be__ = _twin


class Structure(_NoLayout):
    __module__ = _MODULE


class Union(_NoLayout):
    __module__ = _MODULE


_pointers = {}


def POINTER(cls):
    if cls not in _pointers:
        name = f"LP_{getattr(cls, '__name__', cls)}"
        _pointers[cls] = _CType(name, (_NoLayout,), {"_type_": cls, "_size_": _POINTER_SIZE})
    return _pointers[cls]


class _FunctionPointer(_NoLayout):
    """A function type. Its only instances come from `cast` of an address: each holds the integer
    and has no way to be called, since there is no libffi; calling one raises OSError."""

    def __call__(self, *args, **kwargs):
        raise OSError(_MSG)


_CFuncPtr = _FunctionPointer  # the name CPython's ctypes gives the function types' base
_functions = {}


def CFUNCTYPE(restype, *argtypes, **kwargs):
    key = (restype, argtypes, tuple(sorted(kwargs.items())))
    if key not in _functions:
        _functions[key] = _CType(
            "CFunctionType",
            (_FunctionPointer,),
            {"_restype_": restype, "_argtypes_": argtypes, "_size_": _POINTER_SIZE},
        )
    return _functions[key]


def PYFUNCTYPE(restype, *argtypes):
    return CFUNCTYPE(restype, *argtypes, pyfunc=True)


def sizeof(obj):
    """A stand-in type's size on wasm32; OSError for a Structure or Union (no layout is computed);
    TypeError for anything else, as CPython says."""
    cls = obj if isinstance(obj, type) else type(obj)
    if not isinstance(cls, _CType):
        raise TypeError("this type has no size")
    if cls._size_ is None:
        raise OSError(_MSG)
    return cls._size_


class CDLL:
    def __init__(self, *args, **kwargs):
        raise OSError(_MSG)


class PyDLL(CDLL):
    pass


class LibraryLoader:
    def __init__(self, dlltype):
        self._dlltype = dlltype

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._dlltype(name)

    def __getitem__(self, name):
        return self._dlltype(name)

    def LoadLibrary(self, name):
        return self._dlltype(name)


cdll = LibraryLoader(CDLL)
pydll = LibraryLoader(PyDLL)


def cast(*args, **kwargs):
    """An address (an int, or None for NULL) cast to a function type: an instance holding it,
    which cannot be called (spec 037). An int, None or a `c_void_p` cast to `c_void_p`: a new
    `c_void_p` with that value (spec 038). Any other cast, or call, raises OSError."""
    obj, typ = args if len(args) == 2 and not kwargs else (None, None)
    if typ is c_void_p:
        if isinstance(obj, c_void_p):
            return c_void_p(obj.value)
        if obj is None or (isinstance(obj, int) and not isinstance(obj, bool)):
            return c_void_p(obj)
    elif isinstance(typ, _CType) and issubclass(typ, _FunctionPointer):
        if obj is None or (isinstance(obj, int) and not isinstance(obj, bool)):
            made = object.__new__(typ)
            made._address_ = obj
            return made
    raise OSError(_MSG)


byref = pointer = addressof = memmove = memset = string_at = wstring_at = _refuse
create_string_buffer = create_unicode_buffer = resize = get_errno = set_errno = _refuse
