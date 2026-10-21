"""v1.2: the same bytes run here and elsewhere, see only their root, and reach no network."""

from __future__ import annotations

import pytest

from harness import artifacts as rules
from harness import needs, paths, scan

pytestmark = pytest.mark.goal("v1.2")


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_guest_runs_here(guest, which) -> None:
    r = guest(which, ["-c", "print(1)"])
    assert (r.exit_code, r.text) == (0, "1\n"), r.describe()


def test_guest_sees_only_its_root(guest) -> None:
    code = (
        "import os\n"
        "print(sorted(os.listdir('/')))\n"
        "try:\n"
        "    up = sorted(os.listdir('/..'))\n"
        "except OSError:\n"
        "    up = 'refused'\n"
        "print(up)\n"
        "print(os.path.exists('/etc/hosts'))\n"
    )
    r = guest("plain", ["-c", code], files={"/data/x.txt": "x"})
    assert r.exit_code == 0, r.describe()
    root_listing = str(sorted(p.name for p in r.root.iterdir()))
    lines = r.text.splitlines()
    assert lines[0] == root_listing, f"/ lists {lines[0]}, the root holds {root_listing}"
    assert lines[1] in ("refused", root_listing), f"/.. escaped the root: {lines[1]}"
    assert lines[2] == "False", "the guest sees /etc/hosts"


def test_guest_has_no_network(guest) -> None:
    code = (
        "import socket\n"
        "try:\n"
        "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "    s.connect(('1.1.1.1', 80))\n"
        "    print('connected')\n"
        "except (OSError, AttributeError) as e:\n"
        "    print('refused', type(e).__name__)\n"
    )
    r = guest("plain", ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.startswith("refused"), f"the guest reached the network: {r.text.strip()}"


def test_nothing_is_a_shared_library(artifacts, guest) -> None:
    needs.need("stdlib zip")
    shared = rules.shared_library_errors(artifacts.path("python-stdlib.zip"))
    assert not shared, scan.report(shared)
    code = (
        "import sys, numpy, pandas\n"
        "mods = [m for n, m in sorted(sys.modules.items())"
        " if n.startswith(('numpy', 'pandas')) and getattr(m, '__spec__', None)"
        " and m.__spec__.origin and not m.__spec__.origin.endswith('.py')"
        " and not m.__spec__.origin.endswith('.pyc')]\n"
        "print(sorted({m.__spec__.origin for m in mods}))\n"
    )
    r = guest("plain", ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == "['built-in']", f"extension module origins: {r.text.strip()}"


def test_same_bytes_passed_on_three_systems() -> None:
    needs.need("three systems")
    d = paths.artifact_dir()
    from harness import history

    systems = history.systems_that_passed(paths.PROGRESS, paths.sha256_file(d / "python.wasm"))
    assert systems >= {"linux", "darwin", "win32"}, sorted(systems)


def test_the_guest_clocks_resolution_is_the_judges(guest, monkeypatch) -> None:
    """Guards a change: the judge answers `clock_res_get`
    itself, so every host shows the guest the same resolutions. Distinct values prove the judge
    answered, not the host (a Linux host answers 1 ns, which turned CPython's timing tests from
    skips into failures there)."""
    from harness import guest as driver

    monkeypatch.setattr(driver, "CLOCK_RESOLUTION_NS", {0: 7_000, 1: 11_000, 2: 13, 3: 17})
    code = (
        "import time\n"
        "for c in ('time', 'monotonic', 'perf_counter'):\n"
        "    print(round(time.get_clock_info(c).resolution * 1e9))\n"
    )
    r = guest("snapshot", ["-c", code], record=False)
    assert r.exit_code == 0, r.describe()
    # process_time's resolution never reaches clock_res_get in this guest (it reads 1 ns either
    # way, EXECUTED), so only the clocks that ask are checked.
    assert r.text.split() == ["7000", "11000", "11000"], r.text
