"""Repository scanners behind the `rules` and `v1.5` checks. Each returns a list of findings,
one line each; an empty list means the rule holds."""

from __future__ import annotations

import ast
import bisect
import fnmatch
import io
import json
import posixpath
import re
import shlex
import subprocess
import tempfile
import tokenize
import tomllib
import warnings
from collections.abc import Callable, Iterable
from pathlib import Path

from harness import history, news, paths

SKIP_PARTS = {"__pycache__", ".venv", ".pytest_cache", ".ruff_cache"}


def files_under(root: Path, *subdirs: str) -> list[Path]:
    out = []
    for sub in subdirs:
        base = root / sub
        if base.is_file():
            out.append(base)
        elif base.is_dir():
            out += [
                p for p in sorted(base.rglob("*")) if p.is_file() and not SKIP_PARTS & set(p.parts)
            ]
    return out


def _text(p: Path) -> str | None:
    try:
        return p.read_text()
    except (UnicodeDecodeError, OSError):
        return None


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------------------------
# No embedder names in code


def read_names(path: Path) -> list[str]:
    return [
        line.strip().lower()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def embedder_hits(root: Path, subdirs: Iterable[str], names: list[str]) -> list[str]:
    hits = []
    for p in files_under(root, *subdirs):
        r = rel(p, root)
        for name in names:
            if name in r.lower():
                hits.append(f"{r}: in the file's path")
        text = _text(p)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if p.suffix == ".patch" and not _our_patch_line(line):
                continue  # a patch's context and removed lines are upstream's text
            low = line.lower()
            if any(name in low for name in names):
                hits.append(f"{r}:{n}")
    return hits


def _our_patch_line(line: str) -> bool:
    """A patch line this project wrote: an added line, or one naming a file."""
    if line.startswith(("+++", "---")):
        return True
    return line.startswith(("+", "diff --git "))


# ---------------------------------------------------------------------------------------------
# No test reads a clock

CLOCK = re.compile(
    r"\btime\.(time|perf_counter|monotonic|process_time|thread_time)(_ns)?\b"
    r"|\bdatetime\.(now|utcnow|today)\b|\bdate\.today\b|\btimeit\b"
    r"|\bfrom\s+time\s+import\b"
)


def clock_hits(files: Iterable[Path], root: Path) -> list[str]:
    hits = []
    for p in files:
        if p.suffix != ".py":
            continue
        for n, line in enumerate((_text(p) or "").splitlines(), 1):
            if CLOCK.search(line.split("#", 1)[0]):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()}")
    return hits


# ---------------------------------------------------------------------------------------------
# Build scripts


def is_shell(p: Path) -> bool:
    if p.suffix == ".sh":
        return True
    first = (_text(p) or "").split("\n", 1)[0]
    return first.startswith("#!") and ("sh" in first.split("/")[-1])


def _code_lines(p: Path) -> list[tuple[int, str]]:
    """Lines of a shell script with full-line comments dropped."""
    return [
        (n, line)
        for n, line in enumerate((_text(p) or "").splitlines(), 1)
        if not line.lstrip().startswith("#")
    ]


FETCH = re.compile(r"\b(curl|wget|git\s+clone|uv\s+pip|uv\s+add|pip3?\s+install)\b")


def offline_install(line: str) -> bool:
    """An install that cannot fetch: from local, hash-checked files only.
    It exempts a line only when `uv pip` is the line's one fetch word."""
    words = [m.group(1) for m in FETCH.finditer(line)]
    return (
        len(words) == 1
        and re.fullmatch(r"uv\s+pip", words[0]) is not None
        and re.search(r"\buv\s+pip\s+install\b", line) is not None
        and all(flag in line.split() for flag in ("--offline", "--no-index", "--require-hashes"))
        and "://" not in line
    )


def every_file(base: Path) -> list[Path]:
    """Every file under a directory, at any depth, bytecode caches left out."""
    return [p for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def fetch_hits(scripts: list[Path], allowed: str, root: Path) -> list[str]:
    hits = []
    for p in scripts:
        if p.name == allowed:
            continue
        lines = _code_lines(p) if is_shell(p) else enumerate((_text(p) or "").splitlines(), 1)
        for n, line in lines:
            if FETCH.search(line) and not offline_install(line):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


BARE_PY = re.compile(r"(?:^|[;&|(`]|\$\(|\bthen\b|\bdo\b)\s*(python3?|pip3?)(?=\s|$)")


def bare_python_hits(scripts: list[Path], root: Path) -> list[str]:
    hits = []
    for p in scripts:
        if not is_shell(p):
            continue
        for n, line in _code_lines(p):
            if BARE_PY.search(line):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


URL = re.compile(r"https?://[^\s\"')]+")
GET = re.compile(r"^\s*(?:get|research|tests)\s+(https?://\S+)(?:\s+(\S+))?", re.M)


# `rm` as a word anywhere (after `if`, `!`, `xargs`, `command`, an assignment...), or `\rm`,
# `/bin/rm`, `/usr/bin/rm`; a string or a trailing comment can match too, which fails closed.
RM = re.compile(r"(?<![\w./-])(?:\\|/(?:usr/)?bin/)?rm((?:\s+-[-A-Za-z]+)+)")
REMOVE_SH = "scripts/steps/remove.sh"


def _recursive_force(flags: str) -> bool:
    short = "".join(t[1:] for t in flags.split() if not t.startswith("--"))
    long = {t for t in flags.split() if t.startswith("--")}
    recursive = bool(set(short) & {"r", "R"}) or "--recursive" in long
    return recursive and ("f" in short or "--force" in long)


def bare_rm_hits(scripts: list[Path], root: Path) -> list[str]:
    """A recursive, forced `rm` in a build script outside remove.sh, in any spelling (`-rf`,
    `-fr`, `-Rf`, `-r -f`, `--recursive --force`): Finder can make it fail, so every removal goes
    through `remove`, which retries."""
    hits = []
    for p in scripts:
        if not is_shell(p) or rel(p, root) == REMOVE_SH:
            continue
        joined: list[tuple[int, str]] = []  # a line ending in `\` continues on the next
        for n, line in _code_lines(p):
            if joined and joined[-1][1].endswith("\\"):
                joined[-1] = (joined[-1][0], joined[-1][1][:-1] + " " + line)
            else:
                joined.append((n, line.rstrip()))
        for n, line in joined:
            if any(_recursive_force(m.group(1)) for m in RM.finditer(line)):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


def url_errors(download_script: Path, pinned: Iterable[str]) -> list[str]:
    """Every pin is named on a `get <url> <name>` line (or is a literal URL's basename)."""
    text = _text(download_script) or ""
    basenames = {u.rstrip("/").rsplit("/", 1)[-1] for u in URL.findall(text)}
    basenames |= {name for _, name in GET.findall(text) if name}
    return [
        f"{name}: no literal URL ends in it in {download_script.name}"
        for name in sorted(pinned)
        if name not in basenames
    ]


def download_script_errors(download_script: Path) -> list[str]:
    text = "\n".join(line for _, line in _code_lines(download_script))
    errors = []
    if not re.search(r"(shasum\s+-a\s*256|sha256sum)\b[^\n]*\s-c\b[^\n]*SHA256SUMS", text):
        errors.append("it never checks the downloads against SHA256SUMS (`shasum -a 256 -c`)")
    if re.search(r"(>{1,2}\s*\S*SHA256SUMS|\btee\b[^\n]*SHA256SUMS)", text):
        errors.append("it writes SHA256SUMS instead of only reading it")
    return errors


PATH_TOKEN = re.compile(r"(?:\$HERE|\$\{HERE\}|@S12@|@ROOT@)/([A-Za-z0-9_.][\w./-]*)")
GENERATED_ROOTS = {"build", "downloads", ".venv-build"}


def recipe_path_errors(files: Iterable[Path], root: Path) -> list[str]:
    errors = []
    for p in files:
        for n, line in enumerate((_text(p) or "").splitlines(), 1):
            for token in PATH_TOKEN.findall(line):
                token = token.rstrip(".")
                if token.split("/")[0] in GENERATED_ROOTS:
                    continue
                if not (root / token).exists():
                    errors.append(f"{rel(p, root)}:{n}: names {token}, which does not exist")
    return errors


def toolchain_errors(pinned: Iterable[str]) -> list[str]:
    names = [n.lower() for n in pinned]
    errors = []
    for tool in ("wasi-sdk", "wasmtime"):
        mine = [n for n in names if n.startswith(tool + "-")]
        if not any("x86_64-linux" in n or "linux-x86_64" in n for n in mine):
            errors.append(f"{tool}: no Linux x86_64 pin")
        if not any("arm64-macos" in n or "aarch64-macos" in n for n in mine):
            errors.append(f"{tool}: no macOS arm64 pin")
    return errors


CPP_EH_FLAGS = ("'-fwasm-exceptions'", "'-wasm-use-legacy-eh=false'")
CPP_CROSS_FILES = (
    "recipes/wasi-numpy.cross",
    "recipes/wasi-pandas.cross",
    "recipes/wasi-plot-libs.cross",
    "recipes/wasi-matplotlib.cross",
    "recipes/wasi-scipy.cross",  # added for scipy
    "recipes/wasi-sklearn.cross",  # added for scikit-learn
)
# kiwisolver's C++ is compiled by step 55 itself: its flags variable, and the compile that uses it.
CPP_DIRECT = "scripts/steps/55_matplotlib.sh"
CPP_EH_AGAINST = ("'-fno-exceptions'", "'-wasm-use-legacy-eh=true'", "'-fno-wasm-exceptions'")
CPP_SETUP_CROSS = '--cross-file "$B/wasi-matplotlib.cross"'


def cpp_exception_errors(root: Path) -> list[str]:
    """Every C++ object is compiled, and the binary linked, for standard-form exceptions:
    a cross file without the flags compiles C++ whose `throw` is never caught. Every
    C++ build is judged: numpy's and pandas' cross files, HarfBuzz's (step 37),
    matplotlib's, kiwisolver's compile line in step 55, and contourpy's configure there, with
    matplotlib's cross file."""
    errors = []
    for cross in CPP_CROSS_FILES:
        lines = [t for t in (root / cross).read_text().splitlines() if t.startswith("cpp_args")]
        if len(lines) != 1:
            errors.append(f"{cross}: {len(lines)} cpp_args lines, not 1")
            continue
        errors += [f"{cross}: cpp_args lacks {f}" for f in CPP_EH_FLAGS if f not in lines[0]]
        errors += [f"{cross}: cpp_args has {f}" for f in CPP_EH_AGAINST if f in lines[0]]
    direct = (root / CPP_DIRECT).read_text().splitlines()
    flags = [t for t in direct if t.startswith("CXX_EH=")]
    if len(flags) != 1:
        errors.append(f"{CPP_DIRECT}: {len(flags)} CXX_EH= lines, not 1")
    else:
        errors += [
            f"{CPP_DIRECT}: CXX_EH lacks {f}" for f in CPP_EH_FLAGS if f[1:-1] not in flags[0]
        ]
        errors += [f"{CPP_DIRECT}: CXX_EH has {f}" for f in CPP_EH_AGAINST if f[1:-1] in flags[0]]
    compiles = [t for t in direct if t.lstrip().startswith("$CXX ")]
    if not compiles or not all("$CXX_EH" in t for t in compiles):
        errors.append(f"{CPP_DIRECT}: a $CXX compile without $CXX_EH")
    # contourpy's C++ is configured by step 55 with matplotlib's cross file:
    # every meson setup there names it, and one of them is contourpy's.
    setups = [t for t in direct if t.lstrip().startswith("meson setup ")]
    if not all(CPP_SETUP_CROSS in t for t in setups):
        errors.append(f"{CPP_DIRECT}: a meson setup without {CPP_SETUP_CROSS}")
    if not any('"$B/contourpy-build"' in t for t in setups):
        errors.append(f"{CPP_DIRECT}: no meson setup of contourpy-build")
    link = (root / "scripts/steps/60_link.sh").read_text().splitlines()
    if not any("-lunwind" in t and t.lstrip().startswith("echo") for t in link):
        errors.append("scripts/steps/60_link.sh: Setup.local does not link -lunwind")
    flag = 'LDFLAGS_NODIST="-fwasm-exceptions"'
    for target in ("make -j8 all", "make -n python.wasm"):
        calls = [t for t in link if t.lstrip().startswith(target)]
        if not calls or not all(flag in t for t in calls):
            errors.append(f"scripts/steps/60_link.sh: `{target}` without {flag}")
    return errors


# The release workflow's wheel steps: the checkout's LICENSE becomes the project's licence followed
# by every component licence in the set, before each wheel is built, so the wheel's
# .dist-info/licenses/LICENSE carries them all. FreeType's licence (§2) asks a binary
# distribution's documentation for its credit; its text, in the set, carries the sentence.
LICENCE_APPEND = "uv run --no-project python -I release/licences.py append build/artifacts"
LICENCE_CHECK = "uv run --no-project python -I release/licences.py check"
WHEEL_BUILD = "uv build --wheel "


def licence_step_errors(workflow: str) -> list[str]:
    """Every `uv build --wheel` line in the release workflow comes right after the licence append,
    and at least one wheel build is followed by the licence check."""
    lines = [line.strip() for line in workflow.splitlines()]
    builds = [i for i, line in enumerate(lines) if line.startswith(WHEEL_BUILD)]
    if not builds:
        return ["release.yml builds no wheel"]
    errors = [
        f"release.yml line {i + 1}: a wheel built without the licence append before it"
        for i in builds
        if i == 0 or lines[i - 1] != LICENCE_APPEND
    ]
    if not any(i + 1 < len(lines) and lines[i + 1].startswith(LICENCE_CHECK) for i in builds):
        errors.append("release.yml checks no built wheel's LICENSE")
    return errors


def pure_python_errors(pinned: Iterable[str]) -> list[str]:
    names = [paths.norm(n) for n in pinned]
    return [
        f"{pkg}: not pinned"
        for pkg in ("python-dateutil", "tzdata", "six")
        if not any(n.startswith(pkg + "-") for n in names)
    ]


# ---------------------------------------------------------------------------------------------
# Context documents

SPEC_HEADER = ("Status", "Owner", "Kind", "Depends on", "Research it stands on")
SPEC_SECTIONS = ("Decisions", "Intent", "Design", "Scope", "Acceptance criteria", "Landing notes")


def spec_shape_errors(path: Path) -> list[str]:
    text = path.read_text()
    errors = []
    for field in SPEC_HEADER:
        if not re.search(rf"^- \*\*{re.escape(field)}:\*\*", text, re.M):
            errors.append(f"{path.name}: no '{field}' header line")
    for section in SPEC_SECTIONS:
        if not re.search(rf"^## {re.escape(section)}\s*$", text, re.M):
            errors.append(f"{path.name}: no '## {section}' section")
    return errors


def strip_code(text: str) -> str:
    text = re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


OPEN = re.compile(r"\bTBD\b|\bTODO\b|open question", re.I)


def open_question_hits(path: Path) -> list[str]:
    hits = []
    for line in strip_code(path.read_text()).splitlines():
        if line.startswith("#") and "question" in line.lower():
            hits.append(f"{path.name}: a questions heading: {line.strip()}")
        elif OPEN.search(line):
            hits.append(f"{path.name}: {line.strip()[:100]}")
    return hits


def status_line(text: str) -> str:
    m = re.search(r"^- \*\*Status:\*\*(.*)$", text, re.M)
    return m[1].strip().lower() if m else ""


def landed_review_errors(path: Path, reviews: Path) -> list[str]:
    text = path.read_text()
    if not status_line(text).startswith("landed"):
        return []
    notes = text.split("## Landing notes", 1)[-1]
    cited = re.findall(r"reviews/([\w.-]+\.md)", notes)
    if not cited:
        return [f"{path.name}: landed, but its landing notes cite no review"]
    return [
        f"{path.name}: cites reviews/{c}, which does not exist"
        for c in cited
        if not (reviews / c).is_file()
    ]


STRUCTURAL_ROWS = (
    ("R1", "Contract"),
    ("R2", "Safety"),
    ("R3", "Layering"),
    ("R4", "Process state"),
    ("R5", "Portability"),
    ("R6", "Testability"),
    ("R7", "Evolvability"),
    ("R8", "Operability"),
)
RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")  # X.Y.Z with no aN, bN or rcN (release/version.py)


def structural_review_errors(version: str, reviews: Path) -> list[str]:
    """A released version has its structural review of src/ under reviews/, named
    `<version>-structural-review-YYYY-MM-DD.md`, and the review scores every row of the rubric
    (AGENTS.md, "Structure is reviewed"). A prerelease needs none from the judge: its string is
    what the tree carries all cycle."""
    if not RELEASE_VERSION.match(version):
        return []
    name = re.compile(rf"^{re.escape(version)}-structural-review-\d{{4}}-\d{{2}}-\d{{2}}\.md$")
    found = sorted(p for p in reviews.glob("*.md") if name.match(p.name))
    if not found:
        return [f"{version} is a release; reviews/ has no {version}-structural-review-<date>.md"]
    errors = []
    for p in found:
        text = p.read_text()
        for tag, row in STRUCTURAL_ROWS:
            if not re.search(rf"\b{tag}\b", text) or row.lower() not in text.lower():
                errors.append(f"{p.name}: does not score {tag} ({row})")
    return errors


def release_notes_review_errors(version: str, reviews: Path) -> list[str]:
    """A released version whose notes are written for the reader has a review of those notes by
    someone who wrote none of them, `<version>-release-notes-review-YYYY-MM-DD.md`, ending with
    its verdict. A prerelease needs none from the judge: its string is what the tree carries all
    cycle; nor does a version whose notes were published in the older shape."""
    if not RELEASE_VERSION.match(version) or not news.is_reader_version(version):
        return []
    name = re.compile(rf"^{re.escape(version)}-release-notes-review-\d{{4}}-\d{{2}}-\d{{2}}\.md$")
    found = sorted(p for p in reviews.glob("*.md") if name.match(p.name))
    if not found:
        return [f"{version} is a release; reviews/ has no {version}-release-notes-review-<date>.md"]
    return [
        f"{p.name}: has no ## Verdict section"
        for p in found
        if not re.search(r"^## Verdict\s*$", p.read_text(encoding="utf-8"), re.M)
    ]


KIND_LINE = re.compile(r"^- \*\*Kind:\*\*(.*?)(?=^- \*\*|^## )", re.M | re.S)
STRUCTURAL_TOKEN = "**structural**"


def structural_spec_review_errors(path: Path, reviews: Path) -> list[str]:
    """A specification whose Kind line carries the bold token **structural** cites, once its
    Status begins with built or landed, its own review before build, a file named
    `NNN-<slug>-spec-YYYY-MM-DD.md` among the reviews, and the file exists: the mirror of
    landed_review_errors for the review before build."""
    text = path.read_text()
    kind = KIND_LINE.search(text)
    if kind is None or STRUCTURAL_TOKEN not in kind[1]:
        return []
    status = status_line(text).replace("*", "")
    if not re.match(r"(built|landed)\b", status):
        return []
    number = path.name.split("-", 1)[0]
    cited = [
        c
        for c in re.findall(r"reviews/([\w.-]+\.md)", text)
        if c.startswith(f"{number}-") and "-spec-" in c
    ]
    if not cited:
        missing = f"reviews/{number}-<slug>-spec-<date>.md"
        return [f"{path.name}: structural and built, but cites no {missing}"]
    return [
        f"{path.name}: cites reviews/{c}, which does not exist"
        for c in cited
        if not (reviews / c).is_file()
    ]


def memo_label_errors(path: Path) -> list[str]:
    text = path.read_text()
    if "placeholder" in status_line(text):
        return []
    if re.search(r"\b(EXECUTED|READ|INFERRED)\b", text):
        return []
    return [f"{path.name}: no EXECUTED, READ or INFERRED label"]


def prior_art_errors(prior_art: Path) -> list[str]:
    index = (prior_art / "README.md").read_text()
    rows = {}
    for line in index.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.fullmatch(r"`([^`]+)`.*", cells[0]) if cells else None
        if m and len(cells) >= 3:
            rows[m[1]] = cells[2]
    errors = []
    for d in sorted(p for p in prior_art.iterdir() if p.is_dir()):
        if d.name not in rows or not rows[d.name]:
            errors.append(f"{d.name}: no row with a licence in context/prior_art/README.md")
        if not any(re.match(r"(licen[cs]e|copying)", f.name, re.I) for f in d.iterdir()):
            errors.append(f"{d.name}: no licence file in the clone")
    return errors


# ---------------------------------------------------------------------------------------------
# How a check reports its findings


LINE_REF = re.compile(r":\d+(?=[:\s]|$)")


def digest(findings: list[str]) -> str:
    """A short hash of the exact set of findings. A gap matches it, so a gap admits exactly
    the findings it was written for: one more, or one fewer, is a different failure. Line
    numbers are left out, so an edit that only moves a finding does not disturb its gap."""
    return paths.sha256_bytes("\n".join(sorted(LINE_REF.sub("", f) for f in findings)).encode())[
        :12
    ]


def report(findings: list[str], what: str = "findings") -> str:
    shown = "; ".join(findings[:5]) + (f"; +{len(findings) - 5} more" if len(findings) > 5 else "")
    return f"{what}: {len(findings)} finding(s), digest {digest(findings)}: {shown}"


# ---------------------------------------------------------------------------------------------
# The release workflow's provenance

ATTEST_PERMISSIONS = {"id-token: write", "attestations: write", "contents: read"}
ATTEST_USES = re.compile(r"uses:\s*actions/attest@[0-9a-f]{40}\b")
VERIFY_FLAGS = ("--repo", "--signer-workflow", "--source-ref", "--deny-self-hosted-runners")
TAG_ONLY = "github.event_name == 'push' && github.ref_type == 'tag'"
ID_TOKEN = re.compile(r"id-token:\s*write|write-all")


def without_comments(text: str) -> str:
    """The workflow with its comments removed, so a commented-out step or name counts for nothing:
    whole-line comments, and trailing ` # …` comments."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(re.sub(r"\s+#\s.*$", "", line))
    return "\n".join(out) + "\n"


def without_expressions(text: str) -> str:
    """The text with every `${{ … }}` expression removed: an expression's `||` picks a value and
    is no shell's way to carry on past a failure."""
    return re.sub(r"\$\{\{.*?\}\}", "", text)


def workflow_jobs(text: str) -> dict[str, list[str]]:
    """The workflow's jobs, each as its lines, read as text (the judge has no YAML library): a job
    starts at a two-space-indented `name:` line under `jobs:`."""
    jobs: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_jobs = False
    for line in text.splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        m = re.fullmatch(r"  ([A-Za-z0-9_-]+):\s*", line)
        if m:
            current = jobs.setdefault(m[1], [])
        elif line and not line.startswith(" "):
            in_jobs, current = False, None
        elif current is not None:
            current.append(line)
    return jobs


def _job_field(lines: list[str], key: str) -> str | None:
    for line in lines:
        m = re.fullmatch(rf"    {key}:\s*(.*)", line)
        if m:
            return m[1].strip()
    return None


def _job_permissions(lines: list[str]) -> set[str]:
    out, inside = set(), False
    for line in lines:
        if re.fullmatch(r"    permissions:\s*", line):
            inside = True
            continue
        if inside:
            if line.startswith("      ") and line.strip():
                out.add(" ".join(line.split()))
            else:
                break
    return out


def release_attestation_errors(text: str) -> list[str]:
    """Every rule of the release's provenance (each asset attested, then verified), as one line
    per breach, on the workflow without its comments; attest and publish also need gather."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    if "attest" not in jobs:
        return ["no attest job"]
    attest, publish = jobs["attest"], jobs.get("publish", [])
    errors = []
    if _job_field(attest, "if") != TAG_ONLY or _job_field(publish, "if") != TAG_ONLY:
        errors.append("attest's or publish's if: is not the pushed-tag condition")
    needs_attest = _job_field(attest, "needs") or ""
    if not {"build", "verify", "gather"} <= set(re.findall(r"[a-z_-]+", needs_attest)):
        errors.append("attest does not need build, verify and gather")
    if _job_permissions(attest) != ATTEST_PERMISSIONS:
        errors.append(f"attest's permissions are not {sorted(ATTEST_PERMISSIONS)}")
    body = "\n".join(attest)
    if not ATTEST_USES.search(body):
        errors.append("no actions/attest step pinned by a 40-hex commit")
    if not re.search(r"subject-path:\s*release-assets/\*\s*$", body, re.M):
        errors.append("subject-path is not release-assets/*")
    logical = body.replace("\\\n", " ").splitlines()  # a `\`-continued command is one line
    verify = [line for line in logical if "gh attestation verify" in line]
    if not verify or any(not all(flag in line for flag in VERIFY_FLAGS) for line in verify):
        errors.append(
            "a gh attestation verify without --repo, --signer-workflow, --source-ref and "
            "--deny-self-hosted-runners"
        )
    if re.search(r"^    continue-on-error:", body, re.M):
        errors.append("attest has a job-level continue-on-error:")
    if re.search(r"\|\||set \+e", without_expressions(body)):
        errors.append("a step of attest swallows a failure (|| or set +e)")
    if re.search(r"setup-uv|uv run", body):
        errors.append("attest runs setup-uv or uv")
    order = [
        next((i for i, line in enumerate(attest) if any(m in line for m in markers)), None)
        for markers in (
            ("./.github/actions/verify-artifact", "actions/download-artifact@"),
            ("actions/attest@",),
            ("gh attestation verify",),
        )
    ]
    if None in order or order != sorted(order):
        errors.append("attest's steps are not download, attest, verify, in that order")
    if re.search(r"^      (- )?\s*(if|continue-on-error):", body, re.M):
        errors.append("a step of attest has if: or continue-on-error:")
    if ID_TOKEN.search(text.split("\njobs:", 1)[0]):
        errors.append("the workflow-level permissions grant id-token: write or write-all")
    for name, lines in jobs.items():
        if name not in ("attest", "pypi") and ID_TOKEN.search("\n".join(lines)):
            errors.append(f"{name} has id-token: write or write-all")
    if not {"attest", "gather"} <= set(re.findall(r"[a-z_-]+", _job_field(publish, "needs") or "")):
        errors.append("publish does not need attest and gather")
    return errors


# ---------------------------------------------------------------------------------------------
# The build hosts

HOST_NAMES = ("WASI_SDK_DIR", "WASMTIME_DIR", "HOST_PYTHON_ARCHIVE", "CYTHON_WHEEL", "NINJA_WHEEL")
# The file in downloads/ each host name stands for: a directory name is its tarball's stem.
HOST_FILE = {"WASI_SDK_DIR": "{}.tar.gz", "WASMTIME_DIR": "{}.tar.xz"}
CONF_HOST_LINE = re.compile(rf"^([A-Z][A-Z0-9_]*?)_({'|'.join(HOST_NAMES)})=(\S+)$", re.M)
SH_HOST_KEY = re.compile(r"\bHOST_KEY=([A-Z][A-Z0-9_]*)")


def host_case_branches(text: str) -> dict[str, list[str]]:
    """The file names the `get` lines fetch in each branch of the download script's
    `case "$HOST_KEY" in … esac`."""
    branches: dict[str, list[str]] = {}
    current: list[str] | None = None
    inside = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if re.fullmatch(r'case\s+"?\$\{?HOST_KEY\}?"?\s+in', s):
            inside = True
        elif inside and s == "esac":
            break
        elif inside and (m := re.fullmatch(r"([A-Z][A-Z0-9_]*)\)", s)):
            current = branches.setdefault(m[1], [])
        elif inside and s == ";;":
            current = None
        elif inside and current is not None and (g := GET.match(line)):
            current.append(g[2] or g[1].rstrip("/").rsplit("/", 1)[-1])
    return branches


def host_table_errors(
    conf: str, sh_keys: Iterable[str], py_keys: Iterable[str], download: str, pinned: Iterable[str]
) -> list[str]:
    """Every build host has all five host names in `line.conf`; each names a pinned file that the
    download script fetches in that host's own `case` branch; and `line.conf`, `line.sh`,
    `line.py` and `00_download.sh` know the same hosts."""
    pinned = set(pinned)
    table: dict[str, dict[str, str]] = {}
    for key, name, value in CONF_HOST_LINE.findall(conf):
        table.setdefault(key, {})[name] = value
    errors = [
        f"line.conf: {name} is set for every host, not per host key"
        for name in HOST_NAMES
        if re.search(rf"^{name}=", conf, re.M)
    ]
    if not table:
        errors.append("line.conf: no host key names a host's inputs")
    branches = host_case_branches(download)
    for where, keys in (
        ("line.sh", set(sh_keys)),
        ("line.py", set(py_keys)),
        ("00_download.sh", set(branches)),
    ):
        if keys != set(table):
            errors.append(f"{where}: hosts {sorted(keys)}, but line.conf has {sorted(table)}")
    for key in sorted(table):
        for name in HOST_NAMES:
            value = table[key].get(name)
            if value is None:
                errors.append(f"line.conf: no {key}_{name}")
                continue
            file = HOST_FILE.get(name, "{}").format(value)
            if file not in pinned:
                errors.append(f"{key}_{name}: {file} is not pinned")
            if file not in branches.get(key, []):
                errors.append(f"{key}_{name}: {file} is not fetched in the {key} branch")
    return errors


# ---------------------------------------------------------------------------------------------
# The compiler each host runs: each host's own
# pinned clang, natively. One host key carries the five emulation names: the fallback, switched off,
# runnable by one line (COMPILER_SDK_DIR naming another host's SDK).

COMPILER_NAME = "COMPILER_SDK_DIR"
EMULATION_NAMES = (
    "EMULATOR_DEB",
    "AARCH64_LIBC_DEB",
    "AARCH64_LIBSTDCXX_DEB",
    "AARCH64_LIBGCC_DEB",
    "AARCH64_LIBTINFO_DEB",
)
CONF_COMPILER_LINE = re.compile(
    rf"^([A-Z][A-Z0-9_]*?)_({'|'.join((COMPILER_NAME, *EMULATION_NAMES))})=(\S+)$", re.M
)
# What step 10's code must name: the launcher, the guest's root and its empty loader cache, and
# the gate's probes (the InstalledDir, the cpp mode, the loader-cache trace).
STEP_10_WORDS = ("clang-emulated", "aarch64-root", "ld.so.cache", "InstalledDir", "clang-cpp")
STEP_10_STRACE = re.compile(r"qemu-aarch64\S*\s+-strace\b")
LAUNCHER_FLAGS = ("-U LD_PRELOAD", "-U LD_LIBRARY_PATH", "-U LD_AUDIT")
# The name the launcher was called by -> the driver mode it must add (None: no mode).
LAUNCHER_MODES = {"clang": None, "clang++": "--driver-mode=g++", "clang-cpp": "--driver-mode=cpp"}


def code_text(p: Path) -> str | None:
    """A shell script's text with its full-line comments dropped, or None if it is missing."""
    return "\n".join(line for _, line in _code_lines(p)) if p.is_file() else None


def _maps(launcher: str, name: str, mode: str | None) -> bool:
    """The launcher has a `case` arm for the name, adding exactly its mode (or none)."""
    arm = re.search(rf"^\s*{re.escape(name)}\)(.*)$", launcher, re.M)
    if arm is None:
        return False
    return mode in arm[1] if mode else "--driver-mode" not in arm[1]


def compiler_table_errors(
    conf: str, download: str, pinned: Iterable[str], step_10: str, launcher: str | None
) -> list[str]:
    """Every rule of the build hosts' compiler table, one line
    per breach. Each host's COMPILER_SDK_DIR is its own SDK, or another host's own SDK while the
    key carries all five emulation names (the fallback's switch thrown). Exactly one key carries
    the five names, each pinned and fetched in its branch, and that branch fetches another host's
    SDK for the fallback's compiler. `step_10` and `launcher` are scripts/steps/10_tools.sh and
    scripts/clang-emulated without their comment lines (None: the launcher is missing), so a
    comment satisfies nothing."""
    pinned = set(pinned)
    own = {k: v for k, name, v in CONF_HOST_LINE.findall(conf) if name == "WASI_SDK_DIR"}
    table: dict[str, dict[str, str]] = {}
    for key, name, value in CONF_COMPILER_LINE.findall(conf):
        table.setdefault(key, {})[name] = value
    branches = host_case_branches(download)
    errors = [
        f"line.conf: {name} is set for every host, not per host key"
        for name in (COMPILER_NAME, *EMULATION_NAMES)
        if re.search(rf"^{name}=", conf, re.M)
    ]
    carriers = [k for k in sorted(table) if any(n in table[k] for n in EMULATION_NAMES)]
    if not carriers:
        errors.append("no host key carries the emulation names (the fallback is gone)")
    elif len(carriers) > 1:
        errors.append(f"{' and '.join(carriers)} both carry the emulation names")
    for key in sorted(own):
        names = table.get(key, {})
        compiler = names.get(COMPILER_NAME)
        if compiler is None:
            errors.append(f"line.conf: no {key}_{COMPILER_NAME}")
            continue
        have = [n for n in EMULATION_NAMES if n in names]
        if 0 < len(have) < len(EMULATION_NAMES):
            errors.append(f"{key} has {len(have)} of the five emulation names")
        files: dict[str, str] = {}
        if compiler != own[key]:
            if compiler not in own.values():
                errors.append(f"{key}_{COMPILER_NAME}: {compiler} is no host's own WASI_SDK_DIR")
            if not have:
                errors.append(
                    f"{key} compiles with another host's SDK but lacks the five emulation names"
                )
            files[COMPILER_NAME] = f"{compiler}.tar.gz"
        if len(have) == len(EMULATION_NAMES):
            files.update({n: names[n] for n in have})
            foreign = [f"{v}.tar.gz" for k, v in own.items() if k != key]
            if not any(f in branches.get(key, []) for f in foreign):
                errors.append(
                    f"{key}'s branch fetches no other host's SDK (the fallback's compiler)"
                )
        for name, file in files.items():
            if file not in pinned:
                errors.append(f"{key}_{name}: {file} is not pinned")
            if file not in branches.get(key, []):
                errors.append(f"{key}_{name}: {file} is not fetched in the {key} branch")
    errors += [f"10_tools.sh does not name {w}" for w in STEP_10_WORDS if w not in step_10]
    if not STEP_10_STRACE.search(step_10):
        errors.append("10_tools.sh does not trace the guest's loader (qemu-aarch64 -strace)")
    if launcher is None:
        return [*errors, "scripts/clang-emulated is missing"]
    errors += [
        f"scripts/clang-emulated does not pass {f}" for f in LAUNCHER_FLAGS if f not in launcher
    ]
    if not (re.search(r"\bQEMU_", launcher) and re.search(r"\bunset\b", launcher)):
        errors.append("scripts/clang-emulated does not unset the QEMU_ variables")
    errors += [
        f"scripts/clang-emulated does not map {name} to {mode or 'no mode'}"
        for name, mode in LAUNCHER_MODES.items()
        if not _maps(launcher, name, mode)
    ]
    return errors


# ---------------------------------------------------------------------------------------------
# Every compile contracts nothing: -ffp-contract=off lives in the
# toolchain's own clang.cfg and clang++.cfg, written by step 10, and nothing on any compiler's
# command line may override it.

# The options that override or drop the configuration file, as whole
# tokens; any -ffp-contract= value but off is one too (fp_override).
FP_CONTRACT_OVERRIDES = (
    "-ffp-model=",
    "-ffast-math",
    "-Ofast",
    "-funsafe-math-optimizations",
    "--no-default-config",
    "--config",
)
FP_FLAG = "-ffp-contract=off"
# The meson builds, by their folder under build/: every one's compile_commands.json is a compile
# record the judge reads; a specification that adds a meson build extends this.
MESON_BUILDS = (
    "numpy-build",
    "pandas-build",
    "freetype-build",
    "harfbuzz-build",
    "sheenbidi-build",
    "libraqm-build",
    "matplotlib-build",
    "contourpy-build",  # added for matplotlib's contours
    "scipy-build",  # added for scipy
    "sklearn-build",  # added for scikit-learn
    "statsmodels-build",  # added for statsmodels
)
# The Makefiles autoconf generates for the C libraries (libxml2's and libxslt's), and
# step 60's two command files.
AUTOCONF_MAKEFILES = (
    "zlib-build/Makefile",
    "xz-build/Makefile",
    "xz-build/src/liblzma/Makefile",
    "libxml2-build/Makefile",
    "libxslt-build/Makefile",
    "libxslt-build/libxslt/Makefile",
    "libxslt-build/libexslt/Makefile",
)
LINK_RECORDS = ("link/make-n.txt", "link/reactor-commands.txt")
CPYTHON_MAKEFILE = "Python-*/cross-build/wasm32-wasip1/Makefile"
# What step 10's code must name: the two files, the flag, and the -### probe, matched on its -cc1
# line.
STEP_10_FP_WORDS = ("clang.cfg", "clang++.cfg", FP_FLAG, "-###", "-cc1")
# A source pragma that turns contraction back on inside a block.
FP_PRAGMA = re.compile(r"FP_CONTRACT\s+ON\b|\bfp\s+contract\s*\(\s*(?:on|fast)\s*\)")
SOURCE_SUFFIXES = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".pyx", ".pxd", ".pxi"}
_MAKE_ASSIGNMENT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:?+]?=(.*)$")
_FLAG_VARIABLE = re.compile(r"^(CC|CXX|CPP)$|CFLAGS|CXXFLAGS|CPPFLAGS|CCSHARED|OPT")
_COMPILER_TOKEN = re.compile(r"^(\$\((?:CC|CXX|CPP)\)|\S*clang(?:\+\+)?)$")


