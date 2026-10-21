"""`scripts/line.py` on each build host, and on a host that builds nothing.

A build host gets its own toolchain, host Python and wheels under the plain names. Any other host
(Windows, an Intel Mac) still reads the line, with the host names left unset, so the judge's
oracle reads as unavailable there instead of ending the run."""

from __future__ import annotations

import importlib.util
import platform

import pytest

from harness import jobs, scan

BUILD_HOSTS = [
    ("Darwin", "arm64", "MACOS_ARM64"),
    ("Linux", "aarch64", "LINUX_AARCH64"),
    ("Linux", "x86_64", "LINUX_X86_64"),
]
FOREIGN_HOSTS = [("Windows", "AMD64"), ("Darwin", "x86_64")]


def _line():
    spec = importlib.util.spec_from_file_location("wasi_python_line_unit", jobs.LINE_PY)
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    return line


def _on(monkeypatch, system: str, machine: str) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "machine", lambda: machine)


@pytest.mark.parametrize(("system", "machine", "key"), BUILD_HOSTS)
def test_each_build_host_reads_its_own_names(monkeypatch, system, machine, key) -> None:
    _on(monkeypatch, system, machine)
    values = _line().read()
    assert {name: values.get(name) for name in scan.HOST_NAMES} == {
        name: values.get(f"{key}_{name}", f"<no {key}_{name}>") for name in scan.HOST_NAMES
    }


@pytest.mark.parametrize(("system", "machine"), FOREIGN_HOSTS)
def test_a_foreign_host_reads_the_line_and_the_oracle_is_unavailable(
    monkeypatch, system, machine
) -> None:
    _on(monkeypatch, system, machine)
    values = _line().read()
    assert values["PYTHON_MM"] == ".".join(values["PYTHON_VERSION"].split(".")[:2])
    assert sorted(set(scan.HOST_NAMES) & set(values)) == []
    with pytest.raises(RuntimeError, match="no host Python for this host"):
        jobs.host_python_archive()
    jobs.oracle_available.cache_clear()
    try:
        assert jobs.oracle_available() is False
    finally:
        jobs.oracle_available.cache_clear()
