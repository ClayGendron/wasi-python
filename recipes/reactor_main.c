/* python.wasm's entry points as a WASI reactor (spec 003, Decision 6).
 *
 *   _initialize       the reactor runtime's constructor pass (registers the builtin modules)
 *   wizer.initialize  run once by Wizer at build time: a live interpreter with the stdlib's
 *                     bootstrap imported and no package (PREIMPORT; decision 34, spec 069)
 *   run               one program per instance: argv and the environment from WASI, then finalize
 *                     (on the snapshot, after undoing the freeze, as shutdown does: spec 073)
 *   turn              one turn of a session: code from host_alloc'd memory, the interpreter kept
 *   shutdown          a session's end: Python's own shutdown (atexit, finalization), once
 *
 * run and turn exclude each other in one instance (spec 055, Decision 2). A turn never finalizes;
 * only shutdown does, and after it every export refuses.
 * The argument handling is Python (recipes/reactor_bootstrap.py), compiled at build time into
 * reactor_bootstrap.h (scripts/freeze_bootstrap.py, step 60) and loaded as the module `_reactor`
 * when the interpreter starts, so no start compiles source and a snapshot carries it ready to call.
 *
 * The interpreter starts in two phases (spec 035, Decision 3). Between them, before anything is
 * read from the stdlib zip, the frozen module `_zip_directory` (recipes/zip_directory.py, compiled
 * the same way into zip_directory.h) puts its reader of the zip's directory in zipimport's place,
 * and its resource reader on zipimporter; `_zip_resources` (zip_resources.h) loads on first use.
 * Both are an embedder's frozen modules (PyImport_FrozenModules).
 */
#include <Python.h>
#include <marshal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wasi/api.h>
#include <wasi/libc.h>

#include "reactor_bootstrap.h"
#include "zip_directory.h"
#include "zip_resources.h"

/* The one entry on the guest's import path: the stdlib zip, named for the interpreter this file is
 * compiled into (/usr/local/lib/python315.zip), so the two cannot disagree. The same path is
 * written once more, as the name the zip's code objects carry: scripts/steps/70_zip.sh's
 * --code-prefix (spec 051). */
#define STR_(x) #x
#define STR(x) STR_(x)
#define STDLIB_ZIP L"/usr/local/lib/python" STR(PY_MAJOR_VERSION) STR(PY_MINOR_VERSION) ".zip"

/* The recipe modules the frozen importer finds after its bootstrap table, so they cannot shadow
 * zipimport (Python/import.c, look_up_frozen). */
static const struct _frozen recipe_modules[] = {
    {"_zip_directory", ZIP_DIRECTORY, (int)sizeof ZIP_DIRECTORY, 0},
    {"_zip_resources", ZIP_RESOURCES, (int)sizeof ZIP_RESOURCES, 0},
    {NULL, NULL, 0, 0},
};

/* What the snapshot pre-imports: the stdlib's bootstrap, no package, for every package now and
 * later (decision 34, spec 069). This #define is the list's one source: MANIFEST's x-preimport
 * line is read from it (scripts/assemble_artifacts.py) and the judge holds it to
 * tests/harness/paths.py's PREIMPORT. The #ifndef is for stand-ins built by hand; no build step
 * overrides it. */
#ifndef PREIMPORT
#define PREIMPORT "import encodings, io, os, sys, json, csv, re, _colorize"
#endif

/* While pinned, the C runtime's reads of the clocks, of entropy and of file metadata answer
 * constants, so everything captured during initialization is the same bytes on every build:
 * mimalloc's and wasi-libc's load-time state (they run as constructors, before any entry point),
 * the times, inodes and devices of the files that importing stats (and anything a pre-imported
 * module reads from the clock or entropy at import), and a directory's size and link count,
 * which each build host's file system answers its own way. The reactor's link wraps the four
 * WASI calls (scripts/steps/60_link.sh, --wrap); run() unpins before Python starts, and
 * wizer.initialize unpins once the imports are done, so a program only ever sees real values. */
