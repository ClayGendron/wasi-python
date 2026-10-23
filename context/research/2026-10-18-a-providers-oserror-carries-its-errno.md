# A provider's OSError carries its errno

- **Status:** research, 2026-10-18. It commits the project to nothing. It feeds spec 061 (`../specifications/061-a-providers-oserror-carries-its-errno.md`).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the author of spec 061's draft. It wrote none of the code it reads. Box: 60 minutes; stopped at about 55.
- **The question,** from the owner's answer to question 54 (`../decisions.md`, "49–89"): "a provider may also raise `OSError`; its errno is then the guest's answer (any other exception stays a fault, `EIO`). A follow-up change to spec 032's provider." Concretely: where the runner maps a provider's exception today; how a host `OSError`'s errno, whose number differs between macOS, Linux and Windows, becomes a WASI preview1 errno; which numbers must not reach the guest; what the subclasses, the message and the record do.

## Labels

EXECUTED means run here, with the script and its output in `2026-10-18-a-providers-oserror-carries-its-errno/`. READ means read from a file, cited by path. INFERRED means the researcher's reasoning. Every guest run used the main tree's artifact set (`build/artifacts`, `SHA256SUMS` hashing to `3c0ec02e25e0b91d…`, Python 3.15.0 in the guest) with wasmtime-py 49.0.0 on macOS arm64, CPython 3.14.2, from the worktree at main `5e66995`. Nothing measures time; each output is an errno, a count or a string.

## Where things stand (READ)

