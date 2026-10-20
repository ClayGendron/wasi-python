"""The v1.1 rules as functions over an artifact directory, so a self-test can run each one on a
good and a bad synthetic set (spec 002, criterion 7). Each returns a list of findings."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from harness import paths, wasm

PLAIN_EXPORTS = {
    "memory",
    "_initialize",
    "wizer.initialize",
    "run",
    "host_alloc",
    "turn",
    "shutdown",
}
SNAPSHOT_EXPORTS = {"memory", "run", "host_alloc", "turn", "shutdown"}
# The session exports' function types (spec 055, Decision 19).
EXPORT_TYPES = {"turn": "(i32, i32) -> (i32)", "shutdown": "() -> (i32)"}
SNAPSHOT_FORBIDDEN = {"_initialize", "wizer.initialize"}


def complete_errors(d: Path) -> list[str]:
    errors = [f"{name} is missing" for name in paths.ARTIFACT_FILES if not (d / name).is_file()]
    errors += [
        f"LICENSES/{c}.txt is missing"
        for c in paths.LICENCE_COMPONENTS
        if not (d / "LICENSES" / f"{c}.txt").is_file()
    ]
    return errors


def sums_errors(d: Path) -> list[str]:
    sums = d / "SHA256SUMS"
    if not sums.is_file():
        return ["SHA256SUMS is missing"]
    try:
        listed = paths.read_pin_list(sums)
    except ValueError as e:
        return [str(e)]
    present = set(_set_folder_files(d)) - {"SHA256SUMS"}
    errors = [f"{f} is not listed in SHA256SUMS" for f in sorted(present - set(listed))]
    errors += [f"SHA256SUMS lists {f}, which is absent" for f in sorted(set(listed) - present)]
    errors += [
        f"{f} does not match its SHA256SUMS line"
        for f in sorted(present & set(listed))
        if paths.sha256_file(d / f) != listed[f]
    ]
    return errors


def _set_folder_files(d: Path) -> list[str]:
    """The files in an artifact folder, but for litter (a path with a litter part): a desktop's
    files are no finding, any other unlisted file is (spec 090, Decision 4)."""
    rels = (p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    return sorted(rel for rel in rels if not paths.has_litter(rel))


def cwasm_errors(d: Path) -> list[str]:
    return [
        f"{p.relative_to(d).as_posix()} is a compiled module" for p in sorted(d.rglob("*.cwasm"))
    ]


def module_errors(binary: Path) -> list[str]:
    try:
        mod = wasm.parse_file(binary)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    return [f"{binary.name}: {e}" for e in wasm.wall_errors(mod)]


def is_core_module_errors(binary: Path) -> list[str]:
    head = binary.read_bytes()[:8]
    if head[:4] != wasm.MAGIC:
        return [f"{binary.name}: not a wasm binary"]
    if head[4:8] != wasm.CORE_VERSION:
        return [f"{binary.name}: not a core module (version {head[4:8].hex()})"]
    return []


def export_errors(binary: Path, required: set[str], forbidden: set[str] = frozenset()) -> list[str]:
    try:
        exports = set(wasm.parse_file(binary).exports)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    errors = [f"{binary.name}: no export {name}" for name in sorted(required - exports)]
    errors += [f"{binary.name}: exports {name}" for name in sorted(forbidden & exports)]
    return errors


def export_type_errors(binary: Path, types: dict[str, str] = EXPORT_TYPES) -> list[str]:
    """Each named function export has the given type, as `FuncType` prints it (spec 055)."""
    try:
        mod = wasm.parse_file(binary)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    errors = []
    for name, want in sorted(types.items()):
        if mod.exports.get(name) != "func":
            errors.append(f"{binary.name}: no function export {name}")
            continue
        got = mod.func_type(mod.export_index[name])
        if str(got) != want:
            errors.append(f"{binary.name}: {name} has type {got}, not {want}")
    return errors


def start_section_errors(binary: Path) -> list[str]:
    """The binary has no start section, so instantiation runs no guest code: the runner and the
    judge meter fuel from after instantiation (spec 008, Decision 2)."""
    try:
        mod = wasm.parse_file(binary)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    if wasm.START_SECTION in mod.sections:
        return [f"{binary.name}: has a start section (guest code would run unmetered)"]
    return []


def exception_errors(binary: Path) -> list[str]:
    """The binary uses the exception-handling proposal's standard form (spec 005, Decision 9): it
    has a tag section, validates on an engine with exceptions on, and fails with them off.
    wasmtime has no legacy form, so legacy `try` code fails the first validation."""
    import wasmtime

    data = binary.read_bytes()
    try:
        mod = wasm.parse(data)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    errors = []
    if wasm.TAG_SECTION not in mod.sections:
        errors.append(f"{binary.name}: no tag section (no exception tag defined)")
    for on in (True, False):
        config = wasmtime.Config()
        config.wasm_exceptions = on
        try:
            wasmtime.Module.validate(wasmtime.Engine(config), data)
            valid = True
        except wasmtime.WasmtimeError:
            valid = False
        if on and not valid:
            errors.append(f"{binary.name}: does not validate with exceptions on")
        if not on and valid:
            errors.append(f"{binary.name}: validates with exceptions off (no exception handling)")
    return errors


def stdlib_zip_errors(z: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(z) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.filename.endswith(".py"):
                errors.append(f"{info.filename}: source, not bytecode")
            if info.compress_type != zipfile.ZIP_DEFLATED:
                errors.append(f"{info.filename}: stored, not deflated")
    return errors[:20]


SHARED_SUFFIXES = (".so", ".dylib", ".pyd", ".dll")


def shared_library_errors(z: Path) -> list[str]:
    with zipfile.ZipFile(z) as archive:
        return [n for n in archive.namelist() if n.endswith(SHARED_SUFFIXES)]


TYPED = "wasi_python/py.typed"


WHEEL_SET = "wasi_python/artifacts/"


def wheel_errors(wheel: Path, d: Path) -> list[str]:
    """The wheel carries every file of the set's folder (litter aside), byte for byte, and under
    `wasi_python/artifacts/` nothing the set's SHA256SUMS does not list, litter or not: the wheel
    is built from the folder (spec 090, Decision 4)."""
    errors = []
    try:
        listed = set(paths.read_pin_list(d / "SHA256SUMS")) | {"SHA256SUMS"}
    except (OSError, ValueError):
        listed = None  # sums_errors names it
    with zipfile.ZipFile(wheel) as w:
        names = set(w.namelist())
        if TYPED not in names:  # PEP 561: a type checker reads the package's hints (spec 049)
            errors.append(f"{wheel.name} lacks {TYPED}")
        for rel in _set_folder_files(d):
            member = WHEEL_SET + rel
            if member not in names:
                errors.append(f"{wheel.name} lacks {member}")
            elif paths.sha256_bytes(w.read(member)) != paths.sha256_file(d / rel):
                errors.append(f"{wheel.name}: {member} differs from the artifact set")
        if listed is not None:
            errors += [
                f"{wheel.name} carries {n}, which SHA256SUMS does not list"
                for n in sorted(names)
                if n.startswith(WHEEL_SET) and not n.endswith("/")
                and n[len(WHEEL_SET) :] not in listed
            ]  # fmt: skip
    return errors


# The two zip members that once recorded the build host (spec 012, Decision 5), and the words that
# would show a host in them. Case-sensitive: the sysconfig member holds keys such as HAVE_LINUX_*.
HOST_FACT_MEMBERS = (
    "_sysconfigdata__wasi_wasm32-wasi.pyc",
    "numpy/__config__.pyc",
    "contourpy/util/_build_config.pyc",  # spec 043, Decision 4
)
HOST_WORDS = (
    "darwin",
    "apple",
    "linux-gnu",
    "-macos",
    "-linux",
    "aarch64",
    "x86_64",
    "arm64",
    "python.exe",
    "/usr/bin",
)
# numpy's and contourpy's members have no HAVE_LINUX_* keys, so bare `linux` is a host word there.
NUMPY_HOST_WORDS = ("linux",)
BARE_LINUX_MEMBERS = ("numpy/", "contourpy/")


def host_fact_errors(z: Path, repo: str) -> list[str]:
    """The members' bytecode, scanned as ASCII: the judge's Python cannot unmarshal the guest's,
    and the strings a host leaves are plain text inside it."""
    errors = []
    with zipfile.ZipFile(z) as archive:
        names = set(archive.namelist())
        for member in HOST_FACT_MEMBERS:
            if member not in names:
                errors.append(f"{member}: not in the zip")
                continue
            data = archive.read(member)
            bare = NUMPY_HOST_WORDS if member.startswith(BARE_LINUX_MEMBERS) else ()
            words = HOST_WORDS + bare + (repo,)
            errors += [f"{member}: holds {w!r}" for w in words if w.encode() in data]
    return errors


# The builder path of a per-host wasi-sdk tarball's own wasm runtime (spec 012, Decision 2): the
# macOS tarball's libc++abi carries it in two assert messages. The host-neutral runtime the build
# links carries its own builder's path, /src/src/llvm-project, the same bytes on every host.
SDK_HOST_BUILDER_PATHS = ("/Users/runner/work/wasi-sdk",)


def sdk_builder_path_errors(binary: Path) -> list[str]:
    data = binary.read_bytes()
    return [f"{binary.name}: holds {p}" for p in SDK_HOST_BUILDER_PATHS if p.encode() in data]


def build_folders(repo: Path, home: Path) -> list[str]:
    """The folders a binary must not name (spec 046, Decision 10): the checkout, and the build
    user's home folder when it is deep enough to be distinctive (`/Users/<name>`, `/home/<name>`;
    a container's `/root` is two bytes from common strings, and the checkout check covers it)."""
    folders = [str(repo)]
    if len(home.parts) >= 3:
        folders.append(str(home))
    return folders


