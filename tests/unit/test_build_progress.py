"""The build says where it is: build.sh's two modes, every exit path, the failure block,
the summary, the options and the preflight, and the download step's lines.

Each check copies build.sh and its libraries into a temporary tree with fake steps under the eleven
real names, puts stand-ins on PATH, and sets BUILD_CLOCK to a counting script, so a duration is a
count of clock readings. Terminal mode runs on a pty (stdlib `os.openpty`, its width set with
TIOCSWINSZ) whose bytes are replayed to the final screen. Every pty read is bounded by a count, so
a ticker that outlives the build fails the check instead of hanging it. Nothing measures time; the
`select` guard only stops a check that would otherwise wait for ever."""

from __future__ import annotations

import hashlib
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from harness import paths

SCRIPTS = paths.REPO / "scripts"
STEPS = (
    "00_download",
    "10_tools",
    "20_cpython",
    "30_zlib",
    "35_stdlib_libs",
    "36_xml_libs",
    "37_plot_libs",
    "38_openblas",
    "40_numpy",
    "50_pandas",
    "53_regex",
    "54_lxml",
    "55_matplotlib",
    "57_scipy",
    "58_sklearn",
    "59_statsmodels",
    "60_link",
    "70_zip",
    "80_snapshot",
    "90_artifacts",
)
N_STEPS = len(STEPS)  # counted, so a new step moves no frame below
K_NUMPY = STEPS.index("40_numpy") + 1
# Real tools the driver, the libraries and the fake steps run; linked into the tree's own bin/.
REAL_TOOLS = (
    "sh", "sed", "awk", "tr", "cut", "tail", "head", "grep", "wc", "cat", "date", "sleep", "ls",
    "dirname", "basename", "mkdir", "rm", "mv", "env", "sort", "stty", "uname", "touch", "shasum",
    "ln",
)  # fmt: skip
STUBS = ("cc", "make", "tar", "gzip", "xz", "uv", "git")  # the preflight's tools, as stand-ins
FOUND = {t: shutil.which(t) for t in REAL_TOOLS}
HAS_PTY = sys.platform != "win32" and hasattr(os, "openpty")
SH_OF_STEPS = FOUND["sh"] or "sh"  # the `sh` build.sh runs each step with
SHELLS = [s for s in (shutil.which("dash") or shutil.which("sh"), shutil.which("bash")) if s]
READS = 5000  # pty reads one run may take; a ticker left drawing exceeds it
GUARD = 60  # seconds `select` waits for one byte: a hang guard, never a measurement
CLOCK_START, CLOCK_STEP = 1000, 7
BRAILLE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
FRAME = re.compile(r"\r([^\r\n]*?)\x1b\[K")  # a frame may hold an ESC only if it is wrong
TIME = r"\d+s|\d+m\d\ds|\d+h\d\dm"
GRAMMAR = re.compile(  # every part of a status line is the driver's own: names, times, digits
    rf"[{BRAILLE}|/\\-] \[\d+/\d+\] \d\d_[a-z_]+ (?:{TIME})(?: / ~(?:{TIME}))?"
    r"(?: [·-] (?:\[\d+/\d+\]|fetching [A-Za-z0-9._+-]+ \d+ [KM]iB))?"
    rf"(?: [·-] ~(?:{TIME}) left)?"
)
LOG_TEXT = "printf 'LOGTEXT \\033[31mred\\033[0m\\n'\n"  # a log line no frame may show
CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")
LONG = "made " + "abcdefghij" * 14  # a summary past the 120-character cut


def _needs_sh() -> None:
    missing = [t for t, p in FOUND.items() if p is None]
    if missing or not SHELLS:
        pytest.skip("needs: a POSIX sh")


def _needs_pty() -> None:
    _needs_sh()
    if not HAS_PTY:
        pytest.skip("needs: a pty")


def _script(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


class Tree:
    """A copy of the driver with fake steps, its own bin/ and a counting clock."""

    def __init__(self, root: Path, *, df_kib: int = 104857600, missing: tuple[str, ...] = ()):
        self.root = root.resolve()
        for rel in (
            "build.sh",
            "steps/progress.sh",
            "steps/remove.sh",
            "line.sh",
            "line.conf",
            "refuse-python",
        ):
            dst = self.root / "scripts" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SCRIPTS / rel, dst)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for tool, real in FOUND.items():
            if tool not in missing:
                (self.bin / tool).symlink_to(real)
        for tool in STUBS:
            if tool not in missing:
                _script(self.bin / tool, "#!/bin/sh\nexit 0\n")
        if "df" not in missing:
            _script(
                self.bin / "df",
                "#!/bin/sh\necho 'Filesystem 1024-blocks Used Available Capacity Mounted on'\n"
                f"echo '/dev/fake 999999999 1 {df_kib} 1% /'\n",
            )
        (self.root / "go").mkdir()
        self.clock = self.root / "clock.sh"
        self.clock_limit(None)
        for step in STEPS:
            self.step(step)

    def clock_limit(self, limit: int | None) -> None:
        """BUILD_CLOCK: each reading prints the count and adds 7; past `limit` it fails."""
        fail = f'[ "$c" -lt {limit} ] || exit 1\n' if limit is not None else ""
        _script(
            self.clock,
            f"#!/bin/sh\nc=$(cat '{self.root}/clock.count')\n{fail}"
            f"echo $((c + {CLOCK_STEP})) > '{self.root}/clock.count'\necho \"$c\"\n",
        )
        self.reset_clock()

    def reset_clock(self) -> None:
        (self.root / "clock.count").write_text(f"{CLOCK_START}\n")

    def path(self, step: str) -> Path:
        if step.startswith("00_"):
            return self.root / "scripts" / "00_download.sh"
        return self.root / "scripts" / "steps" / f"{step}.sh"

    def step(self, name: str, body: str | None = None) -> None:
        if body is None:
            body = f'echo "{name}: working"\necho "{name}: {LONG}"\n'
            if name == "90_artifacts":
                body = ARTIFACTS + body
        _script(
            self.path(name),
            f"#!/bin/sh\n# Step {name[:2]}: the fake {name} of the progress checks.\nset -eu\n"
            f"T='{self.root}'\n{body}",
        )

    def hold(self, name: str, before: str = "", after: str | None = None) -> None:
        """A step that waits (a bounded number of polls) for go/<name>, which a check creates."""
        after = f'echo "{name}: {LONG}"\n' if after is None else after
        self.step(
            name,
            f'{before}i=0\nwhile [ ! -e "$T/go/{name}" ] && [ "$i" -lt 200 ]; do\n'
            f"  sleep 0.05; i=$((i + 1))\ndone\n{after}",
        )

    def env(self, lang: str = "C", **more: str | None) -> dict[str, str]:
        env = {
            "PATH": str(self.bin),
            "HOME": str(self.root),
            "TERM": "xterm-256color",
            "BUILD_CLOCK": str(self.clock),
            "LANG": lang,
            **more,
        }
        return {k: v for k, v in env.items() if v is not None}

    def plain(self, *args: str, shell: str | None = None, env=None) -> subprocess.CompletedProcess:
        """build.sh with stdout to a pipe: plain mode, stderr folded in as on a terminal."""
        return subprocess.run(
            [shell or SHELLS[0], str(self.root / "scripts" / "build.sh"), *args],
            env=env or self.env(),
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=GUARD,
            check=False,
        )

    def pty(self, *args: str, shell: str | None = None, env=None, cols: int = 80, react=None):
        argv = [shell or SHELLS[0], str(self.root / "scripts" / "build.sh"), *args]
        return Pty(argv, env or self.env(), self.root, cols).run(react)

    def timings(self) -> list[list[str]]:
        f = self.root / "build" / "logs" / "timings.tsv"
        return [line.split("\t") for line in f.read_text().splitlines()] if f.exists() else []


