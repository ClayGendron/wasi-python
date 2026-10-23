# Why WASI

This page explains why wasi-python targets WASI rather than a browser build of Python. It also explains why the hosts that run it must support WebAssembly exception handling.

## WebAssembly and WASI are two different things

*WebAssembly* (wasm) is the machine: an instruction set and a file format. *WASI*, the WebAssembly System Interface, is the operating-system interface a wasm binary talks to: files, the clock, arguments, standard output. wasi-python builds for one target, `wasm32-wasip1`, which is 32-bit WebAssembly with the first preview of WASI.

So `python.wasm` needs a WASI host and nothing else. A *host* is the program that loads the binary and runs it, such as wasmtime. Your own Rust, Go or Python program can be that host.

## Not a browser Python

"Python in wasm" usually means Pyodide. Pyodide is built with Emscripten, and it needs a browser or Node, because Emscripten's JavaScript glue code supplies much of what the interpreter calls. Pyodide is the right tool for Python in a web page.

wasi-python is the other thing. It has no Emscripten build, no JavaScript and no native code path. Its aim is that any program that can host WebAssembly can run real Python, with numpy and pandas, inside a sandbox the program fully controls. It needs no browser, no JavaScript engine, no kernel feature and no package install step.

If something cannot be done inside WASI, it is left out and documented, rather than added through a host-specific route. The [limitations page](../reference/limitations.md) lists what is left out.

## A capability sandbox

WASI uses a *capability* model. A capability is a right the host hands over explicitly, such as one folder. The guest has no ambient access to the host: it sees only what it is given.

In wasi-python the guest reaches the host through exactly two things:

- the WASI preview1 calls, which the host answers;
- one custom import, the *host door* (`host::call`), through which the guest sends opaque bytes to a function you supply.

There is no third import. The guest gets no network, no processes, no shared libraries and no threads. It sees only the folders you grant it, and by default it can write nothing at all. The [security model](security-model.md) describes what that wall enforces, and what it does not.

## One static binary

Most Python builds load C extension modules as shared libraries at import time. WASI has no `dlopen`, so wasi-python links every compiled package into the interpreter as a *builtin module*: part of the binary itself, like `sys`. `import numpy` then finds its C code already inside `python.wasm`. No `.so` file is opened, and nothing is installed inside the guest.

The pure-Python parts of the standard library and the packages ship in one read-only zip beside the binary. The result is one artifact that runs the same way on every host that can load it. [How it works](how-it-works.md) follows a call through those pieces.

## Why hosts need exception handling

Several compiled packages are written in C++, and C++ code throws exceptions. matplotlib's extension modules use pybind11, a C++ binding library that throws and catches exceptions on ordinary calls, not only on errors. So C++ exceptions must work inside the guest.

On WASI there are only a few ways to do that, and only one keeps the rules above:

- **Compile without exceptions.** pybind11 does not compile in that mode at all.
- **Let a throw end the program.** Then every ordinary error path in C++ code kills the guest, and pybind11's normal calls fail.
- **Lower exceptions the way Emscripten does.** That needs the host to supply extra imports, so the guest would reach the host by more than two things, and every host would need to write them.
- **Use the WebAssembly exception-handling proposal.** The binary throws and catches inside wasm itself, and imports nothing extra.

wasi-python uses the last one, in its standard form (`exnref`, part of WebAssembly 3.0). The binaries also need multi-value and reference types (WebAssembly 2.0). A host without exception handling cannot load them.

Most current hosts support it. wasmtime 47 or later and WasmEdge 0.16 or later run the binaries by default. Some other hosts run them once you turn on a switch, and a few cannot run them. The project runs wasmtime 49 itself; the rest of the list comes from each runtime's release notes and source. [Embed from other languages](../how-to/embed-from-other-languages.md) has the full hosts table.

## In one line

WASI gives wasi-python a sandbox of explicit capabilities and one static binary that any WebAssembly host with exception handling can run, with no browser and no JavaScript.
