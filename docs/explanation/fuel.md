# Fuel

This page explains fuel: what it counts, why wasi-python offers it beside a deadline, and how to choose a budget for it.

## Fuel counts operations, not time

*Fuel* is wasmtime's meter for guest work. The store starts with a budget. Every wasm instruction the guest executes spends from it. When the budget is empty, the guest traps, and the call ends with `trapped == "out of fuel"`.

So fuel spent is a count of executed instructions. It is not a measure of time. A program that spends a billion instructions spends them on a fast laptop and on a slow, busy server alike.

You set a cap with `run(..., fuel=N)`, `Session(fuel=N)` or the command's `--fuel N`. `None`, the default, sets no cap. When a cap is given, the result's `fuel_used` reports what the guest spent; without one, `fuel_used` is `None`.

## Why a count makes a limit the same everywhere

A deadline in seconds depends on the machine. The same program can finish in time on your laptop and miss its deadline on a loaded server. A fuel cap does not move like that: the same program, on the same inputs, stops at the same place on every machine.

That makes fuel a deterministic deadline. A guest that loops forever under a cap traps after spending exactly the cap, every time. It also makes fuel a fair way to compare work: two runs that differ in fuel did different work, not the same work on a busier machine. wasi-python's own tests count fuel and never time a run for the same reason.

Fuel is close to exact, not perfectly exact:

- **The hash key.** The snapshot's string-hash key is fixed, so the same program repeats its fuel exactly there. The plain reactor draws a fresh key in every call, which changes the layout of dicts and sets, so its fuel varies by a few thousand instructions.
- **The clock and entropy.** A program that reads the time or random bytes, and acts on them, can do a slightly different amount of work each run.
- **The wasmtime version.** Fuel is wasmtime's own accounting, not part of the WebAssembly standard. Compare fuel only between runs on the same wasmtime version.

Fuel does not depend on how the module was loaded. `fuel_used` counts from the end of instantiation, so a call spends the same fuel whether its module was just compiled or loaded from the `.cwasm` cache.

## What spends fuel, and what does not

Fuel counts the guest's own instructions:

- **Imports.** The snapshot pre-imports no package, so a call that imports pandas or numpy pays for that import in fuel. Large packages cost far more than the program that uses them.
- **Your program.** Every line of Python, and the C code inside numpy, pandas and the other compiled packages.
- **Finalization.** After the program's last line, the interpreter shuts down, and that is counted too: on the snapshot about 34 million instructions more than the program's own, and more after large imports (about 73 million after `import numpy`, about 260 million after `import pandas`). Every finalizer runs as in CPython, but memory is not given back to an instance that is about to be discarded.

Fuel does not count:

- **Waiting.** While the guest sleeps or waits in `select`, no instruction runs, so fuel does not stop it. The deadline does.
- **Work on the host.** Your host function, mount providers and tools run in your process, not in the guest. Their cost is bounded by other limits, such as `max_tool_calls`, and by the deadline.

## Fuel and the deadline together

The two limits answer different questions:

- **Fuel** asks "how much work may this program do?" It is exact and portable, but it cannot stop a guest that waits.
- **The deadline** asks "how long may this call take?" It stops everything, waits included, but where it stops depends on the machine.

Every call has a deadline by default: 60 seconds. Fuel is opt-in. For untrusted code, use both: fuel to bound the work the same way everywhere, and the deadline as the backstop for waiting. If the deadline stops a call first, `trapped` is `"deadline"` and `fuel_used` is `None`.

## How to pick a budget

1. Run the program once with a generous cap, and read `fuel_used`.
2. Add headroom for the inputs you expect. Fuel grows with the data a program handles.
3. Make sure the cap covers finalization. A cap that runs out after the program's last line still ends the call `"out of fuel"`, with `exit_code` `None`, even though the program's own output was written.
4. Measure again when you change wasmtime versions or switch between the snapshot and the plain reactor.

A program stopped by fuel loses what it printed since its last flush, because output is buffered as CPython buffers it. Run it with `-u`, or flush before heavy work, if partial output matters.

In a session, a cap applies to each turn, and running out of fuel ends the session. A metered session's shutdown is also bounded by its fuel, so size the cap to cover it: closing a session runs Python's normal shutdown. See [sessions](sessions.md).

The [limits how-to](../how-to/limits.md) shows how to set fuel with the other limits, and [defaults and limits](../reference/defaults-and-limits.md) lists them all.

## In one line

Fuel counts the guest's instructions, so a fuel cap stops the same program at the same place on every machine; pair it with the deadline, which also stops a guest that only waits.
