# Review of 198 — Bound raw host requests

- **Date:** 2026-11-17
- **Reviewer:** Codex (GPT-6), a fresh sub-agent of the orchestrating session; not the author.
- **Reviewed:** PR #126, from `a85cac7f` to `9ee5e3e2`; the published tree and the local tree at `cd84442f` both have SHA `19ec8d8d1550d0009181b1d1375d2076b52a0f50`. Parallel-safe review, 25-minute box.
- **Run:** [44235027050](https://github.com/ClayGendron/wasi-python/actions/runs/44235027050). Quick, all eleven Windows judges and the gather passed. The gather recorded 1,263 goal passes, zero failures and 4,786 unit passes. The only refusal listed by ci-status and review was the pending review file.
- **Re-ran:** With the released 0.1.5 artifacts, `tests/unit/test_runner_tools.py::test_raw_request_limit_precedes_the_copy`, `tests/unit/test_runner_tools.py::test_raw_request_limit_arguments` and `tests/checks/test_v1_4_embedding.py::test_each_entry_limits_raw_host_requests`; three passed, exit 0.

## Acceptance criteria against evidence

1. EXECUTED. The door unit check observes zero reads, allocations and host callbacks on refusal, then verifies equality, zero and an explicit unbounded request. READ. The new length comparison follows the unsigned bounds check and precedes the Wasmtime memory read. The tool and display paths retain their protocol-specific admission.
2. EXECUTED. The arguments check covers the default, index-only values, zero, explicit opt-out, missing host, and invalid limits. READ. The public API page, its snapshot and the upgrading note describe the field and keyword. Appending the dataclass field preserves existing positional arguments.
3. EXECUTED. The embedding check covers run, run_async and both session turn entry points. A four-byte request was refused under a three-byte cap and the next three-byte request reached the callback. In a separate synchronous round trip I checked the callback's thread identity against the calling thread.

## Findings, most severe first

1. **Medium, resolved. Effective defaults must be normalized.** The initial implementation accepted an index-only limit in Defaults validation but forwarded the original object to the byte comparison. An otherwise admissible request could then fault.

## Constitution checks

- §4. The existing host import, its arguments and its return codes are preserved. The change bounds the Python runner's raw request before host allocation. The news file claims the new embedding check, two unit checks, the public API snapshot and the existing function-length allowances.
- Structure. The signatures and call assembly remain responsible for their existing work. The extra argument introduces no new mutable global, platform branch, engine-private access or test seam. Each increased allowance is claimed with its reason.
- §7. The stricter argument and guest checks run alongside the existing protocol checks. The new field count still requires the frozen record to carry every field. I found no relaxed security check or undeclared release action.

## Disposition

1. Fixed before the reviewed head. The checked entry now normalizes the effective default and an explicit override through the same integer validator. The new unit and embedding checks exercise the index-only case.

## Verdict

Lands on `9ee5e3e2`. The request cap holds across all four public call paths and a refused request leaves the door usable.
