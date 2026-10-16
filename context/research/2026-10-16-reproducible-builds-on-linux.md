# Reproducible builds on Linux

- **Status:** placeholder (research to do), 2026-10-16
- **Owner:** Clay Gendron
- **Blocks:** the release workflow; the claim that the published hash
  can be rebuilt by anyone.

## The question

The spike built on arm64 macOS only. The release workflow runs on
`ubuntu-24.04` (x86_64). The artifact is `wasm32-wasip1` and should
not depend on the host, and CPython's driver sets `SOURCE_DATE_EPOCH`,
but this is unverified. `scripts/python-wasi-cross` names the
`aarch64-apple-darwin` build-Python, which must become host-neutral
first.

## What answers it

1. Make `scripts/python-wasi-cross` derive the build-Python's platform
   directory from `cross-build/` instead of a literal.
2. Run the whole recipe on a Linux x86_64 host (a GitHub runner or a
   container) with the Linux wasi-sdk, Wizer and wasmtime pins added
   to `downloads/SHA256SUMS`.
3. Compare the SHA-256 of `python.wasm`, the snapshot, and the zip with
   the macOS build of the same pins. Where they differ, diff the
   binaries (`wasm-objdump`) and find the source of the difference
   (timestamps in the zip, build paths in debug info, Wizer's heap
   layout).
4. Record the result in this memo and in `MANIFEST`'s format: either
   "byte-identical across hosts" or the list of fields that vary and
   the hash that is stable (for instance, the zip built with
   `SOURCE_DATE_EPOCH` and sorted entries).

## What it decides

Whether the published `SHA256SUMS` is a reproducibility claim or only
an integrity claim, and what the manifest says about it.