def fp_override(token: str) -> str | None:
    """The banned option a whole token is, or None."""
    if token.startswith("-ffp-contract="):
        return None if token == FP_FLAG else token
    for option in FP_CONTRACT_OVERRIDES:
        if option.endswith("="):
            if token.startswith(option):
                return token
        elif token == option or token.startswith(option + "="):
            return token
    return None


def _tokens(text: str) -> list[str]:
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


_ASSIGNED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=(.*)$")


def fp_hits(text: str) -> list[str]:
    """The banned options among the whole tokens of one command line or variable value. A token is
    read without the brackets, commas and quotes a meson list or a Makefile puts around it; a
    quoted multi-flag string (`CXX_EH="-fwasm-exceptions … -ffp-model=precise"`) is split again on
    whitespace, and a leading `NAME=` is dropped (`CFLAGS=-ffast-math`), so a flag inside a shell
    variable's value is a hit too."""
    hits = []
    for tok in _tokens(text):
        for piece in tok.strip("[](),;'\"").split():
            if not piece.startswith("-") and (m := _ASSIGNED.match(piece)):
                piece = m[1]
            if hit := fp_override(piece.strip("'\"")):
                hits.append(hit)
    return hits


def _logical_lines(text: str) -> list[str]:
    """A Makefile's lines with backslash continuations joined."""
    out: list[str] = []
    pending = ""
    for line in text.splitlines():
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        out.append(pending + line)
        pending = ""
    if pending:
        out.append(pending)
    return out


def is_compiler_line(line: str) -> bool:
    """A command line that runs a compiler: `$(CC)`, `$(CXX)`, `$(CPP)` or a word ending in clang
    or clang++ among its whole tokens (wasmtime's `--config` on a line that runs
    no compiler is not a hit)."""
    return any(_COMPILER_TOKEN.match(tok) for tok in _tokens(line))


def fp_makefile_hits(text: str) -> tuple[list[str], int]:
    """(hits, lines read) over a Makefile: compile-flag variables (CC, CXX, CPP, and any name
    holding CFLAGS, CXXFLAGS, CPPFLAGS, CCSHARED or OPT, or whose value runs a compiler, as
    automake's COMPILE does) and recipe lines that run a compiler."""
    hits: list[str] = []
    read = 0
    for line in _logical_lines(text):
        if m := _MAKE_ASSIGNMENT.match(line):
            # By name, or by value: automake's `COMPILE = $(CC) $(DEFS) …` runs the compiler.
            if _FLAG_VARIABLE.search(m[1]) or is_compiler_line(m[2]):
                read += 1
                hits += [f"{m[1]}: {h}" for h in fp_hits(m[2])]
        elif line.startswith("\t") and is_compiler_line(line):
            read += 1
            hits += [f"recipe line: {h}" for h in fp_hits(line)]
    return hits, read


def fp_command_file_hits(text: str) -> tuple[list[str], int]:
    """(hits, compiler lines read) over a file of shell commands (step 60's make -n output)."""
    hits: list[str] = []
    read = 0
    for line in _logical_lines(text):
        if is_compiler_line(line):
            read += 1
            hits += fp_hits(line)
    return hits, read


def fp_record_errors(root: Path) -> tuple[list[str], list[str]]:
    """The compile records a build leaves under build/: every listed meson record exists once any
    does, every record under build/*/ is listed, and no compiler command or compile-flag variable
    in any record holds a banned option. Returns (errors, what was read, one line each)."""
    build = root / "build"
    errors: list[str] = []
    read: list[str] = []
    listed = {name: build / name / "compile_commands.json" for name in MESON_BUILDS}
    present = {n for n, p in listed.items() if p.is_file()}
    if not present:
        return ["no compile record under build/ (build first)"], read
    errors += [
        f"{n}/compile_commands.json is missing (listed in MESON_BUILDS)"
        for n in sorted(set(listed) - present)
    ]
    for p in sorted(build.glob("*/compile_commands.json")):
        if p.parent.name not in listed:
            errors.append(f"{p.parent.name}/compile_commands.json is not listed in MESON_BUILDS")
    for name in sorted(present):
        entries = json.loads(listed[name].read_text())
        read.append(f"{name}/compile_commands.json: {len(entries)} commands")
        for e in entries:
            command = e.get("command") or " ".join(e.get("arguments", []))
            errors += [f"{name}: {e.get('file')}: {h}" for h in fp_hits(command)]
    for rel in (
        *AUTOCONF_MAKEFILES,
        *sorted(str(p.relative_to(build)) for p in build.glob(CPYTHON_MAKEFILE)),
    ):
        p = build / rel
        if not p.is_file():
            errors.append(f"build/{rel} is missing")
            continue
        hits, lines = fp_makefile_hits(p.read_text(errors="replace"))
        read.append(f"{rel}: {lines} compile-flag variables and compiler lines")
        errors += [f"{rel}: {h}" for h in hits]
    if not list(build.glob(CPYTHON_MAKEFILE)):
        errors.append(f"build/{CPYTHON_MAKEFILE} is missing")
    for rel in LINK_RECORDS:
        p = build / rel
        if not p.is_file():
            errors.append(f"build/{rel} is missing")
            continue
        hits, lines = fp_command_file_hits(p.read_text(errors="replace"))
        read.append(f"{rel}: {lines} compiler lines")
        errors += [f"{rel}: {h}" for h in hits]
    return errors, read


def fp_pragma_hits(trees: Iterable[Path]) -> list[str]:
    """Source files under the given trees that turn contraction on by pragma."""
    hits = []
    for tree in trees:
        for p in sorted(tree.rglob("*")):
            if p.suffix not in SOURCE_SUFFIXES or not p.is_file():
                continue
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            if FP_PRAGMA.search(text):
                hits.append(f"{p.relative_to(tree.parent)}: a pragma turns contraction on")
    return hits


def fp_cc1_errors(name: str, output: str) -> list[str]:
    """The -### output of one driver: its -cc1 line carries -ffp-contract=off once and no other
    -ffp-contract= value."""
    lines = [line for line in output.splitlines() if '"-cc1"' in line]
    if not lines:
        return [f"{name} -###: no -cc1 line"]
    values = re.findall(r'"(-ffp-contract=[^"]*)"', lines[0])
    if values != [FP_FLAG]:
        return [
            f"{name} -###: the -cc1 line carries {values or 'no -ffp-contract'}, not {FP_FLAG} once"
        ]
    return []