static int pinned = 1;
#define PINNED_REALTIME_NS ((__wasi_timestamp_t)1767225600 * 1000000000u) /* SOURCE_DATE_EPOCH */

__wasi_errno_t __real___wasi_clock_time_get(__wasi_clockid_t, __wasi_timestamp_t,
                                            __wasi_timestamp_t *);
__wasi_errno_t __real___wasi_random_get(uint8_t *, __wasi_size_t);
__wasi_errno_t __real___wasi_path_filestat_get(__wasi_fd_t, __wasi_lookupflags_t, const char *,
                                               __wasi_filestat_t *);
__wasi_errno_t __real___wasi_fd_filestat_get(__wasi_fd_t, __wasi_filestat_t *);

__wasi_errno_t
__wrap___wasi_clock_time_get(__wasi_clockid_t id, __wasi_timestamp_t precision,
                             __wasi_timestamp_t *time)
{
    if (!pinned) {
        return __real___wasi_clock_time_get(id, precision, time);
    }
    *time = id == __WASI_CLOCKID_REALTIME ? PINNED_REALTIME_NS : 0;
    return __WASI_ERRNO_SUCCESS;
}

__wasi_errno_t
__wrap___wasi_random_get(uint8_t *buf, __wasi_size_t len)
{
    if (!pinned) {
        return __real___wasi_random_get(buf, len);
    }
    memset(buf, 0, len);
    return __WASI_ERRNO_SUCCESS;
}

static void
pin_filestat(__wasi_filestat_t *st)
{
    st->dev = 0;
    st->ino = 0;
    if (st->filetype == __WASI_FILETYPE_DIRECTORY) {
        /* The host's file system answers a directory's size and link count its own way (APFS 96,
         * ext4 4096), and CPython's heap layout follows the answer (spec 012, Decision 4). */
        st->size = 0;
        st->nlink = 1;
    }
    st->atim = st->mtim = st->ctim = PINNED_REALTIME_NS;
}

__wasi_errno_t
__wrap___wasi_path_filestat_get(__wasi_fd_t fd, __wasi_lookupflags_t flags, const char *path,
                                __wasi_filestat_t *st)
{
    __wasi_errno_t err = __real___wasi_path_filestat_get(fd, flags, path, st);
    if (pinned && err == __WASI_ERRNO_SUCCESS) {
        pin_filestat(st);
    }
    return err;
}

__wasi_errno_t
__wrap___wasi_fd_filestat_get(__wasi_fd_t fd, __wasi_filestat_t *st)
{
    __wasi_errno_t err = __real___wasi_fd_filestat_get(fd, st);
    if (pinned && err == __WASI_ERRNO_SUCCESS) {
        pin_filestat(st);
    }
    return err;
}

static int initialized = 0;
static int run_called = 0;
/* Spec 055, Decision 2: a turn was called; a turn is running, or did not return (a trap or
 * proc_exit unwinds without running C, so the flag stays set and every later turn is refused);
 * shutdown was called. */
static int turned = 0;
static int in_turn = 0;
static int shut = 0;
static int session_set_up = 0;
/* Strong references the C side calls through, so replacing _reactor.turn or gc.unfreeze, or
 * deleting the module, changes nothing (spec 055, the review's F1 and the re-review's N1). On the
 * snapshot, wizer.initialize takes unfreeze_function before any guest code exists, and run or
 * shutdown (never both: they exclude each other per instance) calls it once (spec 073). */
static PyObject *turn_function = NULL;
static PyObject *unfreeze_function = NULL;

extern unsigned char __stack_low;
extern unsigned char __stack_high;

/* CPython's C-stack guard (spec 071): it measures the C stack in linear memory, but wasmtime runs
 * every wasm call on a separate native stack of 512 KiB by default, which each C level spends 2 to
 * 25 times faster. So the guard watches only the top 128 KiB of the 16 MiB linear stack, and raises
 * RecursionError ("Stack overflow (used 112 kB)") while the native stack still has room. */
