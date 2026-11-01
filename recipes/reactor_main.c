/* python.wasm's entry points as a WASI reactor (spec 003, Decision 6).
 *
 *   _initialize       the reactor runtime's constructor pass (registers the builtin modules)
 *   wizer.initialize  run once by Wizer at build time: a live interpreter with the stdlib's
 *                     bootstrap imported and no package (PREIMPORT; decision 34, spec 069)
 *   run               one program per instance: argv and the environment from WASI, then finalize
 *                     (on the snapshot, after undoing the freeze, as shutdown does: spec 073)
 *   turn              one turn of a session: code from host_alloc'd memory, the interpreter kept
 *   turn_input        the next turn's stdin, from host_alloc'd memory, held until that turn
 *   shutdown         a session's end: Python's own shutdown (atexit, finalization), once
 *   prepare           code from host_alloc'd memory run once in a snapshot instance that has run
 *                     nothing, with the clocks and entropy pinned, then the instance left as
 *                     wizer.initialize leaves the snapshot: the host reads its memory whole as a
 *                     starting image and copies it into each later instance before run or turn
 *   checkpoint        called twice around the host's read of a live session's memory, after a
 *                     turn returned: checkpoint(1) leaves the instance ready to be imaged, and
 *                     checkpoint(0) puts the live instance back as it was; an instance the image
 *                     is copied into resumes as a fresh start at its first run or turn
 *
 * run and turn exclude each other in one instance (spec 055, Decision 2). A turn never finalizes;
 * only shutdown does, and after it every export refuses. In a prepared instance (an image's), run
 * and shutdown end the call without Python's teardown of every module the image holds.
 * After run or shutdown finalized, every export refuses, running no Python, and the host discards
 * the instance: teardown frees nothing (free_nothing_at_teardown), and its hook stays in place
 * after Py_FinalizeEx. A later export that ran code after teardown would have to put the saved
 * allocators back first.
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
#include <errno.h>
#include <marshal.h>
#include <stdint.h>
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

/* While pinned, the C runtime's reads of the clocks, of entropy (PIN_CLOCKS) and of file metadata
 * (PIN_FILES) answer constants, so everything captured during initialization is the same bytes on
 * every build:
 * mimalloc's and wasi-libc's load-time state (they run as constructors, before any entry point),
 * the times, inodes and devices of the files that importing stats (and anything a pre-imported
 * module reads from the clock or entropy at import), and a directory's size and link count,
 * which each build host's file system answers its own way. The reactor's link wraps the four
 * WASI calls, and poll_oneoff for the monotonic offset below (scripts/steps/60_link.sh, --wrap);
 * run() unpins before Python starts, and wizer.initialize unpins once the imports are done, so a
 * program only ever sees real values.
 * prepare pins the clocks and entropy alone while the host's code runs: no time the image holds
 * then lies in a later call's future, and file metadata stays real, since under PIN_FILES every
 * file has inode 0 on device 0 and any two are one file to os.path.samefile and shutil. */
#define PIN_CLOCKS 1
#define PIN_FILES 2
static int pinned = PIN_CLOCKS | PIN_FILES;
#define PINNED_REALTIME_NS ((__wasi_timestamp_t)1767225600 * 1000000000u) /* SOURCE_DATE_EPOCH */

__wasi_errno_t __real___wasi_clock_time_get(__wasi_clockid_t, __wasi_timestamp_t,
                                            __wasi_timestamp_t *);
__wasi_errno_t __real___wasi_random_get(uint8_t *, __wasi_size_t);
__wasi_errno_t __real___wasi_path_filestat_get(__wasi_fd_t, __wasi_lookupflags_t, const char *,
                                               __wasi_filestat_t *);
__wasi_errno_t __real___wasi_fd_filestat_get(__wasi_fd_t, __wasi_filestat_t *);
__wasi_errno_t __real___wasi_poll_oneoff(const __wasi_subscription_t *, __wasi_event_t *,
                                         __wasi_size_t, __wasi_size_t *);

/* The monotonic clock never runs backwards across a checkpoint. Each store's monotonic clock
 * starts near zero, so an instance resumed from a checkpoint would read times below those the
 * session's heap already holds. checkpoint(1) records the session's reading as the floor; the
 * resume sets the offset that lifts the new store's clock to it, and every monotonic read adds
 * the offset, while every absolute monotonic wait subtracts it before the host sees it. Zero, the
 * usual case, costs each one comparison. */
