# 164: Output while the guest runs, and stdin for a turn

## Changelog

### New

- **See a guest's output while it runs.** `run`, `run_async` and a session's turns take `on_output`, called with each chunk of stdout and stderr as it arrives; `OutputFeed` iterates them from async code. On the command line, `--stream` prints a JSON line per chunk. [Read output while the guest runs](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/)
- **Keep the end of a long output.** `output_keep="tail"` keeps a stream's last bytes past `output_bytes`, after a line counting what was cut, so the traceback at the end is kept; `--output-keep tail` on the command line. [Keep the end of a long output](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/#keep-the-end-of-a-long-output)
- **Answer a turn's `input()`.** `Session.run` and `Session.run_async` take `stdin`, that turn's standard input, which `sys.stdin` and `input()` read. [Give a turn its standard input](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/#give-a-turn-its-standard-input)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "164"
new = ["tests/unit/test_runner_streaming.py", "tests/unit/test_home.py"]
units = 28
[claim.judge]
"tests/release_shards.toml" = "the two new unit files, test_runner_streaming.py and test_home.py, join the own-runner shard on all three systems, as every runner unit file is in a files shard"
"tests/public_api.txt" = "the public names OutputChunk and OutputFeed, and the keywords on_output and output_keep on run, run_async, Session.run and Session.run_async, and stdin on the two Session methods"
```
