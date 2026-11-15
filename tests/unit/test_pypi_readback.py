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
WHEEL_URL = (
    "https://files.pythonhosted.org/packages/ce/3f/"
    f"e60287fc2e8c2b8ec9152fc750c069e82a7ef1b8ebb846e42d4ad26212db/{WHEEL}"
)
SDIST = "wasi_python-0.1.4.tar.gz"
LINUX_WHEEL = "wasi_python-0.1.4-py3-none-manylinux_2_17_x86_64.whl"
PUBLISHER = {"kind": "GitHub", "repository": REPO, "workflow": "release.yml", "environment": "pypi"}


def _entry(name: str = WHEEL, sha: str = SHA, url: str | None = None) -> dict:
    url = WHEEL_URL.replace(WHEEL, name) if url is None else url
    return {"filename": name, "digests": {"sha256": sha}, "url": url}


def _files(sha: str = SHA, name: str = WHEEL, url: str | None = None) -> tuple[int, bytes]:
    return _listing(_entry(name, sha, url))


def _listing(*entries: dict) -> tuple[int, bytes]:
    return 200, json.dumps({"urls": list(entries)}).encode()


def _prov(publisher: dict | None = None, attestations: int = 1) -> tuple[int, bytes]:
    bundles = [] if publisher is None else [
        {"publisher": publisher, "attestations": [{"version": 1}] * attestations}
    ]  # fmt: skip
    return 200, json.dumps({"version": 1, "attestation_bundles": bundles}).encode()


NOT_FOUND = (404, b'{"message": "No provenance available"}')
UNASKED = (500, b"")  # what any URL the check should not read answers


def _run(
    answers: dict[str, list[tuple[int, bytes]]], sums: str = SUMS
) -> tuple[int, list, list, list, list]:
    """The check's exit code, the URLs it fetched in order, the waits it made, the address it
    kept, and the lines it printed."""
    fetched, waits, kept, lines = [], [], [], []

    def fetch(url: str) -> tuple[int, bytes]:
        fetched.append(url)
        queue = answers.get(url, [UNASKED])
        return queue.pop(0) if len(queue) > 1 else queue[0]

    code = rb.check(
        sums, REPO, VERSION, fetch=fetch, sleep=waits.append, out=lines.append, keep=kept.append
    )
    return code, fetched, waits, kept, lines


def test_a_wheel_with_its_digest_and_provenance_passes_and_its_address_is_kept() -> None:
    code, fetched, waits, kept, _ = _run({JSON_URL: [_files()], PROV_URL: [_prov(PUBLISHER)]})
    assert (code, fetched, waits, kept) == (0, [JSON_URL, PROV_URL], [], [WHEEL_URL])


def test_another_file_beside_the_wheel_fails_at_once_and_is_named() -> None:
    answers = {JSON_URL: [_listing(_entry(), _entry(LINUX_WHEEL))], PROV_URL: [_prov(PUBLISHER)]}
    code, fetched, waits, kept, lines = _run(answers)
    assert (code, fetched, waits, kept) == (1, [JSON_URL], [], [])
    assert LINUX_WHEEL in lines[-1]


@pytest.mark.parametrize(
    "answers",
    [
        {JSON_URL: [_files(sha="ef" * 32)], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "repository": "someone/else"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "workflow": "other.yml"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "environment": "staging"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov({**PUBLISHER, "kind": "GitLab"})]},
        {JSON_URL: [_files()], PROV_URL: [_prov(PUBLISHER, attestations=0)]},
        {JSON_URL: [_files(name=SDIST)], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_listing(_entry(), _entry(SDIST))], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_listing(_entry(), _entry())], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=f"https://example.org/{WHEEL}")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=WHEEL_URL + "?x=1")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=WHEEL_URL.replace("/ce/", "/../"))], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=WHEEL_URL[:-4] + ".tar.gz")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=WHEEL_URL + "\n")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files(url=WHEEL_URL.replace("/ce/", "/c@/"))], PROV_URL: [_prov(PUBLISHER)]},
        {
            JSON_URL: [_files(url=WHEEL_URL.replace("/ce/3f/", "/ce/"))],
            PROV_URL: [_prov(PUBLISHER)],
        },
    ],
    ids=[
        "another digest",
        "another repository",
        "another workflow",
        "another environment",
        "another kind",
        "a bundle with no attestation",
        "another file in its place",
        "a source archive beside it",
        "the wheel listed twice",
        "an address off PyPI's file host",
        "an address with a query",
        "an address that climbs",
        "an address of another file",
        "an address with a newline",
        "an address with an at sign",
        "an address not in PyPI's hash shape",
    ],  # fmt: skip
)
def test_a_wrong_answer_fails_at_once(answers) -> None:
    code, fetched, waits, kept, _ = _run(answers)
    assert (code, waits, kept) == (1, [], [])
    assert set(fetched) <= {JSON_URL, PROV_URL}