static __wasi_timestamp_t monotonic_offset = 0;
static __wasi_timestamp_t monotonic_floor = 0;

__wasi_errno_t
__wrap___wasi_clock_time_get(__wasi_clockid_t id, __wasi_timestamp_t precision,
                             __wasi_timestamp_t *time)
{
    if (!(pinned & PIN_CLOCKS)) {
        __wasi_errno_t err = __real___wasi_clock_time_get(id, precision, time);
        if (monotonic_offset != 0 && err == __WASI_ERRNO_SUCCESS
            && id == __WASI_CLOCKID_MONOTONIC) {
            *time += monotonic_offset;
        }
        return err;
    }
    *time = id == __WASI_CLOCKID_REALTIME ? PINNED_REALTIME_NS : 0;
    return __WASI_ERRNO_SUCCESS;
}

/* An absolute monotonic wait, on a copy of the subscriptions, in the store's own time: the
 * offset taken off, saturating at zero, so a deadline already past returns at once. */
__wasi_errno_t
__wrap___wasi_poll_oneoff(const __wasi_subscription_t *in, __wasi_event_t *out,
                          __wasi_size_t count, __wasi_size_t *events)
{
    if (monotonic_offset == 0 || count == 0) {
        return __real___wasi_poll_oneoff(in, out, count, events);
    }
    __wasi_subscription_t *copy = malloc(count * sizeof *copy);
    if (copy == NULL) {
        return __WASI_ERRNO_NOMEM;
    }
    memcpy(copy, in, count * sizeof *copy);
    for (__wasi_size_t i = 0; i < count; i++) {
        __wasi_subscription_clock_t *clock = &copy[i].u.u.clock;
        if (copy[i].u.tag == __WASI_EVENTTYPE_CLOCK && clock->id == __WASI_CLOCKID_MONOTONIC
            && (clock->flags & __WASI_SUBCLOCKFLAGS_SUBSCRIPTION_CLOCK_ABSTIME)) {
            clock->timeout = clock->timeout > monotonic_offset
                                 ? clock->timeout - monotonic_offset
                                 : 0;
        }
    }
    __wasi_errno_t err = __real___wasi_poll_oneoff(copy, out, count, events);
    free(copy);
    return err;
}

