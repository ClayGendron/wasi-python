# 162: A session's state is a snapshot

## Changelog

### New

- **Checkpoint a live session, and fork it.** `Session.checkpoint()` keeps a session's state after its turns as a `Snapshot`; any number of sessions and calls start from it, each from its own copy, and the session goes on. A checkpoint holds every byte the session read. [Checkpoint a session, and fork it](https://claygendron.github.io/wasi-python/how-to/snapshots/#checkpoint-a-session-and-fork-it)
- **Other engines can checkpoint a session too.** The snapshot binary exports `checkpoint`, called with 1 before the host reads a session's memory and with 0 after; an instance given that memory resumes as a fresh start at its first `run` or `turn`. [Embed from other languages](https://claygendron.github.io/wasi-python/how-to/embed-from-other-languages/#checkpoint-a-session)

### Upgrading

- **`SnapshotFailed.completed` may be `None` when no code ran.** A checkpoint refused for an open file raises `SnapshotFailed` with the reason `"open file"` and no `Completed`; code that reads `e.completed.exit_code` checks for `None` first. [Results and errors](https://claygendron.github.io/wasi-python/reference/results-and-errors/#snapshot-exceptions)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "162"
new = [
  "tests/checks/test_v1_4_checkpoint.py",
  "tests/checks/test_v1_4_prepare.py::test_checkpoint_refuses",
  "tests/checks/test_v1_4_prepare.py::test_a_checkpoints_image_resumes_in_run_and_turn",
]
grows = ["tests/checks/test_v1_*"]
growth = "the reactor gains the export `checkpoint`, a resume check at the start of every `run` and `turn`, an offset on each monotonic clock read and a wrapper of `poll_oneoff`, so both binaries are larger and every call runs a few more instructions"
units = 16
[claim.judge]
"tests/public_api.txt" = "the public API gains `Session.checkpoint` and `SnapshotOrigin`'s two defaulted fields, `kind` and `parent_sha256`"
"tests/release_shards.toml" = "the new check file test_v1_4_checkpoint.py joins the own-guest-d shard on all three systems, beside test_v1_4_prepare.py"
```
