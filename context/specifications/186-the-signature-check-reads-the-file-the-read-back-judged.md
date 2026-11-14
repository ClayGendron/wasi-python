# 186: The signature check reads the file the read-back judged

- **Status:** built 2026-11-14, in review. Asked for on 2026-11-14 by the owner ("Start building", on 0.1.5's scope, `../decisions.md`, "0.1.5's scope"). Its two parts were noted for 0.1.5 in `../roadmap.md`: 0.1.4's red signature check (tag run 42110186903) and the 0.1.4 security review's L1.
- **Date:** 2026-11-14
- **Owner:** Clay Gendron
- **Kind:** build-class (the release workflow's `pypi-verify` and `pypi-rehearsal` steps, the read-back script under `release/`, and rule 21 in `tests/harness/scan.py`). Not structural: nothing under `src/` changes. No wasm build, and nothing the build makes changes. Not reviewed before it is built: it changes no job that holds `id-token`, no permission and no upload, only what two `contents: read` jobs read and how they fail (constitution §5.6 asks a pre-build review for the guest's imports or exports, the artifact set and the build recipe).
- **Depends on:** 185 (the read-back, the rehearsal and rule 21).
- **Research it stands on:** the logs of 0.1.4's tag run 42110186903 (`pypi-verify`); pypi-attestations 0.0.30's `_cli.py`, the verifier `attest-action`'s lock pins, read whole for how `verify pypi` finds a file; PyPI's JSON API for 0.1.1 and 0.1.4, read 2026-11-14; the 0.1.4 security review's L1 (`../reviews/0.1.4-security-review-2026-11-05.md`).

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

Two holes in 185's read-back of PyPI.

**The signature check looked the file up in a page that lags.** 0.1.4's tag run 42110186903 uploaded the wheel with its attestation. `pypi-verify`'s first step, `pypi_readback.py check`, passed: the JSON API listed the wheel with the release's SHA-256, the Integrity API held its provenance, and the Simple API page at `https://pypi.org/simple/wasi-python/` listed the file (READ, the job's log). The next step, `pypi_attestations verify pypi ... pypi:wasi_python-0.1.4-py3-none-any.whl`, failed with "Could not find the artifact 'wasi_python-0.1.4-py3-none-any.whl' on PyPI" (READ, the same log). The verifier resolves a `pypi:` name by reading `https://pypi.org/simple/{name}`, with no trailing slash, and dies at once when the file is not listed (READ, pypi-attestations 0.0.30, `_cli.py`, `_get_direct_url_from_arg`). That address is a different cached page from the one the read-back had just read. It still lagged (INFERRED: PyPI listed the file minutes later, `../decisions.md`, "0.1.4's red read-back").

**The read-back passed with another file under the version.** `judge_once` looked for the release's wheel among the JSON API's `urls` and ignored every other entry. A second wheel beside it, for instance a `manylinux` one that pip prefers on Linux, passed (EXECUTED by the 0.1.4 security review, `p_extra_file.py`; its finding L1).

## Decisions

### 1. The verifier is handed the address the read-back judged

`check` and `rehearse` take `--url-out <file>`. On success they write the wheel's address from the JSON API's own entry, the one whose digest they judged, to that file. The signature step reads it (`url=$(cat pypi-wheel-url)`) and passes it to `verify pypi` as a direct address. The verifier then downloads those bytes from `files.pythonhosted.org`, fetches the provenance from the Integrity API, and checks the signature over the bytes. It reads no Simple API page (READ, `_cli.py`, `_get_distribution_from_arg`: an argument that starts with `https://` is downloaded as given, after a check that its host is `files.pythonhosted.org`).

The alternative the roadmap named, retrying the verifier while it says "Could not find the artifact", was not chosen. It keeps the lagging lookup and adds a loop around a third-party command's error text. Handing over the address removes the lookup. The verifier still checks the signature over PyPI's own bytes, so nothing it proved before is lost.

The read-back accepts the address only when it starts with `https://files.pythonhosted.org/packages/`, ends with `/<the wheel's name>`, and has no `?`, `#`, `%`, backslash, space or `..` in it. Anything else is `Wrong`, at once.

With no `pypi:` lookup left, the read-back no longer reads the Simple API either. Its only reason to was that the verifier did (185's code comment, "The signature check that follows finds the file through the Simple API").

### 2. The version holds the release's wheel and nothing else

The JSON API's `urls` must be exactly one entry, the wheel `SHA256SUMS` names. No entry is `Missing` and is asked again, as before. Any other file, beside the wheel or in its place, and the wheel listed twice, are `Wrong` at once, and the line names the other files. An extra file is never "not there yet" (the review's fix). A file under another version stays out of reach of a per-version read; PyPI's single trusted publisher narrows that (`../decisions.md`, "PyPI's publishers").

