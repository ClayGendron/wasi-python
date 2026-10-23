# What a scripted, fully pinned build needs

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: two hours.
- **Feeds:** `../specifications/003-the-pinned-build-end-to-end.md`.
- **Stands on:** `2026-10-16-the-spike-evidence-in-this-repository.md` (the unscripted steps), the spike memo (the recipe).

## The question

The spike's recipe works, but parts of it were done by hand and some of its inputs were never pinned: the host Python that ran the build, the build tools (Cython, meson, ninja, versioneer), the zip's pure-Python packages, and the licence notices of the code wasi-sdk links into `python.wasm`. What does each need, so that the whole build is a script whose every input is a URL and a SHA-256 in `downloads/SHA256SUMS` (constitution §4.2)?

## Findings

1. **A pinned host Python exists at the guest's exact version.** python-build-standalone release `20261009` ships `cpython-3.14.8+20261009-aarch64-apple-darwin-install_only.tar.gz` (`ff8e1ddc02a9df3190b62d5af475cb642a02cfc77901ef780f9826cc23b51934`) and the Linux x86_64 build (`83f9cb480b702548c592443f86209cf0fc03448d90692df257f095c01791dccc`), both read from the release's published `SHA256SUMS` (EXECUTED: `curl … SHA256SUMS | grep`). The spike ran the CPython driver, meson and the zip script under an unpinned `.venv-build` (READ: spike memo header). INFERRED: running every host-side step under this one interpreter removes the build's dependence on whatever Python the host has, and its 3.14 bytecode magic is the guest's, so it can compile the zip's `.pyc` files in process.
2. **The build tools have pinnable wheels.** Cython 3.3.0 (`cython-3.3.0-cp314-cp314-macosx_11_0_arm64.whl`, `0deedc2e…`, and a pure `py3-none-any` wheel, `9b24b5c8…`), meson 1.12.1 (`930bc754…`), ninja 1.13.2 (`ninja-1.13.2-py3-none-macosx_10_9_universal2.whl`, `fd82e26c…`), versioneer 0.29 (`0f1a137b…`); full hashes and URLs in `2026-10-16-the-spike-evidence-in-this-repository.md` and below (EXECUTED: PyPI JSON API, 2026-10-16).
3. **So do the zip's pure-Python packages**: python-dateutil 2.9.0.post0, tzdata 2026.5, six 1.17.0 (same memo, same method).
4. **The pandas sdist has a literal URL** whose hash is the existing pin (`66b07ef7…`), so the download script's fetch-time lookup can go (EXECUTED: PyPI JSON API).
5. **wasi-sdk 24's tarball carries no licence file at all.** Of its 7,006 entries none matches `licen[cs]e|copying|copyright|notice` (EXECUTED: `tar tzf downloads/wasi-sdk-24.0-arm64-macos.tar.gz | grep -iE …`, after `shasum -a 256 -c` verified the tarball). Yet `python.wasm` statically links wasi-libc and, through numpy's and pandas' C++, libc++, libc++abi and compiler-rt.
6. **Those notices are pinnable at the exact commits wasi-sdk 24 was built from.** At tag `wasi-sdk-24`, `src/wasi-libc` is submodule commit `b9ef79d7dbd47c6c5bafdae760823467c2f60b70` and `src/llvm-project` is `26a1d6601d727a96f4301d0d8647b5a42760ae0c` (EXECUTED: GitHub contents API). Raw files at those commits, with their SHA-256 and size (EXECUTED: `curl | shasum -a 256`, `wc -c`):

   | file | sha256 | bytes |
   |---|---|---|
   | wasi-libc `LICENSE` | `673f577e…` | 831 |
   | wasi-libc `LICENSE-APACHE` | `a60eea81…` | 10,847 |
   | wasi-libc `LICENSE-APACHE-LLVM` | `268872b9…` | 12,243 |
   | wasi-libc `LICENSE-MIT` | `23f18e03…` | 1,023 |
   | wasi-libc `libc-top-half/musl/COPYRIGHT` | `f9bc4423…` | 6,204 |
   | llvm-project `libcxx/LICENSE.TXT` | `539dd7ae…` | 16,703 |
   | llvm-project `libcxxabi/LICENSE.TXT` | `e2b35be4…` | 16,706 |
   | llvm-project `compiler-rt/LICENSE.TXT` | `1a8f1058…` | 16,708 |

   A file at a fixed commit never changes, so these are ordinary pins. Their URL basenames collide (three `LICENSE.TXT`), so each needs a local name of its own.
7. **One host input cannot be pinned: the native C compiler and `make`.** CPython's WASI driver first builds a native build-Python with the host's compiler (READ: spike memo finding 1; `Tools/wasm/wasi`). That interpreter runs the freeze step and the sysconfig introspection; nothing it compiles is linked into the guest. INFERRED: it can change the build's bytes only through the frozen modules' bytecode, which depends on the CPython version, not on the compiler. The reproducible-builds memo's cross-host hash comparison is the test of that inference.

## The full hash list (for `downloads/SHA256SUMS`)

```
ff8e1ddc02a9df3190b62d5af475cb642a02cfc77901ef780f9826cc23b51934  cpython-3.14.8+20261009-aarch64-apple-darwin-install_only.tar.gz
0deedc2e9a5a664e1adfa4c2d310aa7b54903e1a647c274b6c9213f77a02d637  cython-3.3.0-cp314-cp314-macosx_11_0_arm64.whl
930bc7542cbd9f57009e182fd014eba48cf1a0180a7b9006d2d32d8f168d8b02  meson-1.12.1-py3-none-any.whl
fd82e26c0706ad4ab88e5fdd26f3fab0a987a90f810160f6c322e752c6af298b  ninja-1.13.2-py3-none-macosx_10_9_universal2.whl
0f1a137bb5d6811e96a79bb0486798aeae9b9c6efc24b389659cebb0ee396cb9  versioneer-0.29-py3-none-any.whl
a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427  python_dateutil-2.9.0.post0-py2.py3-none-any.whl
b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac  tzdata-2026.5-py2.py3-none-any.whl
4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274  six-1.17.0-py2.py3-none-any.whl
673f577e363e80e0058bd78214683f045d1d0c63930969a87f01a1d87d7cf1d6  wasi-libc-b9ef79d7-LICENSE
a60eea817514531668d7e00765731449fe14d059d3249e0bc93b36de45f759f2  wasi-libc-b9ef79d7-LICENSE-APACHE
268872b9816f90fd8e85db5a28d33f8150ebb8dd016653fb39ef1f94f2686bc5  wasi-libc-b9ef79d7-LICENSE-APACHE-LLVM
23f18e03dc49df91622fe2a76176497404e46ced8a715d9d2b67a7446571cca3  wasi-libc-b9ef79d7-LICENSE-MIT
f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af  wasi-libc-b9ef79d7-musl-COPYRIGHT
539dd7aed86e8a4f12cbdd0e6c50c189c7d74847e4fecc64ce2c6ee3a01da38b  llvm-26a1d660-libcxx-LICENSE.TXT
e2b35be49f7284a45b7baca8fc7b3ab7440e7902392b2528a457816b5bb2a15c  llvm-26a1d660-libcxxabi-LICENSE.TXT
1a8f1058753f1ba890de984e48f0242a3a5c29a6a8f2ed9fd813f36985387e8d  llvm-26a1d660-compiler-rt-LICENSE.TXT
```

## One line

Every input the spike left unpinned has a pinnable source, including a host Python at the guest's exact version and the licence texts the SDK omits; only the host's C compiler stays outside the pin list, and the cross-host hash comparison will test whether that matters.