ARTIFACTS = """mkdir -p "$T/build/artifacts"
printf 'wasm' > "$T/build/artifacts/python.wasm"
printf 'snapshot!' > "$T/build/artifacts/python-snapshot.wasm"
printf 'zip' > "$T/build/artifacts/python-stdlib.zip"
(cd "$T/build/artifacts" && shasum -a 256 python.wasm python-snapshot.wasm python-stdlib.zip \\
  > SHA256SUMS)
"""


def _controlling_tty() -> None:
    # The build gets the signals' default actions even when this process inherited them ignored
    # (a background job of a non-interactive shell starts with SIGINT ignored).
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        signal.signal(sig, signal.SIG_DFL)
    os.setsid()
    import fcntl
    import termios

    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class Pty:
    """One run on a fresh pty of `cols` columns; `react(self)` runs after every read."""

    def __init__(self, argv: list[str], env: dict[str, str], cwd: Path, cols: int):
        import fcntl
        import termios

        self.master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, cols, 0, 0))
        self.cols = cols
        self.proc = subprocess.Popen(
            argv,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
            cwd=cwd,
            preexec_fn=_controlling_tty,
        )
        os.close(slave)
        self.data = bytearray()
        self.reads = 0

    def run(self, react=None) -> tuple[int, bytes]:
        try:
            for self.reads in range(1, READS + 1):  # noqa: B007 (react reads the count)
                ready, _, _ = select.select([self.master], [], [], GUARD)
                assert ready, "the pty went quiet without reaching its end"
                try:
                    chunk = os.read(self.master, 65536)
                except OSError:  # EIO on Linux: the last writer closed the pty
                    chunk = b""
                if not chunk:
                    break
                self.data += chunk
                if react is not None:
                    react(self)
            else:
                pytest.fail(f"the pty was still open after {READS} reads: a process outlived it")
            return self.proc.wait(timeout=GUARD), bytes(self.data)
        finally:
            os.close(self.master)
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)  # whatever is left of the group
            except (ProcessLookupError, PermissionError):
                pass
            if self.proc.poll() is None:
                self.proc.wait()

    def text(self) -> str:
        return self.data.decode("utf-8", "replace")


def frames(data: bytes | bytearray) -> list[str]:
    """The status lines drawn: each `\\r<text>ESC[K` with text."""
    return [f for f in FRAME.findall(bytes(data).decode("utf-8", "replace")) if f]


def _only_the_drivers_words(drawn: list[str], whole: bool) -> None:
    """No log text in any frame; with `whole`, every frame (uncut) fits the status grammar."""
    leaked = [f for f in drawn if "LOGTEXT" in f or "red" in f or "\x1b" in f]
    assert not leaked, leaked
    if whole:
        bad = [f for f in drawn if not GRAMMAR.fullmatch(f)]
        assert not bad, bad


def screen(data: bytes, cols: int) -> list[str]:
    """Replay CR, LF, ESC[K and SGR (ignored) on a `cols`-wide terminal that wraps a line past its
    last column, and return the final screen's rows."""
    text = data.decode("utf-8", "replace")
    rows: list[list[str]] = [[]]
    r = c = 0
    i = 0
    while i < len(text):
        m = CSI.match(text, i)
        if m:
            arg, op = m.groups()
            if op == "K" and arg in ("", "0"):
                del rows[r][min(c, cols - 1) if c >= cols else c :]
            elif op != "m":
                raise AssertionError(f"the build wrote an escape it should not: {m.group()!r}")
            i = m.end()
            continue
        ch = text[i]
        i += 1
        if ch == "\r":
            c = 0
        elif ch == "\n":
            r += 1
            while len(rows) <= r:
                rows.append([])
        elif ch == "\x1b" or (ch < " " and ch != "\t"):
            raise AssertionError(f"the build wrote a control byte {ch!r}")
        else:
            if c >= cols:  # the deferred wrap of a full row
                r, c = r + 1, 0
                while len(rows) <= r:
                    rows.append([])
            row = rows[r]
            while len(row) < c:
                row.append(" ")
            if c < len(row):
                row[c] = ch
            else:
                row.append(ch)
            c += 1
    lines = ["".join(x).rstrip() for x in rows]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def fold(text: str, cols: int) -> list[str]:
    """Plain output as a `cols`-wide terminal shows it."""
    rows: list[str] = []
    for line in text.splitlines():
        rows += [line[i : i + cols] for i in range(0, len(line), cols)] or [""]
    rows = [x.rstrip() for x in rows]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def go_when(tree: Tree, step: str, k: int, n: int = N_STEPS, also: str = ""):
    """Create go/<step> once a frame names the step, its [k/n] and `also`."""
    want = f"[{k}/{n}] {step} "

    def react(p: Pty) -> None:
        go = tree.root / "go" / step
        if not go.exists() and any(want in f and also in f for f in frames(p.data)):
            go.touch()

    return react


