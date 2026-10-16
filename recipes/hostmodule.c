/* The host door: the builtin module `_host` (spec 003, Decision 5).
 *
 * The guest reaches its host through WASI preview1 and this one custom import, nothing else
 * (constitution section 4.4). A call passes a request frame; the host answers by asking the guest
 * for memory through the exported `host_alloc`, writing the response there, and storing its
 * pointer and length at the two out-addresses. Frames are opaque bytes: their meaning is the
 * embedder's.
 *
 *   host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0   answered
 *                                                    -1  no host is bound (a runner's default)
 *                                                    -2  the host faulted
 *
 * The host writes the two out-addresses only when it answers 0, and the pointer is one host_alloc
 * returned (NULL only with length 0). A negative length, or a NULL pointer with a length, raises
 * OSError; whatever pointer is there afterwards is freed.
 */
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>

__attribute__((import_module("host"), import_name("call")))
extern int32_t host_door_call(int32_t ptr, int32_t len, int32_t out_ptr_ptr, int32_t out_len_ptr);

/* The host allocates the response in guest memory through this export; `_host.call` frees it. */
__attribute__((export_name("host_alloc")))
void *
host_alloc(int32_t len)
{
    return malloc(len > 0 ? (size_t)len : 1);
}

static int last_call_answered = 0;

static PyObject *
host_call(PyObject *module, PyObject *frame)
{
    Py_buffer request;
    if (PyObject_GetBuffer(frame, &request, PyBUF_SIMPLE) < 0) {
        return NULL;
    }
    /* Zeroed first: a host that answers 0 without writing yields b"". */
    uint8_t *response = NULL;
    int32_t response_len = 0;
    int32_t rc = host_door_call((int32_t)(uintptr_t)request.buf, (int32_t)request.len,
                                (int32_t)(uintptr_t)&response, (int32_t)(uintptr_t)&response_len);
    PyBuffer_Release(&request);
    last_call_answered = (rc == 0);
    if (rc == 0 && (response_len < 0 || (response == NULL && response_len > 0))) {
        /* A host that broke the contract: never hand guest memory it did not write to Python. */
        free(response);
        PyErr_Format(PyExc_OSError, "the host answered with a malformed response (length %d%s)",
                     (int)response_len, response == NULL ? ", no pointer" : "");
        return NULL;
    }
    if (rc == 0) {
        PyObject *result = PyBytes_FromStringAndSize((const char *)response, response_len);
        free(response);
        return result;
    }
    free(response);
    if (rc == -1) {
        PyErr_SetString(PyExc_ConnectionRefusedError, "no host is bound to the door");
    }
    else if (rc == -2) {
        PyErr_SetString(PyExc_OSError, "the host faulted while answering the door");
    }
    else {
        PyErr_Format(PyExc_OSError, "host door returned %d", (int)rc);
    }
    return NULL;
}

static PyObject *
host_available(PyObject *module, PyObject *unused)
{
    return PyBool_FromLong(last_call_answered);
}

static PyMethodDef host_methods[] = {
    {"call", host_call, METH_O,
     "call(frame: bytes) -> bytes\n\nSend one request frame through the door and return the "
     "host's response. Raises ConnectionRefusedError when no host is bound and OSError when the "
     "host faults."},
    {"available", host_available, METH_NOARGS,
     "available() -> bool\n\nWhether the last call was answered by a host."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef host_module = {
    PyModuleDef_HEAD_INIT, "_host", "The host door: one custom import, frames are opaque bytes.",
    0, host_methods,
};

PyMODINIT_FUNC
PyInit__host(void)
{
    return PyModuleDef_Init(&host_module);
}