def build_path_errors(binary: Path, folders: list[str]) -> list[str]:
    """Each folder whose path the binary holds, with how many times: the binary-side twin of
    `host_fact_errors`. A compiled-in `-D` path (libxml2's default catalog, built from configure's
    `--prefix`) or an `assert`'s `__FILE__` names the builder's disk and ties the bytes to it."""
    data = binary.read_bytes()
    return [
        f"{binary.name}: holds {f!r} {data.count(f.encode())} times"
        for f in folders
        if f.encode() in data
    ]


# tqdm is MPL-2.0 AND MIT and ships as bytecode, MPL-2.0's Executable Form (spec 039, Decision 8):
# the set carries its source, the pinned wheel unchanged, and its notice holds the full MPL text.
# The rule reads the artifact set alone (MANIFEST's pin lines, the carried wheel, the zip), so it
# runs wherever the set is, the release's judge shards included, which have no downloads/.
MPL_TEXT = "spdx-31ba1a50-MPL-2.0.txt"
SYMPY_NESTED = "sympy/parsing/latex/LICENSE.txt"
NOTICE_PART = re.compile(r"^==== (.*) ====\n", re.M)


def notice_parts(body: bytes) -> list[tuple[str, bytes]]:
    """A LICENSES file's parts as step 90 writes them (`notice`): each part's header label and
    its bytes, without the blank line that ends the part."""
    text = body.decode("utf-8", errors="surrogateescape")
    heads = list(NOTICE_PART.finditer(text))
    parts = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        data = text[h.end() : end]
        parts.append((h[1], data[:-1].encode("utf-8", errors="surrogateescape")))
    return parts