def _timings_for_every_step(tree: Tree) -> str:
    text = "".join(f"1000-1\t{s}\tok\t{3 + i}\n" for i, s in enumerate(STEPS))
    logs = tree.root / "build" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "timings.tsv").write_text(text)
    return text


FAILING = """echo "checking strerror... yes"
printf 'colour: \\033[31mred\\033[0m line\\n'
echo "ERROR: 100% of the fake failed"
exit 4
"""

# --------------------------------------------------------------------------------------------
# 1. Frames, then equality. A pairwise cover of outcome, timings.tsv, width, locale and shell:
# every pair of their values appears in some case.

EQUALITY = [
    # (fails, timings, cols, lang, shell index)
    (False, False, 80, "en_US.UTF-8", 0),
    (False, True, 30, "C", 0),
    (True, False, 30, "C", 1),
    (True, True, 80, "en_US.UTF-8", 1),
    (False, False, 30, "en_US.UTF-8", 1),
    (False, True, 80, "C", 1),
    (True, False, 80, "C", 0),
    (True, True, 30, "en_US.UTF-8", 0),
]


@pytest.mark.parametrize(("fails", "timings", "cols", "lang", "shell"), EQUALITY)
def test_frames_then_the_final_screen_equals_plain(work, fails, timings, cols, lang, shell):
    _needs_pty()
    if shell >= len(SHELLS):
        pytest.skip("needs: a POSIX sh")  # a second shell (bash) is absent here
    sh = SHELLS[shell]
    tree = Tree(work)
    tree.hold("40_numpy", before=LOG_TEXT + 'echo "[3/9] Compiling C object x.o"\n' + LOG_TEXT)
    if fails:
        tree.step("50_pandas", FAILING)
    before = _timings_for_every_step(tree) if timings else None

    (tree.root / "go" / "40_numpy").touch()
    plain = tree.plain(shell=sh, env=tree.env(lang))
    (tree.root / "go" / "40_numpy").unlink()
    if before is None:
        (tree.root / "build" / "logs" / "timings.tsv").unlink()
    else:
        (tree.root / "build" / "logs" / "timings.tsv").write_text(before)
    tree.reset_clock()

    code, raw = tree.pty(
        shell=sh, env=tree.env(lang), cols=cols, react=go_when(tree, "40_numpy", K_NUMPY)
    )
    drawn = frames(raw)
    assert (tree.root / "go" / "40_numpy").exists(), (
        f"no frame named 40_numpy and [{K_NUMPY}/{N_STEPS}]"
    )
    assert code == plain.returncode == (1 if fails else 0), plain.stdout
    assert screen(raw, cols) == fold(plain.stdout, cols)
    assert all(len(f) <= cols - 1 for f in drawn), [f for f in drawn if len(f) >= cols]
    _only_the_drivers_words(drawn, whole=cols == 80)
    spinners = {f[0] for f in drawn}
    if "UTF-8" in lang:
        assert spinners <= set(BRAILLE), spinners
    else:
        assert spinners <= set("|/-\\"), spinners
        assert all(f.isascii() for f in drawn)
    numpy = [f for f in drawn if f"[{K_NUMPY}/{N_STEPS}] 40_numpy " in f]
    if timings:
        assert any(" / ~" in f for f in numpy), numpy
        if cols == 80:
            assert any(f.endswith(" left") for f in numpy), numpy
    elif cols == 80:
        assert any("[3/9]" in f for f in numpy), numpy
    assert b"\x1b[32mok\x1b[0m " in raw  # colour on a terminal: NO_COLOR unset
    if fails:
        assert b"\x1b[31mERROR\x1b[0m 50_pandas: " in raw
        assert "  | colour: red line" in plain.stdout.splitlines()


def test_the_download_frame_shows_the_partial_file(work) -> None:
    _needs_pty()
    tree = Tree(work)
    part = 'mkdir -p "$T/downloads"\nprintf 12345 > "$T/downloads/x.tgz.part"\n'
    tree.hold("00_download", before=LOG_TEXT + part)
    code, raw = tree.pty(react=go_when(tree, "00_download", 1, also="x.tgz"))
    assert code == 0 and (tree.root / "go" / "00_download").exists()
    assert any("fetching x.tgz 0 KiB" in f for f in frames(raw)), frames(raw)
    _only_the_drivers_words(frames(raw), whole=True)


def test_no_colour_when_no_color_is_set(work) -> None:
    _needs_pty()
    tree = Tree(work)
    code, raw = tree.pty("--from", "90", env=tree.env(NO_COLOR="1"))
    assert code == 0
    assert not re.search(rb"\x1b\[[0-9;]*m", raw)


# --------------------------------------------------------------------------------------------
# 2. Every exit path.


def _gone(pgid: int) -> bool:
    """No process is left in the build's process group (a bounded number of looks)."""
    for _ in range(100):
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:  # macOS: a member has exited and is not yet reaped
            pass
        select.select([], [], [], 0.05)
    return False


