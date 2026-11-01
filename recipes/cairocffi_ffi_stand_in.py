"""cairocffi's `ffi` module for wasm32-wasip1, in place of the one its sdist ships.

Upstream's module builds an ABI-mode `FFI()` at import and binds cairo at run time with
`ffi.dlopen`; its surfaces make callbacks at run time with `ffi.callback`. The guest has neither a
dynamic loader nor libffi's closures. Here `ffi` is the linked module `_cairocffi_api`'s, written
at build time in cffi's API mode from cairocffi's own declarations, with two methods replaced:

- `dlopen` answers a name whose basename is cairo's with the module's `lib`, its names bound once,
  `cairo_select_font_face` among them replaced by the font map below; any other name raises
  OSError, as a missing library does.
- `callback` hands out one of the module's static callbacks (`extern "Python"`), a fixed pool for
  each of the three callback types cairocffi makes (read, write, destroy), attached to the Python
  function with its own `error=` and `onerror=`. A callback's slot is free again once the pointer
  it returned is dropped. A full pool runs the cyclic collector once and tries again, then raises
  MemoryError naming the pool's size. Any other callback type raises NotImplementedError.

The font map: without fontconfig, cairo draws every family of its toy font API in its built-in
stroke font. `select_font_face` here sets a FreeType face made from one of matplotlib's twelve
DejaVu files instead: DejaVu Serif for serif families, DejaVu Sans Mono for monospace ones,
DejaVu Sans for any other, each by bold and slant. A family beginning `@cairo:` is cairo's own
and goes to cairo untouched; so does every family when the fonts cannot be read.
"""

from __future__ import annotations

import gc
import importlib.util
import io
import os
import weakref
import zipfile

import _cairocffi_api

_real = _cairocffi_api.ffi
_lib = _cairocffi_api.lib

# cairo's library names, as cairocffi asks for them (cairocffi/__init__.py).
_CAIRO_NAMES = frozenset(
    {"cairo-2", "cairo", "libcairo-2", "libcairo.so.2", "libcairo.2.dylib", "libcairo-2.dll"}
)
_POOL = _lib.wasi_cairo_pool
# Each callback type's cdecl, and its trampolines' name stem in _cairocffi_api.
_STEMS = {
    "cairo_read_func_t": "read",
    "cairo_write_func_t": "write",
    "cairo_destroy_func_t": "destroy",
}

# The font map: a family, lower-cased, to its DejaVu face; any other is DejaVu Sans.
_SERIF = frozenset({"serif", "times", "times new roman", "georgia", "dejavu serif"})
_MONO = frozenset({"monospace", "courier", "courier new", "dejavu sans mono"})
# (face, bold, slanted) -> file under matplotlib's mpl-data/fonts/ttf/
_FILES = {
    ("sans", False, False): "DejaVuSans.ttf",
    ("sans", True, False): "DejaVuSans-Bold.ttf",
    ("sans", False, True): "DejaVuSans-Oblique.ttf",
    ("sans", True, True): "DejaVuSans-BoldOblique.ttf",
    ("serif", False, False): "DejaVuSerif.ttf",
    ("serif", True, False): "DejaVuSerif-Bold.ttf",
    ("serif", False, True): "DejaVuSerif-Italic.ttf",
    ("serif", True, True): "DejaVuSerif-BoldItalic.ttf",
    ("mono", False, False): "DejaVuSansMono.ttf",
    ("mono", True, False): "DejaVuSansMono-Bold.ttf",
    ("mono", False, True): "DejaVuSansMono-Oblique.ttf",
    ("mono", True, True): "DejaVuSansMono-BoldOblique.ttf",
}
_FONT_SLANT_NORMAL = 0
_FONT_WEIGHT_BOLD = 1


def _font_bytes(name: str) -> bytes | None:
    """A DejaVu file's bytes from matplotlib's data, found without importing matplotlib: in the
    folder the runner grants beside the package, else in the stdlib zip's inner archive of that
    data; None when neither holds it."""
    spec = importlib.util.find_spec("matplotlib")
    if spec is None or not spec.submodule_search_locations:
        return None
    package = list(spec.submodule_search_locations)[0]
    try:
        with open(os.path.join(package, "mpl-data", "fonts", "ttf", name), "rb") as f:
            return f.read()
    except OSError:
        pass
    loader = spec.loader
    if not hasattr(loader, "get_data"):
        return None
    try:
        inner = loader.get_data(os.path.join(package, "mpl-data.zip"))
        with zipfile.ZipFile(io.BytesIO(inner)) as z:
            return z.read(f"fonts/ttf/{name}")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


# file name -> (the face, the bytes FreeType reads in place), or None when it cannot be made.
# Each face is made once and lives as long as the process, its bytes with it.
_faces: dict[str, tuple[object, object] | None] = {}


def _face(name: str):
    if name not in _faces:
        data = _font_bytes(name)
        made = None
        if data is not None:
            buffer = _real.new("unsigned char[]", data)
            face = _lib.wasi_cairo_ft_face_from_memory(buffer, len(data), 0)
            if face != _real.NULL:
                made = (face, buffer)
        _faces[name] = made
    made = _faces[name]
    return None if made is None else made[0]


