"""What PyPI serves for a release's wheel, read back after the upload.

    python3 -I release/pypi_readback.py check --sums release-assets/SHA256SUMS \
        --repository <owner>/<repo> --version <version>
    python3 -I release/pypi_readback.py rehearse

`check` finds the one wheel SHA256SUMS names and requires three answers from PyPI: the JSON API
lists that file with that SHA-256, the Integrity API holds its provenance with at least one
attestation whose publisher is this repository's release.yml in the pypi environment, and the
Simple API, which the signature check reads, lists the file. A file
uploaded without its attestation has no provenance, and PyPI's page then warns that it was lost.
The command-line verifier prints OK for a provenance with no attestation and does not check the
workflow, so this check comes first and the signature check after it.

PyPI's APIs can lag an upload by a few seconds, so an answer that says something is not there
yet (a 404, or a file not listed) is asked again, TRIES times in all, WAIT seconds apart: a bounded
read of this project's own upload, once per release. Anything else fails at once: an answer that
is there and wrong (another digest, another publisher), and a host that is down or will not
answer, which is never retried on a timer. Every request times out after TIMEOUT seconds.

`rehearse` runs the same check on a wheel already released with provenance, so a run that never
uploads still proves that the read-back works before a tag needs it. Standard library only; it
exits 0 with one line when everything holds, and 1 with one line naming what does not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT = "wasi-python"
WORKFLOW = "release.yml"
ENVIRONMENT = "pypi"
TRIES = 6
WAIT = 30
TIMEOUT = 30
INTEGRITY_ACCEPT = "application/vnd.pypi.integrity.v1+json, application/json"
SIMPLE_ACCEPT = "application/vnd.pypi.simple.v1+json"
# A released wheel whose provenance names this repository, release.yml and the pypi environment.
REHEARSAL_VERSION = "0.1.1"
REHEARSAL_WHEEL = "wasi_python-0.1.1-py3-none-any.whl"
REHEARSAL_SHA256 = "191f22a3320a71e471ad202c7e98d60ed4c647f0ba3866a20d96dc29a1715547"
REHEARSAL_REPOSITORY = "ClayGendron/wasi-python"

Fetch = Callable[[str], tuple[int, bytes]]


class Missing(Exception):
    """PyPI does not hold it yet; asked again."""


class Wrong(Exception):
    """PyPI holds something other than the release's; never asked again."""


def fetch_url(url: str) -> tuple[int, bytes]:
    """The status and body of a GET, an HTTP error as its status, a failed connection as 0."""
    request = Request(
        url,
        headers={
            "Accept": SIMPLE_ACCEPT if "/simple/" in url else INTEGRITY_ACCEPT,
            "User-Agent": "wasi-python-release-readback",
        },
    )
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, b""
    except (URLError, TimeoutError, OSError):
        return 0, b""


def one_wheel(sums: str) -> tuple[str, str]:
    """The one wheel SHA256SUMS names, as (file name, SHA-256)."""
    wheels = []
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].endswith(".whl"):
            wheels.append((parts[1].lstrip("*"), parts[0].lower()))
    if len(wheels) != 1:
        raise Wrong(f"SHA256SUMS names {len(wheels)} wheels, not one")
    return wheels[0]


def _json(status: int, body: bytes, what: str) -> dict:
    # Only a 404 means "not there yet". A host that is down, or answers anything else, fails at
    # once: the read is not retried against an outage, and pypi-verify is re-run alone later.
    if status == 404:
        raise Missing(f"{what} answered 404")
    if status != 200:
        raise Wrong(f"{what} answered {status or 'no connection'}")
    try:
        return json.loads(body)
    except ValueError as error:
        raise Missing(f"{what} answered with no JSON") from error


def _same(a: object, b: str) -> bool:
    return isinstance(a, str) and a.casefold() == b.casefold()


def judge_once(fetch: Fetch, version: str, wheel: str, sha256: str, repository: str) -> str:
    """One reading of both APIs: a line saying what holds, or Missing, or Wrong."""
    files = _json(*fetch(f"https://pypi.org/pypi/{PROJECT}/{version}/json"), "the JSON API")
    listed = [f for f in files.get("urls", []) if f.get("filename") == wheel]
    if not listed:
        raise Missing(f"PyPI lists no {wheel} for {version}")
    served = str(listed[0].get("digests", {}).get("sha256", "")).lower()
    if served != sha256:
        raise Wrong(f"PyPI serves {wheel} with SHA-256 {served}, not the release's {sha256}")
    url = f"https://pypi.org/integrity/{PROJECT}/{version}/{wheel}/provenance"
    provenance = _json(*fetch(url), "the Integrity API")
    bundles = provenance.get("attestation_bundles") or []
    if not bundles:
        raise Missing(f"PyPI holds no provenance for {wheel}")
    for bundle in bundles:
        publisher = bundle.get("publisher") or {}
        if (
            _same(publisher.get("kind"), "GitHub")
            and _same(publisher.get("repository"), repository)
            and _same(publisher.get("workflow"), WORKFLOW)
            and _same(publisher.get("environment"), ENVIRONMENT)
            and bundle.get("attestations")
        ):
            # The signature check that follows finds the file through the Simple API, whose
            # cached page can lag the other two.
            simple = _json(*fetch(f"https://pypi.org/simple/{PROJECT}/"), "the Simple API")
            if wheel not in [f.get("filename") for f in simple.get("files", [])]:
                raise Missing(f"the Simple API lists no {wheel} yet")
            return f"ok: {wheel} on PyPI has the release's SHA-256 and provenance from {repository}"
    names = [bundle.get("publisher") for bundle in bundles]
    raise Wrong(
        f"{wheel}'s provenance names {names}, not {repository} {WORKFLOW} in {ENVIRONMENT} "
        "with an attestation"
    )


def check(
    sums: str,
    repository: str,
    version: str,
    *,
    fetch: Fetch = fetch_url,
    sleep: Callable[[float], object] = time.sleep,
    out: Callable[[str], object] = print,
) -> int:
    """0 when PyPI serves the release's wheel with its provenance, else 1, with one line."""
    try:
        wheel, sha256 = one_wheel(sums)
    except Wrong as error:
        out(f"FAIL: {error}")
        return 1
    for attempt in range(1, TRIES + 1):
        try:
            out(judge_once(fetch, version, wheel, sha256, repository))
            return 0
        except Wrong as error:
            out(f"FAIL: {error}")
            return 1
        except Missing as error:
            if attempt == TRIES:
                out(f"FAIL: after {TRIES} tries, {error}")
                return 1
            out(f"try {attempt} of {TRIES}: {error}; again in {WAIT} seconds")
            sleep(WAIT)
    return 1  # not reached: the loop returns on its last try


def rehearse(
    *,
    fetch: Fetch = fetch_url,
    sleep: Callable[[float], object] = time.sleep,
    out: Callable[[str], object] = print,
) -> int:
    """The check on a released wheel that carries provenance."""
    sums = f"{REHEARSAL_SHA256}  {REHEARSAL_WHEEL}\n"
    return check(sums, REHEARSAL_REPOSITORY, REHEARSAL_VERSION, fetch=fetch, sleep=sleep, out=out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("check")
    one.add_argument("--sums", required=True)
    one.add_argument("--repository", required=True)
    one.add_argument("--version", required=True)
    sub.add_parser("rehearse")
    args = parser.parse_args(argv)
    if args.command == "rehearse":
        return rehearse()
    with open(args.sums, encoding="utf-8") as handle:
        sums = handle.read()
    return check(sums, args.repository, args.version)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
