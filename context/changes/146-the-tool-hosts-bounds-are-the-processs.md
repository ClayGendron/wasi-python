# 146: the tool host's bounds are the process's

## Changelog

### Security

- **Abandoned tool threads are capped at 64 per process, a tool call in a run with no deadline waits at most the session's lifetime or an hour, and the pages say what host memory a guest can hold and what a `ToolError`'s text reaches** (spec 146). A tool call that would start while 64 abandoned tool threads are alive in the process is answered `timeout` at once, as the per-call cap of 4 answers; a guest with a writable mount can hold up to three times `memory_bytes` of host memory, about 3 GiB at the default.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "146"
units = 3
```