@pytest.mark.parametrize(
    "answers",
    [
        {JSON_URL: [(404, b"{}")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_listing()], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [_files()], PROV_URL: [NOT_FOUND]},
        {JSON_URL: [_files()], PROV_URL: [_prov(None)]},
    ],
    ids=[
        "no version",
        "no file listed yet",
        "no provenance",
        "a provenance with no bundles",
    ],  # fmt: skip
)
def test_what_is_missing_after_six_tries_fails(answers) -> None:
    code, fetched, waits, kept, _ = _run(answers)
    assert (code, kept) == (1, [])
    assert waits == [rb.WAIT] * (rb.TRIES - 1)
    assert fetched.count(JSON_URL) == rb.TRIES


def test_a_provenance_that_arrives_on_the_third_try_passes() -> None:
    code, _, waits, kept, _ = _run(
        {JSON_URL: [_files()], PROV_URL: [NOT_FOUND, NOT_FOUND, _prov(PUBLISHER)]}
    )
    assert (code, waits, kept) == (0, [rb.WAIT, rb.WAIT], [WHEEL_URL])


def test_a_file_listed_on_the_second_try_passes() -> None:
    code, _, waits, kept, _ = _run({JSON_URL: [_listing(), _files()], PROV_URL: [_prov(PUBLISHER)]})
    assert (code, waits, kept) == (0, [rb.WAIT], [WHEEL_URL])


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
    code, fetched, _, kept, _ = _run({}, sums=sums)
    assert (code, fetched, kept) == (1, [], [])


def test_the_rehearsal_reads_a_released_wheel() -> None:
    fetched, kept = [], []

    def fetch(url: str) -> tuple[int, bytes]:
        fetched.append(url)
        if url.endswith("/json"):
            return _files(sha=rb.REHEARSAL_SHA256, name=rb.REHEARSAL_WHEEL)
        return _prov(PUBLISHER)

    assert rb.rehearse(fetch=fetch, sleep=lambda _: None, out=lambda _: None, keep=kept.append) == 0
    assert fetched == [
        f"https://pypi.org/pypi/wasi-python/{rb.REHEARSAL_VERSION}/json",
        f"https://pypi.org/integrity/wasi-python/{rb.REHEARSAL_VERSION}/"
        f"{rb.REHEARSAL_WHEEL}/provenance",
    ]
    assert kept == [WHEEL_URL.replace(WHEEL, rb.REHEARSAL_WHEEL)]


@pytest.mark.parametrize(
    "argv",
    [["rehearse"], ["check", "--sums", "s", "--repository", "r", "--version", "v"]],
    ids=["rehearse", "check"],
)
def test_both_commands_require_the_file_the_address_goes_to(argv) -> None:
    with pytest.raises(SystemExit):
        rb.main(argv)


def test_the_address_is_written_on_one_line(tmp_path) -> None:
    out = tmp_path / "pypi-wheel-url"
    rb._writer(str(out))(WHEEL_URL)
    assert out.read_text(encoding="utf-8") == WHEEL_URL + "\n"


@pytest.mark.parametrize(
    "answers",
    [
        {JSON_URL: [_files()], PROV_URL: [(503, b"")]},
        {JSON_URL: [(503, b"")], PROV_URL: [_prov(PUBLISHER)]},
        {JSON_URL: [(0, b"")], PROV_URL: [_prov(PUBLISHER)]},
    ],
    ids=["the Integrity API down", "the JSON API down", "no connection"],
)
def test_a_host_that_is_down_fails_at_once_and_is_not_retried(answers) -> None:
    code, fetched, waits, _, _ = _run(answers)
    assert (code, waits) == (1, [])
    assert fetched.count(JSON_URL) == 1