def tier_a_notice_errors(d: Path) -> list[str]:
    """LICENSES/tqdm.txt holds the carried wheel's LICENCE, a part that is the pinned MPL-2.0 text
    byte for byte (its SHA-256 is MANIFEST's pin line) and a `tqdm source` part naming the carried
    source and its SHA-256; the carried source is the pinned wheel MANIFEST names;
    LICENSES/sympy.txt holds the MIT notice nested in sympy's package, as the zip carries it (spec
    039, Decision 8)."""
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    tqdm = m.packages.get("tqdm")
    if tqdm is None or "sympy" not in m.packages:
        return ["MANIFEST names no tqdm or no sympy"]
    wheel, source = f"tqdm-{tqdm}-py3-none-any.whl", f"tqdm-{tqdm}-source.whl"
    errors = [f"MANIFEST has no pin line for {n}" for n in (wheel, MPL_TEXT) if n not in m.pins]
    notice, carried = d / "LICENSES" / "tqdm.txt", d / "LICENSES" / source
    if not notice.is_file():
        errors.append("LICENSES/tqdm.txt is missing")
    if errors:
        return errors
    body = notice.read_bytes()
    if not carried.is_file():
        errors.append(f"LICENSES/{source} is missing")
    elif paths.sha256_file(carried) != m.pins[wheel]:
        errors.append(f"LICENSES/{source} is not the pinned {wheel} that MANIFEST names")
    else:
        with zipfile.ZipFile(carried) as z:
            names = [n for n in z.namelist() if n.endswith(".dist-info/licenses/LICENCE")]
            licence = z.read(names[0]) if names else None
        if licence is None or licence not in body:
            errors.append(f"LICENSES/tqdm.txt does not hold {wheel}'s LICENCE")
    parts = notice_parts(body)
    mpl = [data for label, data in parts if f"({MPL_TEXT})" in label]
    if not mpl or paths.sha256_bytes(mpl[0]) != m.pins[MPL_TEXT]:
        errors.append(f"LICENSES/tqdm.txt does not hold the MPL-2.0 text of {MPL_TEXT}")
    named = b"".join(data for label, data in parts if label == "tqdm source")
    for want in (f"LICENSES/{source}", m.pins[wheel]):
        if want.encode() not in named:
            errors.append(f"LICENSES/tqdm.txt's tqdm source part does not name {want}")
    with zipfile.ZipFile(d / "python-stdlib.zip") as z:
        nested = z.read(SYMPY_NESTED) if SYMPY_NESTED in z.NameToInfo else None
    sympy_notice = d / "LICENSES" / "sympy.txt"
    if nested is None:
        errors.append(f"the zip has no {SYMPY_NESTED}")
    elif not sympy_notice.is_file() or nested not in sympy_notice.read_bytes():
        errors.append(f"LICENSES/sympy.txt does not hold {SYMPY_NESTED} as the zip carries it")
    return errors


