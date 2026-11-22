# Fresh requests from an all-packages snapshot

**Status.** Executed benchmark, 2026-11-18. The question was how much faster a fresh request could start once every package had already been imported. The comparison used the same snapshot, scripts and Python runner on `a85cac7f` (the tip of `dev` that day, tagged `v0.1.5`). The host was one Linux x86-64 machine with Wasmtime 50.0.1. The [warm samples](2026-11-18-package-snapshot-startup/warm.jsonl) include the package mapping, artifact hashes, workload hashes and run order.

**EXECUTED.** `make_package_snapshot()` produced a 253,296,640-byte image. The baseline restored it into each fresh instance with the runner's memory copy. The prototype put those same bytes into a Wasm module's initial memory and loaded the compiled module from a checked file so Wasmtime could map it copy-on-write. Before running guest code, the experiment compared the prepared instance's memory byte for byte with the snapshot.

| Warm service, default runner settings | Current restore | File-backed restore |
|---|---:|---:|
| Median time to the first guest signal | 241 ms | 18 ms |
| Median time to the returned result | 377 ms | 166 ms |
| 90th percentile time to the returned result | 639 ms | 402 ms |

**EXECUTED.** Fifteen functional workloads covered all 85 package entries in the snapshot manifest, alongside an empty control. The workloads checked results from operations including model fitting, CSV grouping, SQL queries, chart rendering, and spreadsheet and document round trips. Each arm ran each case ten times after an excluded warmup, in randomized order. Startup includes the host callback at the first guest statement. Completion includes shutdown and output delivery. This command recalculates the medians from the repository root.

```sh
uv run python - <<'PY'
import json
from pathlib import Path
from statistics import median

path = Path("context/research/2026-11-18-package-snapshot-startup/warm.jsonl")
rows = [json.loads(line) for line in path.read_text().splitlines()]
for arm in ("copy", "cow"):
    samples = [r for r in rows if r["kind"] == "sample" and r["arm"] == arm]
    print(arm, len(samples), *(round(median(r[k] for r in samples)) for k in ("ready_ms", "total_ms")))
PY
```

**EXECUTED.** With a populated compiled cache, four new Python processes per method returned their first empty result in a median 3.69 s with the current runner, 4.94 s when the prototype rebuilt and checked the prepared module at launch, and 3.39 s when that work had been done before launch. Even the staged prototype loaded the original snapshot. The prepared unmetered compiled cache file was about 505 MiB on this host, against 303 MiB for the current module. [Fresh-process samples](2026-11-18-package-snapshot-startup/cold.jsonl)

**INFERRED.** Stage the package image and native compilation before service startup. Benchmark cold processes separately from fresh requests in a warm process. Concurrent throughput, private memory as guests write, and performance on other platforms still need measurements. The sub-5-ms goal in the [November 14 proposal](2026-11-14-what-0-2-0-could-be.md) remains a target.
