"""Making a snapshot: `make_snapshot`, which runs any code once and keeps the guest's memory, and
`make_package_snapshot`, which imports every package the set ships, or the ones named.

A making is a `Session` of one turn that enters the snapshot binary's `prepare` export instead
of `turn`, with the caller's arguments checked by `run`'s rules; its image is read when the
code returned 0, and the session is then closed with no shutdown, since the instance is
discarded."""

from __future__ import annotations

import keyword
import os
import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import _artifacts, _limits, _snapshot, runner
from ._artifacts import Artifacts, ArtifactsMissing
from ._limits import _UNSET
from ._places import Grant
from ._process import process
from ._snapshot import Snapshot, SnapshotFailed

if TYPE_CHECKING:
    from .mounts import Mount

DEADLINE_S = 600.0  # a making is a setup step, run once: the image of every package takes ~30 s
PACKAGE_LINE = "x-snapshot-package"  # MANIFEST: a distribution, then the names it imports
DISTRIBUTION = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")  # as pip names one


def make_snapshot(
    code: str,
    *,
    root: str | os.PathLike[str] | bool | None = False,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    fuel: int | None = None,
    deadline_s: float | None = DEADLINE_S,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    max_file_calls: int | None = _UNSET,
    max_open_files: int | None = _UNSET,
) -> Snapshot:
    """Run your code once in a fresh guest and keep its memory, as a starting image.

    The code runs as a module runs, in `__main__`: it may import packages, read data from a grant
    and define functions and objects. A call later given the snapshot starts from that memory,
    in the same `__main__`, with its own grants, environment, clocks and randomness. The
    keywords are `run`'s, checked by its rules before any work; `tools=` cannot be kept in an
    image, so it goes on the calls. While the code runs its clocks do not move and its entropy is
    zeros, so make no secret in it, and pass none in `env`: both stay in the image.

    Args:
        code: The code to run, a str of at most 16 MiB as UTF-8.
        root: As for `run`: no / by default; `True` a private one, removed after the making.
        grants: As for `run`.
        mounts: As for `run`.
        import_path: As for `run`, while the code runs; a call passes its own to import more.
        env: As for `run`; the origin keeps the names only, but the image holds the values.
        host: As for `run`, while the code runs.
        fuel: A cap on the code's instructions, which the origin then records; `None`, none.
        deadline_s: Wall-clock seconds the making may run. Default: 600. `None`, no limit.
        memory_bytes: As for `run`; it caps the image's size.
        output_bytes: As for `run`.
        cache_dir: As for `run`.
        artifacts: As for `run`; a call from the image must run the same set.
        max_file_calls: As for `run`.
        max_open_files: As for `run`.

    Returns:
        The snapshot: its image and its origin.

    Raises:
        TypeError: An argument has the wrong type, or `run` takes it and a making does not.
        ValueError: An argument is out of range; raised before any work.
        SnapshotFailed: The code exited with a status other than 0, raised, trapped, ran past
            its deadline or its fuel, or left a file or folder open.
        ArtifactsMissing: There is no usable artifact set, or it predates snapshots you make.
        OSError: A host filesystem call failed while the folders were prepared.
        RuntimeError: As for `Session`.
    """
    data = _code(code)
    making: Any = _snapshot.MAKING  # the start `_checked` knows: the image's HOME, no image
    session = runner.Session(
        root=root,
        grants=grants,
        mounts=mounts,
        import_path=import_path,
        env=env,
        host=host,
        snapshot=making,
        fuel=fuel,
        deadline_s=deadline_s,
        memory_bytes=memory_bytes,
        output_bytes=output_bytes,
        cache_dir=cache_dir,
        artifacts=artifacts,
        max_file_calls=max_file_calls,
        max_open_files=max_open_files,
        idle_s=None,
        lifetime_s=None,
        shutdown_s=0,  # the instance is discarded: its teardown would buy nothing
    )
    return _made_in(session, code, data)