__wasi_errno_t
__wrap___wasi_random_get(uint8_t *buf, __wasi_size_t len)
{
    if (!(pinned & PIN_CLOCKS)) {
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
    if ((pinned & PIN_FILES) && err == __WASI_ERRNO_SUCCESS) {
        pin_filestat(st);
    }
    return err;
}

__wasi_errno_t
__wrap___wasi_fd_filestat_get(__wasi_fd_t fd, __wasi_filestat_t *st)
{
    __wasi_errno_t err = __real___wasi_fd_filestat_get(fd, st);
    if ((pinned & PIN_FILES) && err == __WASI_ERRNO_SUCCESS) {
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
/* prepare is running, or did not return: every export refuses, running no Python, so neither a
 * trapped prelude nor a host that re-enters from the door during one reaches the interpreter.
 * prepare_called: prepare reached Python once; it is never cleared, so prepare runs once per
 * instance, and after a prepare that failed (prepare_called without prepared) run and turn refuse
 * too, since the host discards such an instance. prepared: the host's code ran to status 0 and
 * the instance was left ready to be imaged. */
static int preparing = 0;
static int prepare_called = 0;
static int prepared = 0;
/* imageable: set only by wizer.initialize, so only the snapshot binary, whose memory an instance
 * of the same binary can be given, answers checkpoint(1). checkpointing: between checkpoint(1)
 * and checkpoint(0) in the live instance, and in every instance the image is copied into, where
 * it means "resume at the first run or turn". */
static int imageable = 0;
static int checkpointing = 0;
/* Strong references the C side calls through, so replacing _reactor.turn or gc.unfreeze, or
 * deleting the module, changes nothing (spec 055, the review's F1 and the re-review's N1). On the
 * snapshot, wizer.initialize takes unfreeze_function before any guest code exists, and run or
 * shutdown (never both: they exclude each other per instance) calls it once (spec 073). */
static PyObject *turn_function = NULL;
static PyObject *unfreeze_function = NULL;
/* _reactor._end, taken by prepare before the host's code runs: a prepared instance's run and
 * shutdown end through it. */
static PyObject *end_function = NULL;
/* The next turn's stdin, given by turn_input: a host_alloc buffer held until that turn copies it
 * into a bytes and frees it, or until a second turn_input, shutdown or prepare frees it.
 * stdin_given says turn_input was called; a NULL buffer with a length above 0 is then the host's
 * out-of-memory. */
static char *stdin_buffer = NULL;
static int32_t stdin_length = 0;
static int stdin_given = 0;

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

/* Memory a session keeps back while a turn runs, so a turn after one that filled the heap can
 * still parse its code: taken at a turn's start when not held, and let go only when the turn's
 * compile or code raises MemoryError (_reactor._let_go), so a turn on a heap with room never
 * takes it again. A turn's parse and run after a heap filled to its last bytes needed 64 KiB in
 * the measurement; this is four times that. malloc, not a Python object: nothing zeroes it, and
 * every allocator in this build is malloc's. */
#define RESERVE_BYTES ((size_t)256 * 1024)
static void *reserve = NULL;

static PyObject *
let_go(PyObject *module, PyObject *unused)
{
    int held = reserve != NULL;
    free(reserve);
    reserve = NULL;
    return PyBool_FromLong(held);
}

static PyMethodDef reactor_functions[] = {
    {"_let_go", let_go, METH_NOARGS, "Let the turn's reserve go: True if one was held."},
    {NULL, NULL, 0, NULL},
};

/* Teardown frees nothing. Py_FinalizeEx runs whole, every finalizer in CPython's order, but the
 * memory it gives back is not returned to the allocator: the instance is discarded at once, so
 * that work has no effect. Just before Py_FinalizeEx, free_nothing_at_teardown() puts a hook over
 * the raw, mem and object domains (PyMem_SetAllocator, wrapping the allocator each had; in this
 * build all three are the C library's malloc, since there is no pymalloc and no free threading,
 * and the isolated configuration ignores PYTHONMALLOC). Its malloc, calloc and realloc call the
 * saved allocator. Its free does too until it first finds Py_IsFinalizing() true: CPython sets
 * that only once every atexit handler and pending call has run, so they free as before. From then
 * on (armed) a freed block is not freed but threaded onto its domain's list through its first
 * word, where dlmalloc's own free writes its link: every dlmalloc chunk on wasm32 has 12 usable
 * bytes, and a zero-size request takes a whole chunk.
 *
 * A budget keeps teardown's memory within TEARDOWN_BUDGET of what it uses today, for every
 * allocator. The link wraps the C library's allocators (scripts/steps/60_link.sh: malloc,
 * calloc, realloc, aligned_alloc, posix_memalign and musl's __libc_malloc and __libc_calloc),
 * so Python's domains, numpy's data, sqlite, OpenBLAS's emulated mmap, host_alloc and C++'s
 * operator new are all counted. Unarmed, a wrapper checks one flag. Armed, it adds the chunk the
 * request takes in dlmalloc (the request plus its 4-byte header, rounded up to 16, at least 16;
 * plus the alignment for an aligned request; a calloc's product saturating; a realloc's new size,
 * so a shrink counts too): an over-count, which is safe. Before an allocation that would take the
 * count past the budget, and after one that gets NULL, every list is freed (drained) and frees
 * run as before for the rest of the call; a NULL is then tried once more. A failed realloc leaves
 * its block valid, so its retry is sound. A double free traps at the drain, where natively it
 * traps at the second free.
 *
 * The hook stays after Py_FinalizeEx. That is safe only because nothing runs in the instance
 * afterwards: after run or shutdown finalized, every export refuses, running no Python, and the
 * host discards the instance. An export that ran code after teardown would have to put the saved
 * allocators back first. tracemalloc puts back the allocators it saved when it stops, after which
 * frees run as before; a program that is tracing at the end gets no hook at all, since stopping
 * would strand the lists. One thread runs (the guest imports no thread-spawn and its memory is not
 * shared) and wasip1 delivers no asynchronous signal, so plain statics suffice. */
#define TEARDOWN_BUDGET ((size_t)1 << 20)

enum { FREES_RUN, FREES_SKIPPED, FREES_RUN_AGAIN };
static int teardown_phase = FREES_RUN; /* FREES_RUN until armed; FREES_RUN_AGAIN is never left */
static size_t teardown_taken = 0;      /* the chunks counted while armed */

struct skipping_domain {
    PyMemAllocatorEx saved;
    void *skipped; /* the blocks not freed, each holding the next one's address */
};
static struct skipping_domain skipping[3];

static void
drain_skipped(void)
{
    teardown_phase = FREES_RUN_AGAIN;
    for (int i = 0; i < 3; i++) {
        void *block = skipping[i].skipped;
        skipping[i].skipped = NULL;
        while (block != NULL) {
            void *next = *(void **)block;
            skipping[i].saved.free(skipping[i].saved.ctx, block);
            block = next;
        }
    }
}

static void *
skipping_malloc(void *ctx, size_t size)
{
    struct skipping_domain *d = ctx;
    return d->saved.malloc(d->saved.ctx, size);
}

static void *
skipping_calloc(void *ctx, size_t nelem, size_t elsize)
{
    struct skipping_domain *d = ctx;
    return d->saved.calloc(d->saved.ctx, nelem, elsize);
}

static void *
skipping_realloc(void *ctx, void *ptr, size_t size)
{
    struct skipping_domain *d = ctx;
    return d->saved.realloc(d->saved.ctx, ptr, size);
}

static void
skipping_free(void *ctx, void *ptr)
{
    struct skipping_domain *d = ctx;
    if (ptr != NULL && teardown_phase != FREES_RUN_AGAIN) {
        if (teardown_phase == FREES_RUN && Py_IsFinalizing()) {
            teardown_phase = FREES_SKIPPED;
        }
        if (teardown_phase == FREES_SKIPPED) {
            *(void **)ptr = d->skipped;
            d->skipped = ptr;
            return;
        }
    }
    d->saved.free(d->saved.ctx, ptr);
}

/* The chunk dlmalloc takes for a request of n bytes (malloc.c's request2size on wasm32: a 4-byte
 * header, 16-byte alignment, a 16-byte least chunk), saturating. */
static size_t
chunk_of(size_t n)
{
    if (n > SIZE_MAX - 19) {
        return SIZE_MAX;
    }
    size_t chunk = (n + 4 + 15) & ~(size_t)15;
    return chunk < 16 ? 16 : chunk;
}

/* Armed, before an allocation: its chunk counted, or every list drained first when it would take
 * the count past the budget. */
static void
count_request(size_t chunk)
{
    if (chunk > TEARDOWN_BUDGET - teardown_taken) {
        drain_skipped();
    }
    else {
        teardown_taken += chunk;
    }
}

/* After an allocation: 1 when it got NULL while frees were still skipped, with every list drained
 * so that one retry finds the heap native teardown would have. */
static int
drained_after_null(const void *p)
{
    if (p != NULL || teardown_phase != FREES_SKIPPED) {
        return 0;
    }
    drain_skipped();
    return 1;
}

void *__real_malloc(size_t);
void *__real_calloc(size_t, size_t);
void *__real_realloc(void *, size_t);
void *__real_aligned_alloc(size_t, size_t);
int __real_posix_memalign(void **, size_t, size_t);
void *__real___libc_malloc(size_t);
void *__real___libc_calloc(size_t, size_t);

void *
__wrap_malloc(size_t size)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real_malloc(size);
    }
    count_request(chunk_of(size));
    void *p = __real_malloc(size);
    return drained_after_null(p) ? __real_malloc(size) : p;
}

void *
__wrap___libc_malloc(size_t size)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real___libc_malloc(size);
    }
    count_request(chunk_of(size));
    void *p = __real___libc_malloc(size);
    return drained_after_null(p) ? __real___libc_malloc(size) : p;
}

