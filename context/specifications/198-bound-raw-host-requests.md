# 198: Bound raw host requests

- **Status:** in build on `spec/198-bound-raw-host-requests` from `dev` at `a85cac7f`.
- **Date:** 2026-11-17
- **Owner:** Clay Gendron
- **Kind:** parallel-safe runner change and judge change. The door keeps its existing import, arguments, and return codes. No new platform branch, module-level mutable, test seam, or private wasmtime API.
- **Depends on:** 003, 031, 036 and 178.

## Decisions

1. Limit each raw request to 1 MiB by default, matching the tool protocol's per-frame size. Expose `max_host_request_bytes` on `run`, `run_async` and `Session`, and append `host_request_bytes` to `Defaults`. Zero admits the empty request only. Explicit `None` removes the bound. An explicit value requires a raw host.
2. Judge the unsigned request length after checking the addresses and before reading guest memory, copying any bytes or running host code. Refuse an oversize request with the existing host-fault return. A subsequent admissible request can run. Tool and display admission remains owned by their protocols.
3. The session takes its bound at opening and uses it on every turn. A call takes the bound from the same snapshot of defaults as its other limits.

## Acceptance criteria

- The raw door refuses an oversize frame without a read, response allocation or callback. Equality, zero and the opt-out are covered.
- Each public entry point validates its argument before running guest code. The public API page and its snapshot include the option and the new default.
- An ordinary callback's request and answer still cross the door with a bounded call and the callback runs on its home thread.

## Build evidence

- Both new unit checks failed against the original door and defaults, then passed with the bound. The existing tool-door tests, public API checks, recorded function lengths and news-file checks passed (58 tests in all).
- With the 0.1.5 wheel's artifacts on Linux, a 3-byte cap refused a 4-byte request, then delivered a 3-byte request in the same guest. This passed through `run`, `run_async`, `Session.run` and `Session.run_async`.

## Review round 1

The initial implementation validated an integer-like default but passed the original object to the door. A unit check using only the integer index protocol failed, then passed after the call started normalizing its default as it does an override. A goal check with the released artifacts now covers the default and explicit cap across all four public entry points.
