- **Project:** pdfminer.six (https://github.com/pdfminer/pdfminer.six)
- **Against:** 20260107 (the pinned sdist, `pdfminer_six-20260107.tar.gz`)
- **Status:** drafted
- **Title:** Import cryptography only where AES runs, so documents without AES open without it
- **Files:** pdfminer/pdfdocument.py
- **Why we carry it:** the guest has no `cryptography` (a compiled Rust package with no `wasm32-wasip1` build), and `pdfminer/pdfdocument.py` imports it at its top, so `import pdfplumber` and every `pdfminer` entry point fail with `ModuleNotFoundError` even for an unencrypted file.

The patch is `recipes/patches/pdfminer_six-20260107/0001-import-cryptography-where-aes-runs.patch`, written by specification 167's build (2026-10-31). The owner sends this, or not; nothing has been posted, and no agent will post anything to pdfminer.six.

## What the project asks of a contributor

Read 2026-10-31 from the sdist's `CONTRIBUTING.md`: a pull request should close an existing issue ("Fix #123"), target `master`, include unit tests where possible, work on Python 3.10 and later, pass `make check`, and add a line to `CHANGELOG.md` under "Unreleased". It says nothing about AI tools. So the route is an issue first, then the pull request below, which says that an AI tool wrote the change, the honest default.

## Related reports

Searched 2026-10-31 (`gh search issues --repo pdfminer/pdfminer.six cryptography`): no open issue asks for `cryptography` to be optional. The closed #429, "Removing Pycryptodome Dependency: Massive bloat (extra 260 MB)", is the history: the project moved from pycryptodome to `cryptography`, which is lighter but still a compiled dependency that some platforms (WebAssembly, some embedded interpreters) cannot install. An issue would cite it.

## The issue

**Title:** Make `cryptography` needed only for AES-encrypted documents

`pdfminer/pdfdocument.py` imports `cryptography` at module level (lines 13 and 14), but only the AES security handlers use it (`decrypt_aes128`, `PDFStandardSecurityHandlerV5.authenticate`, `_aes_cbc_encrypt` and `decrypt_aes256`). Plain and RC4-encrypted documents need nothing from it, since RC4 is pdfminer's own `arcfour.py`. On a platform where `cryptography` cannot be installed (WebAssembly runtimes such as Pyodide or WASI, some frozen or embedded interpreters), `import pdfminer.high_level` fails for every document.

Reproduction, in an environment without `cryptography`:

```
python -c "import pdfminer.high_level"
ModuleNotFoundError: No module named 'cryptography'
```

## The pull request

**Title:** Import cryptography only where AES runs

The two `cryptography` imports move from the top of `pdfminer/pdfdocument.py` into one helper, `_aes_cbc_cipher(key, iv)`, which returns `Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())`. The five places that built that cipher call the helper. Nothing else changes: with `cryptography` installed, every path runs the same calls as before (`_aes_cbc_encrypt` now passes `backend=default_backend()` as the others did, which `cryptography` has ignored since 3.1). Without it, plain and RC4 documents open, and an AES document raises `ModuleNotFoundError: No module named 'cryptography'` when it is opened.

A follow-up could move `cryptography` to an extra (`pdfminer.six[aes]`); this change does not, so nothing changes for anyone installing the package today.

**Tested** on CPython 3.15.0 (macOS, arm64): the project's suite from the 20260107 tag, 242 passed before and after the change with `cryptography` installed. Without `cryptography`, the stock tree fails to collect 10 test files; the patched tree passes 234 and fails exactly the 8 AES tests (`test_encryption_aes128`, `aes128m`, `aes256`, `aes256m`, `aes256_r6_user`, `aes256_r6_owner` in `test_tools_pdf2txt.py`, and `test_encryption_aes128` and `aes256` in `test_tools_dumppdf.py`), each with `ModuleNotFoundError` naming `cryptography`. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here. A test for the issue could import `pdfminer.pdfdocument` with `cryptography` hidden and open `samples/simple1.pdf`; the PR would add it beside the existing encryption tests.

CHANGELOG line: "Fixed: `cryptography` is imported only when an AES-encrypted document is opened".

## The evidence

Every figure here is EXECUTED on 2026-10-31 in specification 167's build (`context/specifications/167-pdfplumber-plotly-xarray-and-zstd.md`, landing notes):

- the suite, stock and patched, with and without `cryptography`, as above;
- in this project's guest (CPython for `wasm32-wasip1`, pdfminer.six in its stdlib zip, no `cryptography`): `test_pdfplumber_needs_cryptography_only_for_aes` imports pdfplumber, reads a plain file, and finds `cryptography` not imported; an AES-256 file raises `ModuleNotFoundError` naming it. On a set built from the stock sdist, `import pdfplumber` raises.