#define C_STACK_WINDOW (128 * 1024)

/* Zero the shadow stack below the current frame: dead bytes from initialization (scratch, stat
 * buffers) would otherwise land in the snapshot. */
__attribute__((noinline)) static void
clear_unused_stack(void)
{
    volatile unsigned char here = 0;
    unsigned char *low = &__stack_low;
    unsigned char *top = (unsigned char *)&here - 256;
    if (top > low) {
        memset(low, 0, (size_t)(top - low));
    }
}

static void run_private(const char *source);
static void show_and_drop(void);

static void
init_interpreter(int fixed_hash_seed)
{
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.parse_argv = 0;
    config.write_bytecode = 0;
    if (fixed_hash_seed) {
        /* A snapshot's secret is in its published bytes anyway; fixing it makes rebuilds equal. */
        config.use_hash_seed = 1;
        config.hash_seed = 0;
    }
    /* Only the zip is on the import path, and site does not run: the directories getpath would
     * add (python3.X, lib-dynload, site-packages, a venv's) sit in the guest's writable root, so
     * code one run planted there would run in the next (spec 006, Decision 4). stdlib_dir keeps
     * the frozen modules' __file__. */
    config.module_search_paths_set = 1;
    config.site_import = 0;
    static wchar_t program[] = L"/usr/local/bin/python.wasm";
    PyStatus status = PyConfig_SetString(&config, &config.program_name, program);
    if (!PyStatus_Exception(status)) {
        status = PyWideStringList_Append(&config.module_search_paths, STDLIB_ZIP);
    }
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetString(&config, &config.stdlib_dir, STDLIB_ZIP);
    }
    /* The core phase only: the builtin and frozen importers work, and nothing has touched the
     * zip. CPython's private two-phase start, restored in 3.15 (gh-142417); a CPython without it
     * fails this link, and spec 035's Decision 4 (an audit hook) takes its place. */
    config._init_main = 0;
    PyImport_FrozenModules = recipe_modules;
    if (!PyStatus_Exception(status)) {
        status = Py_InitializeFromConfig(&config);
    }
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }
    /* CPython's own call for a stack the OS does not describe (Doc/c-api/threads.rst); the snapshot
     * keeps the limits it sets, and nothing resets them. */
    if (PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(), &__stack_high - C_STACK_WINDOW,
                                                  C_STACK_WINDOW) < 0) {
        PyErr_Print();
        abort();
    }
    if (PyImport_GetMagicNumber() != REACTOR_BOOTSTRAP_MAGIC
        || PyImport_GetMagicNumber() != ZIP_DIRECTORY_MAGIC
        || PyImport_GetMagicNumber() != ZIP_RESOURCES_MAGIC) {
        fputs("python.wasm: a frozen recipe module was compiled for another Python\n", stderr);
        abort();
    }
    /* The value the main phase sets anyway: without it the modules this phase imports (zipimport,
     * _frozen_importlib_external) keep no __file__ (FrozenImporter._resolve_filename). */
    PyObject *zip = PyUnicode_FromWideChar(STDLIB_ZIP, -1);
    if (zip == NULL || PySys_SetObject("_stdlib_dir", zip) < 0) {
        PyErr_Print();
        abort();
    }
    Py_DECREF(zip);
    PyObject *reader = PyImport_ImportModule("_zip_directory");
    PyObject *installed = reader ? PyObject_CallMethod(reader, "install", NULL) : NULL;
    Py_XDECREF(reader);
    if (installed == NULL) {
        PyErr_Print();
        abort();
    }
    Py_DECREF(installed);
    /* The main phase: the path hooks, zipimport's among them, then encodings, read from the zip
     * by the reader just installed. */
    status = _Py_InitializeMain();
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }
    PyObject *code = PyMarshal_ReadObjectFromString((const char *)REACTOR_BOOTSTRAP,
                                                    (Py_ssize_t)sizeof REACTOR_BOOTSTRAP);
    PyObject *module = code ? PyImport_ExecCodeModule("_reactor", code) : NULL;
    Py_XDECREF(code);
    if (module == NULL) {
        PyErr_Print();
        abort();
    }
    turn_function = PyObject_GetAttrString(module, "turn");
    if (turn_function == NULL) {
        PyErr_Print();
        abort();
    }
    Py_DECREF(module);
    /* What site would have added to builtins, without its path work: exit, quit, help,
     * copyright, credits, license. */
    run_private("import site\nsite.setquit()\nsite.setcopyright()\nsite.sethelper()\n");
    initialized = 1;
}