def fp_compiler_errors(bindir: Path) -> list[str]:
    """Run the two -### probes through an SDK's clang and clang++ (what step 10's gate does)."""
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.c"
        probe.write_text("int main(void) { return 0; }\n")
        for name, extra in (("clang", []), ("clang++", ["-x", "c++"])):
            r = subprocess.run(
                [
                    str(bindir / name),
                    "--target=wasm32-wasip1",
                    "-###",
                    "-c",
                    *extra,
                    str(probe),
                    "-o",
                    str(Path(tmp) / "probe.o"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if r.returncode != 0:
                errors.append(
                    f"{name} -### failed: {r.stderr.strip().splitlines()[-1:] or r.returncode}"
                )
                continue
            errors += fp_cc1_errors(name, r.stderr + r.stdout)
    return errors


def fp_recipe_errors(step_10: str | None, files: dict[str, str]) -> list[str]:
    """Step 10's code writes the flag into both configuration files and probes it, and no other
    recipe file (`files`: tracked path -> text) carries a banned option or any -ffp-contract=
    form."""
    if step_10 is None:
        return ["scripts/steps/10_tools.sh is missing"]
    errors = [f"10_tools.sh does not name {w}" for w in STEP_10_FP_WORDS if w not in step_10]
    for rel in sorted(files):
        for n, line in enumerate(files[rel].splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # a comment sets nothing; a comment satisfies nothing either
            if "-ffp-contract=" in line:
                errors.append(f"{rel}:{n}: sets -ffp-contract outside step 10")
            errors += [f"{rel}:{n}: {h}" for h in fp_hits(line)]
    return errors


# The release workflow's steps, read as text (the judge has no YAML library)


def workflow_steps(lines: list[str]) -> list[list[str]]:
    """A job's steps, each as its lines: a step starts at a `      - ` line under `    steps:` and
    runs to the next one; a line indented four spaces ends the steps (another key of the job)."""
    steps: list[list[str]] = []
    inside = False
    for line in lines:
        if re.fullmatch(r"    steps:\s*", line):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("      - "):
            steps.append([line])
        elif steps and (line.startswith("       ") or not line.strip()):
            steps[-1].append(line)
        elif line.strip():
            inside = False
    return steps


def step_fields(step: list[str]) -> dict:
    """A step's keys: a plain value as its text, `with:` and `env:` as dicts of their keys, and a
    `|` or `>` block (a `run:` script) as its lines dedented."""
    lines = ["        " + step[0][len("      - ") :], *step[1:]]
    fields: dict = {}
    i = 0
    while i < len(lines):
        m = re.fullmatch(r"        ([A-Za-z0-9_-]+):\s*(.*?)\s*", lines[i])
        i += 1
        if not m:
            continue
        key, value = m[1], m[2]
        block = []
        while i < len(lines) and (lines[i].startswith("          ") or not lines[i].strip()):
            block.append(lines[i])
            i += 1
        if key in ("with", "env") and not value:
            fields[key] = dict(
                re.fullmatch(r"          ([A-Za-z0-9_-]+):\s*(.*?)\s*", b).groups()
                for b in block
                if re.fullmatch(r"          ([A-Za-z0-9_-]+):\s*(.*?)\s*", b)
            )
        elif value in ("|", "|-", ">", ">-"):
            fields[key] = "\n".join(b[10:] for b in block).rstrip("\n") + "\n"
        else:
            fields[key] = value
    return fields


def workflow_step_script(text: str, job: str, name: str) -> str:
    """The `run:` script of the step named `name` in `job`, exactly as the workflow holds it.
    Raises LookupError when there is no such step, so a check that runs it cannot pass on a
    workflow without it (an empty script would exit 0)."""
    for step in workflow_steps(workflow_jobs(text).get(job, [])):
        fields = step_fields(step)
        if fields.get("name") == name and isinstance(fields.get("run"), str):
            return fields["run"]
    raise LookupError(f"{job} has no step named {name!r} with a run: script")


def _job_map(lines: list[str], key: str) -> dict[str, str]:
    """A job-level mapping (`outputs:`), its keys indented six spaces."""
    out: dict[str, str] = {}
    inside = False
    for line in lines:
        if re.fullmatch(rf"    {key}:\s*", line):
            inside = True
            continue
        if inside:
            m = re.fullmatch(r"      ([A-Za-z0-9_-]+):\s*(.*?)\s*", line)
            if m:
                out[m[1]] = m[2]
            elif line.strip():
                break
    return out


def _permission_set(lines: list[str]) -> set[str] | None:
    """A job's permissions: `{}` as the empty set, a block as its lines, None when absent."""
    value = _job_field(lines, "permissions")
    if value is None:
        return None
    return set() if value == "{}" else _job_permissions(lines)


# ---------------------------------------------------------------------------------------------
# The release workflow's rebuilds

# One job per host, so each job's outputs are its own (a matrix shares one output namespace):
# arm64 Linux (build-shard, whose one compile also serves the build shard) and x86_64 Linux, each
# compiling with its own pinned clang. Each job's time limit, in minutes, and the decision job's
# output it runs on: both rebuild natively, a hung job frees the gate after two hours, and the
# plan sets both outputs on every run of the release shape (a rules check holds that).
REBUILD_JOBS = {
    "build-shard": ("ubuntu-24.04-arm", 120, "needs.plan.outputs.build == 'true'"),
    "rebuild-linux-x86-64": ("ubuntu-24.04", 120, "needs.plan.outputs.rebuild == 'true'"),
}
REBUILD_RUNNERS = tuple(runner for runner, _, _ in REBUILD_JOBS.values())
REBUILD_IF = "needs.plan.outputs.rebuild == 'true'"
TOOLS_STEP = "The runner's own tools"
WHEEL_STEP = "The wheel, as the build job makes it"


def _needs(lines: list[str]) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", _job_field(lines, "needs") or ""))


def _rebuild_shape(lines: list[str]) -> str:
    """A rebuild job's rebuild steps (its tools, the download, the build, the SHA256SUMS upload,
    the wheel and its upload) with its runner named by one placeholder: the two jobs must be this
    text alike (the longer runner name goes first)."""
    kept = []
    for step in workflow_steps(lines):
        f = step_fields(step)
        run = str(f.get("run", "")).strip()
        if (
            str(f.get("name", "")).startswith(TOOLS_STEP)
            or run in ("scripts/00_download.sh", "scripts/build.sh")
            or f.get("id") in ("sums", "wheel")
            or f.get("name") == WHEEL_STEP
        ):
            kept += step
    body = "\n".join(kept)
    for runner in sorted(REBUILD_RUNNERS, key=len, reverse=True):
        body = body.replace(runner, "@RUNNER@")
    return body


def rebuild_gate_errors(text: str) -> list[str]:
    """Every rule of the rebuild gate, one line per breach, on the workflow without its comments:
    a rebuild job on each gated runner beside the build, their rebuild steps alike, each handing
    on its uploads' ids, each running on the plan's output for it; a same-bytes job that
    downloads each by id into that runner's folders and compares every rebuild's SHA256SUMS with
    the set's byte for byte; and nothing signed or published before it."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    same = jobs.get("same-bytes")
    errors = [f"no {job} job" for job in (*REBUILD_JOBS, "same-bytes") if not jobs.get(job)]
    if errors:
        return errors
    for job, (runner, minutes, cond) in REBUILD_JOBS.items():
        lines = jobs[job]
        body = "\n".join(lines)
        if _job_field(lines, "runs-on") != runner:
            errors.append(f"{job} does not run on {runner}")
        if _job_field(lines, "timeout-minutes") != str(minutes):
            errors.append(f"{job}'s timeout-minutes is not {minutes}")
        if _job_field(lines, "if") != cond:
            errors.append(f"{job}'s if: is not the plan's {cond}")
        # The core count beside every time figure, and any binfmt_misc entry that would run an
        # aarch64 ELF through the runner's own qemu and hide a gap in the launcher's closure.
        # The runner's own python3, which step 10's shim keeps out of the build, named
        # in the log.
        for fact, pattern in (
            ("nproc", r"^\s+nproc\s*$"),
            ("binfmt_misc", r"/proc/sys/fs/binfmt_misc"),
            ("python3 --version", r"^\s+python3 --version\s*$"),
        ):
            if not re.search(pattern, body, re.M):
                errors.append(f"{job}'s tools step does not print {fact}")
        if not re.search(r"^\s+(- )?run:\s*scripts/build\.sh\s*$", body, re.M):
            errors.append(f"{job} does not run scripts/build.sh")
        uploads = {
            f.get("id"): f
            for f in map(step_fields, workflow_steps(lines))
            if f.get("uses", "").startswith("actions/upload-artifact@")
        }
        for step_id, name, path in (
            ("sums", f"rebuild-{runner}", "build/artifacts/SHA256SUMS"),
            ("wheel", f"rebuild-wheel-{runner}", "dist/wasi_python-*.whl"),
        ):
            w = uploads.get(step_id, {}).get("with", {})
            if (w.get("name"), w.get("path")) != (name, path):
                errors.append(f"{job} does not upload {path} as {name} (id: {step_id})")
        outputs = _job_map(lines, "outputs")
        if (outputs.get("sums-id"), outputs.get("wheel-id")) != (
            "${{ steps.sums.outputs.artifact-id }}",
            "${{ steps.wheel.outputs.artifact-id }}",
        ):
            errors.append(f"{job}'s outputs are not sums-id and wheel-id from its two uploads")
    if _job_field(same, "if") != REBUILD_IF:
        errors.append(f"same-bytes' if: is not the plan's {REBUILD_IF}")
    for name in (*REBUILD_JOBS, "same-bytes"):
        lines = jobs[name]
        if (_permission_set(lines) or set()) - {"contents: read"}:
            errors.append(f"{name}'s permissions are more than contents: read")
        if re.search(r"^    continue-on-error:", "\n".join(lines), re.M):
            errors.append(f"{name} has a job-level continue-on-error:")
    shapes = {_rebuild_shape(jobs[job]) for job in REBUILD_JOBS}
    if len(shapes) != 1:
        errors.append("the rebuild jobs' rebuild steps differ beyond their runner")
    if not {"build", *REBUILD_JOBS} <= _needs(same):
        errors.append("same-bytes does not need build and both rebuild jobs")
    same_body = "\n".join(line for line in same if not line.startswith("    runs-on:"))
    # One operand a rebuild's download, the other not: comparing the set's file with itself, or
    # one rebuild with another, proves nothing.
    pairs = re.findall(r"\bcmp\s+(\S+)\s+(\S+)", same_body)
    if not any(("rebuilds/" in a) != ("rebuilds/" in b) for a, b in pairs):
        errors.append("same-bytes does not compare a rebuild's SHA256SUMS with the set's (cmp)")
    # Each job's id into its own runner's folder, pairing artifact-ids with the path: of the same
    # with: block; one job's id in the other's folder fails.
    fetched = {
        (w.get("artifact-ids"), w.get("path"))
        for f in map(step_fields, workflow_steps(same))
        if f.get("uses", "").startswith("actions/download-artifact@")
        for w in [f.get("with", {})]
    }
    for job, (runner, _, _) in REBUILD_JOBS.items():
        for output, folder, what in (
            ("sums-id", "rebuilds", "SHA256SUMS"),
            ("wheel-id", "rebuilt-wheels", "rebuilt wheel"),
        ):
            if (f"${{{{ needs.{job}.outputs.{output} }}}}", f"{folder}/{runner}") not in fetched:
                errors.append(
                    f"same-bytes does not download {job}'s {what} by id into {folder}/{runner}"
                )
    # Both of same-bytes' loops, the set's SHA256SUMS and the wheel, run over every runner.
    for what, marker in (("SHA256SUMS", "rebuilds/$"), ("wheel", "rebuilt-wheels/$")):
        looped = {
            runner
            for step in re.split(r"^      - ", same_body, flags=re.M)
            if marker in step
            for m in re.finditer(r"\bfor\s+\w+\s+in\s+([^;\n]*);\s*do\b", step)
            for runner in m[1].split()
        }
        errors += [
            f"same-bytes' {what} loop does not run over {r}"
            for r in REBUILD_RUNNERS
            if r not in looped
        ]
    if re.search(r"\|\||set \+e", without_expressions(same_body)):
        errors.append("a step of same-bytes swallows a failure (|| or set +e)")
    for name in ("attest", "publish"):
        if "same-bytes" not in _needs(jobs.get(name, [])):
            errors.append(f"{name} does not need same-bytes")
    return errors


# ---------------------------------------------------------------------------------------------
# What is checked, signed and published is what the build job made

ASSETS_ID = "${{ needs.build.outputs.assets-id }}"
# A download's `path:` with a leading workspace expression dropped.
WORKSPACE_PREFIX = re.compile(r"^\$\{\{\s*github\.workspace\s*\}\}/+")

SUMS_SHA256 = "${{ needs.build.outputs.sums-sha256 }}"
CHECK_STEP = "These are the bytes the build job made"
GUARD_STEP = "The build job handed on an artifact id"
GUARD_TEST = '"" | *[!0-9]*)'
# The local action every reader of the build's files runs, the one copy of the guard, the
# download and the check, and what each reader hands it.
ASSETS_ACTION = "./.github/actions/verify-artifact"
ASSETS_ACTION_FILE = ".github/actions/verify-artifact/action.yml"
ASSETS_WITH = {"assets-id": ASSETS_ID, "sums-sha256": SUMS_SHA256}
NEEDS_OUTPUT = re.compile(r"^\$\{\{ needs\.([\w-]+)\.outputs\.([\w-]+) \}\}$")
NOT_BY_ID = (
    "name",
    "pattern",
    "github-token",
    "run-id",
    "repository",
    "merge-multiple",
    "skip-decompress",
)
OTHER_FETCH = re.compile(r"gh\s+run\s+download|actions/github-script|/actions/artifacts")
ENVIRONMENTS = {"publish": "release", "pypi": "pypi"}  # accept-push's, by the accept scan
PYPI_IF = TAG_ONLY + " && vars.PYPI_PUBLISH == 'true'"
JOB_PERMISSIONS = {
    # The decision job reads the history, and this pull request's runs to re-use a green one;
    # quick runs the tools and the rules; ci-status reads only its needs' results.
    "plan": {"contents: read", "actions: read"},
    "quick": {"contents: read"},
    "ci-status": set(),
    "build": {"contents: read"},
    **{job: {"contents: read"} for job in REBUILD_JOBS},
    # It checks this commit out for the local action alone.
    "same-bytes": {"contents: read"},
    "verify": {"contents: read"},
    # The judge jobs check out and read the build's files; the gather checks out alone.
    **{
        job: {"contents: read"}
        for job in ("judge-macos", "judge-linux", "judge-windows", "judge-release")
    },
    "gather": {"contents: read"},
    # The acceptance from the gather's record: it checks out and runs the judge, with no secret.
    "accept-record": {"contents: read"},
    # The push of the acceptance: it checks out with the deploy key, which the token never is.
    "accept-push": {"contents: read"},
    # The weekly run's issue: it opens or comments on one, and checks nothing out.
    "weekly-issue": {"issues: write"},
    # The key and the decision; the cache's writer.
    "inputs": {"contents: read"},
    "save-set": {"contents: read"},
    "attest": ATTEST_PERMISSIONS,
    "publish": {"contents: write"},
    # The trusted publisher's token, and the checkout of the local action.
    "pypi": {"contents: read", "id-token: write"},
}
# The systems whose judge job uploads one record per leg, and the gather's download of them: by the
# names those legs upload under, into the job's own folder, each only when the plan ran the job.
RECORD_SYSTEMS = ("macos", "linux", "windows", "release")
RECORD_IFS = {
    "needs.plan.outputs.build == 'true'",
    *(f"needs.plan.outputs.{s} != '[]'" for s in RECORD_SYSTEMS),
}


def _record_download(w: dict) -> str | None:
    """The system a download of records by name is for, when it is exactly one: every
    `record-<system>-*` into `records/judge-<system>`, its digest checked; None otherwise."""
    for s in RECORD_SYSTEMS:
        if w == {
            "pattern": f"record-{s}-*",
            "path": f"records/judge-{s}",
            "digest-mismatch": "error",
        }:
            return s
    return None


def _guard_tests(run: str, var: str) -> bool:
    """The guard's script tests `var` itself: `case "$var"` with the refusing branch, or a `for`
    loop that lists `"$var"` and tests its loop variable so."""
    branch = re.escape(GUARD_TEST) + r"[^\n]*\bexit 1\b"
    if re.search(rf'case "\${re.escape(var)}" in\s*\n\s*{branch}', run):
        return True
    for m in re.finditer(r"for (\w+) in ([^;\n]*); do\n(.*?)\n\s*done", run, re.S):
        if f'"${var}"' in m[2].split() and re.search(rf'case "\${m[1]}" in\s*\n\s*{branch}', m[3]):
            return True
    return False


def download_path(value: object) -> str:
    """A download's `path:` as the folder it names: one pair of matching YAML quotes dropped,
    then a leading `${{ github.workspace }}/`, then `posixpath.normpath`."""
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return posixpath.normpath(WORKSPACE_PREFIX.sub("", text))


def action_steps(text: str) -> list[list[str]]:
    """A composite action's steps, each as its lines, read as a workflow job's are: the action's
    `  steps:` block, indented two spaces more, without its comments."""
    lines = without_comments(text).splitlines()
    at = next((k for k, line in enumerate(lines) if re.fullmatch(r"  steps:\s*", line)), None)
    if at is None:
        return []
    shifted = ["  " + line if line.strip() else line for line in lines[at + 1 :]]
    return workflow_steps(["    steps:", *shifted])


def action_step_script(text: str, name: str) -> str:
    """The `run:` script of the action's step named `name`, exactly as the action holds it.
    Raises LookupError when there is no such step, as `workflow_step_script` does."""
    for step in action_steps(text):
        fields = step_fields(step)
        if fields.get("name") == name and isinstance(fields.get("run"), str):
            return fields["run"]
    raise LookupError(f"the action has no step named {name!r} with a run: script")


def assets_action_errors(text: str) -> list[str]:
    """The local action every reader of the build's files runs: a composite of exactly three
    steps, the id guarded, the release-assets download by that id alone with its digest checked,
    and the check against the SHA-256 of SHA256SUMS the build job handed on; both values required
    inputs; no step with if: or continue-on-error:, no expression in a run: script, no failure
    swallowed."""
    errors = []
    body = without_comments(text)
    if not re.search(r"^runs:\n  using: composite\s*$", body, re.M):
        errors.append("the action is not a composite action")
    for name in ("assets-id", "sums-sha256"):
        if not re.search(rf"^  {name}:\n(?:    .*\n)*?    required: true\s*$", body, re.M):
            errors.append(f"the action has no required input {name}")
    if OTHER_FETCH.search(body):
        errors.append("the action fetches an artifact another way")
    steps = [step_fields(s) for s in action_steps(text)]
    if len(steps) != 3:
        return [*errors, f"the action has {len(steps)} steps, not the guard, download and check"]
    guard, download, check = steps
    if (
        guard.get("name") != GUARD_STEP
        or guard.get("env") != {"ASSETS_ID": "${{ inputs.assets-id }}"}
        or not _guard_tests(str(guard.get("run", "")), "ASSETS_ID")
    ):
        errors.append("the action's first step is not the guard that tests the id it downloads")
    if not str(download.get("uses", "")).startswith("actions/download-artifact@") or download.get(
        "with"
    ) != {
        "artifact-ids": "${{ inputs.assets-id }}",
        "path": "release-assets",
        "digest-mismatch": "error",
    }:
        errors.append(
            "the action's second step is not the download of release-assets by that id alone, "
            "digest-mismatch: error"
        )
    run = str(check.get("run", ""))
    if not (
        check.get("name") == CHECK_STEP
        and check.get("env") == {"SUMS_SHA256": "${{ inputs.sums-sha256 }}"}
        and all(s in run for s in ("SHA256SUMS.sha256", "-c SHA256SUMS", "find . -mindepth 1"))
    ):
        errors.append("the action's third step is not the check against the build's SHA256SUMS")
    for f in steps:
        what = f.get("name") or f.get("uses")
        if {"if", "continue-on-error"} & set(f):
            errors.append(f"the action's step {what!r} has if: or continue-on-error:")
        if "${{" in str(f.get("run", "")):
            errors.append(f"the action's step {what!r} has ${{{{ in a run: script")
        if "run" in f and f.get("shell") != "bash":
            errors.append(f"the action's step {what!r} does not run in bash")
        if re.search(r"\|\||set \+e", str(f.get("run", ""))):
            errors.append(f"the action's step {what!r} swallows a failure (|| or set +e)")
    return errors


def release_binding_errors(text: str, action: str) -> list[str]:
    """Every rule that ties what the release signs to what it built (rules 1 to 18), one line per
    breach, each starting with its rule's number, on the workflow (and the local action
    `action`, the text of ASSETS_ACTION_FILE) without their comments: every reader of the
    build's files reads them through the action, which downloads them by an id it has guarded,
    checks them against the SHA-256 of SHA256SUMS the build job handed on, and acts on nothing
    else; nothing carries on past a failure; PyPI waits on publish and a pushed tag; the publish
    jobs name their environments, run setup-uv with no cache, and hold only the permissions they
    use."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    steps = {
        name: [(s, step_fields(s)) for s in workflow_steps(lines)] for name, lines in jobs.items()
    }
    errors: list[str] = []
    # Rules 1 to 3: the build job's two outputs and its printed record.
    build = steps.get("build", [])
    outputs = _job_map(jobs.get("build", []), "outputs")
    upload = next(
        (
            (i, f)
            for i, (_, f) in enumerate(build)
            if f.get("uses", "").startswith("actions/upload-artifact@")
            and f.get("with", {}).get("name") == "release-assets"
        ),
        (None, {}),
    )
    up_i, up = upload
    up_id = up.get("id")
    if not up_id or outputs.get("assets-id") != f"${{{{ steps.{up_id}.outputs.artifact-id }}}}":
        errors.append(
            "rule 1: build does not hand on its release-assets upload's artifact-id as assets-id"
        )
    m = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", outputs.get("sums-sha256", "")
    )
    sums_i = next((i for i, (_, f) in enumerate(build) if m and f.get("id") == m[1]), None)
    if (
        sums_i is None
        or up_i is None
        or sums_i > up_i
        or not re.search(
            r"(shasum -a 256|sha256sum) release-assets/SHA256SUMS", str(build[sums_i][1].get("run"))
        )
    ):
        errors.append(
            "rule 2: build does not hand on the SHA-256 of release-assets/SHA256SUMS, made before "
            "the upload, as sums-sha256"
        )
    printed = up_id and any(
        {
            f"${{{{ steps.{up_id}.outputs.artifact-id }}}}",
            f"${{{{ steps.{up_id}.outputs.artifact-digest }}}}",
        }
        <= set(f.get("env", {}).values())
        and "cat release-assets/SHA256SUMS" in str(f.get("run", ""))
        for _, f in build[(up_i or 0) + 1 :]
    )
    if not printed:
        errors.append(
            "rule 3: build does not print the artifact id, its digest and SHA256SUMS after the "
            "upload"
        )
    # Rules 4, 5 and 10: every download by one guarded id, refusing a digest mismatch; the
    # gather's records alone by the names their legs uploaded under.
    if OTHER_FETCH.search(text):
        errors.append(
            "rule 4: the workflow fetches an artifact another way (gh run download, "
            "github-script, the artifacts API)"
        )
    for name, job_steps in steps.items():
        for i, (_, f) in enumerate(job_steps):
            if not f.get("uses", "").startswith("actions/download-artifact@"):
                continue
            w = f.get("with", {})
            if name == "gather" and _record_download(w):
                continue  # by name, its digest checked: no id to guard
            ids = w.get("artifact-ids", "")
            # One id, or several joined by commas, all of one job.
            parts = [p.strip() for p in ids.split(",")] if ids else []
            matched = [NEEDS_OUTPUT.match(p) for p in parts]
            if (
                not parts
                or not all(matched)
                or len({m[1] for m in matched if m}) != 1
                or any(key in w for key in NOT_BY_ID)
            ):
                errors.append(f"rule 4: {name} downloads an artifact other than by one id alone")
            if w.get("digest-mismatch") != "error":
                errors.append(f"rule 5: {name} downloads without digest-mismatch: error")
            guards = [
                next(
                    (
                        (g_raw, g)
                        for g_raw, g in reversed(job_steps[:i])
                        for var, value in g.get("env", {}).items()
                        if value == part and _guard_tests(str(g.get("run", "")), var)
                    ),
                    None,
                )
                for part in parts
            ]
            if not parts or None in guards:
                errors.append(f"rule 10: {name} has no guard step that tests the id it downloads")
    # A guard that loops over a variable its own env does not set tests an empty string, and
    # fails every run: each name its loop lists is one its step binds.
    for name, job_steps in steps.items():
        for _, f in job_steps:
            for m in re.finditer(r"for \w+ in ([^;\n]*); do", str(f.get("run", ""))):
                for var in re.findall(r'"\$(\w+)"', m[1]):
                    if var not in f.get("env", {}):
                        errors.append(
                            f"rule 10: {name}'s guard loops over {var}, which its env does not set"
                        )
    # Rule 6: every output a job reads is one the job it needs defines.
    for name, lines in jobs.items():
        for job, output in re.findall(r"needs\.([\w-]+)\.outputs\.([\w-]+)", "\n".join(lines)):
            if job not in _needs(lines) or output not in _job_map(jobs.get(job, []), "outputs"):
                errors.append(f"rule 6: {name} reads needs.{job}.outputs.{output}, which it cannot")
    # Rules 7 to 9: every job that holds the build's files reads them through the one action,
    # with the build's id and hash, after checking this commit out; the action is that one copy.
    holders = [
        name
        for name, lines in jobs.items()
        if ASSETS_ID in "\n".join(lines)
        or {"contents: write", "id-token: write"} & (_permission_set(lines) or set())
    ]
    for name in holders:
        job_steps = [f for _, f in steps[name]]
        at = next((i for i, f in enumerate(job_steps) if f.get("uses") == ASSETS_ACTION), None)
        if at is None or job_steps[at].get("with") != ASSETS_WITH:
            errors.append(
                f"rule 7: {name} does not read the build's files through {ASSETS_ACTION} with "
                "the build's assets-id and sums-sha256"
            )
            continue
        if not any(f.get("uses", "").startswith("actions/checkout@") for f in job_steps[:at]):
            errors.append(f"rule 7: {name} runs {ASSETS_ACTION} before checking this commit out")
    errors += [f"rule 8: {e}" for e in assets_action_errors(action)]
    for name, job_steps in steps.items():
        if any(
            f.get("name") == CHECK_STEP or f.get("with", {}).get("artifact-ids") == ASSETS_ID
            for _, f in job_steps
        ):
            errors.append(f"rule 9: {name} holds a copy of the action's download or check")
    # Rule 11: values reach scripts through env:, never as expressions.
    for name, job_steps in steps.items():
        if any("${{" in str(f.get("run", "")) for _, f in job_steps):
            errors.append(f"rule 11: {name} has ${{{{ in a run: script")
    # Rules 12 to 14: environments, no cache, least privilege.
    for name, environment in ENVIRONMENTS.items():
        if _job_field(jobs.get(name, []), "environment") != environment:
            errors.append(f"rule 12: {name} does not name environment: {environment}")
    for name, job_steps in steps.items():
        for _, f in job_steps:
            if (
                f.get("uses", "").startswith("astral-sh/setup-uv@")
                and f.get("with", {}).get("enable-cache") != "false"
            ):
                errors.append(f"rule 13: {name} runs setup-uv with its cache on")
    top = re.search(r"^permissions:\s*(.*)$", text.split("\njobs:", 1)[0], re.M)
    if not top or top[1].strip() != "{}":
        errors.append("rule 14: the workflow-level permissions are not {}")
    for name, lines in jobs.items():
        if _permission_set(lines) != JOB_PERMISSIONS.get(name):
            errors.append(f"rule 14: {name}'s permissions are not its row in JOB_PERMISSIONS")
    # Rule 15: nothing may let a guard, a check or a download fail quietly or be skipped.
    for name, job_steps in steps.items():
        for _, f in job_steps:
            role = (
                f.get("uses", "").startswith("actions/download-artifact@")
                or f.get("uses") == ASSETS_ACTION
                or f.get("name") == CHECK_STEP
                or GUARD_TEST in str(f.get("run", ""))
            )
            # The one exception: the gather's guard and downloads of the records of a job the
            # plan skipped, which exist only when the plan ran that job. The gather itself is red
            # when a selected record is missing (G1), so the condition hides nothing.
            reads = str(f.get("with", {}).get("artifact-ids", "")) + " ".join(
                f.get("env", {}).values()
            )
            plan_only = (
                name == "gather"
                and f.get("if") in RECORD_IFS
                and "continue-on-error" not in f
                and (
                    _record_download(f.get("with", {})) is not None
                    or "build-shard.outputs.record-id" in reads
                )
            )
            if role and ({"if", "continue-on-error"} & set(f)) and not plan_only:
                errors.append(
                    f"rule 15: {name} has a guard, check or download step with if: or "
                    "continue-on-error:"
                )
    # Rule 16: nothing but the build's files lands in release-assets, and only the action puts
    # them there; a job that holds them downloads nothing else, so no bytes arrive after its
    # check. `path:` is read as a path, so `./release-assets` is release-assets too.
    for name, job_steps in steps.items():
        downloads = [
            f.get("with", {})
            for _, f in job_steps
            if f.get("uses", "").startswith("actions/download-artifact@")
        ]
        for w in downloads:
            path = download_path(w.get("path", ""))
            if path == "release-assets" or path.startswith("release-assets/"):
                errors.append(f"rule 16: {name} downloads into release-assets itself")
        if name in holders and name != "same-bytes" and downloads:
            errors.append(
                f"rule 16: {name} holds the build's files but downloads something else too"
            )
    # Rule 17: nothing in the release may carry on past a failure: a failed judge, verify leg or
    # check must stop what needs it.
    if re.search(r"^\s*(- )?continue-on-error:", text, re.M):
        errors.append("rule 17: the workflow has a continue-on-error:")
    # Rule 18: PyPI only after publish, and only for a pushed tag with the owner's switch on.
    pypi = jobs.get("pypi", [])
    if _job_field(pypi, "if") != PYPI_IF or "publish" not in _needs(pypi):
        errors.append(f"rule 18: pypi's if: is not {PYPI_IF!r}, or it does not need publish")
    return errors


# ---------------------------------------------------------------------------------------------
# The release judges in parallel shards

JUDGE_JOBS = {  # job -> (runner, the plan's system)
    "judge-macos": ("macos-15", "macos"),
    "judge-linux": ("ubuntu-24.04", "linux"),
    "judge-windows": ("windows-2025", "windows"),
    # The release tier's judge: judge-linux's legs over the plan's release shards, only on a run
    # that judges the release tier; the gather runs beside it when it is skipped.
    "judge-release": ("ubuntu-24.04", "release"),
}
GATHER_IF = "${{ !cancelled() && !failure() && needs.plan.outputs.judge == 'true' }}"
STATUS_FUNCTION = re.compile(r"\b(?:always|cancelled|failure|success)\(\)")
# `--shard=NAME`, never `--shard NAME`: before the plugin loads, pytest reads a bare `build` as a
# path, collects build/ instead of tests/, and never loads the plugin (the first branch dry run).
RECORD_PATH = '"$RUNNER_TEMP/record/latest.json"'
RECORD_UPLOAD_PATH = "${{ runner.temp }}/record/latest.json"
FETCH_RUN = 'uv run python tests/upstream/fetch.py --shard "$SHARD"\n'
# The leg the plan's `coverage` output names runs its shard under coverage.py; every other leg runs
# it plainly. The same text in every judge job: only a Linux leg the plan names takes the first arm.
COVERAGE_IF = (
    "contains(fromJSON(needs.plan.outputs.coverage), matrix.shard) && runner.os == 'Linux'"
)
COVERAGE_DATA = "build/coverage/.coverage"
COVERAGE_XML = "build/coverage/coverage.xml"
SHARD_PYTEST = f'pytest -p no:cacheprovider --shard="$SHARD" --progress-latest {RECORD_PATH}'
SHARD_RUN = (
    'if [ "$COVERAGE" = true ]; then\n'
    f"  uv run coverage run --data-file={COVERAGE_DATA} --source=src/wasi_python"
    f" -m {SHARD_PYTEST}\n"
    "else\n"
    f"  uv run {SHARD_PYTEST}\n"
    "fi\n"
)
COVERAGE_REPORT_RUN = f"uv run coverage xml --data-file={COVERAGE_DATA} -o {COVERAGE_XML}"
CODECOV_ACTION = "codecov/codecov-action@"
CODECOV_TOKEN = "${{ secrets.CODECOV_TOKEN }}"
SHA_RUN = (
    "uv run python -c \"import hashlib, sys; print('sha256=' + hashlib.sha256(open(sys.argv[1], "
    f'\'rb\').read()).hexdigest())" {RECORD_PATH} >> "$GITHUB_OUTPUT"\n'
)
BUILD_SHARD_RUN = (
    f"uv run pytest -p no:cacheprovider --shard=build --progress-latest {RECORD_PATH}\n"
)
RECORD_ID_OUTPUT = re.compile(
    r"needs\.(?:build(?:-shard)?\.outputs\.record-id|judge-[a-z]+\.outputs\.[\w-]+-id)\b"
)
# The job whose build tree the build shard reads: a fresh arm64 Linux build.
BUILD_SHARD_JOB = "build-shard"
# The gather's step env, exactly: the build's hashes, where the set came from, the build shard's
# record hash, the tier, and the selected pairs on a pull request into dev alone: the release pull
# request into main is judged whole.
GATHER_ENV = {
    "WASM_SHA256": "${{ needs.build.outputs.wasm-sha256 }}",
    "SET_SUMS_SHA256": "${{ needs.build.outputs.set-sums-sha256 }}",
    "SET_SOURCE": "${{ needs.build.outputs.set-source }}",  # built or reused
    "RECORD_BUILD_BUILD": f"${{{{ needs.{BUILD_SHARD_JOB}.outputs.record-sha256 }}}}",
    "TIER": "${{ needs.plan.outputs.tier }}",
    "PLAN": (
        "${{ github.event_name == 'pull_request' && github.base_ref != 'main' && "
        "needs.plan.outputs.selected || '' }}"
    ),
}


LINT_RUN = "uv run pytest -p no:cacheprovider -q tests/lint"
RULES_STEP = "The rules checks"


def lint_step_errors(text: str) -> list[str]:
    """The quick job runs lint and the rules checks unsilenced: the job has no `continue-on-error`
    and no `if:` but the acceptance push's gate, its `lint` step runs the folder, and neither step
    has either field, so a broken writing rule or rule always fails ci-status."""
    jobs = workflow_jobs(without_comments(text))
    lines = jobs.get("quick", [])
    errors = []
    if _job_field(lines, "continue-on-error") is not None:
        errors.append("quick has continue-on-error:, so its steps can be passed over")
    if _job_field(lines, "if") not in (None, QUICK_IF):
        errors.append(f"quick has if: other than {QUICK_IF}, so its steps can be passed over")
    steps = {f.get("name"): f for f in (step_fields(s) for s in workflow_steps(lines))}
    lint = steps.get("lint", {})
    if str(lint.get("run", "")).strip() != LINT_RUN:
        errors.append(f"quick has no step named lint that runs {LINT_RUN}")
    for name, label in (("lint", "lint step"), (RULES_STEP, "rules step")):
        for key in ("if", "continue-on-error"):
            if key in steps.get(name, {}):
                errors.append(f"quick's {label} has {key}:, so it can be passed over")
    if RULES_STEP not in steps:
        errors.append(f"quick has no step named {RULES_STEP}")
    return errors


def coverage_errors(text: str) -> list[str]:
    """The runner's coverage rides the judge legs the plan names: no job of its own; each judge
    job's shard step takes COVERAGE from the plan's output, then makes the report and sends it to
    Codecov under that same condition; and no other step of the workflow holds Codecov's token."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    errors = []
    if "coverage" in jobs:
        errors.append("a coverage job runs the fast tier a third time; the judge legs measure it")
    if "coverage: ${{ steps.plan.outputs.coverage }}" not in "\n".join(jobs.get("plan", [])):
        errors.append("the plan hands on no coverage output")
    for job in JUDGE_JOBS:
        js = [step_fields(s) for s in workflow_steps(jobs.get(job, []))]
        shard = next((f for f in js if f.get("run") == SHARD_RUN), {})
        if shard.get("env", {}).get("COVERAGE") != f"${{{{ {COVERAGE_IF} }}}}":
            errors.append(f"{job}'s shard step does not take COVERAGE from the plan's coverage")
        report = [
            f for f in js if f.get("if") == COVERAGE_IF and f.get("run") == COVERAGE_REPORT_RUN
        ]
        upload = [
            f
            for f in js
            if f.get("if") == COVERAGE_IF
            and f.get("uses", "").startswith(CODECOV_ACTION)
            and f.get("with", {}).get("files") == COVERAGE_XML
            and f.get("with", {}).get("token") == CODECOV_TOKEN
        ]
        if len(report) != 1 or len(upload) != 1:
            errors.append(
                f"{job} does not make the coverage report and send it, under {COVERAGE_IF}"
            )
    for job, lines in jobs.items():
        for f in (step_fields(s) for s in workflow_steps(lines)):
            holds = CODECOV_TOKEN in " ".join(str(v) for v in f.get("with", {}).values())
            holds |= CODECOV_TOKEN in " ".join(str(v) for v in f.get("env", {}).values())
            holds |= CODECOV_TOKEN in str(f.get("run", ""))
            if holds and not f.get("uses", "").startswith(CODECOV_ACTION):
                errors.append(f"{job}: a step other than Codecov's upload holds its token")
    return errors


def judge_if(system: str) -> str:
    """A judge job runs when the plan selected a shard on its system."""
    return f"needs.plan.outputs.{system} != '[]'"


def judge_matrix(system: str) -> str:
    """A judge job's legs: the plan's output for its system, generated from the shard plan."""
    return f"${{{{ fromJSON(needs.plan.outputs.{system}) }}}}"


def _judge_shape(lines: list[str], runner: str, system: str) -> str:
    """A judge job with its runner, its system and its name set aside: the four must be this text
    alike (rule 3)."""
    body = "\n".join(lines).replace(runner, "@RUNNER@")
    body = re.sub(r"name: judge the release tier \(", "name: judge (", body)
    body = body.replace(f"needs.plan.outputs.{system}", "needs.plan.outputs.@SYSTEM@")
    return body.replace(f"record-{system}-", "record-@SYSTEM@-")


def shard_id_errors(text: str, plan: dict) -> list[str]:
    """No shard of the plan is named in the workflow, its comments aside, and no matrix is a
    written list: each judge job's legs come from the decision job's outputs, generated from
    tests/release_shards.toml, so the two cannot drift. The build shard alone is run by name, in
    build-shard, the job that has its build tree."""
    body = without_comments(text)
    tokens = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9]", body))
    errors = [f"the workflow names the shard {n}" for n in plan if n != "build" and n in tokens]
    for line in body.splitlines():
        if re.fullmatch(r"\s+(shard|os):\s*\[.*", line):
            errors.append(f"a matrix written as a list: {line.strip()[:60]}")
    return errors


def release_shard_errors(text: str, plan: dict) -> list[str]:
    """The workflow against the shard plan, one line per breach, each starting with its rule's
    number, on the workflow without its comments."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    steps = {
        name: [(s, step_fields(s)) for s in workflow_steps(lines)] for name, lines in jobs.items()
    }
    errors: list[str] = []
    shapes = set()
    for job, (runner, system) in JUDGE_JOBS.items():
        lines = jobs.get(job)
        if lines is None:
            errors.append(f"rule 1: no job {job}")
            continue
        body = "\n".join(lines)
        if (
            _job_field(lines, "runs-on") != runner
            or _needs(lines) != {"plan", "build"}
            or _job_field(lines, "timeout-minutes") != "30"
            or _permission_set(lines) != {"contents: read"}
            or not re.search(r"^      fail-fast: false\s*$", body, re.M)
            or _job_field(lines, "continue-on-error") is not None
        ):
            errors.append(
                f"rule 1: {job} is not on {runner}, needing plan and build, 30 minutes, contents: "
                "read, fail-fast: false, with no continue-on-error:"
            )
        if _job_field(lines, "if") != judge_if(system):
            errors.append(f"rule 11: {job}'s if: is not exactly {judge_if(system)}")
        matrix = [ln.strip() for ln in lines if re.fullmatch(r"\s+shard:.*", ln)]
        if matrix != [f"shard: {judge_matrix(system)}"]:
            errors.append(f"rule 2: {job}'s matrix is not the plan's {system} shards")
        shapes.add(_judge_shape(lines, runner, system))
        js = [f for _, f in steps[job]]
        at = {}
        for i, f in enumerate(js):
            run = f.get("run")
            if f.get("uses") == ASSETS_ACTION:
                at.setdefault("assets", i)
            if run == FETCH_RUN and f.get("env", {}).get("SHARD") == "${{ matrix.shard }}":
                at.setdefault("fetch", i)
            if run == SHARD_RUN and f.get("env", {}).get("SHARD") == "${{ matrix.shard }}":
                at.setdefault("shard", i)
            w = f.get("with", {})
            if (
                f.get("id") == "record"
                and f.get("uses", "").startswith("actions/upload-artifact@")
                and w.get("name") == f"record-{system}-${{{{ matrix.shard }}}}"
                and w.get("path") == RECORD_UPLOAD_PATH
                and w.get("if-no-files-found") == "error"
            ):
                at.setdefault("record", i)
        order = ["assets", "fetch", "shard", "record"]
        if any(k not in at for k in order) or [at[k] for k in order] != sorted(
            at[k] for k in order
        ):
            missing = [k for k in order if k not in at]
            errors.append(
                f"rule 4: {job} does not run the build's files, fetch, shard and record in "
                f"order, with their fixed texts (missing or other: {missing or 'the order'})"
            )
        if re.search(r"\|\||set \+e", "\n".join(str(f.get("run", "")) for f in js)):
            errors.append(f"rule 4: a step of {job} swallows a failure (|| or set +e)")
        if _job_map(lines, "outputs"):
            errors.append(f"rule 5: {job} hands on outputs; its records are found by their names")
    if len(shapes) > 1:
        errors.append("rule 3: the four judge jobs differ beyond their runner, system and name")
    # Rule 5: a record's name binds it to its leg, so only that leg uploads under it: judge-<s>
    # under record-<s>-<its shard>, build-shard under record-build-build, nothing else under a
    # record- name, and nothing overwrites an artifact.
    for job, job_steps in steps.items():
        for _, f in job_steps:
            if not f.get("uses", "").startswith("actions/upload-artifact@"):
                continue
            w = f.get("with", {})
            name = str(w.get("name", ""))
            if "overwrite" in w:
                errors.append(f"rule 5: {job} uploads with overwrite:")
            if not name.startswith("record-"):
                continue
            mine = (
                job in JUDGE_JOBS and name == f"record-{JUDGE_JOBS[job][1]}-${{{{ matrix.shard }}}}"
            ) or (job == BUILD_SHARD_JOB and name == "record-build-build")
            if not mine:
                errors.append(f"rule 5: {job} uploads {name}, a name that is not its own record's")
    # Rule 6: build-shard judges the build shard on its own build and hands on its record; the
    # build job hands on python.wasm's hash and runs no other pytest: a reused set has no tree.
    build = [f for _, f in steps.get("build", [])]
    outputs = _job_map(jobs.get("build", []), "outputs")
    runs = [str(f.get("run", "")).strip() for f in build]
    shard_steps = [f for _, f in steps.get(BUILD_SHARD_JOB, [])]
    shard_outputs = _job_map(jobs.get(BUILD_SHARD_JOB, []), "outputs")
    shard_runs = [str(f.get("run", "")).strip() for f in shard_steps]
    upload_at = next(
        (
            i
            for i, f in enumerate(build)
            if f.get("uses", "").startswith("actions/upload-artifact@")
            and f.get("with", {}).get("name") == "release-assets"
        ),
        None,
    )
    wasm = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", outputs.get("wasm-sha256", "")
    )
    wasm_at = next((i for i, f in enumerate(build) if wasm and f.get("id") == wasm[1]), None)
    rec = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.artifact-id \}\}", shard_outputs.get("record-id", "")
    )
    rec_step = next((f for f in shard_steps if rec and f.get("id") == rec[1]), {})
    sha = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", shard_outputs.get("record-sha256", "")
    )
    sha_step = next((f for f in shard_steps if sha and f.get("id") == sha[1]), {})
    # The set's own SHA256SUMS, hashed before the upload, as python.wasm is.
    set_sums = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", outputs.get("set-sums-sha256", "")
    )
    set_sums_at = next(
        (i for i, f in enumerate(build) if set_sums and f.get("id") == set_sums[1]), None
    )

    def other_pytest(rs: list[str], shard_ok: bool) -> list[str]:
        return [
            r
            for r in rs
            if "uv run pytest" in r
            and not (shard_ok and r == BUILD_SHARD_RUN.strip())
            and "-k test_source_tree_matches_its_tarball" not in r
        ]

    if (
        other_pytest(runs, False)
        or wasm_at is None
        or upload_at is None
        or wasm_at > upload_at
        or not re.search(r"(shasum -a 256|sha256sum) build/artifacts/python\.wasm", runs[wasm_at])
        or "record-id" in outputs
        or "record-sha256" in outputs
    ):
        errors.append(
            "rule 6: build runs a pytest other than the zero-patch step, hands on a record, or "
            "does not hand on python.wasm's SHA-256 made before the upload (wasm-sha256)"
        )
    if (
        BUILD_SHARD_RUN.strip() not in shard_runs
        or other_pytest(shard_runs, True)
        or rec_step.get("with", {}).get("path") != RECORD_UPLOAD_PATH
        or str(sha_step.get("run", "")).strip() != SHA_RUN.strip()
    ):
        errors.append(
            f"rule 6: {BUILD_SHARD_JOB} does not run the build shard alone and hand on its record "
            "(record-id, record-sha256)"
        )
    if (
        set_sums_at is None
        or upload_at is None
        or set_sums_at > upload_at
        or not re.search(
            r"(shasum -a 256|sha256sum) build/artifacts/SHA256SUMS\b", runs[set_sums_at]
        )
    ):
        errors.append(
            "rule 6: build does not hand on the set's own SHA256SUMS' SHA-256, made before the "
            "upload (set-sums-sha256)"
        )
    # Rule 7: the gather holds no assets, downloads every record by its job, and runs gather.py.
    gather = jobs.get("gather")
    if gather is None:
        errors.append("rule 7: no job gather")
    else:
        gs = [f for _, f in steps["gather"]]
        if (
            _job_field(gather, "runs-on") != "ubuntu-24.04"
            or _job_field(gather, "timeout-minutes") != "15"
            or _permission_set(gather) != {"contents: read"}
            or not {"plan", "build", BUILD_SHARD_JOB, "same-bytes", *JUDGE_JOBS} <= _needs(gather)
            or _job_field(gather, "continue-on-error") is not None
        ):
            errors.append(
                "rule 7: gather is not on ubuntu-24.04, 15 minutes, contents: read, needing "
                "plan, build, build-shard, same-bytes and the four judge jobs, with no "
                "continue-on-error:"
            )
        if _job_field(gather, "if") != GATHER_IF:
            errors.append(
                f"rule 11: gather's if: is not exactly {GATHER_IF}: it must run beside a skipped "
                "judge job, never after a failed or cancelled need, and only when the plan judges"
            )
        downloads = [
            (f.get("if"), f.get("with", {}))
            for f in gs
            if f.get("uses", "").startswith("actions/download-artifact@")
        ]
        want = [
            (
                "needs.plan.outputs.build == 'true'",
                {
                    "artifact-ids": f"${{{{ needs.{BUILD_SHARD_JOB}.outputs.record-id }}}}",
                    "path": f"records/{BUILD_SHARD_JOB}",
                    "digest-mismatch": "error",
                },
            ),
            *(
                (
                    judge_if(system),
                    {
                        "pattern": f"record-{system}-*",
                        "path": f"records/{job}",
                        "digest-mismatch": "error",
                    },
                )
                for job, (_, system) in JUDGE_JOBS.items()
            ),
        ]
        if downloads != want:
            errors.append(
                "rule 7: gather does not download exactly every record, the build shard's by id "
                "into records/build-shard and each judge job's by name into records/<job>, each "
                "when the plan ran it, and nothing else (never release-assets)"
            )
        step = next((f for f in gs if "tests/harness/gather.py" in str(f.get("run", ""))), {})
        if not step or step.get("env", {}) != GATHER_ENV:
            errors.append(
                "rule 7: gather's step does not run tests/harness/gather.py with exactly "
                "WASM_SHA256, SET_SUMS_SHA256, SET_SOURCE, RECORD_BUILD_BUILD, TIER and PLAN "
                "bound in env:"
            )
        # The build shard's record id is guarded only when the plan ran it.
        for f in gs:
            reads = " ".join(f.get("env", {}).values())
            if (
                "build-shard.outputs.record-id" in reads
                and GUARD_TEST in str(f.get("run", ""))
                and f.get("if") != "needs.plan.outputs.build == 'true'"
            ):
                errors.append("rule 11: gather guards build-shard's record id on another if:")
    # Rule 12: past the gather, a job a branch run reaches needs a status function in its if:,
    # or a skipped judge job would skip it too.
    for job, lines in jobs.items():
        if "gather" not in _needs(lines):
            continue
        cond = _job_field(lines, "if") or ""
        if cond != TAG_ONLY and not STATUS_FUNCTION.search(cond):
            errors.append(
                f"rule 12: {job} needs gather, runs on a branch run, and its if: has no status "
                "function"
            )
    # Rule 8: attest and publish need the gather; only the gather reads a record id.
    for job in ("attest", "publish"):
        if "gather" not in _needs(jobs.get(job, [])):
            errors.append(f"rule 8: {job} does not need gather")
    for job, lines in jobs.items():
        if job != "gather" and RECORD_ID_OUTPUT.search("\n".join(lines)):
            errors.append(f"rule 8: {job} reads a record id")
    # Rule 9: verify runs no pytest.
    if "pytest" in "\n".join(str(f.get("run", "")) for _, f in steps.get("verify", [])):
        errors.append("rule 9: verify runs pytest")
    # Rule 10: only build sets wasm-sha256 and set-sums-sha256, and only the gather
    # reads them.
    for job, lines in jobs.items():
        body = "\n".join(lines)
        for name in ("wasm-sha256", "set-sums-sha256"):
            if job != "gather" and f"needs.build.outputs.{name}" in body:
                errors.append(f"rule 10: {job} reads {name}")
            if job != "build" and re.search(rf"^      {name}:", body, re.M):
                errors.append(f"rule 10: {job} sets {name}")
    # Rule 13: no shard is written in the workflow.
    errors += [f"rule 13: {e}" for e in shard_id_errors(text, plan)]
    return errors


