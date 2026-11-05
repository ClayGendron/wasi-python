"""The release's read-back of PyPI: the wheel's digest and its provenance, judged on recorded
answers with the network replaced. Each row is one way PyPI can answer, and the verdict it gets."""

from __future__ import annotations

import importlib.util
import json

import pytest

from harness import paths


def _module():
    spec = importlib.util.spec_from_file_location(
        "wasi_python_pypi_readback_unit", paths.REPO / "release" / "pypi_readback.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rb = _module()

REPO = "ClayGendron/wasi-python"
VERSION = "0.1.4"
WHEEL = "wasi_python-0.1.4-py3-none-any.whl"
SHA = "ab" * 32
SUMS = f"{'cd' * 32}  wasi-python-0.1.4-artifacts.tar.xz\n{SHA}  {WHEEL}\n"
JSON_URL = f"https://pypi.org/pypi/wasi-python/{VERSION}/json"
PROV_URL = f"https://pypi.org/integrity/wasi-python/{VERSION}/{WHEEL}/provenance"
SIMPLE_URL = "https://pypi.org/simple/wasi-python/"
SIMPLE = (200, json.dumps({"files": [{"filename": WHEEL}]}).encode())
PUBLISHER = {"kind": "GitHub", "repository": REPO, "workflow": "release.yml", "environment": "pypi"}


def _files(sha: str = SHA, name: str = WHEEL) -> tuple[int, bytes]:
    return 200, json.dumps({"urls": [{"filename": name, "digests": {"sha256": sha}}]}).encode()


def _prov(publisher: dict | None = None, attestations: int = 1) -> tuple[int, bytes]:
    bundles = [] if publisher is None else [
        {"publisher": publisher, "attestations": [{"version": 1}] * attestations}
    ]  # fmt: skip
    return 200, json.dumps({"version": 1, "attestation_bundles": bundles}).encode()


NOT_FOUND = (404, b'{"message": "No provenance available"}')


def _run(answers: dict[str, list[tuple[int, bytes]]], sums: str = SUMS) -> tuple[int, list, list]:
    """The check's exit code, the URLs it fetched in order, and the waits it made."""
    fetched, waits = [], []

    def fetch(url: str) -> tuple[int, bytes]:
        fetched.append(url)
        queue = answers.get(url, [SIMPLE])
        return queue.pop(0) if len(queue) > 1 else queue[0]

    code = rb.check(sums, REPO, VERSION, fetch=fetch, sleep=waits.append, out=lambda _: None)
    return code, fetched, waits


def test_a_wheel_with_its_digest_and_provenance_passes() -> None:
    code, fetched, waits = _run({JSON_URL: [_files()], PROV_URL: [_prov(PUBLISHER)]})
    assert (code, fetched, waits) == (0, [JSON_URL, PROV_URL, SIMPLE_URL], [])


def test_a_file_the_simple_api_does_not_list_yet_is_asked_again() -> None:
    late = [(200, b'{"files": []}'), SIMPLE]
    answers = {JSON_URL: [_files()], PROV_URL: [_prov(PUBLISHER)], SIMPLE_URL: late}
    code, _, waits = _run(answers)
    assert (code, waits) == (0, [rb.WAIT])


@pytest.mark.parametrize(
    "answers",
    [
        {JSON_URL: [_files(sha="ef" * 32)], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "repository": "someone/else"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "workflow": "other.yml"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "environment": "staging"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "kind": "GitLab"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov(PUBLISHER, attestations=0)]},
    ],
    ids=[
        "another digest",
        "another repository",
        "another workflow",
        "another environment",
        "another kind",
        "a bundle with no attestation",
    ],  # fmt: skip
)
def test_a_wrong_answer_fails_at_once(answers) -> None:
    code, _, waits = _run(answers)
    assert (code, waits) == (1, [])


@pytest.mark.parametrize(
    "answers",
    [
        {JSON_URL: [(404, b"{}")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(name="wasi_python-0.1.4.tar.gz")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files()], PROV_URL: [NOT_FOUND]},
        {JSON_URL: [_files()], PROV_URL: [_prov(None)]},
        {JSON_URL: [_files()], PROV_URL: [(503, b"")]},
    ],
    ids=[
        "no version",
        "no such file",
        "no provenance",
        "a provenance with no bundles",
        "PyPI unavailable",
    ],  # fmt: skip
)
def test_what_is_missing_after_six_tries_fails(answers) -> None:
    code, fetched, waits = _run(answers)
    assert code == 1
    assert waits == [rb.WAIT] * (rb.TRIES - 1)
    assert fetched.count(JSON_URL) == rb.TRIES


def test_a_provenance_that_arrives_on_the_third_try_passes() -> None:
    code, _, waits = _run(
        {JSON_URL: [_files()], PROV_URL: [NOT_FOUND, NOT_FOUND, _prov(PUBLISHER)]}
    )
    assert (code, waits) == (0, [rb.WAIT, rb.WAIT])


def test_publisher_names_compare_without_case() -> None:
    upper = {**PUBLISHER, "repository": REPO.upper(), "environment": "PyPI"}
    assert _run({JSON_URL: [_files()], PROV_URL: [_prov(upper)]})[0] == 0


@pytest.mark.parametrize(
    "sums",
    ["", f"{'cd' * 32}  wasi-python-0.1.4-artifacts.tar.xz\n",
     SUMS + f"{SHA}  wasi_python-0.1.4-py3-none-manylinux.whl\n"],
    ids=["empty", "no wheel", "two wheels"],
)  # fmt: skip
def test_sums_that_do_not_name_one_wheel_fail_before_any_fetch(sums) -> None:
    code, fetched, _ = _run({}, sums=sums)
    assert (code, fetched) == (1, [])


def test_the_rehearsal_reads_a_released_wheel() -> None:
    fetched = []

    def fetch(url: str) -> tuple[int, bytes]:
        fetched.append(url)
        if url.endswith("/json"):
            return _files(sha=rb.REHEARSAL_SHA256, name=rb.REHEARSAL_WHEEL)
        if "/simple/" in url:
            return 200, json.dumps({"files": [{"filename": rb.REHEARSAL_WHEEL}]}).encode()
        return _prov(PUBLISHER)

    assert rb.rehearse(fetch=fetch, sleep=lambda _: None, out=lambda _: None) == 0
    assert fetched == [
        f"https://pypi.org/pypi/wasi-python/{rb.REHEARSAL_VERSION}/json",
        f"https://pypi.org/integrity/wasi-python/{rb.REHEARSAL_VERSION}/"
        f"{rb.REHEARSAL_WHEEL}/provenance",
        "https://pypi.org/simple/wasi-python/",
    ]
