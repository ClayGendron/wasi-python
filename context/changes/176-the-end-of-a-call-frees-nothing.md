# 176: The end of a call frees nothing

## Changelog

### Faster

- **A call ends on less fuel.** Python still finalizes everything as CPython does, but no longer returns memory to an instance about to be discarded: a bare snapshot call costs 35 million instructions, not 42 million. Every allocation now checks one flag, so a call that allocates much and holds little costs up to 0.4% more. [Fuel](https://claygendron.github.io/wasi-python/explanation/fuel/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "176"
new = ["tests/checks/test_v1_4_the_end_of_a_call.py"]
grows = ["tests/checks/*"]
growth = "The link wraps the C library's allocators, so every allocation of every call checks one flag: a call that never finalizes, ended by os._exit(0), grows by the unarmed wrappers' cost, measured on darwin arm64 against 175's set built from the same tree: a bare call 111,968,568 to 112,369,548 fuel on the plain binary (+0.36%) and 1,412,836 to 1,421,407 on the snapshot (+0.61%), a pandas groupby 4,741,868,973 to 4,751,508,169 (+0.20%) and 4,460,318,703 to 4,470,531,059 (+0.23%). Above the 0.5% the specification inferred on the snapshot's bare call, so by its rule each whole call, teardown included, was measured to use less fuel than before: a bare call 135,278,097 to 132,134,646 (plain) and 41,551,326 to 35,186,249 (snapshot), a pandas groupby 5,039,912,364 to 5,005,696,328 and 4,766,096,475 to 4,730,329,497. A call that allocates much and holds little at its end grows by the same cost, measured by the pull request's review from 175's set to 176's: an allocation churn 4,153,737,054 to 4,169,801,552 (+0.39%, plain) and 4,166,800,598 to 4,176,852,980 (+0.24%, snapshot). python.wasm grows by the hook and the wrappers: 100,660,530 bytes, +21,796 against dev's set at a0b1171d with 175 (the zip +2,815, the snapshot -97,597)"
units = 0
[claim.judge]
"tests/harness/guest.py" = "Result and Turn gain memory_size, the linear memory's bytes once the export returned, and run and Turns take memory_limit, a wasmtime store limit, so a check can fill the heap to a cap and measure teardown's growth"
"tests/harness/instructions.py" = "new: a reader of every function body's instructions, so a check can say from the binary what calls the C library's allocators and what grows the memory"
"tests/release_shards.toml" = "the new check file joins own-guest-c, a files shard on all three systems"
"tests/lint/budget.toml" = "the new check file's fuel cap, twice its largest fuel measured at its first build"
"context/release-claims/176-the-end-of-a-call-frees-nothing.toml" = "a block for the release groups' fuel: most calls end on less, and a group that allocates much and finalizes little grows by up to the unarmed wrappers' cost"
```