# ---------------------------------------------------------------------------------------------
# The decision job, the one required check, and what a pull request checks out

HEAD_REF = "${{ github.event.pull_request.head.sha || github.sha }}"
# The jobs that need no gate of the plan's: the plan itself, quick (every run), the one required
# check, and the three that only a pushed tag reaches.
UNGATED = ("plan", "quick", "ci-status", "attest", "publish", "pypi")
CI_STATUS_ENV = {
    "NEEDS": "${{ toJSON(needs) }}",
    "REFUSALS": "${{ needs.plan.outputs.refusals }}",
}
CONCURRENCY = (
    "concurrency:\n"
    "  group: ${{ github.event_name == 'pull_request' && format('pr-{0}', "
    "github.event.pull_request.number) || format('release-{0}-{1}', github.event_name, "
    "github.ref) }}\n"
    "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n"
)


def checkout_ref_errors(text: str) -> list[str]:
    """Every checkout in the workflow names the head commit: a pull request's is its head, never
    the merge ref, which is a merge commit nobody will merge and the history rules refuse."""
    errors = []
    for job, lines in workflow_jobs(without_comments(text)).items():
        for step in workflow_steps(lines):
            f = step_fields(step)
            if f.get("uses", "").startswith("actions/checkout@") and (
                f.get("with", {}).get("ref") != HEAD_REF
            ):
                errors.append(f"{job} checks out another ref than {HEAD_REF}")
    return errors


def ci_status_errors(text: str) -> list[str]:
    """The one required check and the gates it rests on: no workflow-level paths: filter (a
    filtered run leaves the check pending); ci-status, named so, runs always(), needs every other
    job and fails unless each succeeded or was skipped and the plan refused nothing; every job
    but the plan, quick, ci-status and the tag's three needs the plan and gates on its outputs;
    a pull request's run cancels its older one, and nothing else is cancelled."""
    errors = []
    body = without_comments(text)
    head = body.split("\njobs:", 1)[0]
    if re.search(r"^\s+paths(-ignore)?:", head, re.M):
        errors.append("the workflow has a paths: filter on a trigger")
    for want in (
        "  pull_request:\n    branches: [dev, main]\n",
        '  push:\n    branches: [dev]\n    tags: ["v*"]\n',
        "  schedule:\n",
        "  workflow_dispatch:\n",
    ):
        if want not in head:
            errors.append(f"the workflow's triggers lack {want.strip().splitlines()[0]}")
    if CONCURRENCY not in head:
        errors.append("the concurrency is not one group per pull request, cancelling only there")
    jobs = workflow_jobs(body)
    ci = jobs.get("ci-status")
    if ci is None:
        return [*errors, "no ci-status job"]
    if _job_field(ci, "name") != "ci-status" or _job_field(ci, "if") != "always()":
        errors.append("ci-status is not named ci-status, or its if: is not always()")
    if _needs(ci) != set(jobs) - {"ci-status"}:
        errors.append(f"ci-status does not need every other job: {sorted(set(jobs) - _needs(ci))}")
    if _permission_set(ci) != set():
        errors.append("ci-status's permissions are not {}")
    js = [step_fields(s) for s in workflow_steps(ci)]
    run = str(js[0].get("run", "")) if len(js) == 1 else ""
    if (
        len(js) != 1
        or js[0].get("env") != CI_STATUS_ENV
        or 'n.get("result") not in ("success", "skipped")' not in run
        or 'os.environ.get("REFUSALS") != "[]"' not in run
    ):
        errors.append(
            "ci-status's one step does not fail on a need neither successful nor skipped, or on "
            "a refusal of the plan"
        )
    for job, lines in jobs.items():
        if job in UNGATED:
            continue
        if "plan" not in _needs(lines) or "needs.plan.outputs." not in (
            _job_field(lines, "if") or ""
        ):
            errors.append(f"{job} does not need the plan and gate on its outputs with if:")
    return errors


# The accept jobs. accept-record needs every job a merge's run judges with (ci-status, the push
# and the tag's three aside), so it runs only when each of them is green.
ACCEPT_RECORD_IF = (
    "${{ !cancelled() && !failure() && needs.plan.outputs.accept == 'true' "
    "&& needs.gather.result == 'success' }}"
)
# accept-push on a push alone: after the release pull request, whose run is on the pull request's
# merge ref and reads the pull request's own workflow file, accept-release.yml pushes instead.
ACCEPT_PUSH_IF = (
    "${{ !cancelled() && needs.plan.outputs.accept == 'true' && github.event_name == 'push' "
    "&& needs.accept-record.result == 'success' }}"
)
NOT_JUDGED_WITH = {"accept-record", "accept-push", "ci-status", "weekly-issue", *UNGATED[3:]}
ACCEPT_RUN = (
    "uv run pytest -p no:cacheprovider --accept-from=build/ci/record.json --claims=context/changes/"
)
DEPLOY_KEY = "ACCEPT_DEPLOY_KEY"
# A push of the accepted state alone runs the plan and nothing that judges it.
QUICK_IF = "needs.plan.outputs.acceptance != 'true'"
SKIP_WORDS = ("[skip ci]", "[ci skip]", "[no ci]", "[skip actions]", "[actions skip]")
SSH_KEY = "${{ secrets.ACCEPT_DEPLOY_KEY }}"
# What accept-push's script must do, in this order, each in its own words: hold the change to the
# two files alone, check dev's tip, commit them alone by the acceptance's pathspec, push.
ACCEPT_PUSH_WORDS = (
    "git status --porcelain --untracked-files=all",
    "tip=$(git ls-remote origin refs/heads/dev | cut -f1)",
    'if [ "$tip" != "$GITHUB_SHA" ]; then',
    "git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'",
    "-- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'",
    "git push origin HEAD:refs/heads/dev",
)
# A program of the repository, or an interpreter that could run one.
REPO_CODE = re.compile(
    r"\buv\b|\bpython|\bpytest\b|\bnode\b|(^|\s)\./|\b(scripts|release|tests|src)/"
)


def accept_job_errors(text: str, others: dict[str, str] | None = None) -> list[str]:
    """The two accept jobs after a merge into dev: accept-record, after every job the run judges
    with and only when each is green, with contents: read, no environment and no secret, downloads
    the gather's record and runs --accept-from on it; accept-push, after it alone, is the one job
    in the accept environment, checks out with the deploy key, uses only checkout and the
    download, runs no code of the repository, and commits the two progress files alone onto the
    commit judged and pushes only while dev is that commit. No other job, and no other workflow
    (`others`, name -> text), names the key."""
    body = without_comments(text)
    jobs = workflow_jobs(body)
    errors = []
    record, push = jobs.get("accept-record"), jobs.get("accept-push")
    if record is None or push is None:
        return ["the workflow has no accept-record or no accept-push job"]
    want = set(jobs) - NOT_JUDGED_WITH
    if _needs(record) != want:
        errors.append(f"accept-record does not need every job the run judges with: {sorted(want)}")
    if _job_field(record, "if") != ACCEPT_RECORD_IF:
        errors.append(f"accept-record's if: is not {ACCEPT_RECORD_IF}")
    if _job_field(record, "environment") is not None:
        errors.append("accept-record names an environment; it holds no secret")
    record_steps = [step_fields(st) for st in workflow_steps(record)]
    if not any(f.get("run", "").strip() == ACCEPT_RUN for f in record_steps):
        errors.append(f"accept-record does not run {ACCEPT_RUN}")
    if _needs(push) != {"plan", "accept-record"}:
        errors.append("accept-push does not need the plan and accept-record alone")
    if _job_field(push, "if") != ACCEPT_PUSH_IF:
        errors.append(f"accept-push's if: is not {ACCEPT_PUSH_IF}")
    if _job_field(push, "environment") != "accept":
        errors.append("accept-push does not name environment: accept")
    push_steps = [step_fields(st) for st in workflow_steps(push)]
    for f in push_steps:
        uses = f.get("uses", "")
        if uses and not uses.startswith(("actions/checkout@", "actions/download-artifact@")):
            errors.append(f"accept-push uses {uses}: only the checkout and the download")
        if REPO_CODE.search(str(f.get("run", ""))):
            errors.append("accept-push runs code of the repository or an interpreter")
    checkouts = [f for f in push_steps if f.get("uses", "").startswith("actions/checkout@")]
    if len(checkouts) != 1 or checkouts[0].get("with", {}).get("ssh-key") != SSH_KEY:
        errors.append("accept-push does not check out with the deploy key, once")
    script = "\n".join(str(f.get("run", "")) for f in push_steps)
    at = 0  # each in its order: the checks come before the commit and the push
    for words in ACCEPT_PUSH_WORDS:
        found = script.find(words, at)
        if found < 0:
            errors.append(f"accept-push does not check or do, in its order: {words}")
        else:
            at = found + len(words)
    for name, lines in jobs.items():
        if name != "accept-push" and _job_field(lines, "environment") == "accept":
            errors.append(f"{name} names the accept environment, which only accept-push may")
        if name != "accept-push" and DEPLOY_KEY in "\n".join(lines):
            errors.append(f"the secret {DEPLOY_KEY} is named outside accept-push, in {name}")
    if "secrets." in "\n".join(record):
        errors.append("accept-record names a secret")
    quick = jobs.get("quick", [])
    if "plan" not in _needs(quick) or _job_field(quick, "if") != QUICK_IF:
        errors.append(f"quick does not need the plan and run on {QUICK_IF}")
    if any(word in "\n".join(push).lower() for word in SKIP_WORDS):
        errors.append("accept-push names a skip word, which would skip a release pull request")
    for name, other in sorted((others or {}).items()):
        if name == ACCEPT_RELEASE_FILE:  # its own shape is accept_release_errors'
            continue
        if DEPLOY_KEY in other or "environment: accept" in without_comments(other):
            errors.append(f"the secret {DEPLOY_KEY} or the accept environment is named in {name}")
    return errors


# The release pull request's acceptance onto dev, pushed by a workflow its completion runs on
# dev's own context: the one holder of the deploy key beside accept-push.
ACCEPT_RELEASE_FILE = "accept-release.yml"
ACCEPT_RELEASE_ON = "on:\n  workflow_run:\n    workflows: [release]\n    types: [completed]\n"
ACCEPT_RELEASE_IF = (
    "${{ github.event.workflow_run.event == 'pull_request' "
    "&& github.event.workflow_run.conclusion == 'success' "
    "&& github.event.workflow_run.head_branch == 'dev' "
    "&& github.event.workflow_run.head_repository.full_name == github.repository "
    "&& github.event.workflow_run.pull_requests[0].base.ref == 'main' }}"
)
ACCEPT_RELEASE_REF = "${{ github.event.workflow_run.head_sha }}"
# What its script must do, in this order: hold the change to the two files alone, check that
# dev's tip is the head the run judged and fail when it is not, commit them alone, push.
ACCEPT_RELEASE_WORDS = (
    "git status --porcelain --untracked-files=all",
    "tip=$(git ls-remote origin refs/heads/dev | cut -f1)",
    'if [ "$tip" != "$JUDGED" ]; then',
    "exit 1",
    "git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'",
    "-- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'",
    "git push origin HEAD:refs/heads/dev",
)


def accept_release_errors(text: str) -> list[str]:
    """accept-release.yml: run by the completion of the release workflow alone, with no
    permission at the top; one job, gated on a green run of a pull request from dev into main of
    this repository, in the accept environment with contents: read and actions: read, using only
    the checkout and the download, running no code of the repository (gh to find the artifact,
    git to push), checking the head the run judged out with the deploy key, once; its script holds
    the change to the two progress files and pushes only while dev's tip is that head, and is red
    when it is not."""
    body = without_comments(text)
    head = body.split("\njobs:", 1)[0]
    errors = []
    if ACCEPT_RELEASE_ON not in head:
        errors.append("the release acceptance does not run on the release workflow's completion")
    if "permissions: {}\n" not in head:
        errors.append("the release acceptance's top-level permissions are not {}")
    jobs = workflow_jobs(body)
    if set(jobs) != {"accept-release"}:
        return [
            *errors,
            f"the release acceptance's jobs are not accept-release alone: {sorted(jobs)}",
        ]
    job = jobs["accept-release"]
    if _job_field(job, "if") != ACCEPT_RELEASE_IF:
        errors.append(f"accept-release's if: is not {ACCEPT_RELEASE_IF}")
    if _job_field(job, "environment") != "accept":
        errors.append("accept-release does not name environment: accept")
    if _permission_set(job) != {"contents: read", "actions: read"}:
        errors.append("accept-release's permissions are not contents: read and actions: read")
    steps = [step_fields(st) for st in workflow_steps(job)]
    for f in steps:
        uses = f.get("uses", "")
        if uses and not uses.startswith(("actions/checkout@", "actions/download-artifact@")):
            errors.append(f"accept-release uses {uses}: only the checkout and the download")
        if REPO_CODE.search(str(f.get("run", ""))):
            errors.append("accept-release runs code of the repository or an interpreter")
    checkouts = [f for f in steps if f.get("uses", "").startswith("actions/checkout@")]
    with_ = checkouts[0].get("with", {}) if len(checkouts) == 1 else {}
    if with_.get("ssh-key") != SSH_KEY or with_.get("ref") != ACCEPT_RELEASE_REF:
        errors.append(
            "accept-release does not check out the head the run judged with the deploy key, once"
        )
    script = "\n".join(str(f.get("run", "")) for f in steps)
    at = 0
    for words in ACCEPT_RELEASE_WORDS:
        found = script.find(words, at)
        if found < 0:
            errors.append(f"accept-release does not check or do, in its order: {words}")
        else:
            at = found + len(words)
    mismatch = script.split('if [ "$tip" != "$JUDGED" ]; then', 1)[-1].split("fi", 1)[0]
    if "exit 0" in mismatch:
        errors.append("accept-release succeeds when dev is not the head judged")
    return errors


WEEKLY_IF = (
    "${{ always() && needs.plan.outputs.weekly == 'true' && (contains(needs.*.result, 'failure') "
    "|| contains(needs.*.result, 'cancelled')) }}"
)
WEEKLY_INPUT = (
    "      weekly:\n        description: the weekly run's shape (the release tier, the rebuilds, "
    "an issue when red), dispatched on dev\n        type: boolean\n        default: false\n"
)


def weekly_errors(text: str) -> list[str]:
    """The weekly run: a schedule and a dispatch input that select its shape; one job, with
    issues: write and nothing else, that opens or updates an issue when a job the run judges with
    failed or was cancelled, and never on another run; the accept jobs never follow it (they run on
    the plan's accept output alone, which the weekly shape never sets)."""
    body = without_comments(text)
    head = body.split("\njobs:", 1)[0]
    errors = []
    if '  schedule:\n    - cron: "0 6 * * 1"' not in head:
        errors.append("the workflow has no weekly schedule (cron 0 6 * * 1)")
    if WEEKLY_INPUT not in head:
        errors.append("workflow_dispatch has no weekly input")
    jobs = workflow_jobs(body)
    job = jobs.get("weekly-issue")
    if job is None:
        return [*errors, "no weekly-issue job"]
    if _job_field(job, "if") != WEEKLY_IF:
        errors.append(f"weekly-issue's if: is not {WEEKLY_IF}")
    want = set(jobs) - NOT_JUDGED_WITH
    if _needs(job) != want:
        errors.append(f"weekly-issue does not need every job the run judges with: {sorted(want)}")
    if _permission_set(job) != {"issues: write"}:
        errors.append("weekly-issue's permissions are not issues: write alone")
    script = "\n".join(str(step_fields(st).get("run", "")) for st in workflow_steps(job))
    if "gh issue comment" not in script or "gh issue create" not in script:
        errors.append("weekly-issue does not comment on the open issue or create one")
    for name in ("accept-record", "accept-push"):
        if "needs.plan.outputs.accept == 'true'" not in (
            _job_field(jobs.get(name, []), "if") or ""
        ):
            errors.append(f"{name} does not run on the plan's accept output alone")
    return errors


# A job's if:, as GitHub reads it, rewritten into a Python expression over these names alone.
_EXPR_FUNCTIONS = {
    "startsWith": lambda a, b: str(a).lower().startswith(str(b).lower()),
    "contains": lambda a, b: (b in a) if isinstance(a, list) else str(b).lower() in str(a).lower(),
}


def _evaluate(cond: str, outputs: dict[str, str], context: dict[str, str], ran: dict) -> bool:
    """One job's if: under the plan's outputs, the event's github context and which of its needs
    ran (each succeeded) or were skipped; nothing fails or is cancelled in the run it models."""
    expr = cond.strip()
    if expr.startswith("${{") and expr.endswith("}}"):
        expr = expr[3:-2].strip()
    results = ["success" if r else "skipped" for r in ran.values()]
    subs = [
        (r"needs\.\*\.result", "RESULTS"),
        (r"needs\.plan\.outputs\.([\w-]+)", lambda m: repr(outputs.get(m[1], ""))),
        (r"needs\.([\w-]+)\.result", lambda m: repr("success" if ran.get(m[1]) else "skipped")),
        (r"needs\.[\w-]+\.outputs\.[\w-]+", "''"),
        (r"github\.([\w.]+)", lambda m: repr(context.get(m[1], ""))),
        (r"(?:vars|inputs|secrets)\.[\w-]+", "''"),
        (r"\balways\(\)", "True"),
        (r"\b(?:cancelled|failure)\(\)", "False"),
        (r"\bsuccess\(\)", repr(all(ran.values()))),
        (r"&&", " and "),
        (r"\|\|", " or "),
        (r"!(?!=)", " not "),
    ]
    for pattern, repl in subs:
        expr = re.sub(pattern, repl, expr)
    try:
        return bool(eval(expr, {"__builtins__": {}, **_EXPR_FUNCTIONS, "RESULTS": results}))  # noqa: S307
    except Exception as e:  # an expression this reader does not model
        raise ValueError(f"cannot evaluate the if: {cond!r} ({e})") from None


def jobs_that_run(text: str, outputs: dict[str, str], context: dict[str, str]) -> set[str]:
    """The jobs a run starts, given the decision job's outputs and the event (`context`, the
    github context's fields: event_name, ref, ref_type, base_ref): a job without an if: runs when
    every need ran; one whose if: names no status function needs that too; one that names one
    (always(), !cancelled()) runs on its if: alone. Every job that runs is taken to succeed."""
    jobs = workflow_jobs(without_comments(text))
    ran: dict[str, bool] = {}

    def visit(name: str) -> bool:
        if name not in ran:
            ran[name] = False  # a cycle runs nothing
            lines = jobs[name]
            needs = sorted(_needs(lines) & set(jobs))
            for n in needs:
                visit(n)
            done = {n: ran[n] for n in needs}
            cond = _job_field(lines, "if")
            if cond is None:
                ran[name] = all(done.values())
            else:
                value = _evaluate(cond, outputs, context, done)
                ran[name] = value if STATUS_FUNCTION.search(cond) else value and all(done.values())
        return ran[name]

    return {name for name in jobs if visit(name)}


RELEASE_VERSION_STEP = "The version, and the tag it is released under, agree"
# On a pull request into main, in this order: the branch, the dated section, the free tag, and
# main's tip in the head's history.
RELEASE_VERSION_WORDS = (
    'elif [ "$GITHUB_BASE_REF" = main ]; then',
    'uv run python release/version.py check --tag "v$version"',
    'if git rev-parse -q --verify "refs/tags/v$version" > /dev/null; then',
    "exit 1",
    "git merge-base --is-ancestor origin/main HEAD",
)


def release_version_errors(text: str) -> list[str]:
    """The build job's version step holds, on the release pull request, what the tag's run and
    the owner's push to main will: the version's section dated, its tag free, and main's tip an
    ancestor of the head."""
    try:
        script = workflow_step_script(without_comments(text), "build", RELEASE_VERSION_STEP)
    except LookupError as e:
        return [str(e)]
    errors, at = [], 0
    for words in RELEASE_VERSION_WORDS:
        found = script.find(words, at)
        if found < 0:
            errors.append(f"build's version step does not check, in its order: {words}")
        else:
            at = found + len(words)
    return errors


def action_pin_errors(text: str) -> list[str]:
    """Every `uses:` is a local action or `owner/repo[/path]@<40 hex>`."""
    errors = []
    for m in re.finditer(r"^\s*(?:- )?uses:\s*(\S+)", without_comments(text), re.M):
        ref = m[1]
        if not (ref.startswith("./") or re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref)):
            errors.append(f"{ref}: not pinned by a full commit")
    return errors


def unpinned_fetch_errors(download_script: Path, pinned: Iterable[str]) -> list[str]:
    """Every file a `get` or `research` line fetches is pinned in SHA256SUMS:
    the name given, or else the URL's last part."""
    pinned = set(pinned)
    text = "\n".join(line for _, line in _code_lines(download_script))
    names = [name or url.rstrip("/").rsplit("/", 1)[-1] for url, name in GET.findall(text)]
    return [
        f"{name}: fetched, but not pinned in downloads/SHA256SUMS"
        for name in names
        if name not in pinned
    ]


TESTS_LINE = re.compile(r"^\s*tests\s+(https?://\S+)\s+(\S+)", re.M)


def test_source_errors(download_script: Path, pinned: Iterable[str]) -> list[str]:
    """Every `tests` line (a test source, never built) has its pin, and every pinned test source
    its `tests` line; each name is one source pattern's, so no pin is two sources; a forge's
    archive (a release tag's, or a commit's) is named `-tag.tar.gz`, so no pattern meets an sdist
    by mistake."""
    from harness import needs, pins

    pinned = set(pinned)
    text = "\n".join(line for _, line in _code_lines(download_script))
    lines = TESTS_LINE.findall(text)
    named = {name for _, name in lines}
    errors = [
        f"{n}: a tests line, but not pinned in downloads/SHA256SUMS" for n in sorted(named - pinned)
    ]
    test_patterns = {c: pins.SOURCE_PATTERNS[c] for c in needs.TEST_SOURCES}
    for name in sorted(pinned):
        if any(p.fullmatch(name) for p in test_patterns.values()) and name not in named:
            errors.append(f"{name}: a pinned test source with no tests line")
    for url, name in lines:
        hits = [c for c, p in pins.SOURCE_PATTERNS.items() if p.fullmatch(name)]
        if len(hits) != 1:
            errors.append(f"{name}: matches {len(hits)} source patterns, not one")
        if "/archive/" in url and not name.endswith("-tag.tar.gz"):
            errors.append(f"{name}: a forge's archive, not named -tag.tar.gz")
    return errors


# ---------------------------------------------------------------------------------------------
# A module-level name bound twice: the second silently replaces the first, so checks that used
# the first run the second's code (a rebase once redefined `CTRL_C` and lost two checks).


