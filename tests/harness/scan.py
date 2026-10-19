"""Repository scanners behind the `rules` and `v1.5` checks. Each returns a list of findings,
one line each; an empty list means the rule holds."""

from __future__ import annotations

import ast
import fnmatch
import json
import posixpath
import re
import shlex
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

from harness import history, paths

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
            if p.suffix == ".patch" and not _our_patch_line(line):
                continue  # a patch's context and removed lines are upstream's text (spec 020)
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
    through `remove`, which retries (spec 018)."""
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
)
# kiwisolver's C++ is compiled by step 55 itself: its flags variable, and the compile that uses it.
CPP_DIRECT = "scripts/steps/55_matplotlib.sh"
CPP_EH_AGAINST = ("'-fno-exceptions'", "'-wasm-use-legacy-eh=true'", "'-fno-wasm-exceptions'")
CPP_SETUP_CROSS = '--cross-file "$B/wasi-matplotlib.cross"'


def cpp_exception_errors(root: Path) -> list[str]:
    """Every C++ object is compiled, and the binary linked, for standard-form exceptions (spec 005,
    Decision 9): a cross file without the flags compiles C++ whose `throw` is never caught. Every
    C++ build is judged (spec 023): numpy's and pandas' cross files, HarfBuzz's (step 37),
    matplotlib's, kiwisolver's compile line in step 55, and contourpy's configure there, with
    matplotlib's cross file (spec 043)."""
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
    # contourpy's C++ is configured by step 55 with matplotlib's cross file (spec 043, Decision 4):
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


# FreeType's licence (docs/FTL.TXT, §2): a binary distribution says this in its documentation.
FREETYPE_CREDIT = (
    "Portions of this software are copyright © 2026 The FreeType Project "
    "(https://freetype.org). All rights reserved."
)


def credit_errors(readme: str, pinned: Iterable[str]) -> list[str]:
    """The credit lines the linked libraries' licences ask of the distribution's documentation
    (spec 023's build review, F1): the README, which is also the wheel's description, carries
    FreeType's while FreeType is pinned. Line breaks and a blockquote's `>` are read as spaces."""
    text = " ".join(re.sub(r"^\s*>\s?", "", line) for line in readme.splitlines()).split()
    if any(n.lower().startswith("freetype-") for n in pinned) and FREETYPE_CREDIT not in " ".join(
        text
    ):
        return [f"README.md does not say FreeType's credit line: {FREETYPE_CREDIT!r}"]
    return []


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


