# 163: The result an agent reads

## Changelog

### New

- **A cell's value and displays come back typed.** With `results=True`, `run`, `run_async` and `Session` return a turn's or a `-c` program's last expression as `Completed.value`, not printed, and what the program passes to `display()` as `Completed.displays`, each a `Display` of MIME types; printed bytes never forge one. [Read a cell's value and displays](https://claygendron.github.io/wasi-python/how-to/results/)
- **matplotlib's figures come back as PNGs.** With `figures=True` beside `results=True`, `plt.show()` and a figure a cell leaves open become PNG displays, with no file and no writable grant for the image. [Add figures=True](https://claygendron.github.io/wasi-python/how-to/results/#add-figurestrue)
- **Other hosts can take displays too.** The tool protocol gains the `display` operation, used when the host passes `-Xhost-results` as the program's first argument; the guest falls back to printing against a host that does not serve it. [Tool protocol](https://claygendron.github.io/wasi-python/reference/tool-protocol/#displays)

### Upgrading

- **`-Xhost-results` is the runner's argument.** An `argv` that passes `-Xhost-results` or `-Xhost-results=figures` before the program's `-c`, `-m`, script or `-` now raises `ValueError`; pass `results=` instead. After the program's target it is the program's own, as before. [Read a cell's value and displays](https://claygendron.github.io/wasi-python/how-to/results/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "163"
new = [
  "tests/checks/test_v1_4_results.py",
  "tests/unit/test_results.py",
]
units = 35
grows = ["tests/checks/test_v1_*"]
growth = "the bootstrap reads the results flag at every call's start and every session's setup, and clears a checkpoint's mode, so every call runs a few more instructions; both binaries grow by the bootstrap's code and the zip by host/display.py and host/figures.py (measured on the pins before 0.1.3's move: python.wasm 4,736 bytes, the snapshot 8,726, the zip 6,794)"
[claim.judge]
"tests/checks/test_rules.py" = "LONG_FUNCTIONS: runner.py:run 173 to 182, run_async 208 to 217 and Session.__init__ 178 to 187 take results and figures with their docstrings and pass them to _checked; _call.py:_instance falls 147 to 146 as the door's hosts are made in _results._door_hosts"
"tests/public_api.txt" = "the public class Display, Completed's two defaulted fields value and displays, and the keywords results and figures on run, run_async and Session"
"tests/release_shards.toml" = "the new check file test_v1_4_results.py joins own-guest-d beside test_v1_4_checkpoint.py, and the new unit file test_results.py joins own-runner, on all three systems"
"tests/lint/budget.toml" = "the new family test_v1_4_results gets its cap, twice its largest fuel measured at its first build"
"tests/harness/calls.py" = "the checked call's new field results, None in the stand-ins' base call"
"tests/checks/test_v1_4_public_api.py" = "the top module's export list names Display"
"tests/unit/test_runner_package.py" = "the written order gains _results before _call, and LATE its constructor's imports of _tool_host and tools"
```