def _bound(node: ast.stmt) -> list[str]:
    """The names a module-level statement binds: definitions, imports and assignment targets
    (tuples and starred ones included). Names bound inside `if`, `try`, `for` or `with` are not
    counted: their branches are often real alternatives (a `TYPE_CHECKING` import, a fallback)."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if any(d.endswith("overload") or d.endswith(".register") for d in decorators):
            return []  # typing's overloads and singledispatch's registrations repeat by design
        return [node.name]
    if isinstance(node, ast.ClassDef):
        return [node.name]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [(a.asname or a.name).split(".")[0] for a in node.names if a.name != "*"]
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        targets = [node.target]
    names = []
    while targets:
        t = targets.pop(0)
        if isinstance(t, ast.Name):
            names.append(t.id)
        elif isinstance(t, (ast.Tuple, ast.List)):
            targets[:0] = t.elts
        elif isinstance(t, ast.Starred):
            targets.insert(0, t.value)
    return names


def duplicate_name_hits(files: Iterable[Path], root: Path) -> list[str]:
    hits = []
    for p in files:
        if p.suffix != ".py":
            continue
        try:
            tree = ast.parse(p.read_text(), str(p))
        except (SyntaxError, UnicodeDecodeError):
            continue
        # A guest program under tests/jobs/ rebinds its working names on purpose; there only a
        # constant (an upper-case name), a function or a class bound twice is the hazard.
        guest = rel(p, root).startswith("tests/jobs/")
        seen: dict[str, int] = {}
        defined: set[str] = set()
        for node in tree.body:
            names = _bound(node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.update(names)
            for name in names:
                hazard = not guest or name.isupper() or name in defined
                if name in seen and hazard:
                    hits.append(
                        f"{rel(p, root)}:{node.lineno}: {name} (first bound at {seen[name]})"
                    )
                seen.setdefault(name, node.lineno)
    return hits


# ---------------------------------------------------------------------------------------------
# Seams are injected, not patched. A check or a unit test that replaces a private name of a
# runner module, by a fixture's `setattr` or by assignment, reaches into the runner from
# outside; the one way to set a seam is a field on the process object. The judge's child
# programs are string constants, so every string that parses as Python is walked the same way
# with its own imports, and one that does not is read by a regular expression. `tools`, `cli`
# and the package itself are outside the rule; a class attribute or an attribute of a call's
# result is never a module.
#
# The tool protocol's two private modules stand outside it with `tools`, in both forms: the
# names the judge patches there are bounds it lowers to reach a limit and functions it wraps to
# count their calls, not the process's state, which is what the rule is about. They are named
# one by one, so a later module of the protocol joins them by hand, with its reason.
NOT_TOOL_MODULE = r"(?!(?:_tool_schema|_tool_host)\b)"
RUNNER_MODULE = re.compile(rf"^wasi_python\.(runner|mounts|{NOT_TOOL_MODULE}_\w+)$")
SEAM_IN_TEXT = re.compile(
    r"""\b\w+\.setattr\(\s*([\w.]+)\s*,\s*["'](_\w+)["']|\b([\w.]+)\.(_\w+)\s*=[^=]"""
)
SEAM_BY_PATH = re.compile(rf"^(wasi_python\.(?:runner|mounts|{NOT_TOOL_MODULE}_\w+))\.(_\w+)$")


def _runner_names(tree: ast.AST) -> dict[str, str]:
    """Local name -> the runner module the tree's imports bind it to."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if RUNNER_MODULE.match(a.name):
                    names[a.asname or a.name] = a.name
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("wasi_python"):
            for a in node.names:
                full = f"{node.module}.{a.name}"
                if RUNNER_MODULE.match(full):
                    names[a.asname or a.name] = full
    return names


def _dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None  # a call, a subscript, a literal: never a module


def _runner_module(text: str | None, names: dict[str, str]) -> str | None:
    """The short name of the runner module `text` names, through the imports or by its path."""
    if text is None:
        return None
    full = names.get(text) or (text if RUNNER_MODULE.match(text) else None)
    return full.rsplit(".", 1)[-1] if full else None


def _assigned(node: ast.Assign) -> list[ast.expr]:
    """Every target of an assignment, tuples and starred ones flattened."""
    out: list[ast.expr] = []
    todo = list(node.targets)
    while todo:
        t = todo.pop(0)
        if isinstance(t, (ast.Tuple, ast.List)):
            todo[:0] = t.elts
        elif isinstance(t, ast.Starred):
            todo.insert(0, t.value)
        else:
            out.append(t)
    return out


def _seam_sites(tree: ast.AST, names: dict[str, str], base: int) -> list[tuple[int, str, str]]:
    """(line, module, name) for every patch of a private runner name under `tree`, in code and
    inside its string constants; `base` is the file line of a tree parsed from a string."""
    sites: list[tuple[int, str, str]] = []
    todo: list[ast.AST] = [tree]
    while todo:
        node = todo.pop()
        line = base + getattr(node, "lineno", 1) - 1
        if isinstance(node, ast.JoinedStr):  # an f-string: its pieces read as one text
            text = "".join(v.value if isinstance(v, ast.Constant) else "0" for v in node.values)
            sites += _seam_sites_in_text(text, names, line)
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "_" in node.value:
            sites += _seam_sites_in_text(node.value, names, line)
        elif isinstance(node, ast.Call) and len(node.args) >= 2:
            func, target, name = node.func, node.args[0], node.args[1]
            if isinstance(func, ast.Attribute) and func.attr == "setattr":
                if isinstance(target, ast.Constant) and isinstance(target.value, str):
                    by_path = SEAM_BY_PATH.match(target.value)  # setattr("pkg.mod._name", …)
                    if by_path:
                        sites.append((line, by_path[1].rsplit(".", 1)[-1], by_path[2]))
                elif isinstance(name, ast.Constant) and isinstance(name.value, str):
                    module = _runner_module(_dotted(target), names)
                    if module and name.value.startswith("_"):
                        sites.append((line, module, name.value))
        elif isinstance(node, ast.Assign):
            for t in _assigned(node):
                if isinstance(t, ast.Attribute) and t.attr.startswith("_"):
                    module = _runner_module(_dotted(t.value), names)
                    if module:
                        sites.append((line, module, t.attr))
        todo.extend(ast.iter_child_nodes(node))
    return sites


def _seam_sites_in_text(text: str, names: dict[str, str], base: int) -> list[tuple[int, str, str]]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # a string that is not a program: whatever it holds
            inner = ast.parse(text)
    except (SyntaxError, ValueError):
        sites = []
        for m in SEAM_IN_TEXT.finditer(text):
            target, name = (m[1], m[2]) if m[2] else (m[3], m[4])
            module = _runner_module(target, names)
            if module:
                sites.append((base + text.count("\n", 0, m.start()), module, name))
        return sites
    return _seam_sites(inner, {**names, **_runner_names(inner)}, base)


def seam_hits(files: Iterable[Path], root: Path, allowed: Iterable[str]) -> list[str]:
    """Every `<fixture>.setattr(<runner module>, "_name", …)` and `<runner module>._name = …` in
    the judge, in code and in the programs it runs as subprocesses, whose _name is not allowed;
    and every allowed name no file patches (a stale allowance)."""
    allowed = tuple(allowed)
    hits = []
    seen: set[str] = set()
    for p in sorted(files):
        tree = _parsed(p)
        if tree is None:
            continue
        for line, module, name in sorted(_seam_sites(tree, _runner_names(tree), 1)):
            seen.add(name)
            if name not in allowed:
                hits.append(f"{rel(p, root)}:{line}: {module}.{name}")
    return hits + [f"stale allowance: {name}" for name in allowed if name not in seen]


# ---------------------------------------------------------------------------------------------
# A function a person can read whole. Lines are what a reader scrolls, so the measure is lines,
# def to last line, and a method or a nested function counts on its own under its qualified
# name (`Class.method`, `outer.inner`).

FUNCTION_CEILING = 80


def long_function_hits(files: Iterable[Path], root: Path, allowed: dict[str, int]) -> list[str]:
    """Every function or method (nested ones too) longer than FUNCTION_CEILING lines whose
    `<file>:<qualname>` is not allowed, as `file:line: qualname (n lines)`; and every allowed key
    whose function is at or under the ceiling, or gone, as `stale allowance: key (n lines)`."""
    hits = []
    lengths: dict[str, int] = {}
    for p in sorted(files):
        tree = _parsed(p)
        if tree is None:
            continue
        todo: list[tuple[ast.AST, list[str]]] = [(tree, [])]
        while todo:
            node, scope = todo.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                scope = [*scope, node.name]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n = (node.end_lineno or node.lineno) - node.lineno + 1
                key = f"{p.name}:{'.'.join(scope)}"
                lengths[key] = n
                if n > FUNCTION_CEILING and key not in allowed:
                    hits.append(f"{rel(p, root)}:{node.lineno}: {'.'.join(scope)} ({n} lines)")
            todo.extend((child, scope) for child in ast.iter_child_nodes(node))
    hits.sort()
    for key in allowed:
        n = lengths.get(key)
        if n is None:
            hits.append(f"stale allowance: {key} (gone)")
        elif n <= FUNCTION_CEILING:
            hits.append(f"stale allowance: {key} ({n} lines)")
    return hits


# ---------------------------------------------------------------------------------------------
# One owner for a table's state. A handler module receives the table as a parameter of one
# name and changes it only by calling the table's methods, so every invariant of the state (a
# count that is the sum of the rows, a set that holds only the engine's numbers) is kept in the
# table's own file. A write is any of five forms rooted at that name: a plain, annotated or
# augmented assignment, a subscript store, a `del`, or a mutator method of one of its fields.
# A read is not a write, and neither is a call of the table's own method.

TABLE_MUTATORS = frozenset(
    {"add", "discard", "pop", "clear", "append", "update", "remove", "extend", "setdefault"}
)


def _rooted_field(node: ast.expr, root: str) -> str | None:
    """The table's field a target chain stores into (`files.held`, `files.table[n]`,
    `files.table[n].held`), or None when the chain is not rooted at the name `root`."""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        inner = node.value
        if isinstance(node, ast.Attribute) and isinstance(inner, ast.Name) and inner.id == root:
            return node.attr
        node = inner
    return None


def table_write_hits(files: Iterable[Path], root: Path, name: str = "files") -> list[str]:
    """Every write to the table a handler module makes by hand, as `file:line: <name>.<field>
    <form>`: an assignment, annotated or augmented assignment or `del` whose target chain is
    rooted at the name `name`, or a call of `<name>.<field>.<mutator>(…)`."""
    hits: list[tuple[str, int, str]] = []
    for p in sorted(files):
        tree = _parsed(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            found: list[tuple[str, str]] = []
            if isinstance(node, ast.Assign):
                targets = [e for t in node.targets for e in _unpacked(t)]
                found = [(f, "assigned") for t in targets if (f := _rooted_field(t, name))]
            elif isinstance(node, ast.AnnAssign) and (f := _rooted_field(node.target, name)):
                found = [(f, "assigned")]
            elif isinstance(node, ast.AugAssign) and (f := _rooted_field(node.target, name)):
                found = [(f, "augmented")]
            elif isinstance(node, ast.Delete):
                found = [(f, "deleted") for t in node.targets if (f := _rooted_field(t, name))]
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in TABLE_MUTATORS
                and isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == name
            ):
                found = [(node.func.value.attr, f"mutated by {node.func.attr}")]
            for field_name, form in found:
                hits.append((rel(p, root), node.lineno, f"{name}.{field_name} {form}"))
    return [f"{path}:{line}: {what}" for path, line, what in sorted(hits)]


def sibling_imports(path: Path) -> list[tuple[int, str, bool]]:
    """Every import of a package module in `path`, at any depth, as (line, module, typing_only):
    a relative import (`from . import x`, `from .x import y`) or an absolute one of this package;
    typing_only says it sits under `if TYPE_CHECKING:`."""
    package = path.parent.name

    def named(node: ast.AST) -> list[str]:
        if isinstance(node, ast.ImportFrom):
            if node.level:
                return [node.module.split(".")[0]] if node.module else [a.name for a in node.names]
            if node.module and node.module.split(".")[0] == package:
                return node.module.split(".")[1:2] or [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            return [
                a.name.split(".")[1]
                for a in node.names
                if a.name.split(".")[0] == package and "." in a.name
            ]
        return []

    found: list[tuple[int, str, bool]] = []
    todo: list[tuple[ast.AST, bool]] = [(ast.parse(path.read_text(encoding="utf-8")), False)]
    while todo:
        node, typing_only = todo.pop()
        found += [(getattr(node, "lineno", 0), module, typing_only) for module in named(node)]
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
        ):
            # Only the body is for a type checker; the `else:` branch runs.
            todo += [(child, True) for child in node.body]
            todo += [(child, typing_only) for child in node.orelse]
        else:
            todo += [(child, typing_only) for child in ast.iter_child_nodes(node)]
    return sorted(found)


def _unpacked(target: ast.expr) -> list[ast.expr]:
    """A target and, for a tuple or list target, each of its elements, at any depth."""
    if isinstance(target, (ast.Tuple, ast.List)):
        return [e for elt in target.elts for e in _unpacked(elt)]
    if isinstance(target, ast.Starred):
        return _unpacked(target.value)
    return [target]


# ---------------------------------------------------------------------------------------------
# The process's state has one owner: no lock and no mutable container is bound at module or
# class level in a runner module. A lock made at module level is inherited across a fork, held
# by a thread the child does not have; a cache or registry at module level is one more list the
# fork reset and the exit release must remember. Both scanners read `Assign` and `AnnAssign`
# targets in the module body and in the body of every class defined there.

LOCK_CALLS = frozenset({"Lock", "RLock", "Condition"})
MUTABLE_CALLS = frozenset(
    {
        "dict",
        "list",
        "set",
        "bytearray",
        "deque",
        "defaultdict",
        "OrderedDict",
        "WeakSet",
        "WeakValueDictionary",
        "WeakKeyDictionary",
        "SimpleQueue",
        "Queue",
        "count",
        "local",
    }
)
MUTABLE_DISPLAYS = (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)
READ_ONLY_DISPLAYS = (ast.Dict, ast.List, ast.Set)  # an upper-case table that is only read


def _callee(node: ast.expr) -> str | None:
    """The last name of a call's callee: `threading.Lock(...)` and `Lock(...)` both give `Lock`."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _level_bindings(tree: ast.Module) -> Iterable[tuple[str, int, str, ast.expr]]:
    """Every binding in the module body and in each module-level class body: (the class's name or
    empty, the line, the name, the value)."""
    bodies: list[tuple[str, list[ast.stmt]]] = [("", tree.body)]
    bodies += [(n.name, n.body) for n in tree.body if isinstance(n, ast.ClassDef)]
    for owner, body in bodies:
        for node in body:
            pairs: list[tuple[str, ast.expr]] = []
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    pairs += _paired(target, node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    pairs.append((node.target.id, node.value))
            for name, value in pairs:
                yield owner, node.lineno, name, value


def _paired(target: ast.expr, value: ast.expr) -> list[tuple[str, ast.expr]]:
    """A name with its value; a tuple target over a tuple value of the same length, element by
    element (`a, b = {}, []` binds two displays); any other tuple target with the whole value."""
    if isinstance(target, ast.Name):
        return [(target.id, value)]
    if isinstance(target, ast.Tuple):
        if isinstance(value, ast.Tuple) and len(value.elts) == len(target.elts):
            return [p for t, v in zip(target.elts, value.elts, strict=True) for p in _paired(t, v)]
        return [(e.id, value) for e in target.elts if isinstance(e, ast.Name)]
    return []


def _parsed(p: Path) -> ast.Module | None:
    if p.suffix != ".py":
        return None
    try:
        return ast.parse(p.read_text(encoding="utf-8"), str(p))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def module_lock_hits(files: Iterable[Path], root: Path) -> list[str]:
    """Every `Lock()`, `RLock()` or `Condition()` bound at module or class level, with or without
    its `threading.` prefix. No exceptions."""
    hits = []
    for p in files:
        tree = _parsed(p)
        if tree is None:
            continue
        for owner, line, name, value in _level_bindings(tree):
            kind = _callee(value)
            if kind in LOCK_CALLS:
                shown = f"{owner}.{name}" if owner else name
                hits.append(f"{rel(p, root)}:{line}: {shown} ({kind})")
    return hits


def module_mutable_hits(files: Iterable[Path], root: Path) -> list[str]:
    """Every dict, list or set display or comprehension, and every call to a mutable container
    or a stateful object (MUTABLE_CALLS), bound at module or class level. Three kinds are not
    hits: `__all__`; an upper-case name bound to a dict, set or list display, a table that is
    only read; and `_fields_` in a class body, a ctypes declaration read once."""
    hits = []
    for p in files:
        tree = _parsed(p)
        if tree is None:
            continue
        for owner, line, name, value in _level_bindings(tree):
            if name == "__all__" or (owner and name == "_fields_"):
                continue
            if isinstance(value, MUTABLE_DISPLAYS):
                if name.isupper() and isinstance(value, READ_ONLY_DISPLAYS):
                    continue
                kind = type(value).__name__
            else:
                kind = _callee(value)
                if kind not in MUTABLE_CALLS:
                    continue
            shown = f"{owner}.{name}" if owner else name
            hits.append(f"{rel(p, root)}:{line}: {shown} ({kind})")
    return hits


# Carried patches, recorded and temporary

PATCH_NAME = re.compile(r"(\d{4})-[A-Za-z0-9][A-Za-z0-9._-]*\.patch")
DRAFT_FIELDS = ("Project", "Against", "Status", "Title", "Files", "Why we carry it")
STATUS = re.compile(r"drafted|sent \S+|merged \S+|released (\S+)")
AUTOTOOLS_INPUTS = {"configure.ac", "configure.in", "Makefile.am"}
PATCH_SHAPES = {  # the line's start -> why it is refused
    "new file mode 120000": "adds a link",
    "new mode 120000": "makes a link",
    "old mode": "changes a mode",
    "new mode": "changes a mode",
    "GIT binary patch": "has a binary hunk",
    "Binary files": "has a binary hunk",
    "rename from": "renames a file",
    "copy from": "copies a file",
}
CARRIED_ROW = re.compile(r"upstream patches carried: (\d+)")


def _version(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(x) for x in text.split("."))
    except ValueError:
        return None


def _git_reads(text: str) -> tuple[list[str], str, str]:
    """What git itself would apply: the paths (`--numstat -z`), the summary (modes, creations,
    deletions) and any error; outside any repository, with the caller's configuration cleared."""
    import os
    import shutil
    import subprocess
    import tempfile

    git = shutil.which("git")
    if git is None:
        return [], "", "git is not on PATH, so the patch cannot be read as git reads it"
    with tempfile.TemporaryDirectory() as home:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "XDG_CONFIG_HOME": home}
        env.update(
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CEILING_DIRECTORIES=home
        )
        work = Path(home) / "w"  # below the ceiling, so git never finds an enclosing repository
        work.mkdir()
        out = {}
        for flag in ("--numstat", "--summary"):
            cmd = [git, "-c", "core.quotePath=false", "apply", flag]
            cmd += ["-z", "-"] if flag == "--numstat" else ["-"]
            r = subprocess.run(cmd, input=text.encode(), capture_output=True, cwd=work, env=env)
            if r.returncode != 0:
                return [], "", r.stderr.decode(errors="replace").strip().splitlines()[0]
            out[flag] = r.stdout.decode(errors="replace")
    paths = [rec.split("\t", 2)[2] for rec in out["--numstat"].split("\0") if rec.count("\t") >= 2]
    return paths, out["--summary"], ""


def patch_shape_errors(text: str, where: str) -> tuple[list[str], set[str]]:
    """What a patch may not contain, and the paths it touches, as git reads
    it: a plain `---`/`+++` section after a hunk, or names that differ from `diff --git`, are
    applied by git and so are judged here too."""
    errors: list[str] = []
    for n, line in enumerate(text.splitlines(), 1):
        for start, why in PATCH_SHAPES.items():
            if line.startswith(start):
                errors.append(f"{where}:{n}: {why}")
        if line.startswith("new file mode ") and line.split()[-1] != "100644":
            errors.append(f"{where}:{n}: adds a file with mode {line.split()[-1]}")
    paths, summary, failed = _git_reads(text)
    if failed:
        return [*errors, f"{where}: git cannot read it: {failed}"], set()
    for line in summary.splitlines():
        words = line.split()
        if words[:1] in (["create"], ["delete"]) and words[2] not in ("100644",):
            errors.append(f"{where}: {line.strip()}: only plain files (mode 100644)")
        elif words[:2] == ["mode", "change"] or words[:1] in (["rename"], ["copy"]):
            errors.append(f"{where}: {line.strip()}")
    touched = set()
    for path in paths:
        parts = path.split("/")
        if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
            errors.append(f"{where}: {path!r} is outside the tree")
            continue
        touched.add(path)
        if _has_litter(path):
            errors.append(f"{where}: touches {path}, a name Finder or Explorer writes")
        if parts[-1] in AUTOTOOLS_INPUTS or parts[-1].endswith(".m4"):
            errors.append(f"{where}: changes the autotools input {path}; patch its output")
    if not touched:
        errors.append(f"{where}: changes no file")
    return errors, touched


def _draft_errors(draft: Path, top: str, touched: set[str], where: str) -> list[str]:
    lines = draft.read_text().splitlines()
    errors, fields = [], {}
    for i, field in enumerate(DRAFT_FIELDS):
        m = re.fullmatch(rf"- \*\*{re.escape(field)}:\*\* (.+)", lines[i] if i < len(lines) else "")
        if m is None:
            errors.append(f"{where}: line {i + 1} must be '- **{field}:** …'")
        else:
            fields[field] = m[1].strip()
    if not "".join(lines[len(DRAFT_FIELDS) :]).strip():
        errors.append(f"{where}: no pull request text after the header")
    status = STATUS.fullmatch(fields.get("Status", "drafted"))
    if status is None:
        errors.append(
            f"{where}: status {fields['Status']!r} is not drafted, sent, merged or released"
        )
    elif status[1] is not None:
        pinned = top.rsplit("-", 1)[-1]
        have, fixed = _version(pinned), _version(status[1])
        if have is None or fixed is None or len(have) != len(fixed):
            errors.append(
                f"{where}: write the released version as the pinned file name does ({pinned})"
            )
        elif have >= fixed:
            errors.append(f"{where}: released in {status[1]}, which {top} has: delete the patch")
    if "Files" in fields:
        listed = {f.strip() for f in fields["Files"].split(",") if f.strip()}
        if listed != touched:
            errors.append(
                f"{where}: Files lists {sorted(listed)}, the patch touches {sorted(touched)}"
            )
    return errors


def patch_errors(root: Path, tops: Iterable[str]) -> list[str]:
    """Every rule of a carried patch, on `recipes/patches/` and its drafts. `tops` are
    the pinned source tarballs' top folders."""
    tops = set(tops)
    patches, drafts = root / "recipes" / "patches", root / "context" / "upstream" / "patches"
    changelog = (root / "CHANGELOG.md").read_text() if (root / "CHANGELOG.md").is_file() else ""
    # A pull request that carries a patch names it in its news file, which reaches the changelog
    # only at the release; the news files' entries count as the changelog's own.
    changelog += "".join("\n" + text for _, _, text in news_changelogs(root))
    errors, count, made = [], 0, set()
    folders = sorted(p for p in patches.iterdir()) if patches.is_dir() else []
    for d in folders:
        if _is_litter(d.name):
            continue  # Finder's or Explorer's, not ours
        if not d.is_dir():
            if d.name != "README.md":
                errors.append(f"recipes/patches/{d.name}: only folders and README.md belong here")
            continue
        if d.name not in tops:
            errors.append(f"recipes/patches/{d.name}: no pinned source tarball has this top folder")
        numbers = set()
        for f in sorted(d.iterdir()):
            if _is_litter(f.name):
                continue
            where = f"recipes/patches/{d.name}/{f.name}"
            m = PATCH_NAME.fullmatch(f.name)
            if m is None:
                errors.append(f"{where}: not named NNNN-<slug>.patch, so it would never be applied")
                continue
            if m[1] in numbers:
                errors.append(f"{where}: another patch has the number {m[1]}")
            numbers.add(m[1])
            count += 1
            made.add((d.name, f.stem))
            if where not in changelog:
                errors.append(f"{where}: not named in CHANGELOG.md or in a news file")
            shape, touched = patch_shape_errors(f.read_text(errors="replace"), where)
            errors += shape
            draft = drafts / d.name / f"{f.stem}.md"
            if not draft.is_file():
                errors.append(f"{where}: no pull request draft at {rel(draft, root)}")
            else:
                errors += _draft_errors(draft, d.name, touched, rel(draft, root))
    if drafts.is_dir():
        for draft in sorted(
            p for p in drafts.rglob("*.md") if not _has_litter(p.relative_to(drafts).as_posix())
        ):
            if (draft.parent.name, draft.stem) not in made:
                errors.append(f"{rel(draft, root)}: a draft with no patch")
    readme = (root / "README.md").read_text() if (root / "README.md").is_file() else ""
    m = CARRIED_ROW.search(readme)
    if m is None or int(m[1]) != count:
        errors.append(f"README.md: must say 'upstream patches carried: {count}'")
    return errors


# `paths` is a local name in patch_shape_errors, so the judge's litter rules are reached through
# these two.
def _is_litter(name: str) -> bool:
    from harness import paths

    return paths.is_litter(name)


def _has_litter(rel: str) -> bool:
    from harness import paths

    return paths.has_litter(rel)


# ---------------------------------------------------------------------------------------------
# The landing lane

ACCEPTED_FILE = "context/progress/accepted.json"
PROGRESS_DIR = "context/progress"
VOLUMES_GLOB = ":(glob)context/progress/history*.jsonl"  # every history volume
# Rule 1 requires `dirty: false` of an acceptance whose judge holds this file: the guarded lane's
# own and every later one. Older lines are not re-judged (they all say true: Decision 2).
FIRST_CLEAN_JUDGE = "tests/unit/test_landing_lane.py"


def _committed_json(repo: Path, rev: str, path: str) -> object:
    text = paths.git("show", f"{rev}:{path}", repo=repo)
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None


def acceptance_errors(repo: Path) -> list[str]:
    """Rule 1, read from committed history
    only: the newest commit that changed a history volume sits on (first parent) the commit the
    newest line of its newest volume names, changes nothing but accepted.json and that volume,
    and, from the guarded lane's judge on, says `dirty: false`."""
    found = paths.git("rev-list", "-1", "HEAD", "--", VOLUMES_GLOB, repo=repo)
    if found is None:
        return [f"git rev-list -1 HEAD -- {VOLUMES_GLOB} failed"]
    c = found.strip()
    if not c:
        return []  # nothing accepted yet
    listed = paths.git("ls-tree", "--name-only", c, "--", f"{PROGRESS_DIR}/", repo=repo) or ""
    vols = sorted(
        (history.first_line_of(p.rsplit("/", 1)[-1]), p)
        for p in listed.split("\n")
        if p and history.first_line_of(p.rsplit("/", 1)[-1]) is not None
    )
    if not vols:
        return [f"the newest acceptance {c[:12]} leaves no history volume in its tree"]
    newest = vols[-1][1]
    text = paths.git("show", f"{c}:{newest}", repo=repo) or ""
    lines = [x for x in text.splitlines() if x.strip()]
    try:
        line = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        line = None
    if not isinstance(line, dict):
        return [f"the newest acceptance {c[:12]}: its newest history line is not a JSON object"]
    n, named = line.get("n"), str(line.get("commit"))
    errors = []
    parent = (paths.git("rev-parse", "--verify", "-q", f"{c}^1", repo=repo) or "").strip()
    if not parent:
        errors.append(
            f"the newest acceptance {c[:12]} has no parent; its line {n} judged {named[:12]}"
        )
        changed = (
            paths.git(
                "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", c, repo=repo
            )
            or ""
        )
    else:
        if named != parent:
            errors.append(
                f"the newest acceptance {c[:12]} sits on {parent[:12]}, but its history line {n} "
                f"judged {named[:12]} (carried across a rebase or an amend)"
            )
        changed = (
            paths.git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", parent, c, repo=repo
            )
            or ""
        )
    extra = sorted(set(changed.split("\0")) - {ACCEPTED_FILE, newest, ""})
    if extra:
        more = f" and {len(extra) - 3} more" if len(extra) > 3 else ""
        errors.append(
            f"the newest acceptance {c[:12]} also changes {', '.join(extra[:3])}{more}; an "
            "acceptance commit carries only accepted.json and its newest history volume"
        )
    accepted = _committed_json(repo, c, ACCEPTED_FILE)
    judge = accepted.get("judge") if isinstance(accepted, dict) else None
    files = judge.get("files", {}) if isinstance(judge, dict) else {}
    if FIRST_CLEAN_JUDGE in files and line.get("dirty") is not False:
        errors.append(
            f"the newest acceptance's history line {n} says dirty: {line.get('dirty')}; "
            "an acceptance is made on a clean tree"
        )
    return errors


def merge_commit_errors(repo: Path) -> list[str]:
    """Rule 3: no merge commit is reachable from HEAD."""
    out = paths.git("rev-list", "--merges", "HEAD", repo=repo)
    if out is None:
        return ["git rev-list --merges HEAD failed"]
    return [f"{h[:12]} is a merge commit; main moves only by fast-forward" for h in out.split()]


# Every Python a build step runs is the pinned host Python, or one built from pins. Step
# 10's shim (build/tools/host-python/) comes first on every step's PATH; scripts/build.sh puts a
# refusing stand-in for every other Python name behind it; this part reads the recipe and what the
# meson builds and configure recorded.