static size_t
product(size_t nelem, size_t elsize)
{
    return elsize != 0 && nelem > SIZE_MAX / elsize ? SIZE_MAX : nelem * elsize;
}

void *
__wrap_calloc(size_t nelem, size_t elsize)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real_calloc(nelem, elsize);
    }
    count_request(chunk_of(product(nelem, elsize)));
    void *p = __real_calloc(nelem, elsize);
    return drained_after_null(p) ? __real_calloc(nelem, elsize) : p;
}

void *
__wrap___libc_calloc(size_t nelem, size_t elsize)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real___libc_calloc(nelem, elsize);
    }
    count_request(chunk_of(product(nelem, elsize)));
    void *p = __real___libc_calloc(nelem, elsize);
    return drained_after_null(p) ? __real___libc_calloc(nelem, elsize) : p;
}

/* A failed realloc leaves its block valid, so the retry is sound; realloc(p, 0) may free p and
 * return NULL, so it is never retried. */
void *
__wrap_realloc(void *ptr, size_t size)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real_realloc(ptr, size);
    }
    count_request(chunk_of(size));
    void *p = __real_realloc(ptr, size);
    return (size != 0 || ptr == NULL) && drained_after_null(p) ? __real_realloc(ptr, size) : p;
}

static size_t
aligned_chunk(size_t alignment, size_t size)
{
    size_t chunk = chunk_of(size);
    return chunk > SIZE_MAX - alignment ? SIZE_MAX : chunk + alignment;
}

