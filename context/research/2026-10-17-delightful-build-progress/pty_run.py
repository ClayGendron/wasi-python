"""Run a command under a pseudo-terminal and write what it printed.

Usage: uv run --no-project python -I pty_run.py [--raw] <out file> <cmd> [args...]
Without --raw, escapes are made visible (<ESC>, <CR>); with it the bytes are kept as they were.
Stdlib only; used to capture how a tool renders to a terminal versus a pipe.
"""

import os
import subprocess
import sys


def main() -> int:
    args = sys.argv[1:]
    raw = args[0] == "--raw"
    if raw:
        args = args[1:]
    out_path, argv = args[0], args[1:]
    master, slave = os.openpty()
    proc = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
    os.close(slave)
    chunks: list[bytes] = []
    while True:
        try:
            data = os.read(master, 65536)
        except OSError:  # EIO once the child side closes
            break
        if not data:
            break
        chunks.append(data)
    os.close(master)
    code = proc.wait()
    data = b"".join(chunks)
    if raw:
        with open(out_path, "wb") as f:
            f.write(data)
        return code
    text = data.decode("utf-8", "replace")
    visible = text.replace("\x1b", "<ESC>").replace("\r\n", "\n").replace("\r", "<CR>\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(visible)
    return code


if __name__ == "__main__":
    sys.exit(main())