PYTHON_GLOBS = ("python*", "pypy*", "pip*", "pydoc*", "idle*")
SHIM_DIR = "build/tools/host-python"
STAND_IN_DIR = "build/no-host-python"
REFUSER = "scripts/refuse-python"
UNPINNED_LOG = "build/logs/unpinned-python.log"
SHELLS = {"sh", "bash", "dash", "zsh"}
# env's options (macOS and GNU): these consume the next word; these clear or replace the PATH a
# program is searched on, so a program behind them does not meet the shim.
ENV_ARG_OPTIONS = {"-u", "-C", "-P", "-S"}
ENV_BREACHES = {"-i", "-", "-P", "-S", "--ignore-environment", "--unset=PATH"}
# Direct children of build/ the harness and the lane keep, never a step's records.
CONFIG_LOG_SKIPS = ("uv-cache", "reviews-evidence", "harness", "harness-tmp")
GATE_LINE = re.compile(
    r"^host python: python3 is (\S+), Python (\S+), prefix (\S+); behind it python2 is (.*)$", re.M
)
# The words each recipe file must hold (code, not comments).
STEP_10_HOST_PYTHON_WORDS = (
    "host-python",
    "command -v",
    "/usr/bin/env python3",
    "sys.prefix",
    "host python: python3 is",
    "behind it python2 is",
)
BUILD_SH_HOST_PYTHON_WORDS = (
    STAND_IN_DIR,
    REFUSER,
    "ln -s",
    "unpinned-python.log",
    'export PATH="$P_NOPY:',
    "python2.7",
    *(f'"$p_dir"/{g}' for g in PYTHON_GLOBS),
)
_SHELL_VAR = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*|[0-9*@#?$!-])")
_ASSIGNMENT_WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def is_python_name(name: str) -> bool:
    """A basename one of the five globs matches."""
    return any(fnmatch.fnmatchcase(name, g) for g in PYTHON_GLOBS)


def shim_names(python_version: str) -> tuple[str, ...]:
    """The three names step 10's shim holds: python, python3 and python<major>.<minor>."""
    major, minor = python_version.split(".")[:2]
    return ("python", "python3", f"python{major}.{minor}")


def allowed_interpreter(path: str, root: Path, shims: tuple[str, ...]) -> bool:
    """Decision 1's interpreters, by absolute path: the shim's files, the pinned host Python, the
    target-Python launcher, and the build-Python step 20 makes."""
    p = posixpath.normpath(path)
    r = str(root)
    return (
        any(p == f"{r}/{SHIM_DIR}/{n}" for n in shims)
        or fnmatch.fnmatchcase(p, f"{r}/build/tools/python/bin/python3*")
        or p == f"{r}/scripts/python-wasi-cross"
        or fnmatch.fnmatchcase(p, f"{r}/build/Python-*/cross-build/*/python.exe")
        or fnmatch.fnmatchcase(p, f"{r}/build/Python-*/cross-build/*/python")
    )


def env_program(words: list[str]) -> tuple[int | None, str | None]:
    """(index of the program word, problem) for a command, read past any `env` by its grammar.
    The index is None when there is no program word."""
    i = 0
    while i < len(words) and posixpath.basename(words[i]) == "env":
        i += 1
        while i < len(words):
            w = words[i]
            if w in ENV_BREACHES or w.startswith("--split-string") or w.startswith("PATH="):
                return None, f"`env {w}` does not search the step's PATH"
            if w == "-u":
                if i + 1 < len(words) and words[i + 1] == "PATH":
                    return None, "`env -u PATH` does not search the step's PATH"
                i += 2
            elif w in ENV_ARG_OPTIONS:
                i += 2
            elif w.startswith("-"):
                return None, f"`env {w}` is an option the judge does not read"
            elif _ASSIGNMENT_WORD.match(w):
                i += 1
            else:
                break
    return (i if i < len(words) else None), None


def _shebang(path: Path) -> list[str] | None:
    try:
        with path.open("rb") as f:
            first = f.readline(512)
    except OSError:
        return None
    if not first.startswith(b"#!"):
        return None
    return first[2:].decode(errors="replace").split()


def program_problem(
    words: list[str], root: Path, shims: tuple[str, ...], cwd: Path, depth: int = 0
) -> str | None:
    """Why a command's program would be a Python Decision 1 does not allow, or None. The program
    word is found past `env` and meson's `--internal exe`; a shell with -c is not read; a bare
    Python name must be a shim name; a path with a Python name must be an allowed interpreter; a
    script is read by its shebang the same way."""
    i, problem = env_program(words)
    if problem or i is None:
        return problem
    word, rest = words[i], words[i + 1 :]
    base = posixpath.basename(word)
    if base == "meson" and rest[:2] == ["--internal", "exe"]:
        if "--unpickle" in rest:
            return "`meson --internal exe --unpickle` hides its command in a file"
        if "--" not in rest:
            return "`meson --internal exe` with no program after --"
        return program_problem(rest[rest.index("--") + 1 :], root, shims, cwd, depth)
    if base in SHELLS and "-c" in rest:
        return f"`{base} -c` runs a string the judge does not read"
    if "/" not in word:
        if is_python_name(word) and word not in shims:
            return f"`{word}` is no shim name, so it reaches the stand-in or the host"
        return None
    path = (cwd / word) if not word.startswith("/") else Path(word)
    if is_python_name(base):
        if allowed_interpreter(str(path), root, shims):
            return None
        return f"{posixpath.normpath(str(path))} is not a pinned interpreter"
    if depth == 0 and path.is_file():
        shebang = _shebang(path)
        if shebang:
            problem = program_problem(shebang, root, shims, cwd, depth + 1)
            if problem:
                return f"{word}'s shebang: {problem}"
    return None


_PROGRAM_FOUND = re.compile(r"^Program (.+?) found: YES \((.*)\)\s*$")
_RUNNING = re.compile(r"^Running command: (.*)$")
_NINJA_COMMAND = re.compile(r"^ (?:COMMAND|command) = (.*)$")
_CONFIGURE_FOUND = re.compile(r"^configure:\d+: found (\S.*)$")


def meson_log_hits(text: str, root: Path, shims: tuple[str, ...], cwd: Path) -> list[str]:
    """`Running command:` and `Program … found: YES (…)` lines of one meson log; for the second,
    a requested Python name must also have found an allowed interpreter."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if m := _PROGRAM_FOUND.match(line):
            words = _tokens(m[2])
            if problem := program_problem(words, root, shims, cwd):
                hits.append(f"{n}: Program {m[1]}: {problem}")
            elif is_python_name(posixpath.basename(m[1])):
                i, _ = env_program(words)
                found = words[i] if i is not None else ""
                if not allowed_interpreter(found, root, shims):
                    hits.append(f"{n}: Program {m[1]} found {found}, not a pinned interpreter")
        elif m := _RUNNING.match(line):
            if problem := program_problem(_tokens(m[1]), root, shims, cwd):
                hits.append(f"{n}: {problem}")
    return hits


def ninja_hits(text: str, root: Path, shims: tuple[str, ...], cwd: Path) -> tuple[list[str], int]:
    """(hits, commands read) over one build.ninja's COMMAND and command lines. `$COMMAND` is
    meson's rule indirection and is skipped; any other leading ninja variable is a hit."""
    hits, read = [], 0
    for n, line in enumerate(text.splitlines(), 1):
        if not (m := _NINJA_COMMAND.match(line)):
            continue
        if m[1].strip() in ("$COMMAND", "${COMMAND}"):
            continue  # meson's rule indirection: each COMMAND = line it stands for is read
        read += 1
        if m[1].startswith("$"):
            hits.append(f"{n}: {m[1].split()[0]} is a ninja variable the judge does not read")
            continue
        if problem := program_problem(_tokens(m[1]), root, shims, cwd):
            hits.append(f"{n}: {problem}")
    return hits, read


def config_log_hits(text: str, root: Path, shims: tuple[str, ...]) -> list[str]:
    """Every `configure:NNN: found <path>` with a Python name names an allowed interpreter."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if (m := _CONFIGURE_FOUND.match(line)) and is_python_name(posixpath.basename(m[1])):
            if not allowed_interpreter(m[1], root, shims):
                hits.append(f"{n}: found {m[1]}, not a pinned interpreter")
    return hits


def config_logs(build: Path) -> list[Path]:
    """Every config.log under build/, except under the direct children the harness and lane keep."""
    logs = []
    for child in sorted(build.iterdir()) if build.is_dir() else ():
        if not child.is_dir() or child.name in CONFIG_LOG_SKIPS or child.name.startswith("lane-"):
            continue
        logs += sorted(p for p in child.rglob("config.log") if p.is_file())
    return logs


_PATH_ASSIGN = re.compile(r"""^\s*(?:export\s+)?PATH=["']?(.*?):\$\{?PATH\}?["']?\s*(?:#.*)?$""")
_SIMPLE_ASSIGN = re.compile(
    r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=["']?([^"'`$(]*(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?[^"'`$(]*)*)["']?\s*(?:#.*)?$"""
)


def _resolve(expr: str, values: dict[str, str]) -> str | None:
    """A shell word's variables replaced from `values`; None if one is unknown, or if the word
    holds a command substitution (`$(` or a backtick), which is never resolved."""
    if "$(" in expr or "`" in expr:
        return None
    missing = []

    def sub(m: re.Match[str]) -> str:
        if m[1] in values:
            return values[m[1]]
        missing.append(m[1])
        return ""

    out = _SHELL_VAR.sub(sub, expr)
    return None if missing else out


def step_path_folders(
    steps: dict[str, str], root: Path, line: dict[str, str]
) -> tuple[list[tuple[str, str]], list[str]]:
    """((step, folder), unresolved) for every folder a step script puts on PATH ahead of the rest:
    variables are read from common.sh's and the step's own simple assignments and from line.conf;
    a folder that cannot be resolved is returned as unresolved."""
    base = {"HERE": str(root), **line}
    common = steps.get("common.sh", "")
    folders: list[tuple[str, str]] = []
    unresolved: list[str] = []
    for name, text in sorted(steps.items()):
        values = dict(base)
        lines = (common.splitlines() if name != "common.sh" else []) + text.splitlines()
        for raw in lines:
            if raw.lstrip().startswith("#"):
                continue
            if m := _PATH_ASSIGN.match(raw):
                for part in m[1].split(":"):
                    folder = _resolve(part, values)
                    if folder is None:
                        unresolved.append(f"{name}: PATH folder {part} cannot be resolved")
                    else:
                        folders.append((name, posixpath.normpath(folder)))
            elif m := _SIMPLE_ASSIGN.match(raw):
                if (v := _resolve(m[2], values)) is not None:
                    values[m[1]] = v
    return folders, unresolved


def host_python_recipe_errors(root: Path) -> list[str]:
    """The recipe holds Decisions 3 to 5: the shim first on common.sh's PATH, step 10 writes and
    gates it, build.sh shadows the host's Python names with the stand-in and fails a step that ran
    one, and the stand-in finds its log from its own location."""
    errors = []
    common = code_text(root / "scripts/steps/common.sh") or ""
    if not re.search(r'^\s*export PATH="\$T/host-python:', common, re.M):
        errors.append("common.sh does not put $T/host-python first on PATH")
    step_10 = code_text(root / "scripts/steps/10_tools.sh") or ""
    errors += [
        f"10_tools.sh does not name {w}" for w in STEP_10_HOST_PYTHON_WORDS if w not in step_10
    ]
    build = code_text(root / "scripts/build.sh") or ""
    errors += [f"build.sh does not name {w}" for w in BUILD_SH_HOST_PYTHON_WORDS if w not in build]
    refuser = code_text(root / REFUSER)
    if refuser is None:
        return [*errors, f"{REFUSER} is missing"]
    for w in ('dirname "$0"', "no-host-python", "unpinned-python.log", "exit 1"):
        if w not in refuser:
            errors.append(f"{REFUSER} does not name {w}")
    own = {"0", "*", "name", "dir"}
    if foreign := sorted({m[1] for m in _SHELL_VAR.finditer(refuser)} - own):
        errors.append(f"{REFUSER} reads {', '.join(foreign)}: its log comes from its own location")
    return errors


def host_python_record_errors(
    root: Path, line: dict[str, str], steps: dict[str, str]
) -> tuple[list[str], list[str]]:
    """(errors, what was read) over a build's records: the meson logs and build.ninja files of
    MESON_BUILDS, every config.log under build/, the folders steps put on PATH, step 10's gate line
    and the stand-in's log."""
    build = root / "build"
    shims = shim_names(line["PYTHON_VERSION"])
    errors: list[str] = []
    read: list[str] = []
    for name in MESON_BUILDS:
        folder = build / name
        log = folder / "meson-logs" / "meson-log.txt"
        if log.is_file():
            hits = meson_log_hits(log.read_text(errors="replace"), root, shims, folder)
            errors += [f"{name}/meson-logs/meson-log.txt:{h}" for h in hits]
            read.append(f"{name}/meson-logs/meson-log.txt")
        ninja = folder / "build.ninja"
        if ninja.is_file():
            hits, n = ninja_hits(ninja.read_text(errors="replace"), root, shims, folder)
            errors += [f"{name}/build.ninja:{h}" for h in hits]
            read.append(f"{name}/build.ninja: {n} commands")
    for log in config_logs(build):
        rel_log = log.relative_to(build)
        errors += [
            f"{rel_log}:{h}" for h in config_log_hits(log.read_text(errors="replace"), root, shims)
        ]
        read.append(f"{rel_log}")
    folders, unresolved = step_path_folders(steps, root, line)
    errors += unresolved
    for step, folder in folders:
        if folder == f"{root}/{SHIM_DIR}" or not Path(folder).is_dir():
            continue
        named = sorted(p.name for p in Path(folder).iterdir() if is_python_name(p.name))
        if named:
            errors.append(
                f"{step}: {folder} sits ahead of the stand-in and holds {', '.join(named)}"
            )
        read.append(f"{step}: PATH folder {rel(Path(folder), root)}")
    gate = build / "logs" / "10_tools.log"
    m = GATE_LINE.search(gate.read_text(errors="replace")) if gate.is_file() else None
    if m is None:
        errors.append("build/logs/10_tools.log holds no `host python:` gate line")
    else:
        if (
            m[1] != f"{SHIM_DIR}/python3"
            or m[2] != line["PYTHON_VERSION"]
            or m[3] != "build/tools/python"
        ):
            errors.append(f"10_tools.log's gate line names {m[1]}, {m[2]}, {m[3]}")
        if m[4] != f"{STAND_IN_DIR}/python2":
            errors.append(f"10_tools.log: behind the shim python2 is {m[4]}, not the stand-in")
        read.append("build/logs/10_tools.log: the gate line")
    if (root / UNPINNED_LOG).exists():
        errors.append(f"{UNPINNED_LOG} exists: a step ran an unpinned Python")
    return errors, read


# numpy's own floating-point signals, kept in software: a recipe header force-included
# into every numpy C and C++ compile gives FE_INVALID and its siblings bits and sends numpy's three
# fe* calls to one weak flag word, since wasm has no floating-point status flags.
NPY_FENV_HEADER = "recipes/npy_fenv_flags.h"
NPY_FENV_CROSS = "recipes/wasi-numpy.cross"
NPY_FENV_INCLUDE = "'-include', '@ROOT@/recipes/npy_fenv_flags.h'"
NPY_FENV_COMPILERS = ("scripts/wasi-cc", "scripts/wasi-cxx")
NPY_FENV_RECORDS = "build/numpy-build/compile_commands.json"
NPY_FENV_HEADER_NEEDS = (
    ("the #error guard", re.compile(r"^#if defined\(FE_INVALID\).*\n#error ", re.M)),
    ("FE_INVALID's bit", re.compile(r"^#define FE_INVALID 0x01$", re.M)),
    ("FE_DIVBYZERO's bit", re.compile(r"^#define FE_DIVBYZERO 0x04$", re.M)),
    ("FE_OVERFLOW's bit", re.compile(r"^#define FE_OVERFLOW 0x08$", re.M)),
    ("FE_UNDERFLOW's bit", re.compile(r"^#define FE_UNDERFLOW 0x10$", re.M)),
    ("FE_INEXACT's bit", re.compile(r"^#define FE_INEXACT 0x20$", re.M)),
    (
        "the weak flag word",
        re.compile(r"^__attribute__\(\(weak\)\) int wasi_python_fe_flags;$", re.M),
    ),
    (
        "the feraiseexcept rename",
        re.compile(r"^#define feraiseexcept wasi_python_feraiseexcept$", re.M),
    ),
    (
        "the fetestexcept rename",
        re.compile(r"^#define fetestexcept wasi_python_fetestexcept$", re.M),
    ),
    (
        "the feclearexcept rename",
        re.compile(r"^#define feclearexcept wasi_python_feclearexcept$", re.M),
    ),
)


def npy_fenv_recipe_errors(cross: str, header: str | None) -> list[str]:
    """The recipe as written: the numpy cross file's one `c_args`
    and one `cpp_args` line each force-include the header once, and the header holds its guard,
    its five bits, its weak word and its three renames."""
    errors = []
    for key in ("c_args", "cpp_args"):
        lines = [t for t in cross.splitlines() if t.startswith(f"{key} ")]
        if len(lines) != 1:
            errors.append(f"{NPY_FENV_CROSS}: {len(lines)} {key} lines, not 1")
            continue
        n = lines[0].count(NPY_FENV_INCLUDE)
        if n != 1:
            errors.append(
                f"{NPY_FENV_CROSS}: {key} force-includes {NPY_FENV_HEADER} {n} times, not once"
            )
    if header is None:
        return [*errors, f"{NPY_FENV_HEADER} is missing"]
    errors += [
        f"{NPY_FENV_HEADER} lacks {what}"
        for what, rx in NPY_FENV_HEADER_NEEDS
        if not rx.search(header)
    ]
    return errors


def _record_argv(entry: dict) -> list[str]:
    """One compile record's command as an argument list: meson writes `command`, a shell string;
    the compile-database format allows `arguments`, a list."""
    if isinstance(entry.get("arguments"), list):
        return [str(a) for a in entry["arguments"]]
    return shlex.split(str(entry.get("command", "")))


def _is_cross_compile(argv: list[str]) -> bool:
    """A compile by the cross file's compilers: the first argument's path ends in scripts/wasi-cc or
    scripts/wasi-cxx (a whole path ending, never a name found anywhere in the
    command), and the command compiles (`-c`)."""
    if not argv or "-c" not in argv:
        return False
    first = argv[0].replace("\\", "/")
    return any(first == c or first.endswith("/" + c) for c in NPY_FENV_COMPILERS)


def npy_fenv_record_errors(records: list[dict]) -> tuple[list[str], dict[str, int]]:
    """Every numpy compile carries the header exactly once. An
    entry is read by its compiler, not its file's extension, so a `.S` or a generated source cannot
    escape; `cython` runs and links are not compiles. Returns (errors, counts)."""
    counts = {"compiles": 0, "c": 0, "c++": 0, "not compiles": 0}
    if not records:
        return [f"{NPY_FENV_RECORDS} lists no entry (a build that compiled nothing)"], counts
    errors = []
    for e in records:
        argv = _record_argv(e)
        if not _is_cross_compile(argv):
            counts["not compiles"] += 1
            continue
        counts["compiles"] += 1
        counts["c++" if argv[0].endswith("wasi-cxx") else "c"] += 1
        n = sum(
            1
            for flag, value in zip(argv, argv[1:], strict=False)
            if flag == "-include" and value.replace("\\", "/").endswith("/" + NPY_FENV_HEADER)
        )
        if n != 1:
            errors.append(f"{e.get('file')}: force-includes {NPY_FENV_HEADER} {n} times, not once")
    if not counts["compiles"]:
        errors.append(f"{NPY_FENV_RECORDS} lists no wasi-cc or wasi-cxx compile")
    return errors, counts


def npy_fenv_records_file_errors(root: Path) -> tuple[list[str], dict[str, int]]:
    """numpy's own compile records, read from the file itself: once the `compile records` need is
    met (any meson build left its records), numpy's file missing is a failure, never a skip."""
    p = root / NPY_FENV_RECORDS
    if not p.is_file():
        return [f"{NPY_FENV_RECORDS} is missing (numpy's compile records)"], {}
    return npy_fenv_record_errors(json.loads(p.read_text()))


# ---------------------------------------------------------------------------------------------
# One module, the engine seam, touches wasmtime-py's private API. The rule reads raw
# text, comments and docstrings included. Its last three alternations (the raw function handle,
# the from-pointer constructors, the pointer method) are assembled from two literals each, so
# that this file is not a hit of its own rule (U17 holds that it is not).

PRIVATE_ENGINE = re.compile(
    r"from wasmtime import [^\n]*\b_(?:ffi|bindings|func|wasi)\b"
    r"|\bwasmtime\._(?:ffi|bindings|func|wasi)\b"
    r"|(?<!self)\._context\(\)"
    r"|\._"
    r"func\b"
    r"|\b_from"
    r"_ptr\b"
    r"|\.p"
    r"tr\(\)"
)
ENGINE_SEAM = "src/wasi_python/_wasmtime_ffi.py"
ENGINE_SEAM_UNIT = "tests/unit/test_wasmtime_ffi.py"


def private_engine_hits(root: Path, subdirs: Iterable[str], exempt: Iterable[str]) -> list[str]:
    """Every line of a `.py` file under `subdirs` that reaches wasmtime-py's private API, as
    `path:line: text`, the files named in `exempt` (paths relative to `root`) left out."""
    skip = set(exempt)
    hits = []
    for p in files_under(root, *subdirs):
        if p.suffix != ".py" or rel(p, root) in skip:
            continue
        text = _text(p)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if PRIVATE_ENGINE.search(line):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()}")
    return hits


BINDINGS_HEADING = "## The bindings"
_BINDING_ROW = re.compile(r"^\| `([^`]*)`")


def _tuple_literal(tree: ast.Module, name: str) -> tuple | None:
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            try:
                value = ast.literal_eval(node.value)  # type: ignore[union-attr]
            except ValueError:
                return None
            return value if isinstance(value, tuple) else None
    return None


def sheet_bindings(text: str) -> list[str]:
    """The first cell's backticked text of every row of the sheet's "The bindings" table: a
    line starting with ``| ` `` under that heading, up to the next heading. A tag after the
    backticks, such as `(optional)`, is not part of the name."""
    rows = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == BINDINGS_HEADING
            continue
        m = _BINDING_ROW.match(line) if inside else None
        if m:
            rows.append(m[1])
    return rows


def private_api_debt_errors(adapter: Path, sheet: Path) -> list[str]:
    """The debt sheet holds one row per entry of the adapter's `NEEDED` and `OPTIONAL` tuples,
    each a `(holder, name)` pair read as `holder.name`, and the adapter's module docstring names
    every one; read statically, with `ast`, so no wasmtime-py is imported."""
    if not adapter.is_file():
        return [f"{adapter.name} does not exist"]
    if not sheet.is_file():
        return [f"{sheet} does not exist"]
    tree = ast.parse(adapter.read_text(encoding="utf-8"), str(adapter))
    errors = []
    names: list[str] = []
    for which in ("NEEDED", "OPTIONAL"):
        pairs = _tuple_literal(tree, which)
        if pairs is None:
            errors.append(f"{adapter.name}: {which} is not a tuple literal")
            continue
        for pair in pairs:
            if not (
                isinstance(pair, tuple) and len(pair) == 2 and all(isinstance(s, str) for s in pair)
            ):
                errors.append(f"{adapter.name}: {which} holds {pair!r}, not a (holder, name) pair")
                continue
            names.append(pair[0] + "." + pair[1])
    rows = sheet_bindings(sheet.read_text(encoding="utf-8"))
    errors += [f"{name}: no row of the sheet's table" for name in names if name not in rows]
    errors += [
        f"{row}: a row naming no entry of NEEDED or OPTIONAL" for row in rows if row not in names
    ]
    doc = ast.get_docstring(tree) or ""
    errors += [f"{name}: not named in the adapter's docstring" for name in names if name not in doc]
    return errors


# ---------------------------------------------------------------------------------------------
# Code speaks for itself: a comment or a docstring gives its reason in words and points at no
# project document. The judge may read those documents as data; only what a reader is told is
# held here.

CITATION_RULES = (
    ("specification", re.compile(r"\bspec(?:ification)?s?\s+\d{3}\b", re.I)),
    # A specification by its bare number as a possessive: three digits, the first a zero.
    ("specification", re.compile(r"(?<![\w.$/-])0\d{2}'s\b")),
    # The constitution's sections are numbered like 4.15; a licence's (Apache-2.0's 4(b)) are not.
    ("constitution", re.compile(r"\bconstitution\s*§|§\s*\d+\.\d+", re.I)),
    ("memo", re.compile(r"\bmemo\b", re.I)),
    (
        "review",
        re.compile(r"\breviews?\b[\s,:(`'\"]*(?:\d{4}-\d{2}-\d{2}|[\w.-]*/(?=[\w.-]))", re.I),
    ),
    # A review named by its kind: the one of a build, the one before it, a security one, a
    # second one.
    (
        "review",
        re.compile(
            r"\b(?:pre-build|build|delta|follow-up|security|integration)\s+review\b"
            r"|\bre-review\b|\bconfirmation's",
            re.I,
        ),
    ),
    ("question", re.compile(r"\bquestion\s+\d+\b", re.I)),
    ("context path", re.compile(r"\bcontext/[a-z_]+")),
    ("finding", re.compile(r"(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])")),
    # The other letters a finding takes (High, Medium, a mutation), only where a review names it,
    # since alone they are also a milestone's or a chip's name.
    (
        "named finding",
        re.compile(
            r"(?i:\b(?:re-review|review|confirmation)(?:'s)?),?\s+(?i:(?:finding|mutation)\s+)?"
            r"[ABEGHIJKMOPQRTUVWXYZ]\d{1,2}\b"
        ),
    ),
)
CITATION_SUFFIXES = {".py", ".sh", ".toml", ".yml", ".yaml"}
TRAILING_COMMENT = re.compile(r"\s#\s.*$")


def _comment_blocks(lines: Iterable[tuple[int, str, bool]]) -> list[tuple[int, str]]:
    """Join comments into blocks: each `(line, text, whole_line)` comment that fills its line and
    follows a whole-line comment on the line before joins that block, its `#`s dropped, so a
    citation broken across two comment lines is read whole. A trailing comment stands alone."""
    out: list[tuple[int, str]] = []
    last = -1
    for n, text, whole in lines:
        body = text.lstrip().lstrip("#")
        if whole and n == last + 1 and out:
            out[-1] = (out[-1][0], out[-1][1] + "\n" + body)
        else:
            out.append((n, body))
        last = n if whole else -1
    return out


def _python_prose(text: str) -> list[tuple[int, str]]:
    """(first line, text) of every comment block and every docstring of a Python source:
    comments from `tokenize`, docstrings as the string tokens `ast` places first in a module, a
    class or a function. Code and every other string literal are left out."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        tree = ast.parse(text)
    except (tokenize.TokenError, SyntaxError, ValueError):
        return []
    starts = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                starts.add((first.lineno, first.col_offset))
    lines = text.splitlines()
    comments = [
        (t.start[0], t.string, not lines[t.start[0] - 1][: t.start[1]].strip())
        for t in tokens
        if t.type == tokenize.COMMENT
    ]
    docs = [
        (t.start[0], t.string) for t in tokens if t.type == tokenize.STRING and t.start in starts
    ]
    return _comment_blocks(comments) + docs


def _hash_comments(text: str) -> list[tuple[int, str]]:
    """(first line, text) of every `#` comment block of a shell, TOML or YAML file, or any other
    text file: lines that start with `#`, joined while they run on, or the part of a line after a
    ` # `."""
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            found.append((n, line.strip(), True))
        elif m := TRAILING_COMMENT.search(line):
            found.append((n, m[0].strip(), False))
    return _comment_blocks(found)


def context_citation_hits(path: Path) -> list[tuple[int, str, str]]:
    """(line, rule, phrase) for each citation of a project document in the comments and the
    docstrings of one file: a specification's number, the constitution's sections, the word for
    a research write-up, a review named by its kind or followed by a date or a path, a numbered
    question of the owner's, a path under the knowledge tree, or a review finding's identifier.
    A Python file is read through its tokens; a Markdown page whole, since all of it is prose a
    reader sees; any other file through its `#` comments. A citation broken across lines is found
    whole, on the line it starts, its spaces made one."""
    text = _text(path)
    if text is None:
        return []
    if path.suffix == ".py":
        prose = _python_prose(text)
    elif path.suffix == ".md":
        prose = [(1, text)]
    else:
        prose = _hash_comments(text)
    return sorted(
        (n + block[: m.start()].count("\n"), rule, " ".join(m[0].split()))
        for n, block in prose
        for rule, pattern in CITATION_RULES
        for m in pattern.finditer(block)
    )


def context_citation_files(root: Path) -> list[Path]:
    """The files the citation rule reads: every Python, shell, TOML and YAML file under `tests/`
    and `.github/workflows/`, every text file under `scripts/` and `release/`, and the public
    pages: the README and every Markdown page under `docs/`."""
    picked = [
        p for p in files_under(root, "tests", ".github/workflows") if p.suffix in CITATION_SUFFIXES
    ]
    picked += [p for p in files_under(root, "scripts", "release") if _text(p) is not None]
    return picked + public_pages(root)


def news_changelogs(root: Path) -> list[tuple[Path, int, str]]:
    """(file, first line, text) of every news file's `## Changelog` section, read as text so a
    broken news file is still read; its shape is the news files' own check."""
    folder = root / news.CHANGES
    out = []
    for p in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if not news.NAME.fullmatch(p.name):
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        start = next((i for i, line in enumerate(lines) if line.strip() == "## Changelog"), None)
        if start is None:
            continue
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
        )
        out.append((p, start + 2, "\n".join(lines[start + 1 : end])))
    return out


def release_note_hits(root: Path) -> list[str]:
    """Each citation of a project document, by the public pages' rules, and each reserved
    embedder name in the release's notes: every news file's entries, and the changelog's header
    and its sections written for the reader. The sections published before are not read."""
    names_file = root / "context" / "embedders.txt"
    names = read_names(names_file) if names_file.is_file() else []
    blocks = [(rel(p, root), line, text) for p, line, text in news_changelogs(root)]
    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        blocks += [
            ("CHANGELOG.md", s.line, s.body)
            for s in news.reader_sections(changelog.read_text(encoding="utf-8"))
        ]
    hits = set()
    for where, first, text in blocks:
        for rule, pattern in CITATION_RULES:
            for m in pattern.finditer(text):
                line = first + text[: m.start()].count("\n")
                hits.add((where, line, rule, " ".join(m[0].split())))
        for n, line_text in enumerate(text.splitlines()):
            hits.update((where, first + n, "embedder", x) for x in names if x in line_text.lower())
    return [f"{w}:{n}: {rule}: {phrase}" for w, n, rule, phrase in sorted(hits)]


def public_pages(root: Path) -> list[Path]:
    """The pages a user reads: the README, which is also the wheel's description, and the
    documentation site's Markdown pages."""
    return files_under(root, "README.md") + [
        p for p in files_under(root, "docs") if p.suffix == ".md"
    ]


# ---------------------------------------------------------------------------------------------
# Strings speak for themselves too: a message, a help text, a title or a program a check holds
# gives its reason in words. The forms are the comment rule's but two. In a string a path is
# what the code opens or the file a message asks a person to fix, and a letter with a digit is
# a label (a case, a test id, a placeholder), so neither is refused; a finding a review names is,
# whatever its letter.

_SAME_IN_STRINGS = {"specification", "constitution", "memo", "question"}
STRING_CITATION_RULES = (
    *((rule, pattern) for rule, pattern in CITATION_RULES if rule in _SAME_IN_STRINGS),
    ("review", re.compile(r"\breviews?\b[\s,:(`'\"]*\d{4}-\d{2}-\d{2}", re.I)),
    # A review by the number of the specification it reviewed.
    ("review", re.compile(r"\breviews?\s+0\d{2}\b", re.I)),
    *(
        (rule, pattern)
        for rule, pattern in CITATION_RULES
        if rule == "review" and "pre-build" in pattern.pattern
    ),
    (
        "named finding",
        re.compile(
            r"(?i:\b(?:re-review|review|confirmation)(?:'s)?),?\s+(?i:(?:finding|mutation)\s+)?"
            r"[A-Z]\d{1,2}(?:\.\d+)?\b"
        ),
    ),
)
# The functions of `re` whose first argument is a pattern, the rule's own vocabulary.
PATTERN_FUNCTIONS = {
    "compile",
    "search",
    "match",
    "fullmatch",
    "findall",
    "finditer",
    "sub",
    "subn",
    "split",
}
# The literal text inside an f-string or a t-string, between its replacement fields.
_MIDDLE_TOKENS = {
    getattr(tokenize, name)
    for name in ("FSTRING_MIDDLE", "TSTRING_MIDDLE")
    if hasattr(tokenize, name)
}


def _pattern_nodes(node: ast.AST) -> Iterable[ast.AST]:
    """The nodes of a pattern argument, stopping at a call: what a call is given (the text of
    `re.escape`, say) is text, not the pattern."""
    yield node
    if not isinstance(node, ast.Call):
        for child in ast.iter_child_nodes(node):
            yield from _pattern_nodes(child)


def _not_read(tree: ast.AST) -> tuple[set[tuple[int, int]], set[int]]:
    """What the string rule leaves to others: the start of every token the comment rule reads as
    a docstring (the first token of a plain string constant that opens a module, a class or a
    function), and the nodes that are a pattern given to a function of `re` or the phrase of an
    allowance row (the second item of a three-item row assigned to a name ending in
    `_ALLOWED`)."""
    docs: set[tuple[int, int]] = set()
    nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                # Keyed by the statement, as the comment rule keys it: a parenthesized string
                # starts after its parenthesis, so it is no docstring to either rule.
                docs.add((first.lineno, first.col_offset))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
            and node.func.attr in PATTERN_FUNCTIONS
        ):
            given = node.args[:1] + [k.value for k in node.keywords if k.arg == "pattern"]
            nodes.update(id(sub) for arg in given for sub in _pattern_nodes(arg))
        elif isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id.endswith("_ALLOWED") for t in targets):
                rows = node.value.elts if isinstance(node.value, ast.Tuple | ast.List) else []
                nodes.update(
                    id(row.elts[1])
                    for row in rows
                    if isinstance(row, ast.Tuple) and len(row.elts) == 3
                )
    return docs, nodes


def _literal_pieces(
    tokens: list[tokenize.TokenInfo], skip: set[tuple[int, int]]
) -> list[tuple[int, str, bool]]:
    """(line, text, spans lines) for each literal part of one string literal's tokens, in order:
    a plain string token's value, an f-string's (or a t-string's) literal parts, and `{…}` for
    each replacement field; the strings inside a field are their own literals."""
    pieces: list[tuple[int, str, bool]] = []
    depth = 0
    for tok in tokens:
        if tok.type == tokenize.OP and tok.string == "{":
            depth += 1
        elif tok.type == tokenize.OP and tok.string == "}":
            depth -= 1
            if depth == 0:
                pieces.append((tok.start[0], "{…}", False))
        elif depth == 0 and tok.type == tokenize.STRING and tok.start not in skip:
            value = ast.literal_eval(tok.string)
            text = value.decode("latin-1") if isinstance(value, bytes) else str(value)
            pieces.append((tok.start[0], text, tok.end[0] > tok.start[0]))
        elif depth == 0 and tok.type in _MIDDLE_TOKENS:
            pieces.append((tok.start[0], tok.string, tok.end[0] > tok.start[0]))
    return pieces


def _python_strings(text: str) -> list[list[tuple[int, str, bool]]]:
    """The literal parts of every string literal of a Python source that the string rule reads:
    each `str` or `bytes` constant (its implicitly concatenated tokens together) and each
    f-string or t-string, less what `_not_read` leaves to others. A source that does not parse
    gives none."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        tree = ast.parse(text)
    except (tokenize.TokenError, SyntaxError, ValueError):
        return []
    docs, skipped = _not_read(tree)
    joined = (ast.JoinedStr, getattr(ast, "TemplateStr", ast.JoinedStr))
    parts: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, joined):
            parts.update(id(v) for v in node.values)
        spec = getattr(node, "format_spec", None)  # a field's format spec is part of its field
        if isinstance(spec, ast.AST):
            parts.add(id(spec))
    starts = [t.start for t in tokens]
    literals = []
    for node in ast.walk(tree):
        is_text = isinstance(node, ast.Constant) and isinstance(node.value, str | bytes)
        if not (is_text or isinstance(node, joined)) or id(node) in parts or id(node) in skipped:
            continue
        begin = (node.lineno, node.col_offset)
        end = (node.end_lineno or node.lineno, node.end_col_offset or 0)
        i = bisect.bisect_left(starts, begin)
        span = []
        while i < len(tokens) and tokens[i].start < end:
            span.append(tokens[i])
            i += 1
        literals.append(_literal_pieces(span, docs))
    return literals


def _uncommented_lines(text: str) -> list[list[tuple[int, str, bool]]]:
    """Every line of a shell, TOML or YAML file, or any other text file, that is not a `#`
    comment, without its trailing ` # ` comment: the complement of the comment rule's reading,
    so a command's words, a step's name and a value are read."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        m = TRAILING_COMMENT.search(line)
        out.append([(n, line[: m.start()] if m else line, False)])
    return out


def string_citation_hits(path: Path) -> list[tuple[int, str, str]]:
    """(line, rule, phrase) for each citation of a project document in the string literals of
    one file: a specification's number, the constitution's sections, the word for a research
    write-up, a review dated, numbered or named by its kind, a numbered question of the owner's,
    or a finding a review names. A Python file is read through `ast` and its tokens; any other
    file through its lines that are not comments. Each part of a literal keeps its own line, and
    a part that spans lines adds the newlines before the phrase."""
    text = _text(path)
    if text is None:
        return []
    literals = _python_strings(text) if path.suffix == ".py" else _uncommented_lines(text)
    hits = []
    for pieces in literals:
        joined = "".join(t for _, t, _ in pieces)
        bounds = []
        at = 0
        for line, part, spans in pieces:
            bounds.append((at, line, part, spans))
            at += len(part)
        for rule, pattern in STRING_CITATION_RULES:
            for m in pattern.finditer(joined):
                offset, line, part, spans = next(b for b in reversed(bounds) if b[0] <= m.start())
                if spans:
                    line += part[: m.start() - offset].count("\n")
                hits.append((line, rule, " ".join(m[0].split())))
    return sorted(hits)


def string_citation_files(root: Path, later: Iterable[str] = ()) -> list[Path]:
    """The files the string rule reads: the comment rule's code files (a public page is read
    whole by that rule already), every `.py` under `src/`, and `pyproject.toml`, less those
    whose path from the root matches a pattern of `later`."""
    pages = set(public_pages(root))
    files = [p for p in context_citation_files(root) if p not in pages]
    files += [p for p in files_under(root, "src") if p.suffix == ".py"]
    files += files_under(root, "pyproject.toml")
    return [p for p in files if not any(fnmatch.fnmatch(rel(p, root), g) for g in later)]


# numpy on the set's OpenBLAS: numpy's meson finds step 38's OpenBLAS, a per-file header
# sends numpy's int-declared LAPACK calls to 35 shims of ours, and one OpenBLAS, with no
# lapack_lite, is linked. The rules, pure over text and name sets, need no build.
ONE_LAPACK_CROSS = "recipes/wasi-numpy.cross"
ONE_LAPACK_HEADER = "recipes/numpy_lapack_abi.h"
ONE_LAPACK_MAP = "recipes/numpy_file_includes.txt"
ONE_LAPACK_STEP = "scripts/steps/40_numpy.sh"
ONE_LAPACK_PKGCONF = "pkg-config = '@ROOT@/build/tools/pylib/pkgconf/.bin/pkgconf'"
ONE_LAPACK_MESON = "-Dblas=openblas -Dlapack=openblas -Dallow-noblas=false"
ONE_LAPACK_PREFIX = "#define BLAS_SYMBOL_PREFIX wasi_numpy_"
ONE_LAPACK_ENTRIES = (
    ("linalg/umath_linalg.cpp", "@ROOT@/recipes/numpy_lapack_abi.h", 1),
    ("linalg/lapack_litemodule.c", "@ROOT@/recipes/numpy_lapack_abi.h", 1),
    ("lapack_lite/python_xerbla.c", "@ROOT@/recipes/numpy_lapack_abi.h", 2),
    ("common/python_xerbla.c", "@ROOT@/recipes/numpy_lapack_abi.h", 1),
)
ONE_LAPACK_ARCHIVE = "libopenblas.a"
ONE_LAPACK_SHIMS = "libnumpy_lapack_shims.a"
ONE_LAPACK_XERBLA = "wasi_numpy_xerbla_"
ONE_LAPACK_REQUIRED = ("dgesv_", "dgesdd_", "cblas_dgemm", "xerbla_", "wasi_numpy_dgesv_")
LINK_MAP_SYMBOL = re.compile(r"^\s+-\s+[0-9a-f]+\s+[0-9a-f]+\s+(\S+?)\((.+)\):\(([^)]+)\)$")


def include_map_entries(text: str) -> list[tuple[str, str, int]]:
    """A per-file include map's entries (wasi-cc's format): suffix, header, count (1 if absent)."""
    entries = []
    for line in text.splitlines():
        words = line.split()
        if not words or words[0].startswith("#"):
            continue
        entries.append((words[0], words[1], int(words[2]) if len(words) > 2 else 1))
    return entries


def one_lapack_recipe_errors(
    cross: str, header: str | None, include_map: str, step: str
) -> list[str]:
    """The recipe as written: the numpy cross file names step 10's pkgconf and no
    BLAS_SYMBOL_PREFIX; the header sets numpy's prefix; the per-file map has exactly its four
    entries and counts; step 40 asks meson for OpenBLAS and refuses a fallback."""
    errors = []
    if "BLAS_SYMBOL_PREFIX" in cross:
        errors.append(f"{ONE_LAPACK_CROSS} still names BLAS_SYMBOL_PREFIX")
    if ONE_LAPACK_PKGCONF not in cross:
        errors.append(f"{ONE_LAPACK_CROSS} does not name step 10's pkgconf")
    if header is None:
        errors.append(f"{ONE_LAPACK_HEADER} is missing")
    elif ONE_LAPACK_PREFIX not in header.splitlines():
        errors.append(f"{ONE_LAPACK_HEADER} does not say {ONE_LAPACK_PREFIX!r}")
    got = include_map_entries(include_map)
    if got != list(ONE_LAPACK_ENTRIES):
        errors.append(f"{ONE_LAPACK_MAP} has {got}, not {list(ONE_LAPACK_ENTRIES)}")
    if ONE_LAPACK_MESON not in step:
        errors.append(f"{ONE_LAPACK_STEP} does not pass {ONE_LAPACK_MESON}")
    return errors


def include_log_errors(entries: list[tuple[str, str, int]], log: str | None) -> list[str]:
    """Each per-file entry matched exactly its count of compiles in wasi-cc's log (its first field
    is the matched suffix). A missing log, once a build exists, is a failure."""
    if log is None:
        return ["build/numpy-build/file-includes.log is missing (step 40's per-file include log)"]
    seen = [line.split("\t", 1)[0] for line in log.splitlines() if line.strip()]
    return [
        f"per-file include {suffix} matched {seen.count(suffix)} compiles, not {count}"
        for suffix, _, count in entries
        if seen.count(suffix) != count
    ]


def numpy_blas_record_errors(records: list[dict], objects: list[str]) -> list[str]:
    """numpy's records name no lapack_lite f2c compile, object or BLAS_SYMBOL_PREFIX."""
    errors = []
    for e in records:
        argv = _record_argv(e)
        if re.search(r"lapack_lite/f2c[^/]*\.c$", str(e.get("file", ""))):
            errors.append(f"numpy compiles {e.get('file')}: lapack_lite's f2c LAPACK")
        if any(a.startswith("-DBLAS_SYMBOL_PREFIX") for a in argv):
            errors.append(f"{e.get('file')}: carries -DBLAS_SYMBOL_PREFIX")
    errors += [f"build/numpy-build holds {o}" for o in objects if "lapack_lite_f2c" in o]
    return errors


def numpy_deps_errors(deps: dict[str, list[str]], archive: Path) -> list[str]:
    """Each numpy module's .deps names OpenBLAS, and only as `archive` by path or as -lopenblas
    with -L its folder: one OpenBLAS, scipy's."""
    errors = []
    for name, tokens in deps.items():
        named = [t for t in tokens if "openblas" in t]
        if not named:
            errors.append(f"{name} names no OpenBLAS")
        for t in named:
            if t == "-lopenblas":
                continue
            p = t[2:] if t.startswith("-L") else t
            want = archive.parent if t.startswith("-L") else archive
            if Path(p).resolve() != want.resolve():
                errors.append(f"{name} names {t}, not {want}")
    return errors


def one_lapack_errors(
    map_lines: Iterable[str],
    openblas_defined: set[str],
    shims_defined: set[str],
    called: set[str],
    is_global: Callable[[str, str, str], bool] = lambda archive, member, symbol: True,
) -> list[str]:
    """One OpenBLAS and no lapack_lite in python.wasm's link map: every symbol libopenblas.a defines
    that the link takes comes from that archive, once; no lapack_lite f2c object and no
    numpy_lapack_lite_ symbol; every wasi_numpy_ shim once, from numpy's shims archive, and
    wasi_numpy_xerbla_ once, from numpy's python_xerbla; and the shims defined are exactly the
    wasi_numpy_ names numpy's two linear-algebra objects call, less xerbla. Only global definitions
    count: `is_global(archive, member, symbol)` says whether that member defines the name globally.
    f2c's LAPACK files, OpenBLAS's own among them, and scipy's PROPACK and ARPACK each carry a file-
    local `static` complex dot wrapper named cdotc_ or zdotu_, which the map lists like any function
    but which no other object can call (build phase 2)."""
    errors = []
    sources: dict[str, list[tuple[str, str]]] = {}
    for line in map_lines:
        m = LINK_MAP_SYMBOL.match(line.rstrip("\n"))
        if not m:
            continue
        archive, member, symbol = m[1], m[2], m[3]
        if member.startswith("lapack_lite_f2c"):
            errors.append(f"the link takes {member} from {Path(archive).name}")
        if symbol.startswith("numpy_lapack_lite_"):
            errors.append(f"the link takes {symbol}")
        if symbol in openblas_defined or symbol.startswith("wasi_numpy_"):
            if is_global(archive, member, symbol):
                sources.setdefault(symbol, []).append((archive, member))
    for symbol, where in sorted(sources.items()):
        if len(where) != 1:
            errors.append(f"{symbol} is linked {len(where)} times")
        archive, member = where[0]
        name = archive.replace("\\", "/").rsplit("/", 1)[-1]
        if symbol == ONE_LAPACK_XERBLA:
            if "python_xerbla" not in member:
                errors.append(f"{symbol} comes from {name}({member}), not numpy's python_xerbla")
        elif symbol.startswith("wasi_numpy_"):
            if name != ONE_LAPACK_SHIMS:
                errors.append(f"{symbol} comes from {name}, not {ONE_LAPACK_SHIMS}")
        elif name != ONE_LAPACK_ARCHIVE:
            errors.append(f"{symbol} comes from {name}, not {ONE_LAPACK_ARCHIVE}")
    if not any(s in openblas_defined for s in sources):
        errors.append(f"the link takes no symbol from {ONE_LAPACK_ARCHIVE}")
    errors += [f"the link takes no {s}" for s in ONE_LAPACK_REQUIRED if s not in sources]
    wanted = called - {ONE_LAPACK_XERBLA}
    errors += [f"shim {s} is called by no numpy object" for s in sorted(shims_defined - wanted)]
    errors += [f"numpy calls {s}, which no shim defines" for s in sorted(wanted - shims_defined)]
    return errors


# ---------------------------------------------------------------------------------------------
# A uv project's lock, read as uv reads it

_REQUIREMENT = re.compile(
    r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:@\s*([^;\s]+))?([^;]*)"
)
_SOURCE_TREE = ("directory", "editable", "virtual")


