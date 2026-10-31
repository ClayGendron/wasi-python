/* Teardown's allocations through the three domains, counted natively: a hook installed at the
 * program's last line that counts only once Py_IsFinalizing() is true. With TALLY_SKIP set, it
 * also skips frees, threading each skipped block onto a list through its first word, and frees
 * them all once the bytes asked pass TALLY_B (the design of the specification). */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static PyMemAllocatorEx prev[3];
static void *skipped[3];
static int skip = 0, drained = 0;
static size_t limit = 0, asked = 0, allocs = 0, frees = 0, skips = 0, biggest = 0;

static int armed(void) { return Py_IsFinalizing(); }

static void drain(void) {
    if (drained) return;
    drained = 1;
    for (int d = 0; d < 3; d++) {
        void *p = skipped[d];
        skipped[d] = NULL;
        while (p) { void *next = *(void **)p; prev[d].free(prev[d].ctx, p); p = next; }
    }
}
static void note(size_t n) {
    if (!armed()) return;
    asked += n; allocs++;
    if (n > biggest) biggest = n;
    if (skip && !drained && limit && asked > limit) drain();
}
static void *h_malloc(void *ctx, size_t n) {
    PyMemAllocatorEx *p = ctx; note(n); return p->malloc(p->ctx, n);
}
static void *h_calloc(void *ctx, size_t a, size_t b) {
    PyMemAllocatorEx *p = ctx; note(a * b); return p->calloc(p->ctx, a, b);
}
static void *h_realloc(void *ctx, void *q, size_t n) {
    PyMemAllocatorEx *p = ctx; note(n); return p->realloc(p->ctx, q, n);
}
static void h_free(void *ctx, void *q) {
    PyMemAllocatorEx *p = ctx;
    if (q && armed()) {
        frees++;
        if (skip && !drained) {
            int d = (int)(p - prev);
            *(void **)q = skipped[d]; skipped[d] = q; skips++;
            return;
        }
    }
    p->free(p->ctx, q);
}
static void report(void) {
    char buf[256];
    int n = snprintf(buf, sizeof buf, "tally: asked %zu allocs %zu biggest %zu frees %zu skipped %zu drained %d\n",
                     asked, allocs, biggest, frees, skips, drained);
    write(2, buf, n);
}
static PyObject *install(PyObject *m, PyObject *unused) {
    const char *s = getenv("TALLY_SKIP"); skip = s && *s == '1';
    const char *b = getenv("TALLY_B"); limit = b ? strtoull(b, NULL, 10) : 0;
    PyMemAllocatorDomain doms[3] = {PYMEM_DOMAIN_RAW, PYMEM_DOMAIN_MEM, PYMEM_DOMAIN_OBJ};
    for (int d = 0; d < 3; d++) {
        PyMem_GetAllocator(doms[d], &prev[d]);
        PyMemAllocatorEx h = {&prev[d], h_malloc, h_calloc, h_realloc, h_free};
        PyMem_SetAllocator(doms[d], &h);
    }
    Py_AtExit(report);
    Py_RETURN_NONE;
}
static PyMethodDef methods[] = {{"install", install, METH_NOARGS, NULL}, {NULL}};
static struct PyModuleDef mod = {PyModuleDef_HEAD_INIT, "tally", NULL, -1, methods};
PyMODINIT_FUNC PyInit_tally(void) { return PyModule_Create(&mod); }
