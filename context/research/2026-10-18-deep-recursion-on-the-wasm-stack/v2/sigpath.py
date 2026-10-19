"""Spec 071 v2: does dladdr name the same file wasmtime-py loaded (wasmtime._ffi.dll._name)?"""
import ctypes, os, signal, wasmtime
from wasmtime import _ffi
libc = ctypes.CDLL(None)
class Dl_info(ctypes.Structure):
    _fields_ = [("dli_fname", ctypes.c_char_p), ("dli_fbase", ctypes.c_void_p),
                ("dli_sname", ctypes.c_char_p), ("dli_saddr", ctypes.c_void_p)]
libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(Dl_info)]
libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
wasmtime.Engine()
buf = (ctypes.c_char * 1024)()
libc.sigaction(signal.SIGILL, None, buf)
info = Dl_info(); libc.dladdr(ctypes.c_void_p.from_buffer(buf).value, ctypes.byref(info))
print("dll._name      ", os.path.realpath(_ffi.dll._name))
print("dladdr(SIGILL) ", os.path.realpath(info.dli_fname.decode()))
print("same file      ", os.path.samefile(_ffi.dll._name, info.dli_fname.decode()))