- **One boundary.** Every provider call goes through `_Files._invoke` (`src/wasi_python/mounts.py`). It counts the call, calls the method, and on any `Exception` records a `FileFault` (via `_described`: the type's name and the first line of its text, at most 200 characters) and answers `EIO` (29). A `BaseException` that is not an `Exception` passes through: it is the call's stop (spec 032, Decision 4).
- **Three more catch sites** judge what came back, inside the same boundary: `_stat` (a `Stat`'s fields), `_read` (the buffer export, `memoryview(answer)`) and `_list` (iterating the listing, `iter()` and `next()`, and checking each item). Each turns an `Exception` into `EIO` and a fault. A generator `list` method runs its body only in `_list`'s loop, not in `_invoke`.
- **The write half** (spec 034) goes through `_made`: an `Errno` answer is a refusal, recorded as `RefusedWrite(..., errno, at, "refused")`; a fault is recorded twice, as a `FileFault` and as `RefusedWrite(..., EIO, at, "fault")`. The ending's walk uses `_made` too.
- **The closed set.** `Errno` has 21 members, each with WASI preview1's own number (spec 032, Decision 3). The set deliberately leaves out success, `EINTR` and `EAGAIN` (they make the guest's C library retry), and `EBADF` and `EFAULT` (they describe the guest's own arguments). The runner returns a member's `int` from the shadowed preview1 call, unchanged; wasmtime-py passes whatever `i32` the host function returns, so the closed set is the runner's rule, not wasmtime's.
- **Spec 032 chose values over exceptions** (its Decision 3): an exception always means a bug, and "no host's `errno` numbering enters the runner (an `OSError`'s `errno` differs between Windows and POSIX)". The owner's answer keeps the first half for every exception but `OSError`. The second half becomes the design constraint: the host's number must be translated, never passed.
- **No existing check raises an `OSError` that carries an errno** from a provider. One raises `OSError("x" * 500)` (errno `None`, plain class) and expects a fault (`tests/unit/test_runner_mounts.py`, `test_the_record_keeps_the_first_thousand_faults`). The hostile fault table (`tests/checks/test_v1_2_hostile_guest.py`, `FAULTS`) raises `ValueError`, `RuntimeError` and `BufferError` only.

## Findings

### 1. Today every raised OSError is EIO and a fault (EXECUTED)

`guest_sees.py` mounts 20 providers, each raising one exception from one method, and the guest prints the errno it caught (`guest_sees_as_built.json`). All 20 give the guest `[29, "OSError", "I/O error"]`: `FileNotFoundError(ENOENT)`, `PermissionError(EACCES)`, `OSError(EDQUOT)`, an `IsADirectoryError` from `read`, a `NotADirectoryError` from `list`, `OSError(EROFS)` from a write-back at close, `FileExistsError` from `mkdir`, and the rest. `done.files.faults` holds 20 faults; the first is `["read", "FileNotFoundError: [Errno 2] secret /host/path"]`: the provider's message reaches the host's record, never the guest. The two write-half cases are `RefusedWrite`s with cause `"fault"` and errno 29.

`equivalence.py` (`equivalence.json`): a provider whose `stat` raises `OSError(errno.<NAME>, …)` against one whose `stat` returns `Errno.<NAME>`, for all 21 names. The guest's answers differ for 20 of them (they agree only on `EIO`); the raising provider leaves 22 faults (21 stats and a generator `list` that raises `FileNotFoundError` mid-listing).

### 2. Host numbers differ, and raw numbers collide with WASI's (EXECUTED, READ)

`host_errno.py` prints the host's number for each member's name (`host_errno_macos.json`, and `host_errno_linux.json` from the local `python:3.13-slim` image, `docker run --pull never --network none`, Linux aarch64, CPython 3.13.15):

| name | WASI | macOS | Linux | Windows (READ and INFERRED) |
|---|---|---|---|---|
| EPERM | 63 | 1 | 1 | 1 |
| ENOENT | 44 | 2 | 2 | 2 |
| EIO | 29 | 5 | 5 | 5 |
| EACCES | 2 | 13 | 13 | 13 |
| EBUSY | 10 | 16 | 16 | 16 |
| EEXIST | 20 | 17 | 17 | 17 |
| EXDEV | 75 | 18 | 18 | 18 |
| ENOTDIR | 54 | 20 | 20 | 20 |
| EISDIR | 31 | 21 | 21 | 21 |
| EINVAL | 28 | 22 | 22 | 22 |
| EFBIG | 22 | 27 | 27 | 27 |
| ENOSPC | 51 | 28 | 28 | 28 |
| EROFS | 69 | 30 | 30 | 30 |
| ENAMETOOLONG | 37 | 63 | 36 | 38 |
| ENOTEMPTY | 55 | 66 | 39 | 41 |
| ENOSYS | 52 | 78 | 38 | 40 |
| EDQUOT | 19 | 69 | 122 | 10069 (WSAEDQUOT) |
| ESTALE | 72 | 70 | 116 | 10070 (WSAESTALE) |
| ETIMEDOUT | 73 | 60 | 110 | 10060 (WSAETIMEDOUT) |
| ECANCELED | 11 | 89 | 125 | 105 |
| ENOTSUP | 58 | 45 | 95 | 129 |
| EOPNOTSUPP (alias) | 58 in the guest | 102 | 95 | 10045 (WSAEOPNOTSUPP) |

- WASI's numbers: READ, `wasi/wasip1.h` in wasi-sdk 33's sysroot (`build/tools/wasi-sdk-33.0-arm64-macos/share/wasi-sysroot/include/wasm32-wasip1/wasi/wasip1.h`, main tree), the same numbers spec 032 cites.
- macOS and Linux: EXECUTED. Every member's name exists on both, and no two members share a number on either (`"missing": []`, `"shared_numbers": {}`). On Linux `EOPNOTSUPP` and `ENOTSUP` are both 95 and `errno.errorcode[95]` is `"ENOTSUP"`; on macOS they are 45 and 102.
- Windows: READ, CPython 3.14.8's `Modules/errnomodule.c` (from `downloads/Python-3.14.8.tar.xz`): under `MS_WINDOWS` it `#undef`s `ETIMEDOUT`, `EOPNOTSUPP` and `EWOULDBLOCK` and defines them from the `WSAE*` values, and it defines `EDQUOT` and `ESTALE` from `WSAEDQUOT` and `WSAESTALE` when the C library has none. The small numbers are the MSVC C library's `errno.h`, INFERRED from memory: no Windows host was available. The spec's three-system check decides them.
- **A raw number would lie** (INFERRED from the table): on macOS and Linux, `ENOENT` is 2, which is WASI's `EACCES`; `EACCES` is 13, WASI's `ECONNABORTED`; macOS's `EDQUOT` is 69, WASI's `EROFS`; Linux's `EIO` is 5, WASI's `EAFNOSUPPORT`. The translation must go by name.
- **The guest spells `EOPNOTSUPP` as `ENOTSUP`** (READ, `wasm32-wasip1/__errno_values.h` in the same sysroot: `#define EOPNOTSUPP ENOTSUP`, and `#define EWOULDBLOCK EAGAIN`), so a host `EOPNOTSUPP` has a faithful member.
- **Windows produces its own errno for some host errors** (READ, `PC/errmap.h`, `winerror_to_errno`): `WAIT_TIMEOUT` becomes the C library's `ETIMEDOUT`, which on Windows is not `errno.ETIMEDOUT` (the WSA value). So a `TimeoutError` from such a call carries a number the host's own `errno` module does not name (INFERRED). And `ERROR_ACCESS_DENIED` becomes `EACCES`, which is what CPython raises for `open()` of a folder on Windows (INFERRED from the same map): a provider that passes host errors through gives `EACCES`, not `EISDIR`, for a folder there.

### 3. EINTR loops; EAGAIN misleads (EXECUTED)

`retry.py` patches `_Files._read` to answer WASI's `EINTR` (27) or `EAGAIN` (6) after making the provider call, with `max_file_calls=50` (`retry.json`):

- `EINTR`: the guest's `open()` never returns. It retried until the file-call limit: 50 provider reads for one `open`, `trapped == "out of file calls"`. CPython retries an interrupted `open` (PEP 475). With no limit (`max_file_calls=None`) only the deadline would stop it.
- `EAGAIN`: one read, and the guest raises `BlockingIOError` (errno 6): a non-blocking descriptor's "try again", which says nothing true about a whole-file provider.

So both stay out of the set, as spec 032 decided, whether returned or raised.

### 4. Subclasses: the class is often the only errno there is (EXECUTED)

`host_errno.py`: `FileNotFoundError("only a message")` and its siblings carry `errno is None`; only the two-argument form sets it. `OSError(errno.ENOENT, "x")` constructs a `FileNotFoundError`, and `OSError(EACCES)` and `OSError(EPERM)` both construct a `PermissionError` (PEP 3151's table). A one-argument `raise FileNotFoundError(path)` is the common Python idiom (INFERRED), and so is a socket's `TimeoutError("timed out")` (errno `None`). Six classes name exactly one closed-set errno when the errno is missing: `FileNotFoundError` (ENOENT), `FileExistsError` (EEXIST), `IsADirectoryError` (EISDIR), `NotADirectoryError` (ENOTDIR), `PermissionError` (EACCES or EPERM; EACCES is the permission check's answer and the one spec 032 and the README use for a policy) and `TimeoutError` (ETIMEDOUT). The others (`InterruptedError`, `BlockingIOError`, `ChildProcessError`, `ProcessLookupError`, the `ConnectionError` family) name nothing in the set.

### 5. A total reading of a hostile exception (EXECUTED)

`model.py` is a model of the boundary, not the implementation: it replaces `_Files._invoke` with one that looks up the exception's errno slot through `OSError.__dict__["errno"]` (the member descriptor, past any subclass's `errno` property), accepts it only when `type(n) is int`, maps it by name through a table built from the host's `errno` module (with `EOPNOTSUPP` as `ENOTSUP`), then falls back to the six classes by `issubclass(type(e), …)`, and otherwise leaves a fault. `hostile.py` (`hostile.json`), host only:

- an `OSError` subclass whose `errno` property says `ENOENT` while its slot holds `EINTR`: a fault; the property never ran;
- an errno of `True`, of an `int` subclass whose `__eq__` and `__hash__` claim `ENOENT`, of `2**70`, of `-1`, of `"2"`: each a fault, with no code of theirs run;
- a class whose metaclass's `__subclasscheck__` and `__instancecheck__` say yes to everything, and a class whose `__class__` property claims `FileNotFoundError`: each a fault, with no code of theirs run (`issubclass(type(e), FileNotFoundError)` asks `type`, never the exception);
- `OSError(EOPNOTSUPP)` is `ENOTSUP`; `PermissionError(EPERM)` is `EPERM` (the errno wins); `FileNotFoundError(EACCES)` is `EACCES`; `TimeoutError("timed out")` is `ETIMEDOUT`; `ConnectionRefusedError("x")` is a fault;
- after the boundary returns and a collection, a weak reference to the mapped exception is dead: the runner keeps nothing of it.

### 6. With the model, raising is returning (EXECUTED)

`equivalence.py --model` (`equivalence_model.json`): for all 21 names the guest's errno is the same whether `stat` raised the host's `OSError` or returned the `Errno`, with 0 faults from the stats. `guest_sees.py --model` (`guest_sees_model.json`): `FileNotFoundError(ENOENT)` gives `[44, "FileNotFoundError", "No such file or directory"]`, `PermissionError(EACCES)` 2, `OSError(EDQUOT)` 19, `OSError(ENAMETOOLONG)` 37, `FileNotFoundError("only a message")` 44, `PermissionError("only a message")` 2, a write-back's `OSError(EROFS)` 69 at close and `RefusedWrite(write, 69, close, "refused")`, `mkdir`'s `FileExistsError` 20 and `RefusedWrite(mkdir, 20, call, "refused")`. Still `EIO` and a fault each: `OSError("only a message")`, `InterruptedError(EINTR)`, `BlockingIOError(EAGAIN)`, `OSError(EBADF)`, `OSError(ELOOP)`, `OSError(99999)`, `ValueError`. The guest's text is its own C library's (`strerror`), never the provider's: the preview1 call returns one `i32`.

One gap in the model, which the specification closes, and one constraint it keeps:

- the gap: the generator `list` that raises `FileNotFoundError` while it is iterated is still `EIO` and a fault (`raises.listdir` 29, one fault): the model maps only at `_invoke`, and a generator's body runs in `_list`'s loop;
- the constraint: `IsADirectoryError` from `read` must become the `EISDIR` *answer* (a folder descriptor), not the errno 31. `folder.py` (`folder.json`): as built, `os.open` of the path gives a folder descriptor when `read` returns `EISDIR` and fails with 29 when it raises `IsADirectoryError`; with the model, which returns the member as the answer, both give a folder descriptor (`os.fstat` says a folder), one `read` call each, no fault.

### 7. Interactions (READ, INFERRED)

- **Read-only and writable mounts** differ only in which methods are called. A read-only mount never calls the write half (spec 032, Decision 3). On a writable mount, every write-half call goes through `_made`, the walk included, so a mapped `OSError` there is a refusal at open, call, close, sync or exit.
- **Spec 053** leaves async providers out: an `async def` method's call returns a coroutine, a bad answer closed at once; its body, and any `raise` in it, never runs. No interaction.
- **Spec 054** refuses a mount as an import-path server. A guest that puts a mount on its own `sys.path` sees `ENOENT` instead of `EIO` for a module a raising provider lacks; importlib's path finder treats a failed `stat` as missing either way (INFERRED). No interaction.
- **Spec 055** (sessions, not yet built) uses the same mount table, so it inherits the rule.
- **The runner's own guards** answer `ECANCELED`, `ETIMEDOUT` and `EIO` (`_gate`). A provider could already return each of these; raising adds no number a provider could not already give, because the mapping's image is the closed set. Only the gate sets `call.ended`.

## Recommendation

1. Map a raised `OSError` at the provider boundary into the `Errno` it names, and treat it exactly as the returned `Errno`: same guest answer, same record (no fault; a write-half refusal is `"refused"`).
2. Name, never number: a table from the host's `errno` module, built once, member names plus `EOPNOTSUPP` as `ENOTSUP`.
3. The errno first (the slot, an exact `int`), then the six classes, else a fault (`EIO`).
4. Map where the method's own code runs: the call, and `iter()` and `next()` on its listing.
5. Keep nothing of a mapped exception; the guest never sees its text.

## One line

A provider's `OSError` becomes the `Errno` of the same *name* (never the same number), or of its class when it has no usable errno; anything outside the closed set stays `EIO` and a fault.
