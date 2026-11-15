//! `_rust_probe`, a builtin module the build's own checks use and nobody else should: it panics on
//! purpose, and builds a hash map whose order depends on the keys Rust's standard library draws from
//! the guest's entropy.
//!
//! - `panic(message)` panics inside a PyO3 function. PyO3 catches the unwind at its boundary and
//!   raises `pyo3_runtime.PanicException`, so the run goes on. Built with panics that abort, it
//!   ends the run instead.
//! - `panic_in_c(message)` panics inside a plain C entry point, the way orjson's functions are
//!   written. Nothing can catch an unwind there, so it ends the run under either strategy.
//! - `hashed(keys)` returns the keys in the order a `std::collections::HashMap` holds them. Two
//!   images prepared alike give the same order only if the map's random keys were drawn from the
//!   entropy the preparation pins.

use std::cell::UnsafeCell;
use std::ffi::{c_char, CStr};

use pyo3::ffi;

/// A method table entry CPython reads and writes through a pointer, so it lives in a static that
/// is shared by every interpreter of the process.
struct MethodDef(UnsafeCell<ffi::PyMethodDef>);

// CPython reads the entry while it holds the interpreter's lock; nothing else touches it.
unsafe impl Sync for MethodDef {}

static PANIC_IN_C: MethodDef = MethodDef(UnsafeCell::new(ffi::PyMethodDef {
    ml_name: c"panic_in_c".as_ptr(),
    ml_meth: ffi::PyMethodDefPointer {
        PyCFunction: panic_in_c,
    },
    ml_flags: ffi::METH_O,
    ml_doc: c"Panic in a plain C entry point; the run ends.".as_ptr(),
}));

/// The C entry point: its argument is the message, a `str`. A panic may not leave an
/// `extern "C"` function, so Rust aborts here after printing the message.
unsafe extern "C" fn panic_in_c(_module: *mut ffi::PyObject, arg: *mut ffi::PyObject) -> *mut ffi::PyObject {
    let text: *const c_char = unsafe { ffi::PyUnicode_AsUTF8AndSize(arg, std::ptr::null_mut()) };
    if text.is_null() {
        return std::ptr::null_mut();
    }
    let message = unsafe { CStr::from_ptr(text) }.to_string_lossy().into_owned();
    panic!("{message}");
}

#[pyo3::pymodule]
mod _rust_probe {
    use std::collections::HashMap;

    use pyo3::prelude::*;
    use pyo3::types::PyCFunction;

    /// Panic with the message; PyO3 raises it as `PanicException`.
    #[pyfunction]
    fn panic(message: &str) -> PyResult<()> {
        panic!("{message}");
    }

    /// The keys in the order a standard `HashMap` built from them iterates.
    #[pyfunction]
    fn hashed(keys: Vec<String>) -> Vec<String> {
        let map: HashMap<String, ()> = keys.into_iter().map(|k| (k, ())).collect();
        map.into_keys().collect()
    }

    #[pymodule_init]
    fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
        let py = m.py();
        // SAFETY: the entry is a static, so it outlives the function object CPython makes from it.
        let raw = unsafe { pyo3::ffi::PyCFunction_NewEx(super::PANIC_IN_C.0.get(), m.as_ptr(), std::ptr::null_mut()) };
        let function = unsafe { Bound::from_owned_ptr_or_err(py, raw)? }.cast_into::<PyCFunction>()?;
        m.add("panic_in_c", function)
    }
}