void *
__wrap_aligned_alloc(size_t alignment, size_t size)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real_aligned_alloc(alignment, size);
    }
    count_request(aligned_chunk(alignment, size));
    void *p = __real_aligned_alloc(alignment, size);
    return drained_after_null(p) ? __real_aligned_alloc(alignment, size) : p;
}

int
__wrap_posix_memalign(void **out, size_t alignment, size_t size)
{
    if (teardown_phase != FREES_SKIPPED) {
        return __real_posix_memalign(out, alignment, size);
    }
    count_request(aligned_chunk(alignment, size));
    int rc = __real_posix_memalign(out, alignment, size);
    if (rc == ENOMEM && drained_after_null(NULL)) {
        rc = __real_posix_memalign(out, alignment, size);
    }
    return rc;
}

/* The three hooks, one per domain, as data: the linker numbers the function table's entries in the
 * order it meets their addresses, and taking these in code would put them ahead of the table's
 * first entries, which the judge's scan of the binary reads by their place. */
static PyMemAllocatorEx skipping_hooks[3] = {
    {&skipping[0], skipping_malloc, skipping_calloc, skipping_realloc, skipping_free},
    {&skipping[1], skipping_malloc, skipping_calloc, skipping_realloc, skipping_free},
    {&skipping[2], skipping_malloc, skipping_calloc, skipping_realloc, skipping_free},
};

/* Called by run and shutdown just before Py_FinalizeEx. A program that is tracing with
 * tracemalloc keeps today's teardown: stopping in teardown, tracemalloc would put back the
 * allocators it wrapped, the hook's lists stranded under it. */
static void
free_nothing_at_teardown(void)
{
    int tracing = 0;
    PyObject *name = PyUnicode_FromString("_tracemalloc");
    PyObject *module = name != NULL ? PyImport_GetModule(name) : NULL;
    Py_XDECREF(name);
    if (module != NULL) {
        PyObject *on = PyObject_CallMethod(module, "is_tracing", NULL);
        tracing = on == NULL || PyObject_IsTrue(on) != 0;
        Py_XDECREF(on);
        Py_DECREF(module);
    }
    PyErr_Clear();
    if (tracing) {
        return;
    }
    static const PyMemAllocatorDomain domains[3] = {PYMEM_DOMAIN_RAW, PYMEM_DOMAIN_MEM,
                                                    PYMEM_DOMAIN_OBJ};
    for (int i = 0; i < 3; i++) {
        PyMem_GetAllocator(domains[i], &skipping[i].saved);
        skipping[i].skipped = NULL;
        PyMem_SetAllocator(domains[i], &skipping_hooks[i]);
    }
}

/* zipimport's dict for the stdlib zip, held from the start to the instance's end. Teardown then
 * leaves it alive: the instance is discarded at once, so freeing thousands of entries would be
 * work with no effect. Taken once per instance, so a session's turns grow nothing; a dict read
 * again after importlib.invalidate_caches() is not this one and is freed as before. An object a
 * program stores in this dict is never finalized. */
static PyObject *stdlib_directory = NULL;

