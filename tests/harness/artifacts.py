"""The v1.1 rules as functions over an artifact directory, so a self-test can run each one on a
good and a bad synthetic set. Each returns a list of findings."""

from __future__ import annotations

import re
import tarfile
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
# The session exports' function types.
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
    files are no finding, any other unlisted file is."""
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
    """Each named function export has the given type, as `FuncType` prints it."""
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
    judge meter fuel from after instantiation."""
    try:
        mod = wasm.parse_file(binary)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    if wasm.START_SECTION in mod.sections:
        return [f"{binary.name}: has a start section (guest code would run unmetered)"]
    return []


def exception_errors(binary: Path) -> list[str]:
    """The binary uses the exception-handling proposal's standard form: it
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
    is built from the folder."""
    errors = []
    try:
        listed = set(paths.read_pin_list(d / "SHA256SUMS")) | {"SHA256SUMS"}
    except (OSError, ValueError):
        listed = None  # sums_errors names it
    with zipfile.ZipFile(wheel) as w:
        names = set(w.namelist())
        if TYPED not in names:  # PEP 561: a type checker reads the package's hints
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


# The two zip members that once recorded the build host, and the words that
# would show a host in them. Case-sensitive: the sysconfig member holds keys such as HAVE_LINUX_*.
HOST_FACT_MEMBERS = (
    "_sysconfigdata__wasi_wasm32-wasi.pyc",
    "numpy/__config__.pyc",
    "contourpy/util/_build_config.pyc",  # made host-neutral at build time
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


# The builder path of a per-host wasi-sdk tarball's own wasm runtime: the
# macOS tarball's libc++abi carries it in two assert messages. The host-neutral runtime the build
# links carries its own builder's path, /src/src/llvm-project, the same bytes on every host.
SDK_HOST_BUILDER_PATHS = ("/Users/runner/work/wasi-sdk",)


def sdk_builder_path_errors(binary: Path) -> list[str]:
    data = binary.read_bytes()
    return [f"{binary.name}: holds {p}" for p in SDK_HOST_BUILDER_PATHS if p.encode() in data]


def build_folders(repo: Path, home: Path) -> list[str]:
    """The folders a binary must not name: the checkout, and the build
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


# tqdm is MPL-2.0 AND MIT and ships as bytecode, MPL-2.0's Executable Form:
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
    LICENSES/sympy.txt holds the MIT notice nested in sympy's package, as the zip carries it."""
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


# scikit-learn's notice: its licence and each bundled component's notice,
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


# seaborn and reportlab. reportlab's fonts are left out of the zip (their licences are
# not approved, and reportlab cannot read them from a zip; Decision 4), and so is its barcode
# folder until a later change ships it with Tyler C. Sarna's acknowledgement (Decision 4a). The
# font formats of Decision 4: matplotlib's AFM files travel inside its one inner archive, so no
# outer member name ends so.
REPORTLAB_LEFT_OUT = ("reportlab/fonts/", "reportlab/graphics/barcode/")
FONT_SUFFIXES = (".pfb", ".afm", ".sfd")
# seaborn's notice (Decision 7): its sdist's licence and the five licences of the code it vendors,
# each a part headed `seaborn <path in the sdist>`.
SEABORN_NOTICES = (
    "LICENSE.md",
    "licences/APPDIRS_LICENSE",
    "licences/HUSL_LICENSE",
    "licences/NUMPYDOC_LICENSE",
    "licences/PACKAGING_LICENSE",
    "licences/SCIPY_LICENSE",
)
# reportlab's notice (Decisions 4a and 7): the wheel's LICENSE, then three files' leading comment
# blocks, each a part headed `<wheel>: <path>, its leading comment (...)`, and the MIT text the QR
# encoder's names, a part headed `... (<the pinned wasi-libc LICENSE-MIT>)`.
REPORTLAB_NOTICES = (
    "reportlab/graphics/barcode/__init__.py",
    "reportlab/pdfbase/_glyphlist.py",
    "reportlab/graphics/barcode/qrencoder.py",
)
SARNA_ACKNOWLEDGEMENT = b"This product includes software developed by Tyler C. Sarna."
MIT_PIN = re.compile(r"wasi-libc-[0-9a-f]+-LICENSE-MIT")


def reportlab_left_out_errors(names: list[str]) -> list[str]:
    """No zip member under reportlab's fonts or barcode folder, and no font file of Decision 4's
    formats anywhere in the zip's names."""
    errors = []
    for prefix in REPORTLAB_LEFT_OUT:
        held = sorted(n for n in names if n.startswith(prefix))
        if held:
            errors.append(f"the zip holds {len(held)} members under {prefix}, the first {held[0]}")
    fonts = sorted(n for n in names if n.lower().endswith(FONT_SUFFIXES))
    if fonts:
        errors.append(f"the zip holds {len(fonts)} font files, the first {fonts[0]}")
    return errors


def leading_comment(data: bytes) -> bytes:
    """A Python file's leading comment block, byte for byte: its first lines that begin with `#`,
    up to the first that does not."""
    lines = []
    for line in data.splitlines(keepends=True):
        if not line.startswith(b"#"):
            break
        lines.append(line)
    return b"".join(lines)


def _as_part(data: bytes) -> bytes:
    """A file's bytes as notice_parts gives them back: step 90 ends a part with a newline."""
    return data if data.endswith(b"\n") else data + b"\n"


def _parts(notice: Path) -> dict[str, bytes] | None:
    return dict(notice_parts(notice.read_bytes())) if notice.is_file() else None


def seaborn_notice_errors(d: Path, sdist: Path | None) -> list[str]:
    """LICENSES/seaborn.txt holds a part headed by each of SEABORN_NOTICES; given the pinned sdist
    (hash-checked by the caller), each part is that file of the sdist, byte for byte. Without it,
    the headings only, as licence_errors checks presence only."""
    parts = _parts(d / "LICENSES" / "seaborn.txt")
    if parts is None:
        return ["LICENSES/seaborn.txt is missing"]
    files: dict[str, bytes] = {}
    if sdist is not None:
        top = sdist.name.removesuffix(".tar.gz")
        with tarfile.open(sdist) as t:
            for n in SEABORN_NOTICES:
                f = t.extractfile(f"{top}/{n}")
                files[n] = f.read() if f else b""
    errors = []
    for n in SEABORN_NOTICES:
        label = f"seaborn {n}"
        if label not in parts:
            errors.append(f"LICENSES/seaborn.txt has no part headed {label!r}")
        elif sdist is not None and parts[label] != _as_part(files[n]):
            errors.append(f"LICENSES/seaborn.txt: {label!r} is not {sdist.name}'s {n}")
    return errors


def reportlab_notice_errors(d: Path, wheel: Path | None) -> list[str]:
    """LICENSES/reportlab.txt holds the wheel's LICENSE and a part for each of REPORTLAB_NOTICES,
    Sarna's with his acknowledgement sentence, and the MIT text the QR encoder's notice names,
    whose SHA-256 is MANIFEST's pin line for it. Given the pinned wheel (hash-checked by the
    caller), the LICENSE part is the wheel's and each comment part that file's leading comment
    block, byte for byte; without it, the headings."""
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    version = m.packages.get("reportlab")
    if version is None:
        return ["MANIFEST names no reportlab"]
    parts = _parts(d / "LICENSES" / "reportlab.txt")
    if parts is None:
        return ["LICENSES/reportlab.txt is missing"]
    name = f"reportlab-{version}-py3-none-any.whl"
    licence = f"{name}: reportlab-{version}.dist-info/licenses/LICENSE"
    errors = []
    members: dict[str, bytes] = {}
    if wheel is not None:
        with zipfile.ZipFile(wheel) as z:
            for n in (licence.split(": ", 1)[1], *REPORTLAB_NOTICES):
                members[n] = z.read(n)
    if licence not in parts:
        errors.append(f"LICENSES/reportlab.txt has no part headed {licence!r}")
    elif wheel is not None and parts[licence] != _as_part(members[licence.split(": ", 1)[1]]):
        errors.append(f"LICENSES/reportlab.txt: {licence!r} is not the wheel's")
    for n in REPORTLAB_NOTICES:
        head = f"{name}: {n}, its leading comment"
        found = [label for label in parts if label.startswith(head)]
        if not found:
            errors.append(f"LICENSES/reportlab.txt has no part headed {head!r}")
            continue
        data = parts[found[0]]
        if wheel is not None and data != _as_part(leading_comment(members[n])):
            errors.append(f"LICENSES/reportlab.txt: {n}'s part is not its leading comment")
        if n.endswith("barcode/__init__.py") and SARNA_ACKNOWLEDGEMENT not in data:
            errors.append(f"LICENSES/reportlab.txt: {n}'s part lacks Sarna's acknowledgement")
    mit = sorted(f for f in m.pins if MIT_PIN.fullmatch(f))
    if len(mit) != 1:
        return errors + [f"MANIFEST has {len(mit)} pin lines for wasi-libc's LICENSE-MIT, not one"]
    text = [data for label, data in parts.items() if label.endswith(f"({mit[0]})")]
    if not text or paths.sha256_bytes(text[0]) != m.pins[mit[0]]:
        errors.append(f"LICENSES/reportlab.txt does not hold the MIT text of {mit[0]}")
# statsmodels' notice (spec 045, Decision 13): its licence, COPYRIGHTS.txt (the numpy, scipy,
# pandas, matplotlib, scikit-learn and qsturng-py code it carries), the two folders with licences of
# their own, and each bundled component the build's notice sweep found, matched against the pinned
# sdist's bytes as scikit-learn's are; then the pinned licence texts of the two projects whose
# adapted code carries none; then the datasets part. (path in the sdist, first line, last line), or
# the whole file when no range is given.
STATSMODELS_PARTS = (
    ("LICENSE.txt", None, None),
    ("COPYRIGHTS.txt", None, None),
    ("statsmodels/multivariate/factor_rotation/LICENSE.txt", None, None),
    ("statsmodels/multivariate/factor_rotation/COPYRIGHTS.txt", None, None),
    ("statsmodels/stats/libqsturng/LICENSE.txt", None, None),
    ("statsmodels/tools/parallel.py", 1, 12),
    ("statsmodels/tools/docstring.py", 1, 1),
    ("statsmodels/stats/libqsturng/qsturng_.py", 1926, 1961),
    ("statsmodels/tsa/stl/_stl.pyx", 3, 13),
    ("statsmodels/graphics/boxplots.py", 3, 4),
    ("statsmodels/regression/quantile_regression.py", 1, 16),
)
STATSMODELS_PINNED_TEXTS = ("mne-python-2c4a3b03-LICENSE.txt", "numpydoc-894c8c47-LICENSE.txt")
# The sixteen datasets that ship, each named in the datasets part with its stated terms, and the
# thirteen whose files stay out (Decision 9).
STATSMODELS_DATASETS = (
    "anes96", "co2", "danish_data", "elec_equip", "elnino", "engel", "grunfeld", "longley",
    "macrodata", "modechoice", "nile", "randhie", "stackloss", "statecrime", "strikes", "sunspots",
)  # fmt: skip
STATSMODELS_LEFT_OUT = (
    "cancer", "ccard", "china_smoking", "committee", "copper", "cpunish", "fair", "fertility",
    "heart", "interest_inflation", "scotland", "spector", "star98",
)  # fmt: skip


def statsmodels_notice_errors(d: Path, tarball: Path, downloads: Path) -> list[str]:
    """Each part STATSMODELS_PARTS names, as the pinned sdist holds it, and each pinned text, as its
    pin holds it, is in LICENSES/statsmodels.txt; the datasets part names every dataset that ships
    with the public-domain statement its module gives, and every one left out."""
    import tarfile

    m = paths.parse_manifest((d / "MANIFEST").read_text())
    notice = d / "LICENSES" / "statsmodels.txt"
    if not notice.is_file():
        return ["LICENSES/statsmodels.txt is missing"]
    body = notice.read_bytes()
    errors = []
    if paths.sha256_file(tarball) != m.pins.get(tarball.name):
        errors.append(f"{tarball.name} is not the tarball MANIFEST pins")
    top = tarball.name.removesuffix(".tar.gz")
    with tarfile.open(tarball) as t:
        for rel, first, last in STATSMODELS_PARTS:
            f = t.extractfile(f"{top}/{rel}")
            data = f.read() if f is not None else b""
            if first is not None:
                lines = data.decode("utf-8").splitlines()[first - 1 : last]
                data = ("\n".join(lines) + "\n").encode()
            where = rel if first is None else f"{rel}, lines {first}-{last}"
            if not data.strip() or data not in body:
                errors.append(f"LICENSES/statsmodels.txt does not hold {where}")
    for name in STATSMODELS_PINNED_TEXTS:
        path = downloads / name
        if not path.is_file() or paths.sha256_file(path) != m.pins.get(name):
            errors.append(f"downloads/{name} is missing or not the file MANIFEST pins")
        elif path.read_bytes() not in body:
            errors.append(f"LICENSES/statsmodels.txt does not hold {name}")
    data = b"".join(b for label, b in notice_parts(body) if "bundled datasets" in label)
    text = data.decode("utf-8", errors="replace")
    for name in STATSMODELS_DATASETS:
        if not re.search(rf"^- {name}: .*public domain", text, re.M | re.I):
            errors.append(f"LICENSES/statsmodels.txt's datasets part does not ship {name}")
    for name in STATSMODELS_LEFT_OUT:
        if not re.search(rf"^- {name}\b", text, re.M) or f"- {name}: " in text:
            errors.append(f"LICENSES/statsmodels.txt's datasets part does not leave {name} out")
    return errors