# scikit-learn's notice (spec 044, Decision 11): its licence and each bundled component's notice,
# matched against the pinned sdist's bytes, read from the tarball itself, and the pinned licence
# texts of the projects whose adapted code carries none. The judge keeps its own list, so a part
# step 90 drops or a range it moves is named here. (path in the sdist, first line, last line), or
# the whole file when no range is given.
SKLEARN_PARTS = (
    ("COPYING", None, None),
    ("sklearn/svm/src/liblinear/COPYRIGHT", None, None),
    ("sklearn/externals/array_api_compat/LICENSE", None, None),
    ("sklearn/externals/array_api_extra/LICENSE", None, None),
    ("sklearn/svm/src/libsvm/svm.cpp", 1, 32),
    ("sklearn/externals/_arff.py", 1, 25),
    ("sklearn/externals/_packaging/version.py", 4, 26),
    ("sklearn/externals/_packaging/_structures.py", 4, 26),
    ("sklearn/utils/src/MurmurHash3.cpp", 2, 3),
    ("sklearn/utils/_pprint.py", 7, 67),
    ("sklearn/utils/_testing.py", 575, 577),
    ("sklearn/cluster/_hdbscan/_tree.pxd", 1, 28),
    ("sklearn/model_selection/_split.py", 1001, 1015),
)
SKLEARN_PINNED_TEXTS = (
    "numpydoc-894c8c47-LICENSE.txt",
    "django-1dae4ac1-LICENSE",
    "pytest-0d90a31d-LICENSE",
)
# The plain Apache-2.0 text, for _split.py's kernel: wasi-libc's pinned copy, at the line's commit.
APACHE_TEXT = re.compile(r"wasi-libc-[0-9a-f]{8}-LICENSE-APACHE")
# The datasets' attribution part: each UCI source, the licence and its link.
SKLEARN_DATA_WORDS = (
    "https://archive.ics.uci.edu/dataset/80",
    "https://archive.ics.uci.edu/dataset/17",
    "https://archive.ics.uci.edu/dataset/109",
    "CC BY 4.0",
    "https://creativecommons.org/licenses/by/4.0/",
    "Fisher",
    "Unchanged from scikit-learn 1.9.1's copy.",
)


def sklearn_notice_errors(d: Path, tarball: Path, downloads: Path) -> list[str]:
    """Each part SKLEARN_PARTS names, as the pinned sdist holds it, and each pinned text, as its
    pin holds it, is in LICENSES/scikit-learn.txt; the datasets' part names sources and terms."""
    import tarfile

    m = paths.parse_manifest((d / "MANIFEST").read_text())
    notice = d / "LICENSES" / "scikit-learn.txt"
    if not notice.is_file():
        return ["LICENSES/scikit-learn.txt is missing"]
    body = notice.read_bytes()
    errors = []
    if paths.sha256_file(tarball) != m.pins.get(tarball.name):
        errors.append(f"{tarball.name} is not the tarball MANIFEST pins")
    top = tarball.name.removesuffix(".tar.gz")
    with tarfile.open(tarball) as t:
        for rel, first, last in SKLEARN_PARTS:
            f = t.extractfile(f"{top}/{rel}")
            data = f.read() if f is not None else b""
            if first is not None:
                lines = data.decode("utf-8").splitlines()[first - 1 : last]
                data = ("\n".join(lines) + "\n").encode()
            where = rel if first is None else f"{rel}, lines {first}-{last}"
            if not data.strip() or data not in body:
                errors.append(f"LICENSES/scikit-learn.txt does not hold {where}")
    apache = sorted(n for n in m.pins if APACHE_TEXT.fullmatch(n))
    if len(apache) != 1:
        errors.append(f"MANIFEST pins {len(apache)} wasi-libc Apache-2.0 texts, not 1")
    for name in (*SKLEARN_PINNED_TEXTS, *apache[:1]):
        path = downloads / name
        if not path.is_file() or paths.sha256_file(path) != m.pins.get(name):
            errors.append(f"downloads/{name} is missing or not the file MANIFEST pins")
        elif path.read_bytes() not in body:
            errors.append(f"LICENSES/scikit-learn.txt does not hold {name}")
    data = b"".join(b for label, b in notice_parts(body) if "bundled datasets" in label)
    errors += [
        f"LICENSES/scikit-learn.txt's datasets part does not say {w!r}"
        for w in SKLEARN_DATA_WORDS
        if w.encode() not in data
    ]
    return errors