@pytest.mark.parametrize("shell", range(2))
def test_ctrl_c_interrupts_the_step_and_leaves_nothing(work, shell) -> None:
    _needs_pty()
    if shell >= len(SHELLS):
        pytest.skip("needs: a POSIX sh")
    tree = Tree(work)
    # One long command, not a poll loop: a `sleep` that ends on its own as SIGINT arrives makes
    # bash's step shell carry on (it takes the child to have handled the signal).
    tree.step("40_numpy", 'echo "40_numpy: holding"\nsleep 30\necho "40_numpy: done"\n')
    sent = []

    def react(p: Pty) -> None:
        if not sent and any(f"[{K_NUMPY}/{N_STEPS}] 40_numpy " in f for f in frames(p.data)):
            sent.append(os.write(p.master, b"\x03"))

    p = Pty([SHELLS[shell], str(tree.root / "scripts/build.sh")], tree.env(), tree.root, 80)
    code, raw = p.run(react)
    assert sent, "no frame named 40_numpy"
    assert code == 130
    assert screen(raw, 80)[-1] == "INTERRUPTED 40_numpy (log: build/logs/40_numpy.log)"
    assert _gone(p.proc.pid), "a process of the build outlived it"
    assert tree.timings()[-1][1:3] == ["40_numpy", "interrupted"]


@pytest.mark.parametrize("shell", range(2))
def test_term_waits_for_the_step_then_stops_before_the_next(work, shell) -> None:
    _needs_pty()
    if shell >= len(SHELLS):
        pytest.skip("needs: a POSIX sh")
    tree = Tree(work)
    tree.hold("40_numpy")

    def react(p: Pty) -> None:
        go = tree.root / "go" / "40_numpy"
        if not go.exists() and any(f"[{K_NUMPY}/{N_STEPS}] 40_numpy " in f for f in frames(p.data)):
            p.proc.send_signal(signal.SIGTERM)  # to build.sh alone, not its process group
            go.touch()

    p = Pty([SHELLS[shell], str(tree.root / "scripts/build.sh")], tree.env(), tree.root, 200)
    code, raw = p.run(react)
    rows = screen(raw, 200)
    assert code == 143, rows[-3:]
    assert rows[-2].startswith("ok 40_numpy: ")
    assert rows[-1] == "INTERRUPTED before 50_pandas"  # it never started: no log to point at
    assert tree.timings()[-1][1:] == ["50_pandas", "interrupted", "0"]
    resumed = tree.plain("--resume")
    oks = [x.split(":")[0][3:] for x in resumed.stdout.splitlines() if x.startswith("ok ")]
    assert resumed.returncode == 0 and oks == list(STEPS[STEPS.index("50_pandas") :]), (
        resumed.stdout
    )


def test_term_during_the_last_step_ends_without_a_summary(work) -> None:
    _needs_pty()
    tree = Tree(work)
    tree.hold("90_artifacts", before=ARTIFACTS)

    def react(p: Pty) -> None:
        go = tree.root / "go" / "90_artifacts"
        if not go.exists() and any(
            f"[{N_STEPS}/{N_STEPS}] 90_artifacts " in f for f in frames(p.data)
        ):
            p.proc.send_signal(signal.SIGTERM)
            go.touch()

    p = Pty([SHELLS[0], str(tree.root / "scripts/build.sh")], tree.env(), tree.root, 200)
    code, raw = p.run(react)
    rows = screen(raw, 200)
    assert code == 143, rows[-3:]
    assert rows[-2].startswith("ok 90_artifacts: ")
    assert rows[-1] == "INTERRUPTED after 90_artifacts: every step had finished"
    assert not any(r.startswith("done:") for r in rows)
    assert tree.timings()[-1][1:3] == ["90_artifacts", "ok"]


# The session leader outlives build.sh: it starts it, records its id, reaps it, then stays two
# seconds (eight of the ticker's frames) before it exits. Were build.sh the leader, its death would
# hang up the terminal (SIGHUP to the group; macOS also revokes the tty), which would stop the
# ticker without kill -0.
LEADER = 'sh "$0" & echo "$!" > "$1/build.pid"\nwait\nsleep 2\n'


def test_the_ticker_ends_itself_when_the_build_is_gone(work) -> None:
    """SIGKILL to build.sh alone runs no EXIT trap; the ticker must see the build gone (kill -0)
    and draw at most the one frame it may have begun."""
    _needs_pty()
    tree = Tree(work)
    tree.hold("40_numpy")
    drawn_before: list[int] = []

    def react(p: Pty) -> None:
        if not drawn_before and any(
            f"[{K_NUMPY}/{N_STEPS}] 40_numpy " in f for f in frames(p.data)
        ):
            os.kill(int((tree.root / "build.pid").read_text()), signal.SIGKILL)
            drawn_before.append(len(frames(p.data)))
            (tree.root / "go" / "40_numpy").touch()

    build = str(tree.root / "scripts/build.sh")
    p = Pty([SH_OF_STEPS, "-c", LEADER, build, str(tree.root)], tree.env(), tree.root, 80)
    _, raw = p.run(react)
    assert drawn_before, "no frame named 40_numpy"
    after = len(frames(raw)) - drawn_before[0]
    assert after <= 1, f"the ticker drew {after} frames after the build was gone"
    assert _gone(p.proc.pid), "a process of the build outlived it"


def test_a_renderer_failure_stops_the_ticker_too(work) -> None:
    _needs_pty()
    tree = Tree(work)
    tree.hold("00_download")
    tree.clock_limit(CLOCK_START + 2 * CLOCK_STEP)  # the third reading, at step 00's end, fails
    code, raw = tree.pty(react=go_when(tree, "00_download", 1))
    assert (tree.root / "go" / "00_download").exists(), "no frame before the failure"
    assert code != 0
    assert not any(f"[1/{N_STEPS}]" in row for row in screen(raw, 80)), screen(raw, 80)