# ---------------------------------------------------------------------------------------------
# The release workflow's provenance (spec 009)

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
    """Every rule of spec 009, Decision 6, as one line per breach, on the workflow without its
    comments; attest and publish also need gather (spec 063, Decision 13)."""
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
    if re.search(r"\|\||set \+e", body):
        errors.append("a step of attest swallows a failure (|| or set +e)")
    if re.search(r"setup-uv|uv run", body):
        errors.append("attest runs setup-uv or uv")
    order = [
        next((i for i, line in enumerate(attest) if marker in line), None)
        for marker in ("actions/download-artifact@", "actions/attest@", "gh attestation verify")
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
# The build hosts (spec 012, Decision 1)

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
# The compiler each host runs (spec 040, Decision 4; spec 059, Decisions 3 and 4): each host's own
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
    """Every rule of spec 059, Decision 4's rule check (spec 040, Decision 7, amended), one line
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
# Every compile contracts nothing (spec 059, Decisions 1, 2 and 4): -ffp-contract=off lives in the
# toolchain's own clang.cfg and clang++.cfg, written by step 10, and nothing on any compiler's
# command line may override it.

# The options that override or drop the configuration file (the pre-build review's F1), as whole
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
# record the judge reads; a specification that adds a meson build extends this (spec 059, N2).
MESON_BUILDS = (
    "numpy-build",
    "pandas-build",
    "freetype-build",
    "harfbuzz-build",
    "sheenbidi-build",
    "libraqm-build",
    "matplotlib-build",
    "contourpy-build",  # spec 043
)
# The Makefiles autoconf generates for the C libraries (libxml2's and libxslt's: spec 046), and
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
# A source pragma that turns contraction back on inside a block (the pre-build review's F5).
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
    variable's value is a hit too (the build review's finding 1)."""
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
    or clang++ among its whole tokens (the review's N1: wasmtime's `--config` on a line that runs
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


# The release workflow's steps, read as text (the judge has no YAML library; spec 009, Decision 6)


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
    workflow without it (an empty script would exit 0; spec 057's review, F5.4)."""
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
# The release workflow's rebuilds (spec 012, Decision 7; specs 040 and 059; spec 057, Decision 4)

# One job per host, so each job's outputs are its own (a matrix shares one output namespace;
# spec 057's pre-build review, F2): arm64 Linux and x86_64 Linux, each compiling with its own
# pinned clang (spec 059). Each job's time limit, in minutes: both rebuild natively, and a hung
# job frees the gate after two hours (spec 059, Decision 5).
REBUILD_JOBS = {
    "rebuild-linux-arm64": ("ubuntu-24.04-arm", 120),
    "rebuild-linux-x86-64": ("ubuntu-24.04", 120),
}
REBUILD_RUNNERS = tuple(runner for runner, _ in REBUILD_JOBS.values())


def _needs(lines: list[str]) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", _job_field(lines, "needs") or ""))


def _rebuild_shape(lines: list[str]) -> str:
    """A rebuild job with its runner named by one placeholder and its name, runner and time limit
    set aside: the two jobs must be this text alike (the longer runner name goes first)."""
    kept = [line for line in lines if not re.match(r"    (name|runs-on|timeout-minutes):", line)]
    body = "\n".join(kept)
    for runner in sorted(REBUILD_RUNNERS, key=len, reverse=True):
        body = body.replace(runner, "@RUNNER@")
    return body


def rebuild_gate_errors(text: str) -> list[str]:
    """Every rule of spec 012, Decision 7, as spec 040 and spec 057 (Decision 4) left it, one line
    per breach, on the workflow without its comments: a rebuild job on each gated runner beside the
    build, the two alike, each handing on its uploads' ids; a same-bytes job that downloads each by
    id into that runner's folders and compares every rebuild's SHA256SUMS with the set's byte for
    byte; and nothing signed or published before it."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    same = jobs.get("same-bytes")
    errors = [f"no {job} job" for job in (*REBUILD_JOBS, "same-bytes") if not jobs.get(job)]
    if errors:
        return errors
    for job, (runner, minutes) in REBUILD_JOBS.items():
        lines = jobs[job]
        body = "\n".join(lines)
        if _job_field(lines, "runs-on") != runner:
            errors.append(f"{job} does not run on {runner}")
        if _job_field(lines, "timeout-minutes") != str(minutes):
            errors.append(f"{job}'s timeout-minutes is not {minutes}")
        # The core count beside every time figure, and any binfmt_misc entry that would run an
        # aarch64 ELF through the runner's own qemu and hide a gap in the launcher's closure.
        # The runner's own python3, which step 10's shim keeps out of the build (spec 079), named
        # in the log (spec 085; the a7 security review's N5).
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
        if outputs != {
            "sums-id": "${{ steps.sums.outputs.artifact-id }}",
            "wheel-id": "${{ steps.wheel.outputs.artifact-id }}",
        }:
            errors.append(f"{job}'s outputs are not sums-id and wheel-id from its two uploads")
    for name in (*REBUILD_JOBS, "same-bytes"):
        lines = jobs[name]
        if _job_field(lines, "if") is not None:
            errors.append(f"{name} has a job-level if: (a dry run must run it)")
        if (_permission_set(lines) or set()) - {"contents: read"}:
            errors.append(f"{name}'s permissions are more than contents: read")
        if re.search(r"^    continue-on-error:", "\n".join(lines), re.M):
            errors.append(f"{name} has a job-level continue-on-error:")
    shapes = {_rebuild_shape(jobs[job]) for job in REBUILD_JOBS}
    if len(shapes) != 1:
        errors.append("the rebuild jobs differ beyond their runner, its time limit and names")
    if not {"build", *REBUILD_JOBS} <= _needs(same):
        errors.append("same-bytes does not need build and both rebuild jobs")
    same_body = "\n".join(line for line in same if not line.startswith("    runs-on:"))
    # One operand a rebuild's download, the other not: comparing the set's file with itself, or
    # one rebuild with another, proves nothing (spec 012's build review, mutation M18).
    pairs = re.findall(r"\bcmp\s+(\S+)\s+(\S+)", same_body)
    if not any(("rebuilds/" in a) != ("rebuilds/" in b) for a, b in pairs):
        errors.append("same-bytes does not compare a rebuild's SHA256SUMS with the set's (cmp)")
    # Each job's id into its own runner's folder, pairing artifact-ids with the path: of the same
    # with: block; one job's id in the other's folder fails (spec 057's Confirmation, M5).
    fetched = {
        (w.get("artifact-ids"), w.get("path"))
        for f in map(step_fields, workflow_steps(same))
        if f.get("uses", "").startswith("actions/download-artifact@")
        for w in [f.get("with", {})]
    }
    for job, (runner, _) in REBUILD_JOBS.items():
        for output, folder, what in (
            ("sums-id", "rebuilds", "SHA256SUMS"),
            ("wheel-id", "rebuilt-wheels", "rebuilt wheel"),
        ):
            if (f"${{{{ needs.{job}.outputs.{output} }}}}", f"{folder}/{runner}") not in fetched:
                errors.append(
                    f"same-bytes does not download {job}'s {what} by id into {folder}/{runner}"
                )
    # Both of same-bytes' loops, the set's SHA256SUMS and spec 016's wheel, run over every runner.
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
    if re.search(r"\|\||set \+e", same_body):
        errors.append("a step of same-bytes swallows a failure (|| or set +e)")
    for name in ("attest", "publish"):
        if "same-bytes" not in _needs(jobs.get(name, [])):
            errors.append(f"{name} does not need same-bytes")
    return errors


# ---------------------------------------------------------------------------------------------
# What is checked, signed and published is what the build job made (spec 057)

ASSETS_ID = "${{ needs.build.outputs.assets-id }}"
# A download's `path:` with a leading workspace expression dropped (spec 070, Decision 1).
WORKSPACE_PREFIX = re.compile(r"^\$\{\{\s*github\.workspace\s*\}\}/+")

SUMS_SHA256 = "${{ needs.build.outputs.sums-sha256 }}"
CHECK_STEP = "These are the bytes the build job made"
GUARD_TEST = '"" | *[!0-9]*)'
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
ENVIRONMENTS = {"publish": "release", "pypi": "pypi"}
PYPI_IF = TAG_ONLY + " && vars.PYPI_PUBLISH == 'true'"
JOB_PERMISSIONS = {
    "build": {"contents: read"},
    **{job: {"contents: read"} for job in REBUILD_JOBS},
    "same-bytes": set(),
    "verify": {"contents: read"},
    # Spec 063: the judge jobs check out and read the build's files; the gather checks out alone.
    **{job: {"contents: read"} for job in ("judge-macos", "judge-linux", "judge-windows")},
    "gather": {"contents: read"},
    "attest": ATTEST_PERMISSIONS,
    "publish": {"contents: write"},
    "pypi": {"id-token: write"},
}


def _guard_tests(run: str, var: str) -> bool:
    """The guard's script tests `var` itself: `case "$var"` with the refusing branch, or a `for`
    loop that lists `"$var"` and tests its loop variable so (spec 057's Confirmation, M1)."""
    branch = re.escape(GUARD_TEST) + r"[^\n]*\bexit 1\b"
    if re.search(rf'case "\${re.escape(var)}" in\s*\n\s*{branch}', run):
        return True
    for m in re.finditer(r"for (\w+) in ([^;\n]*); do\n(.*?)\n\s*done", run, re.S):
        if f'"${var}"' in m[2].split() and re.search(rf'case "\${m[1]}" in\s*\n\s*{branch}', m[3]):
            return True
    return False


def download_path(value: object) -> str:
    """A download's `path:` as the folder it names: one pair of matching YAML quotes dropped,
    then a leading `${{ github.workspace }}/`, then `posixpath.normpath` (spec 070, Decision 1)."""
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return posixpath.normpath(WORKSPACE_PREFIX.sub("", text))


def release_binding_errors(text: str) -> list[str]:
    """Every rule of spec 057's Design (rules 1 to 18), one line per breach, each starting with its
    rule's number, on the workflow without its comments: every reader of the build's files
    downloads them by an id it has guarded, checks them against the SHA-256 of SHA256SUMS the
    build job handed on, and acts on nothing else; nothing carries on past a failure; PyPI waits
    on publish and a pushed tag; the publish jobs name their environments, run setup-uv with no
    cache, and hold only the permissions they use."""
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
    # Rules 4, 5 and 10: every download by one guarded id, refusing a digest mismatch.
    if OTHER_FETCH.search(text):
        errors.append(
            "rule 4: the workflow fetches an artifact another way (gh run download, "
            "github-script, the artifacts API)"
        )
    guard_blocks: dict[str, list[str]] = {}
    for name, job_steps in steps.items():
        for i, (_, f) in enumerate(job_steps):
            if not f.get("uses", "").startswith("actions/download-artifact@"):
                continue
            w = f.get("with", {})
            ids = w.get("artifact-ids", "")
            # One id, or several joined by commas, all of one job (spec 063, Decision 16).
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
            elif ids == ASSETS_ID:
                guard_blocks[name] = guards[0][0]
    # Rule 6: every output a job reads is one the job it needs defines.
    for name, lines in jobs.items():
        for job, output in re.findall(r"needs\.([\w-]+)\.outputs\.([\w-]+)", "\n".join(lines)):
            if job not in _needs(lines) or output not in _job_map(jobs.get(job, []), "outputs"):
                errors.append(f"rule 6: {name} reads needs.{job}.outputs.{output}, which it cannot")
    # Rules 7 to 9: every job that holds the build's files checks them first, with one step.
    holders = [
        name
        for name, lines in jobs.items()
        if ASSETS_ID in "\n".join(lines)
        or {"contents: write", "id-token: write"} & (_permission_set(lines) or set())
    ]
    check_blocks = {}
    for name in holders:
        job_steps = steps[name]
        at = next(
            (
                i
                for i, (_, f) in enumerate(job_steps)
                if f.get("uses", "").startswith("actions/download-artifact@")
                and f.get("with", {}).get("artifact-ids") == ASSETS_ID
                and f.get("with", {}).get("path") == "release-assets"
            ),
            None,
        )
        if at is None:
            errors.append(f"rule 7: {name} does not download the build's release-assets by id")
            continue
        nxt = job_steps[at + 1] if at + 1 < len(job_steps) else ([], {})
        run = str(nxt[1].get("run", ""))
        if not (
            nxt[1].get("name") == CHECK_STEP
            and nxt[1].get("env", {}).get("SUMS_SHA256") == SUMS_SHA256
            and all(s in run for s in ("SHA256SUMS.sha256", "-c SHA256SUMS", "find . -mindepth 1"))
        ):
            errors.append(
                f"rule 8: {name}'s step after the download is not the check against the "
                "build's SHA256SUMS"
            )
            continue
        check_blocks[name] = nxt[0]
    if len({"\n".join(b) for b in check_blocks.values()}) > 1:
        errors.append("rule 9: the check steps are not the same step")
    if len({"\n".join(b) for b in guard_blocks.values()}) > 1:
        errors.append(
            "rule 10: the guards before the release-assets downloads are not the same step"
        )
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
            errors.append(f"rule 14: {name}'s permissions are not its row in spec 057's table")
    # Rule 15: nothing may let a guard, a check or a download fail quietly or be skipped.
    for name, job_steps in steps.items():
        for _, f in job_steps:
            role = (
                f.get("uses", "").startswith("actions/download-artifact@")
                or f.get("name") == CHECK_STEP
                or GUARD_TEST in str(f.get("run", ""))
            )
            if role and ({"if", "continue-on-error"} & set(f)):
                errors.append(
                    f"rule 15: {name} has a guard, check or download step with if: or "
                    "continue-on-error:"
                )
    # Rule 16: nothing but the build's files lands in release-assets, and a job that holds them
    # downloads nothing else, so no bytes arrive after its check (spec 057's build review, F1).
    # `path:` is read as a path, so `./release-assets` is release-assets too (spec 070).
    for name, job_steps in steps.items():
        downloads = [
            f.get("with", {})
            for _, f in job_steps
            if f.get("uses", "").startswith("actions/download-artifact@")
        ]
        for w in downloads:
            path = download_path(w.get("path", ""))
            if (path == "release-assets" or path.startswith("release-assets/")) and w.get(
                "artifact-ids"
            ) != ASSETS_ID:
                errors.append(
                    f"rule 16: {name} downloads into release-assets other than by assets-id"
                )
        if name in holders and name != "same-bytes" and len(downloads) > 1:
            errors.append(
                f"rule 16: {name} holds the build's files but downloads something else too"
            )
    # Rule 17: nothing in the release may carry on past a failure: a failed judge, verify leg or
    # check must stop what needs it (spec 057's build review, F2).
    if re.search(r"^\s*(- )?continue-on-error:", text, re.M):
        errors.append("rule 17: the workflow has a continue-on-error:")
    # Rule 18: PyPI only after publish, and only for a pushed tag with the owner's switch on.
    pypi = jobs.get("pypi", [])
    if _job_field(pypi, "if") != PYPI_IF or "publish" not in _needs(pypi):
        errors.append(f"rule 18: pypi's if: is not {PYPI_IF!r}, or it does not need publish")
    return errors


# ---------------------------------------------------------------------------------------------
# The release judges in parallel shards (spec 063)

JUDGE_JOBS = {  # job -> (runner, the plan's system)
    "judge-macos": ("macos-15", "macos"),
    "judge-linux": ("ubuntu-24.04", "linux"),
    "judge-windows": ("windows-2025", "windows"),
}
# `--shard=NAME`, never `--shard NAME`: before the plugin loads, pytest reads a bare `build` as a
# path, collects build/ instead of tests/, and never loads the plugin (the first branch dry run).
RECORD_PATH = '"$RUNNER_TEMP/record/latest.json"'
RECORD_UPLOAD_PATH = "${{ runner.temp }}/record/latest.json"
FETCH_RUN = 'uv run python tests/upstream/fetch.py --shard "$SHARD"\n'
SHARD_RUN = f'uv run pytest -p no:cacheprovider --shard="$SHARD" --progress-latest {RECORD_PATH}\n'
SHA_RUN = (
    "uv run python -c \"import hashlib, sys; print('sha256=' + hashlib.sha256(open(sys.argv[1], "
    f'\'rb\').read()).hexdigest())" {RECORD_PATH} >> "$GITHUB_OUTPUT"\n'
)
OUT_ENV = {
    "SHARD": "${{ matrix.shard }}",
    "RECORD_ID": "${{ steps.record.outputs.artifact-id }}",
    "RECORD_SHA256": "${{ steps.sha.outputs.sha256 }}",
}
OUT_RUN = (
    'echo "$SHARD-id=$RECORD_ID" >> "$GITHUB_OUTPUT"\n'
    'echo "$SHARD-sha256=$RECORD_SHA256" >> "$GITHUB_OUTPUT"\n'
)
BUILD_SHARD_RUN = (
    f"uv run pytest -p no:cacheprovider --shard=build --progress-latest {RECORD_PATH}\n"
)
RECORD_ID_OUTPUT = re.compile(
    r"needs\.(?:build\.outputs\.record-id|judge-[a-z]+\.outputs\.[\w-]+-id)\b"
)


def _matrix_shards(lines: list[str]) -> list[str] | None:
    for line in lines:
        m = re.fullmatch(r"\s+shard:\s*\[(.*)\]\s*", line)
        if m:
            return [x.strip() for x in m[1].split(",") if x.strip()]
    return None


def _judge_shape(lines: list[str], runner: str, system: str) -> str:
    """A judge job with its runner, its system and its own lists set aside: the three must be this
    text alike (spec 063, rule 3)."""
    kept, skip = [], False
    for line in lines:
        if re.fullmatch(r"    outputs:\s*", line):
            skip = True
            continue
        if skip and line.startswith("      "):
            continue
        skip = False
        if re.fullmatch(r"\s+shard:\s*\[.*\]\s*", line):
            line = "        shard: [@SHARDS@]"
        kept.append(line)
    return "\n".join(kept).replace(runner, "@RUNNER@").replace(system, "@SYSTEM@")


def release_shard_errors(text: str, plan: dict) -> list[str]:
    """The workflow against the shard plan (spec 063's Design, rules 1 to 10), one line per
    breach, each starting with its rule's number, on the workflow without its comments."""
    from harness import shards

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
            or _needs(lines) != {"build"}
            or _job_field(lines, "timeout-minutes") != "30"
            or _permission_set(lines) != {"contents: read"}
            or not re.search(r"^      fail-fast: false\s*$", body, re.M)
            or _job_field(lines, "if") is not None
            or _job_field(lines, "continue-on-error") is not None
        ):
            errors.append(
                f"rule 1: {job} is not on {runner}, needing build, 30 minutes, contents: read, "
                "fail-fast: false, with no job-level if: or continue-on-error:"
            )
        want = shards.on(plan, system)
        if _matrix_shards(lines) != want:
            errors.append(f"rule 2: {job}'s matrix is not the plan's {system} shards {want}")
        shapes.add(_judge_shape(lines, runner, system))
        js = [f for _, f in steps[job]]
        at = {}
        for i, f in enumerate(js):
            run = f.get("run")
            if f.get("uses", "").startswith("actions/download-artifact@"):
                at.setdefault("download", i)
            if f.get("name") == CHECK_STEP:
                at.setdefault("check", i)
            if run == FETCH_RUN and f.get("env", {}).get("SHARD") == "${{ matrix.shard }}":
                at.setdefault("fetch", i)
            if run == SHARD_RUN and f.get("env", {}).get("SHARD") == "${{ matrix.shard }}":
                at.setdefault("shard", i)
            if f.get("id") == "sha" and run == SHA_RUN:
                at.setdefault("sha", i)
            if (
                f.get("id") == "record"
                and f.get("uses", "").startswith("actions/upload-artifact@")
                and f.get("with", {}).get("path") == RECORD_UPLOAD_PATH
                and f.get("with", {}).get("if-no-files-found") == "error"
            ):
                at.setdefault("record", i)
            if f.get("id") == "out" and f.get("env") == OUT_ENV and run == OUT_RUN:
                at.setdefault("out", i)
        order = ["download", "check", "fetch", "shard", "sha", "record", "out"]
        if any(k not in at for k in order) or [at[k] for k in order] != sorted(
            at[k] for k in order
        ):
            missing = [k for k in order if k not in at]
            errors.append(
                f"rule 4: {job} does not run download, check, fetch, shard, sha, record, out in "
                f"order, with their fixed texts (missing or other: {missing or 'the order'})"
            )
        if re.search(r"\|\||set \+e", "\n".join(str(f.get("run", "")) for f in js)):
            errors.append(f"rule 4: a step of {job} swallows a failure (|| or set +e)")
        outputs = _job_map(lines, "outputs")
        expect = {}
        for name in want:
            expect[f"{name}-id"] = f"${{{{ steps.out.outputs.{name}-id }}}}"
            expect[f"{name}-sha256"] = f"${{{{ steps.out.outputs.{name}-sha256 }}}}"
        if outputs != expect:
            errors.append(
                f"rule 5: {job}'s outputs are not <shard>-id and <shard>-sha256 of its shards"
            )
    if len(shapes) > 1:
        errors.append("rule 3: the three judge jobs differ beyond their runner, system and lists")
    # Rule 6: the build job judges its own shard and hands on its record and python.wasm's hash.
    build = [f for _, f in steps.get("build", [])]
    outputs = _job_map(jobs.get("build", []), "outputs")
    runs = [str(f.get("run", "")).strip() for f in build]
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
        r"\$\{\{ steps\.([\w-]+)\.outputs\.artifact-id \}\}", outputs.get("record-id", "")
    )
    rec_step = next((f for f in build if rec and f.get("id") == rec[1]), {})
    sha = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", outputs.get("record-sha256", "")
    )
    sha_step = next((f for f in build if sha and f.get("id") == sha[1]), {})
    # Spec 085: the set's own SHA256SUMS, hashed before the upload, as python.wasm is.
    set_sums = re.fullmatch(
        r"\$\{\{ steps\.([\w-]+)\.outputs\.sha256 \}\}", outputs.get("set-sums-sha256", "")
    )
    set_sums_at = next(
        (i for i, f in enumerate(build) if set_sums and f.get("id") == set_sums[1]), None
    )
    other_pytest = [
        r
        for r in runs
        if "uv run pytest" in r
        and "--shard" not in r
        and "-k test_source_tree_matches_its_tarball" not in r
    ]
    if (
        BUILD_SHARD_RUN.strip() not in runs
        or other_pytest
        or wasm_at is None
        or upload_at is None
        or wasm_at > upload_at
        or not re.search(r"(shasum -a 256|sha256sum) build/artifacts/python\.wasm", runs[wasm_at])
        or rec_step.get("with", {}).get("path") != RECORD_UPLOAD_PATH
        or str(sha_step.get("run", "")).strip() != SHA_RUN.strip()
    ):
        errors.append(
            "rule 6: build does not run the build shard alone, hand on its record (record-id, "
            "record-sha256) and python.wasm's SHA-256 made before the upload (wasm-sha256)"
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
            "upload (set-sums-sha256; spec 085)"
        )
    # Rule 7: the gather holds no assets, downloads every record id by job, and runs gather.py.
    gather = jobs.get("gather")
    if gather is None:
        errors.append("rule 7: no job gather")
    else:
        gs = [f for _, f in steps["gather"]]
        if (
            _job_field(gather, "runs-on") != "ubuntu-24.04"
            or _job_field(gather, "timeout-minutes") != "15"
            or _permission_set(gather) != {"contents: read"}
            or not {"build", *JUDGE_JOBS} <= _needs(gather)
            or _job_field(gather, "if") is not None
            or _job_field(gather, "continue-on-error") is not None
        ):
            errors.append(
                "rule 7: gather is not on ubuntu-24.04, 15 minutes, contents: read, needing build "
                "and the three judge jobs, with no job-level if: or continue-on-error:"
            )
        downloads = [
            f.get("with", {})
            for f in gs
            if f.get("uses", "").startswith("actions/download-artifact@")
        ]
        want_ids = {"build": ["${{ needs.build.outputs.record-id }}"]}
        for job, (_, system) in JUDGE_JOBS.items():
            want_ids[job] = [
                f"${{{{ needs.{job}.outputs.{n}-id }}}}" for n in shards.on(plan, system)
            ]
        got = {
            w.get("path", "").rstrip("/"): [x.strip() for x in w.get("artifact-ids", "").split(",")]
            for w in downloads
        }
        want = {f"records/{job}": ids for job, ids in want_ids.items()}
        if got != want or len(downloads) != len(want):
            errors.append(
                "rule 7: gather does not download exactly every record id, each job's into "
                "records/<job>, and nothing else (never release-assets)"
            )
        step = next((f for f in gs if "tests/harness/gather.py" in str(f.get("run", ""))), {})
        env = step.get("env", {})
        want_env = {
            "WASM_SHA256": "${{ needs.build.outputs.wasm-sha256 }}",
            "SET_SUMS_SHA256": "${{ needs.build.outputs.set-sums-sha256 }}",
            "RECORD_BUILD_BUILD": "${{ needs.build.outputs.record-sha256 }}",
        }
        for job, (_, system) in JUDGE_JOBS.items():
            for n in shards.on(plan, system):
                key = f"RECORD_{system}_{n}".upper().replace("-", "_")
                want_env[key] = f"${{{{ needs.{job}.outputs.{n}-sha256 }}}}"
        if not step or env != want_env:
            errors.append(
                "rule 7: gather's step does not run tests/harness/gather.py with exactly "
                "WASM_SHA256, SET_SUMS_SHA256 and every record's SHA-256 bound in env:"
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
    # Rule 10: only build sets wasm-sha256 and set-sums-sha256 (spec 085), and only the gather
    # reads them.
    for job, lines in jobs.items():
        body = "\n".join(lines)
        for name in ("wasm-sha256", "set-sums-sha256"):
            if job != "gather" and f"needs.build.outputs.{name}" in body:
                errors.append(f"rule 10: {job} reads {name}")
            if job != "build" and re.search(rf"^      {name}:", body, re.M):
                errors.append(f"rule 10: {job} sets {name}")
    return errors


def action_pin_errors(text: str) -> list[str]:
    """Every `uses:` is a local action or `owner/repo[/path]@<40 hex>` (spec 057, Decision 7)."""
    errors = []
    for m in re.finditer(r"^\s*(?:- )?uses:\s*(\S+)", without_comments(text), re.M):
        ref = m[1]
        if not (ref.startswith("./") or re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref)):
            errors.append(f"{ref}: not pinned by a full commit")
    return errors


def unpinned_fetch_errors(download_script: Path, pinned: Iterable[str]) -> list[str]:
    """Every file a `get` or `research` line fetches is pinned in SHA256SUMS (spec 057; the a4
    security review's N1): the name given, or else the URL's last part."""
    pinned = set(pinned)
    text = "\n".join(line for _, line in _code_lines(download_script))
    names = [name or url.rstrip("/").rsplit("/", 1)[-1] for url, name in GET.findall(text)]
    return [
        f"{name}: fetched, but not pinned in downloads/SHA256SUMS"
        for name in names
        if name not in pinned
    ]


# ---------------------------------------------------------------------------------------------
# A module-level name bound twice: the second silently replaces the first, so checks that used
# the first run the second's code (spec 019's rebase redefined `CTRL_C` and lost two checks).


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


# Constitution §4.1: carried patches, recorded and temporary (spec 020)

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
    """What a patch may not contain (spec 020, Decision 6), and the paths it touches, as git reads
    it: a plain `---`/`+++` section after a hunk, or names that differ from `diff --git`, are
    applied by git and so are judged here too (the build review, finding 2)."""
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
            errors.append(f"{where}: touches {path}, a name Finder or Explorer writes (spec 026)")
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
    """Every rule of spec 020, Decisions 6 and 7, on `recipes/patches/` and its drafts. `tops` are
    the pinned source tarballs' top folders."""
    tops = set(tops)
    patches, drafts = root / "recipes" / "patches", root / "context" / "upstream" / "patches"
    changelog = (root / "CHANGELOG.md").read_text() if (root / "CHANGELOG.md").is_file() else ""
    errors, count, made = [], 0, set()
    folders = sorted(p for p in patches.iterdir()) if patches.is_dir() else []
    for d in folders:
        if _is_litter(d.name):
            continue  # Finder's or Explorer's, not ours (specs 018, 090)
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
                errors.append(f"{where}: not named in CHANGELOG.md")
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
# these two (spec 090, Decision 1).
def _is_litter(name: str) -> bool:
    from harness import paths

    return paths.is_litter(name)


def _has_litter(rel: str) -> bool:
    from harness import paths

    return paths.has_litter(rel)


# ---------------------------------------------------------------------------------------------
# The landing lane (spec 029)

ACCEPTED_FILE = "context/progress/accepted.json"
PROGRESS_DIR = "context/progress"
VOLUMES_GLOB = ":(glob)context/progress/history*.jsonl"  # every history volume (spec 062)
# Rule 1 requires `dirty: false` of an acceptance whose judge holds this file: 029's own and every
# later one. Older lines are not re-judged (they all say true: Decision 2).
FIRST_CLEAN_JUDGE = "tests/unit/test_landing_lane.py"


def _committed_json(repo: Path, rev: str, path: str) -> object:
    text = paths.git("show", f"{rev}:{path}", repo=repo)
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None


def acceptance_errors(repo: Path) -> list[str]:
    """Rule 1 (spec 029, Decisions 1 and 2; spec 062, Decision 11), read from committed history
    only: the newest commit that changed a history volume sits on (first parent) the commit the
    newest line of its newest volume names, changes nothing but accepted.json and that volume,
    and, from 029's judge on, says `dirty: false`."""
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
    """Rule 3 (spec 029, Decision 3): no merge commit is reachable from HEAD."""
    out = paths.git("rev-list", "--merges", "HEAD", repo=repo)
    if out is None:
        return ["git rev-list --merges HEAD failed"]
    return [f"{h[:12]} is a merge commit; main moves only by fast-forward" for h in out.split()]


# Spec 079: every Python a build step runs is the pinned host Python, or one built from pins. Step
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
    """(index of the program word, problem) for a command, read past any `env` by its grammar (the
    confirmation's C1). The index is None when there is no program word."""
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
    variables are read from common.sh's and the step's own simple assignments and from line.conf
    (the confirmation's C3); a folder that cannot be resolved is returned as unresolved."""
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