def _dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_pins(pyproject: dict) -> set[tuple[str, str]]:
    """The project's requirements as (name, url or specifier), its uv sources applied, the
    specifier without spaces as uv writes it."""
    sources = pyproject.get("tool", {}).get("uv", {}).get("sources", {})
    urls = {_dist_name(k): v["url"] for k, v in sources.items() if "url" in v}
    pins = set()
    for text in pyproject.get("project", {}).get("dependencies", []):
        m = _REQUIREMENT.match(text)
        name = _dist_name(m[1]) if m else text
        pins.add((name, (m[2] or urls.get(name) or re.sub(r"\s+", "", m[3])) if m else "?"))
    return pins


def _dependency_entries(package: dict) -> list[dict]:
    entries = list(package.get("dependencies", []))
    for table in ("optional-dependencies", "dev-dependencies"):
        for group in package.get(table, {}).values():
            entries += group
    return entries


def lock_errors(lock_text: str, pyproject_text: str) -> list[str]:
    """What keeps uv from taking a lock as its project's: the lock does not parse; a dependency
    entry for a name that several packages share does not name its source, and its version too
    unless the source is a source tree; an entry matches no package, or several; or the root
    package's requirements (names and pins; markers and extras are left out) or Python bound
    differ from the project's. It reads the files only, so it needs no network, cache or
    interpreter."""
    try:
        lock = tomllib.loads(lock_text)
    except tomllib.TOMLDecodeError as e:
        return [f"the lock does not parse: {e}"]
    pyproject = tomllib.loads(pyproject_text)
    packages = lock.get("package", [])
    by_name: dict[str, list[dict]] = {}
    for p in packages:
        by_name.setdefault(_dist_name(p["name"]), []).append(p)
    errors = []
    for p in packages:
        for dep in _dependency_entries(p):
            same = by_name.get(_dist_name(dep["name"]), [])
            tree = any(k in dep.get("source", {}) for k in _SOURCE_TREE)
            if len(same) > 1 and ("source" not in dep or ("version" not in dep and not tree)):
                missing = "source" if "source" not in dep else "version"
                errors.append(
                    f"{p['name']} {p.get('version', '')}: its {dep['name']} entry has no {missing},"
                    f" and {len(same)} packages are named {dep['name']}"
                )
                continue
            found = [
                q
                for q in same
                if dep.get("version", q.get("version")) == q.get("version")
                and dep.get("source", q.get("source")) == q.get("source")
            ]
            if len(found) != 1:
                by = "+".join(k for k in ("version", "source") if k in dep)
                entry = f"{dep['name']} entry by {by}" if by else f"bare {dep['name']} entry"
                errors.append(
                    f"{p['name']} {p.get('version', '')}: its {entry} matches {len(found)} packages"
                )
    project = pyproject.get("project", {})
    root = [p for p in packages if _dist_name(p["name"]) == _dist_name(project.get("name", ""))]
    if len(root) != 1:
        return errors + [f"the lock holds {len(root)} packages named {project.get('name')}"]
    locked = {
        (_dist_name(r["name"]), r.get("url") or re.sub(r"\s+", "", r.get("specifier", "")))
        for r in root[0].get("metadata", {}).get("requires-dist", [])
    }
    wanted = _requirement_pins(pyproject)
    errors += [
        f"the project requires {n} {pin}, the lock does not" for n, pin in sorted(wanted - locked)
    ]
    errors += [
        f"the lock requires {n} {pin}, the project does not" for n, pin in sorted(locked - wanted)
    ]
    if lock.get("requires-python") != project.get("requires-python"):
        errors.append(
            f"the lock's requires-python {lock.get('requires-python')!r} is not the project's"
            f" {project.get('requires-python')!r}"
        )
    return errors


# ---------------------------------------------------------------------------------------------
# A faster release run: a set reused where a cached set is trusted

CACHE_RESTORE = "actions/cache/restore@"
CACHE_SAVE = "actions/cache/save@"
SET_PATH = "wasi-python-set"
REUSE_TRUE = "needs.inputs.outputs.reuse == 'true'"
REUSE_FALSE = "needs.inputs.outputs.reuse != 'true'"
COMPILED = "steps.compile.outcome == 'success'"
# A reused set on Linux; else the published host on the release shape, and arm64 Linux for the
# one compile of a pull request or a push to dev whose key no cache holds.
BUILD_RUNS_ON = (
    "${{ needs.inputs.outputs.reuse == 'true' && 'ubuntu-24.04' || "
    "needs.plan.outputs.rebuild == 'true' && 'macos-15' || 'ubuntu-24.04-arm' }}"
)
SET_SOURCE = (
    "${{ steps.compile.outcome == 'success' && 'built' || "
    "format('reused {0}', needs.inputs.outputs.key) }}"
)
KEY_RUN = 'uv run --no-project python -I release/set_key.py key >> "$GITHUB_OUTPUT"'
DECIDE_STEP = "Reuse only where a cached set is trusted"
SET_CHECK_STEP = "The set is this commit's"
MOVE_STEP = "The reused set in build/artifacts"
ZERO_PATCH_STEP = "The source trees are their tarballs plus the recorded patches"
LOGS_STEP = "Keep the build logs when something fails"
REUSED_KEY = "${{ needs.inputs.outputs.reuse == 'true' && needs.inputs.outputs.key || '' }}"
# A set this run built, on a run that is not a tag's, kept once its build succeeded, and on the
# release shape only once same-bytes matched it with both rebuilds.
SAVE_IF = (
    "${{ !cancelled() && needs.build.result == 'success' && "
    "needs.build.outputs.set-source == 'built' && !startsWith(github.ref, 'refs/tags/') && "
    "(needs.plan.outputs.rebuild != 'true' || needs.same-bytes.result == 'success') }}"
)
CACHE_TRIGGERS = "on:\n  push:\n    branches: [dev]\n  workflow_dispatch:\n"
DISPATCH_INPUT = (
    "  workflow_dispatch:\n    inputs:\n      from-source:\n"
    "        description: build the set from the pins even when a set for this commit is cached\n"
    "        type: boolean\n        default: false\n"
)


def top_env(text: str) -> dict[str, str]:
    """A workflow's top-level `env:`, each value as written, quotes dropped."""
    out: dict[str, str] = {}
    inside = False
    for line in without_comments(text).splitlines():
        if line.startswith("env:"):
            inside = True
            continue
        if inside:
            m = re.fullmatch(r"  ([A-Za-z0-9_]+):\s*(.*?)\s*", line)
            if m:
                out[m[1]] = m[2].strip("\"'")
            elif line and not line.startswith(" "):
                break
    return out


def _step_runs(job_steps: list[dict]) -> list[str]:
    return [str(f.get("run", "")).strip() for f in job_steps]


def _build_step_errors(job: str, job_steps: list[dict]) -> list[str]:
    """A job that builds runs exactly `scripts/00_download.sh` then `scripts/build.sh`, no
    arguments, and no other step names either script, so the key's env is the build's."""
    errors = []
    runs = _step_runs(job_steps)
    for r in runs:
        if ("scripts/build.sh" in r or "scripts/00_download.sh" in r) and r not in (
            "scripts/build.sh",
            "scripts/00_download.sh",
        ):
            errors.append(f"{job}: a step runs {r.splitlines()[0]!r}, not the bare build command")
    if "scripts/build.sh" in runs and (
        "scripts/00_download.sh" not in runs
        or runs.index("scripts/00_download.sh") > runs.index("scripts/build.sh")
    ):
        errors.append(f"{job}: scripts/build.sh does not follow scripts/00_download.sh")
    return errors