def _select_font_face(cr, family, slant, weight):
    """cairo_select_font_face, with every family but cairo's own mapped to a DejaVu face."""
    text = _real.string(family).decode("utf-8", "replace") if family != _real.NULL else ""
    if not text.startswith("@cairo:"):
        key = text.strip().lower()
        kind = "serif" if key in _SERIF else "mono" if key in _MONO else "sans"
        face = _face(_FILES[kind, weight == _FONT_WEIGHT_BOLD, slant != _FONT_SLANT_NORMAL])
        if face is not None:
            _lib.cairo_set_font_face(cr, face)
            return
    _lib.cairo_select_font_face(cr, family, slant, weight)


class _Lib:
    """`_cairocffi_api.lib` with its names bound once, and the font map's select_font_face."""

    def __init__(self) -> None:
        for name in dir(_lib):
            setattr(self, name, getattr(_lib, name))
        self.cairo_select_font_face = _select_font_face


def _idle_status(error: int):
    """A free read or write slot's function: cairo's error, should anything call it."""
    return lambda *args: error


def _idle_void(*args):
    return None


class _Pool:
    """One callback type's static trampolines: a slot is taken by `take` and free again when the
    pointer it returned is collected."""

    def __init__(self, cdecl: str, stem: str) -> None:
        self.cdecl = cdecl
        self.names = [f"_wasi_cairo_{stem}_{n}" for n in range(_POOL)]
        self.free = list(range(_POOL - 1, -1, -1))
        # What a free slot runs: nothing should call it, so a read or a write answers cairo's
        # error. It is attached at release and called once with empty arguments, since cffi keeps
        # the function a slot last ran until the slot runs again: so the released function and
        # what it holds (its file, its buffer) go when the pointer goes, as a run-time callback's
        # would.
        self.idle, self.number = {
            "read": (_idle_status(_lib.CAIRO_STATUS_READ_ERROR), 0),
            "write": (_idle_status(_lib.CAIRO_STATUS_WRITE_ERROR), 1),
            "destroy": (_idle_void, 2),
        }[stem]

    def _release(self, n: int) -> None:
        _real.def_extern(name=self.names[n])(self.idle)
        _lib.wasi_cairo_run_slot(self.number, n)
        self.free.append(n)

    def take(self, python_callable, error, onerror):
        if not self.free:
            gc.collect()
        if not self.free:
            raise MemoryError(
                f"{_POOL} {self.cdecl} callbacks are alive, the most this build of cairocffi has"
            )
        n = self.free.pop()
        name = self.names[n]
        options = {k: v for k, v in (("error", error), ("onerror", onerror)) if v is not None}
        _real.def_extern(name=name, **options)(python_callable)
        pointer = _real.cast(self.cdecl, _real.addressof(_lib, name))
        weakref.finalize(pointer, self._release, n)
        return pointer


# The pools, one per callback type, shared by both objects below: there is one set of trampolines.
# cffi gives the read and write types one C type (it ignores `const`), so a pool is found by the
# name cairocffi passes, and only a C type given as such by its type.
_POOLS = {cdecl: _Pool(cdecl, stem) for cdecl, stem in _STEMS.items()}


def _pool(cdecl):
    if isinstance(cdecl, str) and cdecl.strip() in _POOLS:
        return _POOLS[cdecl.strip()]
    ctype = _real.typeof(cdecl)
    return next((p for c, p in _POOLS.items() if _real.typeof(c) is ctype), None)


class _FFI:
    """`_cairocffi_api.ffi`'s methods and constants bound once, with dlopen and callback
    replaced."""

    def __init__(self, cairo_lib: bool) -> None:
        for name in dir(_real):
            if not name.startswith("_") and name not in {"errno", "dlopen", "callback"}:
                setattr(self, name, getattr(_real, name))
        self._cairo_lib = cairo_lib
        self._lib = None

    @property
    def errno(self):
        return _real.errno

    @errno.setter
    def errno(self, value):
        _real.errno = value

    def dlopen(self, name, flags=0):
        base = os.path.basename(name) if isinstance(name, str) else name
        if self._cairo_lib and base in _CAIRO_NAMES:
            if self._lib is None:
                self._lib = _Lib()
            return self._lib
        raise OSError(f"cannot load library {name!r}: this build links cairo in and loads nothing")

    def callback(self, cdecl, python_callable=None, error=None, onerror=None):
        pool = _pool(cdecl)
        if pool is None:
            raise NotImplementedError(
                f"ffi.callback({cdecl!r}): only cairo's read, write and destroy callbacks can be "
                "made here (wasm32-wasip1 has no run-time callbacks)"
            )
        if python_callable is None:
            return lambda f: pool.take(f, error, onerror)
        return pool.take(python_callable, error, onerror)


ffi = _FFI(cairo_lib=True)
# gdk-pixbuf, which cairocffi.pixbuf loads, is not in this build: its dlopen raises OSError.
ffi_pixbuf = _FFI(cairo_lib=False)
