/* An empty stand-in for <sys/ipc.h> (spec 037, Decision 4): wasi-libc has none, and OpenBLAS is
 * built with -DNO_SYSV_IPC, so nothing a System V IPC header declares is used. Only step 38 puts
 * this folder on the include path. */
