"""Repository scanners behind the `rules` and `v1.5` checks. Each returns a list of findings,
one line each; an empty list means the rule holds."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from harness import paths

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
# Constitution §4.5: no embedder names in code


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
            low = line.lower()
            if any(name in low for name in names):
                hits.append(f"{r}:{n}")
    return hits


# ---------------------------------------------------------------------------------------------
# Constitution §4.9: no test reads a clock

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
    """An install that cannot fetch: from local, hash-checked files only (spec 003, Decision 13).
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
GET = re.compile(r"^\s*(?:get|research)\s+(https?://\S+)(?:\s+(\S+))?", re.M)


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
CPP_EH_AGAINST = ("'-fno-exceptions'", "'-wasm-use-legacy-eh=true'", "'-fno-wasm-exceptions'")


def cpp_exception_errors(root: Path) -> list[str]:
    """Every C++ object is compiled, and the binary linked, for standard-form exceptions (spec 005,
    Decision 9): a cross file without the flags compiles C++ whose `throw` is never caught."""
    errors = []
    for cross in ("recipes/wasi-numpy.cross", "recipes/wasi-pandas.cross"):
        lines = [t for t in (root / cross).read_text().splitlines() if t.startswith("cpp_args")]
        if len(lines) != 1:
            errors.append(f"{cross}: {len(lines)} cpp_args lines, not 1")
            continue
        errors += [f"{cross}: cpp_args lacks {f}" for f in CPP_EH_FLAGS if f not in lines[0]]
        errors += [f"{cross}: cpp_args has {f}" for f in CPP_EH_AGAINST if f in lines[0]]
    link = (root / "scripts/steps/60_link.sh").read_text().splitlines()
    if not any("-lunwind" in t and t.lstrip().startswith("echo") for t in link):
        errors.append("scripts/steps/60_link.sh: Setup.local does not link -lunwind")
    flag = 'LDFLAGS_NODIST="-fwasm-exceptions"'
    for target in ("make -j8 all", "make -n python.wasm"):
        calls = [t for t in link if t.lstrip().startswith(target)]
        if not calls or not all(flag in t for t in calls):
            errors.append(f"scripts/steps/60_link.sh: `{target}` without {flag}")
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
# How a check reports its findings (spec 002, Decision 4)


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