# --------------------------------------------------------------------------------------------
# 3. The step sees nothing of the renderer.

RECORD = """{
  env | sort
  if [ -t 0 ]; then echo "stdin: a terminal"; else echo "stdin: not a terminal"; fi
  echo "argv: $0 $#"
  ls /dev/fd
} > "$T/record"
echo "30_zlib: recorded"
"""


def test_the_step_sees_the_same_in_every_mode(work) -> None:
    _needs_pty()
    tree = Tree(work)
    tree.step("30_zlib", RECORD)
    env = tree.env("en_US.UTF-8")
    seen = []
    for args in (["30"], ["--plain", "30"]):
        code, _ = tree.pty(*args, shell=SH_OF_STEPS, env=env)
        assert code == 0
        seen.append((tree.root / "record").read_text())
    alone = (
        'export SOURCE_DATE_EPOCH=1767225600 UV_CACHE_DIR="$0/build/uv-cache" '
        'PYTHONHASHSEED=0 LC_ALL=C PATH="$0/build/no-host-python:$PATH"; '
        'sh "$0/scripts/steps/30_zlib.sh" '
        '> "$0/build/logs/30_zlib.log" 2>&1'
    )
    code, _ = Pty([SH_OF_STEPS, "-c", alone, str(tree.root)], env, tree.root, 80).run()
    assert code == 0
    seen.append((tree.root / "record").read_text())
    assert "stdin: a terminal" in seen[0]
    assert seen[0] == seen[1] == seen[2]


# --------------------------------------------------------------------------------------------
# 4. The failure block.


def _fail_with(tree: Tree, log: str, code: int = 3, **env: str) -> list[str]:
    body = "cat <<'EOF'\n" + log + "EOF\n" + f"exit {code}\n"
    tree.step("40_numpy", body)
    out = tree.plain("--from", "40", env=tree.env(**env))
    assert out.returncode == 1, out.stdout
    lines = out.stdout.splitlines()
    return lines[lines.index(next(x for x in lines if x.startswith("FAILED"))) :]


def test_the_reason_is_the_steps_own_error_line(work) -> None:
    _needs_sh()
    log = "ERROR: the real reason\nchecking strerror... yes\nmake: *** [all] Error 2\n"
    block = _fail_with(Tree(work), log)
    assert block[0] == (
        f"FAILED 40_numpy: exit 3 after {CLOCK_STEP}s; the last 20 lines of "
        "build/logs/40_numpy.log:"
    )
    assert block[1:4] == ["  | " + x for x in log.splitlines()]
    assert block[-1] == "ERROR 40_numpy: ERROR: the real reason (log: build/logs/40_numpy.log)"
    assert sum(x.startswith("ERROR") for x in block) == 1
    assert not any(x.startswith("::error") for x in block)


def test_an_indented_error_is_not_the_reason(work) -> None:
    _needs_sh()
    block = _fail_with(Tree(work), "  ERROR: indented\nmore\n", code=5)
    assert block[-1] == "ERROR 40_numpy: exit 5 (log: build/logs/40_numpy.log)"


@pytest.mark.parametrize(("lines", "shown"), [(50, 20), (5, 5)])
def test_the_tail_is_the_last_twenty_lines(work, lines, shown) -> None:
    _needs_sh()
    log = "".join(f"line {n}\n" for n in range(1, lines + 1))
    block = _fail_with(Tree(work), log)
    assert block[1:-1] == [f"  | line {n}" for n in range(lines - shown + 1, lines + 1)]


def test_github_gets_one_error_annotation_before_the_last_line(work) -> None:
    _needs_sh()
    log = "noise\nERROR: 100% broken\n"
    block = _fail_with(Tree(work), log, GITHUB_ACTIONS="true")
    assert block[-2] == "::error title=build step 40_numpy failed::ERROR: 100%25 broken"
    assert block[-1] == "ERROR 40_numpy: ERROR: 100% broken (log: build/logs/40_numpy.log)"
    assert sum(x.startswith("ERROR") for x in block) == 1


def test_escapes_in_the_log_never_reach_the_output(work) -> None:
    _needs_sh()
    block = _fail_with(Tree(work), "plain\n\x1b[31mred\x1b[0m\tend\x07\n")
    assert "  | red\tend" in block
    assert not any("\x1b" in x or "[31m" in x for x in block)


# --------------------------------------------------------------------------------------------
# 5. Tables: numbers and choices in, strings out.


def _call(*words: str) -> str:
    lib = SCRIPTS / "steps" / "progress.sh"
    script = '. "$0"; "$@"'
    out = subprocess.run(
        [SHELLS[0], "-c", script, str(lib), *words],
        capture_output=True,
        text=True,
        timeout=GUARD,
        check=True,
        env={"PATH": os.environ.get("PATH", os.defpath)},
    )
    return out.stdout


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [(0, "0s"), (7, "7s"), (59, "59s"), (60, "1m00s"), (182, "3m02s"), (3599, "59m59s"),
     (3600, "1h00m"), (3840, "1h04m"), (90061, "25h01m")],
)  # fmt: skip
def test_duration_format(seconds, shown) -> None:
    _needs_sh()
    assert _call("progress_fmt", str(seconds)) == shown


@pytest.mark.parametrize(
    ("args", "left"),
    [
        (("10", "30", "20", "5"), "45"),  # 30-10 left of this step, then 20 and 5
        (("50", "10"), "0"),  # past the estimate, within ten times it: never below 0
        (("101", "10"), ""),  # past ten times the estimate: dropped
        (("0", "0", "0", "0"), "3"),  # every estimate at least 1 s
        (("11", "0"), ""),  # ten times max(0, 1) is 10
        (("5", "-", "3"), ""),  # this step has no estimate
        (("3", "10", "-"), ""),  # a later step has none
    ],
)
def test_time_left(args, left) -> None:
    _needs_sh()
    assert _call("progress_left", *args).strip() == left