def _code(code: Any) -> bytes:
    data = str.encode(_limits._text("code", code), "utf-8")
    if len(data) > _snapshot.MAX_CODE_BYTES:
        raise ValueError(
            f"code must be at most {_snapshot.MAX_CODE_BYTES:,} bytes as UTF-8; give larger "
            "data through a grant"
        )
    return data


def _made_in(session: runner.Session, code: str, data: bytes) -> Snapshot:
    """The making's one turn, then the session closed, never used again whatever the turn did;
    the image and its origin, or the `SnapshotFailed` that says why there is none."""
    c = session._state.checked
    try:
        done, captured, digests = session._prepare(data, c.fuel, c.deadline_s, c.output_bytes)
    finally:
        session.close()
    image = _made_or_failed(done, captured, c.deadline_s, c.fuel)
    paths = ["/"] if c.root is not False else []
    paths += [g.guest for g in c.grants] + [m.guest for m in c.mounts]
    origin = _snapshot._origin_of(
        code, image, done.fuel_used, paths, (c.env or {}), (digests.binary, digests.zip)
    )
    p = process()
    with p.cache_lock:
        p.counts["snapshots_made"] += 1
    return _snapshot._made(image, origin)


def _made_or_failed(
    done: runner.Completed,
    captured: tuple[bytes, int] | None,
    deadline_s: float | None,
    fuel: int | None,
) -> bytes:
    """The image, or the `SnapshotFailed` that says why there is none."""
    lines = [ln for ln in done.stderr.decode("utf-8", "replace").splitlines() if ln.strip()]
    last = f": {lines[-1].strip()}" if lines else ""
    if done.trapped is not None:
        if done.trapped == "deadline":
            why = (
                f"the snapshot's code ran past its deadline of {deadline_s:g} s; a snapshot's code "
                "sees a clock that does not move, so code that waits for time to pass never "
                "finishes"
            )
        elif done.trapped == "out of fuel":
            why = f"the snapshot's code ran out of fuel ({fuel:,} instructions); pass more fuel"
        else:
            why = f"the snapshot's code trapped: {done.trapped}{last}"
        raise SnapshotFailed(why, reason="trapped", completed=done)
    if done.exit_code != 0 or captured is None:
        status = done.exit_code
        why = f"the snapshot's code exited with status {status}{last}"
        raise SnapshotFailed(why, reason="exit", completed=done)
    image, left = captured
    if left:
        raise SnapshotFailed(
            f"the snapshot's code left {left} file{'s' if left > 1 else ''} open; close what it "
            "opens (use `with`), since a call started from the image cannot reopen it",
            reason="open file",
            completed=done,
        )
    return image


