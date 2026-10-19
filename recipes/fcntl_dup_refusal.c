/*
 * Refuse fcntl's two dup commands as not supported, the answer wasi-libc's own dup gives on WASI
 * preview1 (spec 086, Decision 5). wasi-sdk 34's wasi-libc (2e6fb9d8) defines F_DUPFD and
 * F_DUPFD_CLOEXEC in <fcntl.h>, but its fcntl compiles both cases out on __wasip1__, so they fall
 * to its default and answer EINVAL ("Invalid argument"), while dup, dup2 and dup3 answer ENOTSUP.
 * CPython's _Py_dup (Python/fileutils.c) uses fcntl(fd, F_DUPFD_CLOEXEC, 0) whenever the header
 * defines the command, so without this file os.dup raises EINVAL where wasi-sdk 33's guest raised
 * ENOTSUP. There is no real duplicate behind the two cases on preview1, so nothing is hidden.
 *
 * Step 60 compiles this file into the reactor's link with -Wl,--wrap=fcntl, so every fcntl call
 * reaches __wrap_fcntl and the real function is __real_fcntl. It changes no upstream source. The
 * facts sheet for wasi-libc is context/upstream/25-wasi-libc-fcntl-dupfd/. Remove this file, and
 * its wrap flag, when a wasi-sdk release's fcntl answers ENOTSUP for these two commands on
 * preview1. No check turns red that day (spec 086, Decision 5): the facts sheet's answer and the
 * next toolchain move's recipe table are the signals.
 *
 * fcntl is variadic. wasm32 clang passes a null vararg buffer to a call with no variadic
 * arguments, so the argument is read only for the commands that take one: F_SETFD and F_SETFL an
 * int, F_GETLK, F_SETLK and F_SETLKW a pointer. Every other command is passed on without one, as
 * its caller passed it (spec 086's pre-build review, F8).
 */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>

int __real_fcntl(int fd, int cmd, ...);

int __wrap_fcntl(int fd, int cmd, ...) {
    va_list ap;
    switch (cmd) {
    case F_DUPFD:
    case F_DUPFD_CLOEXEC:
        errno = ENOTSUP;
        return -1;
    case F_SETFD:
    case F_SETFL: {
        va_start(ap, cmd);
        int value = va_arg(ap, int);
        va_end(ap);
        return __real_fcntl(fd, cmd, value);
    }
    case F_GETLK:
    case F_SETLK:
    case F_SETLKW: {
        va_start(ap, cmd);
        void *lock = va_arg(ap, void *);
        va_end(ap);
        return __real_fcntl(fd, cmd, lock);
    }
    default:
        return __real_fcntl(fd, cmd);
    }
}