@pytest.mark.parametrize(
    ("tty", "term", "ci", "flag", "env", "mode"),
    [
        ("yes", "xterm", "", "no", "", "tty"),
        ("no", "xterm", "", "no", "", "plain"),
        ("yes", "", "", "no", "", "plain"),
        ("yes", "dumb", "", "no", "", "plain"),
        ("yes", "xterm", "true", "no", "", "plain"),
        ("yes", "xterm", "", "yes", "", "plain"),
        ("yes", "xterm", "", "no", "plain", "plain"),
    ],
)
def test_mode_choice(tty, term, ci, flag, env, mode) -> None:
    _needs_sh()
    assert _call("progress_mode_for", tty, term, ci, flag, env).strip() == mode


@pytest.mark.parametrize(
    ("mode", "no_color", "colour"),
    [("tty", "", "yes"), ("tty", "1", "no"), ("plain", "", "no"), ("plain", "1", "no")],
)
def test_colour_choice(mode, no_color, colour) -> None:
    _needs_sh()
    assert _call("progress_colour_for", mode, no_color).strip() == colour


@pytest.mark.parametrize(
    ("mode", "lc_all", "lc_ctype", "lang", "glyphs"),
    [
        ("tty", "", "", "en_US.UTF-8", "utf8"),
        ("tty", "", "", "en_US.utf8", "utf8"),
        ("tty", "C", "", "en_US.UTF-8", "ascii"),  # LC_ALL first
        ("tty", "", "en_US.UTF-8", "C", "utf8"),  # then LC_CTYPE
        ("tty", "", "", "C", "ascii"),
        ("tty", "", "", "", "ascii"),
        ("plain", "", "", "en_US.UTF-8", "ascii"),  # glyphs only in the status line
    ],
)
def test_glyph_choice(mode, lc_all, lc_ctype, lang, glyphs) -> None:
    _needs_sh()
    assert _call("progress_glyphs_for", mode, lc_all, lc_ctype, lang).strip() == glyphs


# --------------------------------------------------------------------------------------------
# 6. Options, the summary and the preflight.


def _oks(out: str) -> list[str]:
    return [x.split(":")[0][3:] for x in out.splitlines() if x.startswith("ok ")]


def test_a_whole_build_ends_with_its_summary(work) -> None:
    _needs_sh()
    tree = Tree(work)
    out = tree.plain()
    lines = out.stdout.splitlines()
    assert out.returncode == 0, out.stdout
    assert re.fullmatch(
        r"preflight: (MACOS_ARM64|LINUX_AARCH64|LINUX_X86_64); 11 tools; 100\.0 GiB free", lines[0]
    ), lines[0]
    assert _oks(out.stdout) == list(STEPS)
    summary = f"00_download: {LONG}"[:120]
    assert lines[1] == f"ok 00_download: {summary} [{CLOCK_STEP}s]"
    sums = {
        name: hashlib.sha256(data).hexdigest()[:16]
        for name, data in (
            ("python.wasm", b"wasm"),
            ("python-snapshot.wasm", b"snapshot!"),
            ("python-stdlib.zip", b"zip"),
        )
    }
    total = (2 * len(STEPS) + 1) * CLOCK_STEP  # the summary's reading less the build's first
    assert lines[N_STEPS + 1 :] == [
        f"done: {N_STEPS} steps in {total // 60}m{total % 60:02d}s; the artifact set is in "
        "build/artifacts/",
        f"  python.wasm 4 bytes  {sums['python.wasm']}",
        f"  python-snapshot.wasm 9 bytes  {sums['python-snapshot.wasm']}",
        f"  python-stdlib.zip 3 bytes  {sums['python-stdlib.zip']}",
        'next: uv run pytest -m "not slow"',
    ]
    rows = tree.timings()
    assert [r[1:3] for r in rows] == [[s, "ok"] for s in STEPS]
    assert len({r[0] for r in rows}) == 1 and all(r[3] == str(CLOCK_STEP) for r in rows)


def test_a_partial_build_names_its_steps_only(work) -> None:
    _needs_sh()
    out = Tree(work).plain("20", "30")
    assert out.returncode == 0
    assert out.stdout.splitlines()[-1] == f"done: 2 steps in {5 * CLOCK_STEP}s: 20_cpython 30_zlib"


def test_list_names_each_step_and_its_last_time(work) -> None:
    _needs_sh()
    tree = Tree(work)
    _timings_for_every_step(tree)
    out = tree.plain("--list")
    assert out.returncode == 0
    lines = out.stdout.splitlines()
    assert [x.split()[0] for x in lines] == list(STEPS)
    for i, (step, line) in enumerate(zip(STEPS, lines, strict=True)):
        assert line == f"{step:<15} the fake {step} of the progress checks. [{3 + i}s]"
    assert not (tree.root / "build" / "logs" / "40_numpy.log").exists()  # nothing ran


def test_list_shows_the_newest_ok_time(work) -> None:
    _needs_sh()
    tree = Tree(work)
    logs = tree.root / "build" / "logs"
    logs.mkdir(parents=True)
    rows = [("1-1", "ok", "5"), ("2-2", "ok", "99"), ("3-3", "error", "500")]
    (logs / "timings.tsv").write_text("".join(f"{r}\t40_numpy\t{st}\t{t}\n" for r, st, t in rows))
    out = tree.plain("--list")
    line = next(x for x in out.stdout.splitlines() if x.startswith("40_numpy"))
    assert line.endswith(" [1m39s]"), line


def _first_sentence(script: Path) -> str:
    lines = script.read_text().splitlines()[1:]
    header = " ".join(
        x[2:] if x.startswith("# ") else x[1:]
        for x in lines[: next(i for i, x in enumerate(lines) if not x.startswith("#"))]
    )
    header = re.sub(r"^Step \d+: *", "", header)
    m = re.search(r"\.( |$)", header)
    return header[: m.start() + 1] if m else header


