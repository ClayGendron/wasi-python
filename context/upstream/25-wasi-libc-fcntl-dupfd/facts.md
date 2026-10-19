- **Project:** wasi-libc (https://github.com/WebAssembly/wasi-libc)
- **Against:** wasi-libc `2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13` (the commit wasi-sdk 34's `VERSION` names; `scripts/line.conf`'s `WASI_LIBC_COMMIT`)
- **Status:** drafted
- **Title:** fcntl: on wasip1, answer F_DUPFD and F_DUPFD_CLOEXEC with ENOTSUP, as dup does
- **Files:** libc-bottom-half/cloudlibc/src/libc/fcntl/fcntl.c
- **Why we carry it:** spec 086 carries a recipe, not a patch: `recipes/fcntl_dup_refusal.c`, linked with `-Wl,--wrap=fcntl`. It answers the two commands with ENOTSUP, so CPython's `os.dup` keeps the error it gave with wasi-sdk 33.

**This is a facts sheet, not an issue or a pull request** (question 82(d); decision 80). The owner
writes in their own words. Nothing has been posted, and no agent will post anything.

**The short version.** On `wasm32-wasip1`, wasi-libc's header says `F_DUPFD` and
`F_DUPFD_CLOEXEC` exist, but its `fcntl` answers them with `EINVAL`, as if the command were
unknown. Its own `dup`, `dup2` and `dup3` answer `ENOTSUP` on the same target, and so do `fcntl`'s
lock commands. A program that checks the header and then calls `fcntl` gets "Invalid argument"
for a call that is valid but not supported. The fix is to answer the two commands with `ENOTSUP`
on wasip1, beside the lock commands.

## The facts

1. **The header defines both commands on every target** (EXECUTED: `wasi-sysroot-34.0.tar.gz`,
   `include/wasm32-wasip1/__header_fcntl.h:50-51`, `#define F_DUPFD (5)` and
   `#define F_DUPFD_CLOEXEC (6)`). wasi-sdk 33's sysroot (wasi-libc `161b3195`) defined neither
   (EXECUTED, `diff -r` of the two sysroots).
2. **`fcntl` compiles them out on wasip1** (READ, `fcntl.c` at `2e6fb9d8`, lines 92-110):

   ```c
   #ifndef __wasip1__
       case F_DUPFD:
       case F_DUPFD_CLOEXEC: { ... return descriptor_table_dup(fildes, DUP_OP_DUPFD, minfd); }
   #endif
       case F_GETLK:
       case F_SETLK:
       case F_SETLKW:
         // POSIX advisory record locking is not supported by WASI.
         errno = ENOTSUP;
         return -1;
       default:
         errno = EINVAL;
         return -1;
   ```

   So on wasip1 both reach `default` and answer `EINVAL`.
3. **`dup` answers `ENOTSUP` on wasip1** (READ, `libc-bottom-half/sources/dup.c` at `2e6fb9d8`:
   `dup`, `dup2` and `__dup3` each `#ifdef __wasip1__ errno = ENOTSUP; return -1;`).
4. **What a program sees** (EXECUTED, CPython 3.15.0 built with wasi-sdk 34 for wasm32-wasip1, run
   under wasmtime 49.0.3, spec 086's trial): `os.dup(1)` raises `OSError: [Errno 28] Invalid
   argument`. CPython's `_Py_dup` (`Python/fileutils.c`) calls `fcntl(fd, F_DUPFD_CLOEXEC, 0)`
   whenever `<fcntl.h>` defines `F_DUPFD_CLOEXEC`. Built with wasi-sdk 33, the same call raised
   `[Errno 58] Not supported`, from CPython's own fallback. `os.dup2(1, 5)`, which reaches
   `dup2`, raises `[Errno 58] Not supported` on 34.
5. **What a fix would be.** Move the two cases out of the `#ifndef __wasip1__` block with an
   `ENOTSUP` answer on wasip1, for example by adding `case F_DUPFD: case F_DUPFD_CLOEXEC:` to the
   lock commands' `ENOTSUP` arm under `#ifdef __wasip1__`. One line of behaviour. With it,
   `fcntl` and `dup` agree on wasip1, and the header's promise means "not supported" rather than
   "unknown command".
6. **What we do meanwhile** (spec 086, Decision 5): the link-time wrap in
   `recipes/fcntl_dup_refusal.c` gives the same answer from outside wasi-libc. It is removed when a
   wasi-sdk release carries the fix.