static void
keep_directory(void)
{
    PyObject *zipimport = PyImport_ImportModule("zipimport");
    PyObject *cache = zipimport ? PyObject_GetAttrString(zipimport, "_zip_directory_cache") : NULL;
    PyObject *zip = PyUnicode_FromWideChar(STDLIB_ZIP, -1);
    PyObject *files = NULL;
    if (cache != NULL && zip != NULL && PyDict_Check(cache)) {
        files = PyDict_GetItemWithError(cache, zip); /* borrowed */
    }
    if (files != NULL) {
        Py_XSETREF(stdlib_directory, Py_NewRef(files));
    }
    PyErr_Clear();
    Py_XDECREF(zip);
    Py_XDECREF(cache);
    Py_XDECREF(zipimport);
}

static void run_private(const char *source);
static void show_and_drop(void);
static void drop_stdin(void);
static void freeze_for_image(void);
static int end_prepared(void);
static int resume_if_restored(void);

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
    /* The plain reactor reads the stdlib zip by its folder table, each folder on first use; the
     * snapshot reads it whole at build time, so its image holds today's dict and an import
     * after it pays nothing to read a folder. */
    PyObject *reader = PyImport_ImportModule("_zip_directory");
    PyObject *installed = reader ? PyObject_CallMethod(reader, "install", "O",
                                                       fixed_hash_seed ? Py_False : Py_True)
                                 : NULL;
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
    if (turn_function == NULL || PyModule_AddFunctions(module, reactor_functions) < 0) {
        PyErr_Print();
        abort();
    }
    Py_DECREF(module);
    /* What site would have added to builtins, without its path work: exit, quit, help,
     * copyright, credits, license. */
    run_private("import site\nsite.setquit()\nsite.setcopyright()\nsite.sethelper()\n");
    keep_directory();
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
    freeze_for_image();
    imageable = 1;
}

/* What the build-time snapshot and a starting image both end with: what the code left behind
 * frozen out of the collector's way, the clocks unpinned, the preopens forgotten so the table is
 * rebuilt from the runtime's, by name and in any order, on first use, and the dead stack
 * zeroed. */