def test_list_cuts_the_real_descriptions_at_a_word(work) -> None:
    """The real step scripts' headers: the first sentence, cut at a word to fit 80 columns."""
    _needs_sh()
    tree = Tree(work)
    for step in STEPS:
        shutil.copy2(SCRIPTS / tree.path(step).relative_to(tree.root / "scripts"), tree.path(step))
    out = tree.plain("--list")
    assert out.returncode == 0
    for step, line in zip(STEPS, out.stdout.splitlines(), strict=True):
        assert len(line) <= 80 and not re.search(r"Step \d+:", line), line
        shown = line[16:]
        whole = _first_sentence(tree.path(step))
        if shown != whole:
            assert shown.endswith("..."), line
            kept = shown[:-3]
            assert whole.startswith(kept) and whole[len(kept)] in " ,;:(", (line, whole)


def test_from_runs_that_step_and_every_later_one(work) -> None:
    _needs_sh()
    out = Tree(work).plain("--from", "60")
    assert out.returncode == 0 and _oks(out.stdout) == list(STEPS[STEPS.index("60_link") :])


def test_resume_runs_from_the_last_failure_or_says_nothing(work) -> None:
    _needs_sh()
    tree = Tree(work)
    tree.step("40_numpy", "echo nope\nexit 1\n")
    assert tree.plain().returncode == 1
    assert tree.timings()[-1][1:3] == ["40_numpy", "error"]
    tree.step("40_numpy")
    out = tree.plain("--resume")
    assert out.returncode == 0 and _oks(out.stdout) == list(STEPS[STEPS.index("40_numpy") :]), (
        out.stdout
    )
    again = tree.plain("--resume")
    assert again.returncode == 2 and again.stdout.splitlines()[-1] == "nothing to resume"


def test_resume_with_no_record_has_nothing_to_resume(work) -> None:
    _needs_sh()
    out = Tree(work).plain("--resume")
    assert out.returncode == 2 and out.stdout.splitlines()[-1] == "nothing to resume"


@pytest.mark.parametrize(
    "args",
    [
        ["7"],
        ["--nope"],
        ["--from"],
        ["--from", "99"],
        ["40", "--from", "60"],
        ["--resume", "40"],
        ["--list", "40"],
        ["--check", "--list"],
        ["--help", "--from", "60"],
    ],
)
def test_a_wrong_option_or_step_exits_2_with_the_usage(work, args) -> None:
    _needs_sh()
    tree = Tree(work)
    out = tree.plain(*args)
    assert out.returncode == 2, out.stdout
    assert "usage: scripts/build.sh" in out.stdout
    assert out.stdout.splitlines()[-1].startswith("ERROR build: ")
    assert not (tree.root / "build" / "logs" / "00_download.log").exists()


def test_help_prints_the_usage(work) -> None:
    _needs_sh()
    out = Tree(work).plain("--help")
    assert out.returncode == 0 and out.stdout.startswith("usage: scripts/build.sh")


def test_check_runs_the_preflight_alone(work) -> None:
    _needs_sh()
    tree = Tree(work)
    out = tree.plain("--check")
    assert out.returncode == 0 and len(out.stdout.splitlines()) == 1
    assert out.stdout.startswith("preflight: ") and "; 11 tools; " in out.stdout
    assert not (tree.root / "build" / "logs" / "00_download.log").exists()


def test_check_refuses_a_missing_tool(work) -> None:
    _needs_sh()
    out = Tree(work, missing=("make", "uv")).plain("--check")
    assert out.returncode == 1
    assert out.stdout.splitlines() == ["ERROR preflight: no make, uv on PATH"]


def test_check_refuses_too_little_space_only_on_a_first_build(work) -> None:
    _needs_sh()
    tree = Tree(work, df_kib=1048576)  # 1 GiB
    out = tree.plain("--check")
    assert out.returncode == 1
    assert out.stdout.splitlines() == [
        "ERROR preflight: 1.0 GiB free under build/; a first build needs 2.5 GiB"
    ]
    assert tree.plain().returncode == 1  # a build runs the preflight first, and stops
    assert not (tree.root / "build" / "logs" / "00_download.log").exists()
    (tree.root / "build" / "tools").mkdir(parents=True)
    out = tree.plain("--check")
    assert out.returncode == 0 and out.stdout.endswith("; 1.0 GiB free\n")


# --------------------------------------------------------------------------------------------
# 7. The download step.

GET = re.compile(r"^\s*get\s+https?://\S+\s+(\S+)", re.M)
DOWNLOAD = SCRIPTS / "00_download.sh"
CURL = """#!/bin/sh
while [ "$#" -gt 0 ]; do
  case "$1" in -o) out=$2; shift;; esac
  shift
done
name=$(basename "$out" .part)
printf '%s' "$name" > "$out"
"""


def _download_tree(root: Path, *, curl: bool, other: bool = False) -> Path:
    root = root.resolve()
    for rel in ("00_download.sh", "line.sh", "line.conf"):
        dst = root / "scripts" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCRIPTS / rel, dst)
    bin_ = root / "bin"
    bin_.mkdir()
    for tool, real in FOUND.items():
        bin_.joinpath(tool).symlink_to(real)
    if curl:
        _script(bin_ / "curl", CURL)
    names = GET.findall(DOWNLOAD.read_text())
    d = root / "downloads"
    d.mkdir()
    if other:  # a pinned file this run does not get, present (the research input, say)
        names.append("other-input.zip")
        (d / "other-input.zip").write_text("other-input.zip")
    (d / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(n.encode()).hexdigest()}  {n}\n" for n in names)
    )
    for n in ("Python-3.15.0.tar.xz", "zlib-1.3.1.tar.gz"):
        (d / n).write_text(n)
    return root