/* Run build-time code in a private namespace, so __main__ starts as empty as CPython's. */
static void
run_private(const char *source)
{
    PyObject *globals = PyDict_New();
    PyObject *result = NULL;
    if (globals != NULL && PyDict_SetItemString(globals, "__builtins__", PyEval_GetBuiltins()) == 0) {
        result = PyRun_String(source, Py_file_input, globals, globals);
    }
    if (result == NULL) {
        PyErr_Print();
        abort();
    }
    Py_DECREF(result);
    Py_DECREF(globals);
}

__attribute__((export_name("wizer.initialize")))
void
wizer_initialize(void)
{
    init_interpreter(1);
    run_private(PREIMPORT);
    /* Then what the imports left behind is frozen out of the collector's way, so a program runs
     * without the collector walking it; run() undoes the freeze before it finalizes, so the
     * snapshot finalizes as CPython does (the owner's answer to question 103, spec 073), at about
     * 28 M fuel a call; spec 069's check (b) is coupled to it. The reference is taken here,
     * before the freeze and before any guest code, so a program cannot replace what run calls.
     * run() reseeds random and numpy.random from WASI entropy on every call, for whichever of
     * them a program has imported. */
    PyObject *gc = PyImport_ImportModule("gc");
    unfreeze_function = gc != NULL ? PyObject_GetAttrString(gc, "unfreeze") : NULL;
    Py_XDECREF(gc);
    if (unfreeze_function == NULL) {
        PyErr_Print();
        abort();
    }
    run_private("import gc\ngc.collect()\ngc.freeze()\n");
    pinned = 0;
    /* Forget the preopens Wizer gave, so the table is rebuilt from the runtime's, by name and in
     * any order, on first use (spec 006, Decision 5). */
    __wasilibc_reset_preopens();
    clear_unused_stack();
}

/* A list of str from WASI's NUL-separated strings. */
static PyObject *
strings(char **items, size_t count)
{
    PyObject *list = PyList_New((Py_ssize_t)count);
    for (size_t i = 0; list != NULL && i < count; i++) {
        PyObject *s = PyUnicode_DecodeFSDefault(items[i]);
        if (s == NULL) {
            Py_CLEAR(list);
            break;
        }
        PyList_SET_ITEM(list, (Py_ssize_t)i, s);
    }
    return list;
}

static PyObject *
read_argv(void)
{
    size_t count = 0, size = 0;
    if (__wasi_args_sizes_get(&count, &size) != 0) {
        return NULL;
    }
    char **items = calloc(count + 1, sizeof(char *));
    char *buf = malloc(size + 1);
    PyObject *list = NULL;
    if (items && buf && __wasi_args_get((uint8_t **)items, (uint8_t *)buf) == 0) {
        list = strings(items, count);
    }
    free(items);
    free(buf);
    return list;
}

