# 146: the tool host's bounds are the process's

## Changelog

### New

- **Budget host memory for each guest.** The limits page says what one guest can hold on the host: with a writable mount, up to three times `memory_bytes`, about 3 GiB at the default. [Budget host memory](https://claygendron.github.io/wasi-python/how-to/limits/#budget-host-memory)

### Security

- **A guest cannot pile up threads in your process.** A tool call that times out leaves its function running on a thread; once 64 such threads are alive in a process, the next tool call is answered `timeout` at once. [Bound a tool's time](https://claygendron.github.io/wasi-python/how-to/tools/#bound-a-tools-time)

### Upgrading

- **Unbounded tool calls now end after an hour.** With `deadline_s=None`, a tool call used to wait as long as its tool ran; it now waits at most the session's lifetime, or 3,600 seconds outside a session. Give the tool a `timeout_s` to choose another bound. [Bound a tool's time](https://claygendron.github.io/wasi-python/how-to/tools/#bound-a-tools-time)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "146"
units = 3
```