def _download(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [SHELLS[0], str(root / "scripts" / "00_download.sh")],
        env={"PATH": str(root / "bin"), "HOME": str(root)},
        cwd=root,
        capture_output=True,
        text=True,
        timeout=GUARD,
        check=False,
    )


def test_the_download_step_says_what_it_fetched_and_verified(work) -> None:
    _needs_sh()
    root = _download_tree(work, curl=True)
    out = _download(root)
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    present = [x for x in lines if x.startswith("present ")]
    fetched = [x for x in lines if x.startswith("fetched ")]
    assert present == ["present Python-3.15.0.tar.xz", "present zlib-1.3.1.tar.gz"]
    n = len(present) + len(fetched)
    assert n > 20
    assert sum(x.endswith(": OK") for x in lines) == n
    assert lines[-1] == f"downloads: {n} pins, {n - 2} fetched, {n} verified"
    again = _download(root).stdout.splitlines()
    assert again[-1] == f"downloads: {n} pins, 0 fetched, {n} verified"


def test_a_verified_file_that_is_no_pin_is_named_apart(work) -> None:
    _needs_sh()
    out = _download(_download_tree(work, curl=True, other=True))
    lines = out.stdout.splitlines()
    n = sum(x.startswith(("present ", "fetched ")) for x in lines)
    assert sum(x.endswith(": OK") for x in lines) == n + 1
    assert lines[-1] == (
        f"downloads: {n} pins, {n - 2} fetched, {n} verified; "
        "1 other file in downloads/ verified too"
    )


def test_the_download_step_refuses_without_curl(work) -> None:
    _needs_sh()
    root = _download_tree(work, curl=False)
    out = _download(root)
    assert out.returncode == 1
    m = re.fullmatch(r"ERROR: no curl on PATH; it fetches (\S+)", out.stderr.strip())
    assert m, out.stderr
    assert m.group(1) in GET.findall(DOWNLOAD.read_text())
    assert not (root / "downloads" / m.group(1)).exists()


def test_a_download_that_does_not_match_fails_the_step(work) -> None:
    _needs_sh()
    root = _download_tree(work, curl=True)
    (root / "downloads" / "zlib-1.3.1.tar.gz").write_text("changed")
    out = _download(root)
    assert out.returncode != 0
    assert "zlib-1.3.1.tar.gz: FAILED" in out.stdout
    assert not any(x.startswith("downloads: ") for x in out.stdout.splitlines())


# --------------------------------------------------------------------------------------------
# 8. Only the pinned host Python: behind the shim, every other Python name
# refuses, and a step that ran one fails even when it swallowed the refusal.


def test_a_step_that_runs_an_unpinned_python_fails(work) -> None:
    _needs_sh()
    tree = Tree(work)
    tree.step("40_numpy", "python3 -c 'print(1)'\n")
    out = tree.plain("40")
    assert out.returncode == 1, out.stdout
    assert out.stdout.splitlines()[-1] == (
        "ERROR 40_numpy: ERROR: an unpinned python3 was run; a build step runs only "
        "build/tools/host-python's Python (spec 079) (log: build/logs/40_numpy.log)"
    ), out.stdout
    logged = (work / "build" / "logs" / "unpinned-python.log").read_text()
    assert logged.endswith("/build/no-host-python/python3 -c print(1)\n"), logged


@pytest.mark.parametrize(
    "body",
    [
        "python3 -V 2> /dev/null || true\necho swallowed\n",
        # Configure under `env -i` keeps PATH and drops every other variable.
        "env -i PATH=\"$PATH\" sh -c 'python3.14 -V 2> /dev/null || true'\necho swallowed\n",
    ],
    ids=["plain", "env-i"],
)
def test_a_swallowed_refusal_still_fails_the_step(work, body) -> None:
    _needs_sh()
    tree = Tree(work)
    tree.step("40_numpy", body)
    out = tree.plain("40")
    assert out.returncode == 1, out.stdout
    assert out.stdout.splitlines()[-1] == (
        "ERROR 40_numpy: ERROR: 40_numpy ran an unpinned Python (build/logs/unpinned-python.log) "
        "(log: build/logs/40_numpy.log)"
    ), out.stdout
    assert (work / "build" / "logs" / "40_numpy.log").read_text().startswith("swallowed\n")


def test_every_python_name_on_the_callers_path_is_shadowed(work) -> None:
    _needs_sh()
    tree = Tree(work)
    host = work / "host bin"  # a folder whose path holds a space
    _script(host / "python3-intel64", "#!/bin/sh\necho reached the host\n")
    _script(host / "python3.10", "#!/bin/sh\necho reached the host\n")
    _script(work / "other" / "python3.10", "#!/bin/sh\necho reached the host\n")  # a duplicate
    (host / "pip-folder").mkdir()  # not a file, so not swept
    (host / "pydoc-data").write_text("")  # not executable, so not swept
    tree.step("40_numpy", "python3-intel64\n")
    env = tree.env(PATH=f"{tree.bin}:{host}:{work / 'other'}:relative/bin::")
    out = tree.plain("40", env=env)
    assert out.returncode == 1, out.stdout
    assert "reached the host" not in out.stdout
    assert "an unpinned python3-intel64 was run" in out.stdout.splitlines()[-1], out.stdout
    nopy = work / "build" / "no-host-python"
    names = sorted(p.name for p in nopy.iterdir())
    assert {"python3-intel64", "python3.10", "python", "python2.7", "python3.20"} <= set(names)
    assert "pip-folder" not in names and "pydoc-data" not in names
    # The step's PATH: the stand-in first, then the caller's absolute entries only.
    tree.step("40_numpy", 'echo "PATH=$PATH"\n')
    out = tree.plain("40", env=env)
    shown = (work / "build" / "logs" / "40_numpy.log").read_text().strip()
    assert shown == f"PATH={nopy}:{tree.bin}:{host}:{work / 'other'}", shown