static PyObject *
read_environ(void)
{
    size_t count = 0, size = 0;
    if (__wasi_environ_sizes_get(&count, &size) != 0) {
        return NULL;
    }
    char **items = calloc(count + 1, sizeof(char *));
    char *buf = malloc(size + 1);
    PyObject *env = NULL;
    if (items && buf && __wasi_environ_get((uint8_t **)items, (uint8_t *)buf) == 0) {
        env = PyDict_New();
        for (size_t i = 0; env != NULL && i < count; i++) {
            const char *eq = strchr(items[i], '=');
            if (eq == NULL) {
                continue;
            }
            PyObject *key = PyUnicode_DecodeFSDefaultAndSize(items[i], eq - items[i]);
            PyObject *value = PyUnicode_DecodeFSDefault(eq + 1);
            if (key == NULL || value == NULL || PyDict_SetItem(env, key, value) < 0) {
                Py_CLEAR(env);
            }
            Py_XDECREF(key);
            Py_XDECREF(value);
        }
    }
    free(items);
    free(buf);
    return env;
}

__attribute__((export_name("run")))
int
run(void)
{
    pinned = 0;
    if (run_called || turned) {
        fputs("python.wasm: run() may be called once per instance, and not after turn()\n",
              stderr);
        return 70;
    }
    run_called = 1;
    if (!initialized) {
        init_interpreter(0);  /* the plain reactor: a random hash secret, as CPython has */
    }
    int rc = 1;
    PyObject *argv = read_argv();
    PyObject *env = read_environ();
    PyObject *reactor = PyImport_ImportModule("_reactor");
    PyObject *result = NULL;
    if (argv && env && reactor) {
        result = PyObject_CallMethod(reactor, "run", "OO", argv, env);
    }
    if (result != NULL) {
        rc = (int)PyLong_AsLong(result);
        if (rc == -1 && PyErr_Occurred()) {
            PyErr_Print();
            rc = 1;
        }
    }
    else {
        PyErr_Print();
    }
    Py_XDECREF(result);
    Py_XDECREF(reactor);
    Py_XDECREF(env);
    Py_XDECREF(argv);
    Py_CLEAR(turn_function); /* run never turns */
    /* The snapshot's freeze undone before finalizing, as shutdown does (spec 073, Decision 4):
     * the atexit handlers and the teardown see the whole heap, so what a program hung on it is
     * finalized as in CPython. On the plain reactor nothing is frozen and nothing is taken. */
    if (unfreeze_function != NULL) {
        PyObject *done = PyObject_CallNoArgs(unfreeze_function);
        if (done == NULL) {
            show_and_drop();
        }
        Py_XDECREF(done);
    }
    Py_CLEAR(unfreeze_function);
    if (Py_FinalizeEx() < 0) {
        rc = 120;
    }
    fflush(stdout);
    fflush(stderr);
    return rc;
}

/* Show a failed call's exception and drop it, never through PyErr_Print, whose handling of a
 * pending SystemExit finalizes and exits (spec 055, the Confirmation's N1). */
static void
show_and_drop(void)
{
    PyObject *exc = PyErr_GetRaisedException();
    if (exc != NULL) {
        PyErr_DisplayException(exc);
        Py_DECREF(exc);
    }
    PyErr_Clear();
}

/* An int's low byte, with no overflow path: a huge or negative guest-made int leaves no exception
 * pending (spec 055, the re-review's C1). The caller has checked PyLong_Check. */
static int
low_byte(PyObject *value)
{
    unsigned long bits = PyLong_AsUnsignedLongMask(value);
    PyErr_Clear();
    return (int)(bits & 0xFF);
}

/* The bootstrap's result read with no guest code run: an int is its low byte; an exact 2-tuple
 * (status, quit) is the status's low byte, plus 256 when quit is True itself; anything else is 1
 * (spec 055, Decision 2). */
static int
turn_status(PyObject *result)
{
    if (PyLong_Check(result)) {
        return low_byte(result);
    }
    if (PyTuple_CheckExact(result) && PyTuple_GET_SIZE(result) == 2
        && PyLong_Check(PyTuple_GET_ITEM(result, 0))) {
        int status = low_byte(PyTuple_GET_ITEM(result, 0));
        return PyTuple_GET_ITEM(result, 1) == Py_True ? status + 256 : status;
    }
    return 1;
}

