# 150: A starting image the embedder chooses

## Changelog

### Added

- **Start every call from your own snapshot.** Run your setup code once, imports, data and functions, with `make_snapshot`, or import every package with `make_package_snapshot()`, then pass `snapshot=` to `run` or `Session`: each call is still a fresh, sealed instance, and skips the seconds its imports took. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "150"
new = ["tests/checks/test_v1_4_starting_image.py"]
units = 33
[claim.judge]
"tests/public_api.txt" = "the starting image's public names: Snapshot with origin, save, load (a class method) and check, SnapshotOrigin's fields, SnapshotFailed, SnapshotMismatch, make_snapshot and make_package_snapshot, snapshot= widened to bool | Snapshot on run, run_async and Session, Completed.image_sha256, and the stats keys snapshots_made and snapshots_restored"
"tests/release_shards.toml" = "the new check file test_v1_4_starting_image.py joins own-guest, and the new unit file test_snapshot.py joins own-runner, on all three systems, as every product check file and runner unit file is in a files shard"
"tests/checks/test_rules.py" = "the long-function record set to the lengths this tree measures: _sessions.py:_open_session rises 136 to 140 and _call.py:_instance 155 to 157, each to thread a snapshot's set check, fixed HOME and image through the opening and the instance, which the specification claims; run, run_async and Session.__init__ stay at 156, 181 and 178, and Session.run_async is 81 as 144 left it; _open_session's other 2 lines are 146's, landed on dev; _Process.__init__ rises 83 (as 144 left it) to 84 for one field, the registry of what live calls may write, which save and load read so no running guest can rewrite a snapshot file"
"tests/harness/api.py" = "the API harness lists a class method as one (Snapshot.load), and the two new modules in its lists"
"tests/checks/test_v1_4_embedding.py" = "the module-cache check compares stats() whole, which now holds snapshots_made and snapshots_restored at 0 for a call without a snapshot"
"tests/lint/budget.toml" = "the new family test_v1_4_starting_image is capped at twice the largest fuel of its first local run (test_a_call_does_not_keep_the_makings_import_path, 98,428,031); the first acceptance may set it again"
```