### 3. The rehearsal runs the same two steps

`pypi-rehearsal` runs `rehearse --url-out pypi-wheel-url` and then the verifier on that address, for 0.1.1's wheel. So every release-shaped run proves the handover before a tag needs it.

### 4. Rule 21 holds the new scripts

`READBACK_CHECK`, `READBACK_VERIFY` and the rehearsal's two scripts in `tests/harness/scan.py` change to the new text, and rule 21 holds them exactly, as before. `--url-out` is required by both commands, so a script that drops it fails at once (EXECUTED: exit 2, "the following arguments are required: --url-out").

## Design

The decisions are the design. `judge_once` returns the line and the address; `check` hands the address to a `keep` callable on success and prints the line; `main` gives `keep` a writer for `--url-out`. The workflow passes the address between two steps of one job through a file in the job's workspace, `pypi-wheel-url`, which no other job reads.

## Intent

A release's signature check passes as soon as PyPI serves the file, and a version with any file but the release's wheel is red.

## Scope

`release/pypi_readback.py`; `tests/unit/test_pypi_readback.py`; `.github/workflows/release.yml`, the read-back and signature steps of `pypi-verify` and `pypi-rehearsal` and `pypi-verify`'s comment; `tests/harness/scan.py`, the four scripts; `docs/contributing/release-process.md`, step 8. Nothing else.

## Acceptance criteria

1. `tests/unit/test_pypi_readback.py` covers: the address is kept on a pass; another file beside the wheel fails at once and is named; a source archive beside it, another file in its place and the wheel listed twice fail at once; an address off `files.pythonhosted.org`, with a query, with `..`, or of another file fails at once; an empty listing is asked again and passes when the file arrives; no URL but the JSON and Integrity APIs is read; both commands require `--url-out`. Each new row is seen failing on 185's script.
2. `rehearse --url-out` against the real PyPI writes 0.1.1's address and exits 0.
3. Rule 21 passes on the workflow, and `tests/unit/test_scan.py` passes with the new scripts.
4. The next release-shaped run's `pypi-rehearsal` is green, its signature step on the handed address.

## Landing notes

Built 2026-11-14 on `claude/project-thread-5s6fa0`, from `dev` at `25e49df5`, by the session https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC.

- **Seen failing first** (criterion 1). The new test file run against 185's script, with only a `keep=None` parameter added to its `check` so the rows load: 16 failed, among them every new row (the address kept, the extra wheel named, the seven new wrong answers, the listing that arrives on the second try, the rehearsal's fetches, the required `--url-out`), and 16 passed (EXECUTED). With this change: 32 passed (EXECUTED).
- **The real PyPI** (criterion 2). `python3 -I release/pypi_readback.py rehearse --url-out <file>`: "ok: wasi_python-0.1.1-py3-none-any.whl on PyPI has the release's SHA-256 and provenance from ClayGendron/wasi-python", exit 0, and the file holds `https://files.pythonhosted.org/packages/40/25/5e30f96b898fc799b2c577a7990100e78beafd28ba530fb5ef517409ba33/wasi_python-0.1.1-py3-none-any.whl` (EXECUTED). `check` on 0.1.4, with PyPI's own digest as its sums: ok, exit 0; PyPI lists that one file for 0.1.4 (EXECUTED).
- **The verifier on a direct address.** pypi-attestations 0.0.30 from PyPI, `verify pypi --repository https://github.com/ClayGendron/wasi-python <0.1.1's address>`, in this container: it took the address, downloaded the wheel and stopped at Sigstore's trust root, "Failed to refresh TUF metadata", which this container's network does not reach (EXECUTED). The rehearsal on GitHub's runners is where the whole check runs (criterion 4).
- **The rules** (criterion 3). `uv run pytest tests/unit/test_scan.py tests/unit/test_pypi_readback.py`: 586 passed. `tests/lint` and `tests/checks/test_rules.py`: 157 passed, 1 failed, `test_every_prior_art_clone_has_its_licence_recorded`, for four clones this container holds and CI does not (orjson, pydantic, pydantic-core, pyo3, from the 0.1.5 spikes); their rows land with the Rust pipeline's specification (EXECUTED).
- **Base state.** `tests/unit` in this container: 1 failed, 1,777 passed, the failure `test_the_walk_judges_links`, from running as root, as 185's notes record (EXECUTED).