static void
freeze_for_image(void)
{
    run_private("import gc\ngc.collect()\ngc.freeze()\n");
    pinned = 0;
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
    if (resume_if_restored() < 0) {
        return 70;
    }
    if (preparing || (prepare_called && !prepared)) {
        return 70;
    }
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
    if (prepared) {
        if (end_prepared() < 0) {
            rc = 120;
        }
        fflush(NULL);
        return rc;
    }
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
    free_nothing_at_teardown();
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
 * the guest. The stdin a turn_input gave is this turn's, freed on every path; without one the
 * turn's stdin is the session's own, which reads end of file. */
__attribute__((export_name("turn")))
int
reactor_turn(int32_t ptr, int32_t len)
{
    char *code = (char *)(uintptr_t)(uint32_t)ptr;
    if (resume_if_restored() < 0 || preparing || (prepare_called && !prepared)) {
        free(code);
        drop_stdin();
        return -1;
    }
    pinned = 0;
    if (run_called || in_turn || shut || len < 0) {
        free(code);
        drop_stdin();
        return -1;
    }
    in_turn = 1;
    turned = 1;
    if (!initialized) {
        init_interpreter(0); /* the plain reactor: a random hash secret, as CPython has */
    }
    if (reserve == NULL) {
        reserve = malloc(RESERVE_BYTES); /* NULL on a full heap: the next turn tries again */
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
    /* The turn's stdin: None when no turn_input came, its bytes, or False when the host or the
     * copy had no memory for them, which the bootstrap raises as a MemoryError. */
    PyObject *input = NULL;
    if (stdin_given && (stdin_buffer != NULL || stdin_length == 0)) {
        input = PyBytes_FromStringAndSize(stdin_buffer != NULL ? stdin_buffer : "",
                                          (Py_ssize_t)stdin_length);
        PyErr_Clear();
    }
    if (input == NULL) {
        input = Py_NewRef(stdin_given ? Py_False : Py_None);
    }
    drop_stdin(); /* copy, then free, before any Python runs */
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
        result = PyObject_CallFunctionObjArgs(turn_function, source, environ, input, NULL);
    }
    if (result != NULL) {
        rc = turn_status(result);
        Py_DECREF(result);
    }
    else {
        show_and_drop();
    }
    Py_XDECREF(environ);
    Py_DECREF(input);
    Py_DECREF(source);
    fflush(stdout);
    fflush(stderr);
    in_turn = 0;
    return rc;
}

/* The held stdin freed, and none given. */
static void
drop_stdin(void)
{
    free(stdin_buffer);
    stdin_buffer = NULL;
    stdin_length = 0;
    stdin_given = 0;
}

/* The next turn's stdin: `len` bytes at `ptr`, a buffer from host_alloc, held until that turn
 * copies and frees it. A second turn_input before the turn frees the first. A NULL pointer with a
 * length above 0 is the host's out-of-memory: the turn raises MemoryError before its code. Returns
 * 0, or -1 for a refusal, where turn would refuse, with the buffer freed. Runs no Python. */
__attribute__((export_name("turn_input")))
int
reactor_turn_input(int32_t ptr, int32_t len)
{
    char *data = (char *)(uintptr_t)(uint32_t)ptr;
    drop_stdin();
    if (preparing || (prepare_called && !prepared) || run_called || in_turn || shut || len < 0) {
        free(data);
        return -1;
    }
    stdin_buffer = data;
    stdin_length = len;
    stdin_given = 1;
    return 0;
}

/* A session's end (spec 055, Decisions 2 and 8): Python's normal shutdown, once, in an instance
 * whose last turn returned. gc.unfreeze() first, so a snapshot's frozen heap is finalized as
 * CPython's own (the memo's section 8, P10b and P12). Returns 0, or 120 when finalization
 * reported an error, as run does; -1 for a refusal, which runs no Python. */
__attribute__((export_name("shutdown")))
int
reactor_shutdown(void)
{
    drop_stdin(); /* a stdin no turn took */
    if (preparing || checkpointing) {
        return -1;
    }
    pinned = 0;
    if (!turned || in_turn || shut) {
        return -1;
    }
    shut = 1;
    if (prepared) {
        int rc = end_prepared() < 0 ? 120 : 0;
        fflush(NULL);
        return rc;
    }
    if (unfreeze_function != NULL) {
        PyObject *done = PyObject_CallNoArgs(unfreeze_function);
        if (done == NULL) {
            show_and_drop();
        }
        Py_XDECREF(done);
    }
    Py_CLEAR(unfreeze_function);
    Py_CLEAR(turn_function);
    free_nothing_at_teardown();
    int rc = Py_FinalizeEx() < 0 ? 120 : 0;
    fflush(stdout);
    fflush(stderr);
    return rc;
}

/* The end of a call from a starting image: _reactor._end runs the atexit handlers, drops the
 * call's own names and collects what they held, and flushes every writer the call left open,
 * without Python's teardown of every module the image holds. Returns 0, or -1 when a standard
 * stream could not be flushed or the end raised, as run's finalization error. */
static int
end_prepared(void)
{
    PyObject *done = end_function != NULL ? PyObject_CallNoArgs(end_function) : NULL;
    int rc = done == Py_True ? 0 : -1;
    if (done == NULL) {
        show_and_drop();
    }
    Py_XDECREF(done);
    return rc;
}

/* Code the host passes, run once in a snapshot instance that has run nothing (the starting image
 * of an embedder's own code): `len` bytes of UTF-8 at `ptr`, a buffer from host_alloc that this
 * function frees on every path. The code runs in __main__ with the clocks and entropy pinned, the
 * making call's argv and environment read as a session's first turn reads them, and its import
 * path dropped again after it. On status 0 the instance is then left as wizer.initialize leaves
 * the snapshot, ready for the host to read its memory; run and turn work in each instance the
 * image is copied into. Returns the code's exit status (0 to 255), or -1 for a refusal, which runs
 * no Python: on the plain reactor, in an instance that ran anything, and a second time. A NULL
 * pointer with a length above 0 is the host's out-of-memory: a MemoryError in the guest. After a
 * prepare that returned anything but 0, prepare, run and turn refuse: the host discards the
 * instance. */
__attribute__((export_name("prepare")))
int
reactor_prepare(int32_t ptr, int32_t len)
{
    char *code = (char *)(uintptr_t)(uint32_t)ptr;
    drop_stdin(); /* a stdin no turn took: the image never holds one */
    if (!initialized || prepare_called || run_called || turned || shut || checkpointing
        || len < 0) {
        free(code);
        return -1;
    }
    preparing = 1;
    prepare_called = 1;
    pinned = PIN_CLOCKS;
    PyObject *source = NULL;
    if (code != NULL || len == 0) {
        source = PyBytes_FromStringAndSize(code != NULL ? code : "", (Py_ssize_t)len);
        PyErr_Clear(); /* no memory for the copy: the code's MemoryError below */
    }
    free(code); /* copy, then free, before any Python runs */
    if (source == NULL) {
        source = Py_NewRef(Py_None);
    }
    PyObject *reactor = PyImport_ImportModule("_reactor");
    PyObject *prepare_function = reactor ? PyObject_GetAttrString(reactor, "prepare") : NULL;
    end_function = reactor ? PyObject_GetAttrString(reactor, "_end") : NULL;
    Py_XDECREF(reactor);
    PyObject *argv = read_argv();
    PyObject *env = read_environ();
    PyObject *environ = (argv != NULL && env != NULL) ? PyTuple_Pack(2, argv, env) : NULL;
    Py_XDECREF(argv);
    Py_XDECREF(env);
    int rc = 1;
    PyObject *result = NULL;
    if (prepare_function != NULL && end_function != NULL && environ != NULL) {
        result = PyObject_CallFunctionObjArgs(prepare_function, source, environ, NULL);
    }
    if (result != NULL && PyLong_Check(result)) {
        rc = low_byte(result);
    }
    else if (result == NULL) {
        show_and_drop();
    }
    Py_XDECREF(result);
    Py_XDECREF(environ);
    Py_XDECREF(prepare_function);
    Py_DECREF(source);
    fflush(NULL);
    if (rc == 0) {
        freeze_for_image();
        prepared = 1;
    }
    pinned = 0;
    preparing = 0;
    return rc;
}

/* A live session's memory as a starting image, read by the host between two calls, after a turn
 * returned. checkpoint(1) records the monotonic floor, zeros the dead stack and sets
 * checkpointing, which the image keeps; checkpoint(0) clears it, so the live instance goes on
 * unchanged. Returns 0, or -1 for a refusal, which changes nothing: checkpoint(1) on the plain
 * reactor, before a turn returned, after run, during a turn, a prepare or a shutdown, and while
 * entered; checkpoint(0) unless entered; any other argument. */
__attribute__((export_name("checkpoint")))
int
reactor_checkpoint(int32_t enter)
{
    if (enter == 1) {
        if (!imageable || !turned || in_turn || shut || preparing || run_called || checkpointing
            || (prepare_called && !prepared)) {
            return -1;
        }
        __wasi_timestamp_t now = 0;
        if (__real___wasi_clock_time_get(__WASI_CLOCKID_MONOTONIC, 1, &now)
            != __WASI_ERRNO_SUCCESS) {
            return -1;
        }
        monotonic_floor = now + monotonic_offset;
        drop_stdin(); /* a checkpoint never holds a turn's stdin */
        checkpointing = 1;
        clear_unused_stack();
        return 0;
    }
    if (enter == 0 && checkpointing) {
        checkpointing = 0;
        return 0;
    }
    return -1;
}

/* The first run or turn of an instance a checkpoint's image was copied into: the clock lifted
 * to the floor, the preopens forgotten so the table is rebuilt from this store's, the next turn
 * a first turn (its setup reads this start's argv and environment and reseeds), the call ended
 * as a starting image's call ends, and _reactor._resume, which puts the import path back and
 * takes the checkpoint's __main__ as the image's. Returns 0, or -1 when the resume raised. */
static int
resume_if_restored(void)
{
    if (!checkpointing) {
        return 0;
    }
    checkpointing = 0;
    __wasi_timestamp_t now = 0;
    if (__real___wasi_clock_time_get(__WASI_CLOCKID_MONOTONIC, 1, &now) != __WASI_ERRNO_SUCCESS) {
        now = monotonic_floor;
    }
    monotonic_offset = monotonic_floor > now ? monotonic_floor - now : 0;
    __wasilibc_reset_preopens();
    turned = 0;
    session_set_up = 0;
    prepared = 1;
    PyObject *reactor = PyImport_ImportModule("_reactor");
    if (end_function == NULL && reactor != NULL) {
        end_function = PyObject_GetAttrString(reactor, "_end");
    }
    PyObject *done = reactor != NULL ? PyObject_CallMethod(reactor, "_resume", NULL) : NULL;
    Py_XDECREF(reactor);
    if (done == NULL || end_function == NULL) {
        Py_XDECREF(done);
        show_and_drop();
        return -1;
    }
    Py_DECREF(done);
    return 0;
}