def make_package_snapshot(
    packages: Iterable[str] | None = None,
    *,
    root: str | os.PathLike[str] | bool | None = True,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    fuel: int | None = None,
    deadline_s: float | None = DEADLINE_S,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    max_file_calls: int | None = _UNSET,
    max_open_files: int | None = _UNSET,
) -> Snapshot:
    """Import packages once and keep the guest's memory: by default every package the set ships.

    With no `packages` it imports every name the set's MANIFEST lists for its packages, the
    submodules a program reaches for included, so you never type the list. A name given is a
    distribution's as you install it (`scikit-learn`), which imports that package's list, or a
    dotted module name, imported as given (`sklearn.tree`, `json`). Its code is one `import`
    line per name. The keywords are `make_snapshot`'s, but `root` defaults to a private root,
    removed after the making, since matplotlib needs a writable /tmp to import; the calls from
    the image need none.

    Args:
        packages: Distribution or module names; `None` (the default) every package the set
            ships. A str alone is refused: pass `["numpy"]`.
        root: As for `make_snapshot`. Default: `True`, a private root.
        grants: As for `make_snapshot`.
        mounts: As for `make_snapshot`.
        import_path: As for `make_snapshot`.
        env: As for `make_snapshot`.
        host: As for `make_snapshot`.
        fuel: As for `make_snapshot`.
        deadline_s: As for `make_snapshot`. Default: 600.
        memory_bytes: As for `make_snapshot`.
        output_bytes: As for `make_snapshot`.
        cache_dir: As for `make_snapshot`.
        artifacts: As for `make_snapshot`; its MANIFEST names the packages.
        max_file_calls: As for `make_snapshot`.
        max_open_files: As for `make_snapshot`.

    Returns:
        The snapshot, whose origin's `prelude` is the import lines.

    Raises:
        TypeError: `packages` is a str or holds a non-str, or another argument's type is wrong.
        ValueError: A name is neither a distribution's nor a dotted module name, or another
            argument is out of range.
        SnapshotFailed: As for `make_snapshot`.
        ArtifactsMissing: No usable artifact set, or its MANIFEST lists no packages.
        OSError: As for `make_snapshot`.
        RuntimeError: As for `make_snapshot`.
    """
    given = _checked_names(packages)
    if artifacts is not None and not isinstance(artifacts, Artifacts):
        raise TypeError(f"artifacts must be an Artifacts, or None; got {type(artifacts).__name__}")
    found = artifacts if artifacts is not None else _artifacts.artifacts()
    code = _package_code(_package_names(given, found.manifest))
    return make_snapshot(
        code,
        root=root,
        grants=grants,
        mounts=mounts,
        import_path=import_path,
        env=env,
        host=host,
        fuel=fuel,
        deadline_s=deadline_s,
        memory_bytes=memory_bytes,
        output_bytes=output_bytes,
        cache_dir=cache_dir,
        artifacts=artifacts,
        max_file_calls=max_file_calls,
        max_open_files=max_open_files,
    )


def _dotted(name: str) -> bool:
    """A dotted Python name: identifiers, none a keyword, joined by dots."""
    parts = name.split(".")
    return all(p.isidentifier() and not keyword.iskeyword(p) for p in parts)


def _checked_names(packages: Any) -> tuple[str, ...] | None:
    """`packages` as a tuple of names, each a distribution's or a dotted Python name."""
    if packages is None:
        return None
    if isinstance(packages, (str, bytes)) or not isinstance(packages, Iterable):
        raise TypeError(
            f"packages must be an iterable of names, not a {type(packages).__name__}: "
            "pass ['numpy']"
        )
    names = tuple(packages)
    for i, name in enumerate(names):
        if not isinstance(name, str):
            raise TypeError(f"packages[{i}] must be a str; got {type(name).__name__}")
        if not (_dotted(name) or DISTRIBUTION.match(name)):
            raise ValueError(
                f"packages[{i}] {name!r} is neither a distribution's name nor a dotted module name"
            )
    return names


def _package_lines(manifest: Path) -> list[tuple[str, list[str]]]:
    lines = []
    for line in manifest.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == PACKAGE_LINE:
            lines.append((parts[1], parts[2:]))
    return lines


def _package_names(given: Iterable[str] | None, manifest: Path) -> list[str]:
    """The modules to import, in order, each once: every line's names for `None`; else a
    distribution's line for its name, case-folded; a line for its first name; and any other
    dotted name as given."""
    lines = _package_lines(manifest)
    if given is None and not lines:
        raise ArtifactsMissing(
            f"{manifest} has no {PACKAGE_LINE} lines: this artifact set predates package "
            "snapshots; name the modules to import, or use make_snapshot"
        )
    by_distribution = {d.casefold(): names for d, names in lines}
    by_first = {names[0]: names for _, names in lines}
    out: list[str] = []
    for name in [d for d, _ in lines] if given is None else given:
        names = by_distribution.get(name.casefold()) or by_first.get(name)
        if names is None and not _dotted(name):
            if not lines:
                raise ArtifactsMissing(
                    f"{manifest} has no {PACKAGE_LINE} lines, so {name!r}, a distribution's "
                    "name, cannot be resolved; name the modules to import"
                )
            raise ValueError(f"packages: this artifact set ships no package named {name!r}")
        out += [n for n in names or [name] if n not in out]
    return out


def _package_code(names: Iterable[str]) -> str:
    return "".join(f"import {n}\n" for n in names)