/* One turn of a session (spec 055, Decision 2): the code is `len` bytes of UTF-8 at `ptr`, a
 * buffer from host_alloc that this function frees on every path. Returns the turn's exit status
 * (0 to 255), 256 plus it when the turn called exit() or quit(), or -1 for a refusal, which runs
 * no Python. A NULL pointer with a length above 0 is the host's out-of-memory: a MemoryError in
 * the guest. */
__attribute__((export_name("turn")))
int
reactor_turn(int32_t ptr, int32_t len)
{
    pinned = 0;
    char *code = (char *)(uintptr_t)(uint32_t)ptr;
    if (run_called || in_turn || shut || len < 0) {
        free(code);
        return -1;
    }
    in_turn = 1;
    turned = 1;
    if (!initialized) {
        init_interpreter(0); /* the plain reactor: a random hash secret, as CPython has */
    }
    if (unfreeze_function == NULL) {
        /* The first turn, before any Python runs (the re-review's N1): not in init_interpreter,
         * which would put gc in every plain run's sys.modules. The snapshot took it already, in
         * wizer.initialize (spec 073). */
        PyObject *gc = PyImport_ImportModule("gc");
        unfreeze_function = gc != NULL ? PyObject_GetAttrString(gc, "unfreeze") : NULL;
        Py_XDECREF(gc);
        PyErr_Clear();
    }
    PyObject *source = NULL;
    if (code != NULL || len == 0) {
        source = PyBytes_FromStringAndSize(code != NULL ? code : "", (Py_ssize_t)len);
        PyErr_Clear(); /* no memory for the copy: the turn's MemoryError below */
    }
    free(code); /* copy, then free, before any Python runs */
    if (source == NULL) {
        source = Py_NewRef(Py_None);
    }
    PyObject *environ = NULL;
    if (!session_set_up) {
        session_set_up = 1;
        PyObject *argv = read_argv();
        PyObject *env = read_environ();
        environ = (argv != NULL && env != NULL) ? PyTuple_Pack(2, argv, env) : NULL;
        Py_XDECREF(argv);
        Py_XDECREF(env);
        if (environ == NULL) {
            PyErr_Clear();
            environ = PyTuple_Pack(2, Py_None, Py_None);
        }
    }
    else {
        environ = Py_NewRef(Py_None);
    }
    int rc = 1;
    PyObject *result = NULL;
    if (environ != NULL && turn_function != NULL) {
        result = PyObject_CallFunctionObjArgs(turn_function, source, environ, NULL);
    }
    if (result != NULL) {
        rc = turn_status(result);
        Py_DECREF(result);
    }
    else {
        show_and_drop();
    }
    Py_XDECREF(environ);
    Py_DECREF(source);
    fflush(stdout);
    fflush(stderr);
    in_turn = 0;
    return rc;
}

/* A session's end (spec 055, Decisions 2 and 8): Python's normal shutdown, once, in an instance
 * whose last turn returned. gc.unfreeze() first, so a snapshot's frozen heap is finalized as
 * CPython's own (the memo's section 8, P10b and P12). Returns 0, or 120 when finalization
 * reported an error, as run does; -1 for a refusal, which runs no Python. */
__attribute__((export_name("shutdown")))
int
reactor_shutdown(void)
{
    pinned = 0;
    if (!turned || in_turn || shut) {
        return -1;
    }
    shut = 1;
    if (unfreeze_function != NULL) {
        PyObject *done = PyObject_CallNoArgs(unfreeze_function);
        if (done == NULL) {
            show_and_drop();
        }
        Py_XDECREF(done);
    }
    Py_CLEAR(unfreeze_function);
    Py_CLEAR(turn_function);
    int rc = Py_FinalizeEx() < 0 ? 120 : 0;
    fflush(stdout);
    fflush(stderr);
    return rc;
}