def release_reuse_errors(release_text: str, cache_text: str, key_env: Iterable[str]) -> list[str]:
    """The reuse rules on both workflows, one line per breach: where a set may be reused, the
    build job's steps, build-shard, the writers and readers of the cache, and set-cache.yml's
    rules. Where a reused set is trusted is the decision step's script, run by its own rules
    check."""
    errors: list[str] = []
    text = without_comments(release_text)
    jobs = workflow_jobs(text)
    steps = {n: [step_fields(s) for s in workflow_steps(lines)] for n, lines in jobs.items()}
    if DISPATCH_INPUT not in text:
        errors.append("R0: workflow_dispatch has no boolean from-source input, default false")
    # R1: only inputs (a lookup) and build (the restore) read the cache; only save-set writes it.
    for name, job_steps in steps.items():
        for f in job_steps:
            u = f.get("uses", "")
            if u.startswith("actions/cache@"):
                errors.append(f"R1: {name} uses actions/cache itself, not its restore or save")
            if u.startswith(CACHE_RESTORE) and name not in ("inputs", "build"):
                errors.append(f"R1: {name} restores from the cache")
            if u.startswith(CACHE_SAVE) and name != "save-set":
                errors.append(f"R1: {name} saves to the cache")
    # R2: the inputs job: the key, a lookup, and the decision as one script.
    inp = steps.get("inputs", [])
    by_id = {f.get("id"): f for f in inp if f.get("id")}
    lookup = by_id.get("lookup", {})
    decide = by_id.get("decide", {})
    if not inp:
        errors.append("R2: no inputs job")
    else:
        if str(by_id.get("key", {}).get("run", "")).strip() != KEY_RUN:
            errors.append("R2: inputs' key step does not run release/set_key.py key")
        w = lookup.get("with", {})
        if not lookup.get("uses", "").startswith(CACHE_RESTORE) or w != {
            "path": SET_PATH,
            "key": "${{ steps.key.outputs.key }}",
            "lookup-only": "true",
        }:
            errors.append("R2: inputs' lookup is not a lookup-only restore of the key")
        if decide.get("name") != DECIDE_STEP or decide.get("env") != {
            "FROM_SOURCE": "${{ inputs.from-source }}",
            "HIT": "${{ steps.lookup.outputs.cache-hit }}",
            "KEY": "${{ steps.key.outputs.key }}",
        }:
            errors.append("R2: inputs' decision step is not the reuse script with its values")
        if _job_map(jobs["inputs"], "outputs") != {
            "key": "${{ steps.key.outputs.key }}",
            "reuse": "${{ steps.decide.outputs.reuse }}",
        }:
            errors.append("R2: inputs does not hand on key and reuse from its steps")
        if _job_field(jobs["inputs"], "needs") != "plan":
            errors.append("R2: inputs needs another job than the plan")
    # R3: the build job.
    build_lines = jobs.get("build", [])
    build = steps.get("build", [])
    if _job_field(build_lines, "runs-on") != BUILD_RUNS_ON:
        errors.append(f"R3: build's runs-on is not {BUILD_RUNS_ON}")
    if _needs(build_lines) != {"plan", "inputs", "quick"}:
        errors.append("R3: build does not need the plan, inputs and quick alone")
    if _job_map(build_lines, "outputs").get("set-source") != SET_SOURCE:
        errors.append("R3: build's set-source is not made from the compile step's outcome")
    want_if = {}
    for k, f in enumerate(build):
        run, name, uses = str(f.get("run", "")).strip(), f.get("name"), f.get("uses", "")
        if run == "scripts/00_download.sh":
            want_if[k] = REUSE_FALSE
        elif run == "scripts/build.sh":
            want_if[k] = REUSE_FALSE
            if f.get("id") != "compile":
                errors.append("R3: build's scripts/build.sh step is not id: compile")
        elif uses.startswith(CACHE_RESTORE):
            want_if[k] = REUSE_TRUE
            if f.get("with") != {
                "path": SET_PATH,
                "key": "${{ needs.inputs.outputs.key }}",
                "fail-on-cache-miss": "true",
            }:
                errors.append("R3: build's restore is not the key's, failing on a miss")
        elif name == MOVE_STEP:
            want_if[k] = REUSE_TRUE
        elif name == ZERO_PATCH_STEP:
            want_if[k] = COMPILED
        elif name == LOGS_STEP:
            want_if[k] = "failure()"
        else:
            want_if[k] = None
        if f.get("if") != want_if[k]:
            errors.append(f"R3: build's step {name or run or uses!r} has if: {f.get('if')!r}")
    names = [f.get("name") for f in build]
    check = next((f for f in build if f.get("name") == SET_CHECK_STEP), None)
    if check is None:
        errors.append(f"R3: build has no step {SET_CHECK_STEP!r}")
    else:
        run = str(check.get("run", ""))
        if (
            check.get("env") != {"REUSED_KEY": REUSED_KEY}
            or 'release/set_key.py verify build/artifacts --key "$REUSED_KEY"' not in run
            or "release/set_key.py verify build/artifacts\n" not in run
        ):
            errors.append("R3: build's set check does not verify build/artifacts, with the key")
        at = names.index(SET_CHECK_STEP)
        later = [
            k
            for k, f in enumerate(build)
            if str(f.get("run", "")).strip() in ("scripts/build.sh",)
            or f.get("uses", "").startswith(CACHE_RESTORE)
            or f.get("name") == MOVE_STEP
        ]
        wheel = next(
            (k for k, f in enumerate(build) if "cp -R build/artifacts" in str(f.get("run", ""))),
            None,
        )
        if any(k > at for k in later) or wheel is None or wheel < at:
            errors.append("R3: build's set check is not after the set is made and before the wheel")
    if any("--shard" in r for r in _step_runs(build)):
        errors.append("R3: build runs a shard (the build shard is build-shard's)")
    errors += [f"R3: {e}" for e in _build_step_errors("build", build)]
    # R4: build-shard builds from the pins on every run, then the zero-patch step and its shard.
    bs_lines = jobs.get("build-shard")
    if bs_lines is None:
        errors.append("R4: no build-shard job")
    else:
        bs = steps["build-shard"]
        body = "\n".join(bs_lines)
        if _job_field(bs_lines, "runs-on") != "ubuntu-24.04-arm":
            errors.append("R4: build-shard is not on ubuntu-24.04-arm")
        if (
            _job_field(bs_lines, "needs") != "plan"
            or _job_field(bs_lines, "if") != REBUILD_JOBS["build-shard"][2]
        ):
            errors.append("R4: build-shard needs another job than the plan, or runs on another if:")
        if "WASI_PYTHON_ARTIFACTS" in body:
            errors.append("R4: build-shard names WASI_PYTHON_ARTIFACTS")
        if any(f.get("uses", "").startswith("actions/download-artifact@") for f in bs):
            errors.append("R4: build-shard downloads an artifact")
        runs = _step_runs(bs)
        order = ["scripts/00_download.sh", "scripts/build.sh", ZERO_PATCH_STEP, BUILD_SHARD_RUN]
        at = []
        for want in order:
            k = next(
                (k for k, f in enumerate(bs) if runs[k] == want.strip() or f.get("name") == want),
                None,
            )
            at.append(k)
        if None in at or at != sorted(at):
            errors.append("R4: build-shard does not download, build, check the trees, then shard")
        for f in bs:
            if f.get("if") is not None and f.get("name") != LOGS_STEP:
                errors.append(
                    f"R4: build-shard's step {f.get('name') or f.get('run')!r} has an if:"
                )
        zp = next((f for f in bs if f.get("name") == ZERO_PATCH_STEP), {})
        bz = next((f for f in build if f.get("name") == ZERO_PATCH_STEP), {})
        if zp.get("run") != bz.get("run"):
            errors.append("R4: build-shard's zero-patch step is not the build job's, text for text")
        errors += [f"R4: {e}" for e in _build_step_errors("build-shard", bs)]
    # R5: save-set saves only a set this run built (on the release shape, one both rebuilds
    # matched), after its check.
    ss_lines = jobs.get("save-set")
    if ss_lines is None:
        errors.append("R5: no save-set job")
    else:
        ss = steps["save-set"]
        if not {"build", "same-bytes"} <= _needs(ss_lines):
            errors.append("R5: save-set does not need build and same-bytes")
        if _job_field(ss_lines, "if") != SAVE_IF:
            errors.append(f"R5: save-set's if: is not {SAVE_IF}")
        save = next((k for k, f in enumerate(ss) if f.get("uses", "").startswith(CACHE_SAVE)), None)
        verify = next(
            (
                k
                for k, f in enumerate(ss)
                if f"release/set_key.py verify {SET_PATH} --key" in str(f.get("run", ""))
            ),
            None,
        )
        if save is None or verify is None or verify > save:
            errors.append("R5: save-set does not verify the set before it saves it")
        elif ss[save].get("with") != {"path": SET_PATH, "key": "${{ steps.key.outputs.key }}"}:
            errors.append("R5: save-set does not save the set under the key its checkout gives")
    # R6: the gather waits for the proof and is told where the set came from.
    g = jobs.get("gather", [])
    if not {"build-shard", "same-bytes"} <= _needs(g):
        errors.append("R6: gather does not need build-shard and same-bytes")
    # The set-cache workflow, the writer to dev's cache.
    errors += set_cache_errors(cache_text, release_text, key_env)
    return errors


def set_cache_errors(cache_text: str, release_text: str, key_env: Iterable[str]) -> list[str]:
    """set-cache.yml, the writer to dev's cache: its triggers, permissions, uv, env, build steps
    and the order of its check and its save."""
    errors: list[str] = []
    text = without_comments(cache_text)
    m = re.search(r"^on:\n(?:[ ].*\n|\n)*", text, re.M)
    if not m or m[0].rstrip("\n") + "\n" != CACHE_TRIGGERS:
        errors.append("C1: set-cache.yml's triggers are not exactly a push to dev and dispatch")
    top = re.search(r"^permissions:\s*(.*)$", text.split("\njobs:", 1)[0], re.M)
    if not top or top[1].strip() != "{}":
        errors.append("C2: set-cache.yml's workflow-level permissions are not {}")
    jobs = workflow_jobs(text)
    if set(jobs) != {"lookup", "seed"}:
        errors.append(f"C3: set-cache.yml's jobs are {sorted(jobs)}, not lookup and seed")
    for name, lines in jobs.items():
        if _permission_set(lines) != {"contents: read"}:
            errors.append(f"C3: set-cache.yml's {name} permissions are not contents: read")
        js = [step_fields(s) for s in workflow_steps(lines)]
        for f in js:
            if f.get("uses", "").startswith("astral-sh/setup-uv@") and f.get("with") != {
                "version": "${{ env.UV_VERSION }}",
                "enable-cache": "false",
            }:
                errors.append(
                    f"C4: set-cache.yml's {name} runs setup-uv other than pinned, no cache"
                )
            if "${{" in str(f.get("run", "")):
                errors.append(f"C4: set-cache.yml's {name} has ${{{{ in a run: script")
            if f.get("uses", "").startswith(CACHE_SAVE) and name != "seed":
                errors.append(f"C5: set-cache.yml's {name} saves to the cache")
        errors += [f"C6: set-cache.yml's {e}" for e in _build_step_errors(name, js)]
        # A build here saves under dev's key, so it runs under the workflow's env alone, as
        # release.yml's builds do: a variable the key does not hold would make every reader red.
        if any("scripts/build.sh" in r for r in _step_runs(js)):
            if _job_map(lines, "env"):
                errors.append(f"C10: set-cache.yml's {name} builds under a job-level env")
            for f in js:
                if str(f.get("run", "")).strip() in (
                    "scripts/build.sh",
                    "scripts/00_download.sh",
                ) and f.get("env"):
                    errors.append(f"C10: set-cache.yml's {name}'s build step sets env")
    env, release_env = top_env(cache_text), top_env(release_text)
    keyed = {n: release_env.get(n) for n in key_env}
    if env != keyed:
        errors.append("C7: set-cache.yml's env is not the key's env lines as release.yml sets them")
    seed = [step_fields(s) for s in workflow_steps(jobs.get("seed", []))]
    if "scripts/build.sh" not in _step_runs(seed):
        errors.append("C6: set-cache.yml's seed does not build from the pins")
    save = next((k for k, f in enumerate(seed) if f.get("uses", "").startswith(CACHE_SAVE)), None)
    verify = next(
        (k for k, f in enumerate(seed) if "release/set_key.py verify" in str(f.get("run", ""))),
        None,
    )
    if save is None or verify is None or verify > save:
        errors.append("C8: set-cache.yml saves before release/set_key.py verify, or not at all")
    if "needs.lookup.outputs.hit != 'true'" != _job_field(jobs.get("seed", []), "if"):
        errors.append("C9: set-cache.yml's seed does not run only when lookup found nothing")
    return errors


def local_import_files(repo: Path, root: str, modules: Iterable[str]) -> set[str]:
    """Every file under `repo/root` that `modules` import, directly or not, with the packages on
    the way: the judge's own walk, written apart from release/set_key.py's so each checks the
    other."""
    found: set[str] = set()
    todo, seen = list(modules), set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        parts = name.split(".")
        for k in range(1, len(parts) + 1):
            stem = repo / root / Path(*parts[:k])
            path = next(
                (p for p in (stem / "__init__.py", stem.with_suffix(".py")) if p.is_file()), None
            )
            if path is None:
                break
            rel = path.relative_to(repo).as_posix()
            if rel in found:
                continue
            found.add(rel)
            package = (
                ".".join(parts[:k]) if path.name == "__init__.py" else ".".join(parts[: k - 1])
            )
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Import):
                    todo += [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    if n.level:
                        up = package.split(".")[: len(package.split(".")) - n.level + 1]
                        base = ".".join([*up, n.module] if n.module else up)
                    else:
                        base = n.module or ""
                    todo += [base, *(f"{base}.{a.name}" for a in n.names)]
    return found


# Names the build looks up at the checkout's root, found by a traced build from the pins on arm64
# Linux, none of them tracked today: CPython's make probes its source folders and RCS/SCCS one
# level above its source tree, git reads .mailmap, uv looks for uv.toml, the host Python for
# lib/python315.zip, a linker probe writes a.out where it runs, and two tools name "-" and
# "<stdin>". A tracked file at one of them would change the build without changing the key.
TRACED_ROOT_LOOKUPS = (
    "-",
    ".mailmap",
    "<stdin>",
    "Include",
    "Lib",
    "Misc",
    "Modules",
    "Objects",
    "Parser",
    "Programs",
    "Python",
    "RCS",
    "SCCS",
    "Tools",
    "a.out",
    "lib",
    "uv.toml",
)


def set_key_errors(
    closure: Iterable[str],
    tracked: Iterable[str],
    texts: dict[str, str],
    release_text: str,
    key_env: Iterable[str],
    gate_root: str,
    gates: Iterable[str],
    tests_names: Iterable[str],
    gate_imports: Iterable[str] = (),
    root_names: Iterable[str] = (),
    pyproject_text: str = "",
    members: dict[str, str] | None = None,
) -> list[str]:
    """The first layer of the key's proof: what the set's key (release/set_key.py) must hold,
    one line per input it leaves out. `tracked` is every tracked file under scripts/ and
    recipes/; `texts` their text; `tests_names` the top-level names under the gate root (files
    and folders); `gate_imports` the files `local_import_files` finds for the gates;
    `root_names` the top-level names of every tracked file; `pyproject_text` pyproject.toml;
    `members` each workspace member's path and its project's name (`workspace_members`)."""
    import sys

    errors: list[str] = []
    held = set(closure)
    if "downloads/SHA256SUMS" not in held:
        errors.append("K9: downloads/SHA256SUMS, every pin, is not in the key")
    for rel in sorted(set(gate_imports) - held):
        errors.append(f"K8: {rel} is imported by the build's gate and not in the key")
    for rel in tracked:
        if rel not in held:
            errors.append(f"K1: {rel} is tracked under scripts/ or recipes/ and not in the key")
    roots = set()
    for rel, text in texts.items():
        for m in re.finditer(r'PYTHONPATH="?(?:\$HERE|\$\{HERE\})/([\w./-]+)', text):
            roots.add(m[1])
        for m in re.finditer(
            r'PYTHONPATH="?(?:\$HERE|\$\{HERE\})/([\w./-]+)[^\n]*?\s-m\s+([\w.]+)', text
        ):
            if m[1].split("/")[0] in GENERATED_ROOTS:  # the build's own tools, pinned by hash
                continue
            if m[1] != gate_root:
                errors.append(f"K3: {rel} runs -m {m[2]} with PYTHONPATH {m[1]}, not {gate_root}")
            elif m[2] not in set(gates):
                errors.append(f"K3: {rel} runs -m {m[2]} from {m[1]}/, which the key does not hold")
        for line in text.splitlines():
            for token in PATH_TOKEN.findall(line):
                token = token.rstrip(".").rstrip("/")
                if token.split("/")[0] in GENERATED_ROOTS or token in roots:
                    continue
                if token in held or any(h.startswith(token + "/") for h in held):
                    if token not in held:  # a folder: every tracked file under it must be held
                        under = [t for t in tracked if t.startswith(token + "/")]
                        errors += [
                            f"K2: {rel} names {token}/, and {t} is not in the key"
                            for t in under
                            if t not in held
                        ]
                    continue
                errors.append(f"K2: {rel} names {token}, which the key does not hold")
    env = top_env(release_text)
    if set(env) != set(key_env):
        errors.append(
            f"K4: release.yml's top-level env {sorted(env)} is not the key's {sorted(key_env)}"
        )
    for name in key_env:
        value = env.get(name, "")
        if "/" in value and value not in held:
            errors.append(f"K5: {name}={value} names a file the key does not hold")
    text = without_comments(release_text)
    for job, lines in workflow_jobs(text).items():
        js = [step_fields(s) for s in workflow_steps(lines)]
        if not any("scripts/build.sh" in r for r in _step_runs(js)):
            continue
        if _job_map(lines, "env"):
            errors.append(f"K4: {job} builds under a job-level env: the key does not hold")
        for f in js:
            if str(f.get("run", "")).strip() in (
                "scripts/build.sh",
                "scripts/00_download.sh",
            ) and f.get("env"):
                errors.append(f"K4: {job}'s build step sets env: the key does not hold")
        errors += [f"K6: {e}" for e in _build_step_errors(job, js)]
    bad = set(sys.stdlib_module_names) | {"sitecustomize", "usercustomize"}
    for name in tests_names:
        stem = name.removesuffix(".py")
        if stem in bad:
            errors.append(
                f"K7: {gate_root}/{name} would be imported by the gate ahead of the stdlib"
            )
    for name in sorted(set(root_names) & set(TRACED_ROOT_LOOKUPS)):
        errors.append(
            f"K10: {name} is tracked at the checkout's root, where the build looks it up, and the"
            " key does not hold it"
        )
    # Read as TOML, so a [tool.uv] table, a dotted uv key under [tool] and an inline uv table
    # are one case; an unparsable file is named, since uv would refuse it too.
    try:
        tool = tomllib.loads(pyproject_text).get("tool", {})
    except tomllib.TOMLDecodeError as e:
        errors.append(f"K11: pyproject.toml does not parse as TOML: {e}")
        tool = {}
    if "uv" in tool:
        errors += _uv_table_errors(tool["uv"], members or {})
    return errors


def workspace_members(repo: Path, pyproject_text: str) -> dict[str, str]:
    """Each path pyproject.toml's [tool.uv.workspace] lists, with its own project's name (empty
    when it has none)."""
    try:
        uv = tomllib.loads(pyproject_text).get("tool", {}).get("uv", {})
    except tomllib.TOMLDecodeError:
        return {}
    listed = uv.get("workspace", {}).get("members", []) if isinstance(uv, dict) else []
    out = {}
    for rel in listed if isinstance(listed, list) else []:
        f = repo / str(rel) / "pyproject.toml"
        name = (
            tomllib.loads(f.read_text()).get("project", {}).get("name", "") if f.is_file() else ""
        )
        out[str(rel)] = str(name)
    return out


# The two [tool.uv] tables only uv's project commands read: the workspace's members, and sources
# that point a dependency at one of them. The build's uv runs `uv pip install -r <file>` alone,
# which reads uv's settings from the checkout's root (an index, a find-links folder) but neither
# of these, so they leave the set's bytes alone; every other key under [tool.uv] is a setting.
UV_PROJECT_TABLES = ("workspace", "sources")


def _uv_table_errors(uv: object, members: dict[str, str]) -> list[str]:
    """K11's findings for pyproject.toml's [tool.uv]: anything but a workspace of members and
    sources that name a workspace member, by the member's own project name."""
    k11 = (
        "K11: pyproject.toml's [tool.uv] has {}, which the build's uv reads from the checkout's"
        " root, and the key does not hold pyproject.toml"
    )
    if not isinstance(uv, dict):
        return [k11.format("a value that is not a table")]
    errors = [k11.format(f"the setting {k}") for k in sorted(set(uv) - set(UV_PROJECT_TABLES))]
    workspace = uv.get("workspace", {})
    if not isinstance(workspace, dict) or set(workspace) - {"members"}:
        errors.append(k11.format("a workspace table with more than its members"))
    sources = uv.get("sources", {})
    for name, source in sources.items() if isinstance(sources, dict) else [("?", None)]:
        if source != {"workspace": True}:
            errors.append(k11.format(f"the source {name}, which is not a workspace member"))
        elif _dist_name(str(name)) not in {_dist_name(n) for n in members.values() if n}:
            errors.append(k11.format(f"the source {name}, which names no workspace member"))
    return errors


# ---------------------------------------------------------------------------------------------
# The build's inputs, read by their pins; the release's tarball, checked file by file

# A pin looked up by a pattern: `grep "  <name>$" …SHA256SUMS`, where a `.` in the name matches any
# character, so an unpinned name can pass on another name's line. Pins are selected by their exact
# name field instead (scripts/steps/common.sh's pin_line).
PIN_GREP = re.compile(r"""\bgrep\b[^|;]*["'] +\$""")
# The same in awk: the name field matched as a regular expression, not compared as text.
PIN_AWK_MATCH = re.compile(r"\$2\s*~")


def pin_lookup_hits(files: Iterable[Path], root: Path) -> list[str]:
    """Every shell line that selects a line of SHA256SUMS by a pattern: `grep " $…"` (any number of
    spaces) on a line naming SHA256SUMS, or an awk `$2 ~` match in a script that reads it (an awk
    program spans lines, so the file is the unit there)."""
    hits = []
    for p in files:
        if not is_shell(p):
            continue
        reads_pins = "SHA256SUMS" in (_text(p) or "")
        for n, line in _code_lines(p):
            if (PIN_GREP.search(line) and "SHA256SUMS" in line) or (
                reads_pins and PIN_AWK_MATCH.search(line)
            ):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


# Meson never downloads: a wrap that pkg-config does not satisfy fails the configure instead of
# cloning. Every configure passes common.sh's MESON_WRAP; step 37's HarfBuzz keeps its own stricter
# default (nofallback, which refuses a local subproject too). Contourpy's configure is the one
# exemption: its sdist ships no wrap file and no subprojects folder, so it has nothing to fetch,
# and it writes meson's options into a file that ships, so the flag would change the zip. The
# exemption holds only for the sdist that was checked; a new contourpy is checked again first.
MESON_WRAP_LINE = re.compile(r'^MESON_WRAP="?--wrap-mode=nodownload"?\s*$', re.M)
MESON_SETUP = re.compile(r'\bmeson\s+setup\b|"\$MESON"\s+setup\b')
WRAP_ASSIGNMENT = re.compile(r"(?<![\w$-])wrap=(\S*)")
WRAP_MODES = ("--wrap-mode=nofallback", "--wrap-mode=nodownload")
CONTOURPY_STEP = "55_matplotlib.sh"
CONTOURPY_SETUP = "contourpy-build"
CONTOURPY_CHECKED = "1.4.0"
CONTOURPY_VERSION = re.compile(r"\bcontourpy-(\d+(?:\.\d+)*)")


def meson_wrap_errors(steps: dict[str, str]) -> list[str]:
    """`steps` maps each file name under scripts/steps/ to its text. One line per configure that
    could fetch a subproject, per `wrap=` that names another mode, and for common.sh's variable."""
    errors = []
    if not MESON_WRAP_LINE.search(steps.get("common.sh", "")):
        errors.append('common.sh does not set MESON_WRAP="--wrap-mode=nodownload"')
    setups = 0
    for name, text in sorted(steps.items()):
        code = [
            (n, s) for n, s in enumerate(text.splitlines(), 1) if not s.lstrip().startswith("#")
        ]
        for n, line in code:
            for m in WRAP_ASSIGNMENT.finditer(line):
                if m[1].strip("\"'") not in WRAP_MODES:
                    errors.append(f"{name}:{n}: wrap={m[1]} is not nofallback or nodownload")
            if not MESON_SETUP.search(line):
                continue
            setups += 1
            if "$MESON_WRAP" in line:
                continue
            if name == CONTOURPY_STEP and CONTOURPY_SETUP in line:
                found = set(CONTOURPY_VERSION.findall(text))
                if found != {CONTOURPY_CHECKED}:
                    errors.append(
                        f"{name}:{n}: contourpy's configure is exempt only for contourpy-"
                        f"{CONTOURPY_CHECKED}, whose sdist was checked for wrap files; this step"
                        f" unpacks {', '.join(sorted(found)) or 'no contourpy'}"
                    )
                continue
            errors.append(f"{name}:{n}: a meson configure without $MESON_WRAP")
    if not setups:
        errors.append("no meson setup line under scripts/steps/")
    return errors


# curl keeps HTTPS: on the first request, on every redirect, and at TLS 1.2 or later.
# A command word: at the start, after a separator or a keyword, or after a prefix that runs the next
# word as a command (`!`, `command`, `sudo`, `env`, `timeout N`, a variable assignment).
COMMAND_START = (
    r"(?:^|[;&|(`]|\$\(|\bthen\b|\bdo\b|\bexec\b|\brun:|\bif\b|\bwhile\b|\buntil\b|!|"
    r"\bcommand\b|\bsudo\b|\benv\b|\btimeout\s+\S+|\b[A-Za-z_]\w*=\S*)"
)
CURL_COMMAND = re.compile(COMMAND_START + r"\s*curl(?=\s|$)")
# wget has no way to refuse a redirect off HTTPS, so the fetches use curl alone.
WGET_COMMAND = re.compile(COMMAND_START + r"\s*wget(?=\s|$)")
CURL_FLAGS = ("--proto '=https'", "--proto-redir '=https'", "--tlsv1.2")


def curl_lines(text: str, command: re.Pattern[str] = CURL_COMMAND) -> list[tuple[int, str]]:
    """The curl commands (or those `command` matches) of a shell script or a workflow,
    `\\`-continued lines joined, comments and `curl --version` left out; each with the number of
    its first line."""
    out, start, held = [], 0, ""
    for n, line in enumerate(text.splitlines(), 1):
        if not held:
            start = n
            if line.lstrip().startswith("#"):
                continue
        if line.rstrip().endswith("\\"):
            held += line.rstrip()[:-1] + " "
            continue
        logical, held = held + line, ""
        if command.search(logical) and not re.search(r"\bcurl\s+--version\b", logical):
            out.append((start, logical))
    return out


def curl_flag_errors(files: Iterable[Path], root: Path) -> list[str]:
    """Every curl command in `files` that does not keep HTTPS at TLS 1.2, and every wget command."""
    errors = []
    for p in files:
        text = _text(p) or ""
        for n, line in curl_lines(text):
            missing = [flag for flag in CURL_FLAGS if flag not in line]
            if missing:
                errors.append(f"{rel(p, root)}:{n}: curl without {', '.join(missing)}")
        for n, _ in curl_lines(text, WGET_COMMAND):
            errors.append(f"{rel(p, root)}:{n}: wget, which cannot be held to HTTPS on a redirect")
    return errors


# Every read of a download goes through its pin. In scripts/assemble_artifacts.py the downloads
# folder is `d`; a read of a path built from it is a hit unless it is inside the function that
# checks the pin first, or it reads the pin list itself.
READ_METHODS = frozenset({"read_bytes", "read_text", "open"})
READ_FUNCTIONS = frozenset({"open", "ZipFile"})


def _names(node: ast.AST, name: str, reader: str) -> bool:
    """Whether `node` uses `name` other than as an argument of a call to `reader` (bytes that
    call has already checked)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == reader:
        return False
    if isinstance(node, ast.Name):
        return node.id == name
    return any(_names(child, name, reader) for child in ast.iter_child_nodes(node))


def _pin_list(node: ast.AST, folder: str) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.left, ast.Name)
        and node.left.id == folder
        and isinstance(node.right, ast.Constant)
        and node.right.value == "SHA256SUMS"
    )


def _read_target(call: ast.Call) -> ast.expr | None:
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr in READ_METHODS:
        return f.value
    named = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
    if named in READ_FUNCTIONS and call.args:
        return call.args[0]
    return None


def downloads_read_hits(
    text: str, where: str, folder: str = "d", reader: str = "pinned_bytes"
) -> list[str]:
    """Every `read_bytes`, `read_text`, `open` or `ZipFile` of a path built from `folder` outside
    the function `reader`, but the pin list `folder / "SHA256SUMS"`."""
    hits: list[str] = []

    def visit(node: ast.AST, inside: bool) -> None:
        for child in ast.iter_child_nodes(node):
            now = inside or (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == reader
            )
            if isinstance(child, ast.Call) and not now:
                target = _read_target(child)
                if (
                    target is not None
                    and _names(target, folder, reader)
                    and not _pin_list(target, folder)
                ):
                    hits.append(f"{where}:{child.lineno}: {ast.unparse(child)[:90]}")
            visit(child, now)

    visit(ast.parse(text), False)
    return hits


# The same-bytes job binds every file inside the set's tarball, not only its index: each file is
# checked against the inner SHA256SUMS, nothing else is in the tarball (a nested SHA256SUMS or a
# symlink cannot hide), and every published file is among the listed names.
SAME_BYTES_JOB = "same-bytes"
SAME_BYTES_STEP = "Every rebuild's SHA256SUMS is the set's, byte for byte"
SAME_BYTES_UNPACK = "tar -xJf release-assets/*.tar.xz -C set"
SAME_BYTES_SHAPES = (
    ("cd set/wasi-python-*", "does not check inside the unpacked set"),
    ("sha256sum --strict -c SHA256SUMS", "does not run sha256sum --strict -c SHA256SUMS"),
    ("awk '{print $2}' SHA256SUMS | LC_ALL=C sort", "does not list SHA256SUMS's names"),
    (
        "find . -mindepth 1 ! -type d ! -path ./SHA256SUMS",
        "does not list every file present but the index",
    ),
    ('"$listed" != "$present"', "does not compare the listed names with the files present"),
    ("find set -type l", "does not refuse a symlink"),
)


def same_bytes_inner_errors(text: str, artifact_files: Iterable[str]) -> list[str]:
    """The same-bytes step's check of every inner file, one line per missing part."""
    jobs = workflow_jobs(without_comments(text))
    step = next(
        (
            f
            for f in (step_fields(s) for s in workflow_steps(jobs.get(SAME_BYTES_JOB, [])))
            if f.get("name") == SAME_BYTES_STEP
        ),
        None,
    )
    if step is None or not isinstance(step.get("run"), str):
        return [f"{SAME_BYTES_JOB} has no step {SAME_BYTES_STEP!r} with a run: script"]
    run = step["run"]
    errors = []
    unpack = run.find(SAME_BYTES_UNPACK)
    if unpack < 0:
        errors.append(f"the same-bytes step does not run {SAME_BYTES_UNPACK!r}")
    for shape, why in SAME_BYTES_SHAPES:
        at = run.find(shape)
        if at < 0 or at < unpack:
            errors.append(f"the same-bytes step {why} (after the unpack)")
    link, enter = run.find("find set -type l"), run.find("cd set/wasi-python-*")
    if link >= 0 and enter >= 0 and link > enter:
        errors.append(
            "the same-bytes step refuses a symlink only after it enters the set's folder, which"
            " can itself be a symlink"
        )
    for name in [*artifact_files, "LICENSES/"]:
        if name == "SHA256SUMS":
            continue
        if not re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w.-])", run):
            errors.append(f"the same-bytes step does not require {name} among the listed names")
    return errors


# The build job checks the set again just before it packs the release assets: the wheel's copy
# and the zero-patch step run in between, and what is packed is what was checked.
RELEASE_ASSETS_STEP = "Release assets"
REVERIFY = "release/set_key.py verify build/artifacts"
PACK = "release/version.py assets build/artifacts"


def producer_reverify_errors(text: str) -> list[str]:
    """The build job's "Release assets" step verifies build/artifacts first, then packs it, and
    comes after the zero-patch step."""
    build = [
        step_fields(s)
        for s in workflow_steps(workflow_jobs(without_comments(text)).get("build", []))
    ]
    names = [f.get("name") for f in build]
    if RELEASE_ASSETS_STEP not in names:
        return [f"build has no step {RELEASE_ASSETS_STEP!r}"]
    at = names.index(RELEASE_ASSETS_STEP)
    run = str(build[at].get("run", ""))
    commands = [line.strip() for line in run.splitlines() if line.strip()]
    errors = []
    if not commands or REVERIFY not in commands[0]:
        errors.append(f"{RELEASE_ASSETS_STEP!r} does not run {REVERIFY} first")
    if not any(PACK in c for c in commands[1:]):
        errors.append(f"{RELEASE_ASSETS_STEP!r} does not pack the set after verifying it")
    if ZERO_PATCH_STEP not in names or names.index(ZERO_PATCH_STEP) > at:
        errors.append(f"{RELEASE_ASSETS_STEP!r} does not come after the zero-patch step")
    return errors
