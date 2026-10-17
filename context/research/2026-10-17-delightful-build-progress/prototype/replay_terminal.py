"""Replay a terminal byte stream and print the final screen: what a person sees once it ends.

Usage: uv run --no-project python -I replay_terminal.py <raw capture>
Understands what the prototype emits: CR, LF, ESC[K, ESC[J, ESC[<n>A, and SGR colour (ignored).
A pty turns LF into CR LF, so a CR is a column reset only. The check that uses it compares this
screen with the plain mode's output: the two modes must say the same thing.
"""

import re
import sys

CSI = re.compile(rb"\x1b\[([0-9;?]*)([A-Za-z])")


def screen(data: bytes) -> list[str]:
    rows: list[list[str]] = [[]]
    r = c = 0
    i = 0
    while i < len(data):
        m = CSI.match(data, i)
        if m:
            arg, op = m.group(1).decode(), m.group(2).decode()
            if op == "K":
                del rows[r][c:]
            elif op == "J":
                del rows[r][c:]
                del rows[r + 1 :]
            elif op == "A":
                r = max(0, r - int(arg or 1))
            i = m.end()
            continue
        ch = data[i : i + 1]
        i += 1
        if ch == b"\r":
            c = 0
        elif ch == b"\n":
            r += 1
            c = 0
            while len(rows) <= r:
                rows.append([])
        else:
            row = rows[r]
            while len(row) < c:
                row.append(" ")
            if c < len(row):
                row[c] = ch.decode("latin-1")
            else:
                row.append(ch.decode("latin-1"))
            c += 1
    lines = ["".join(x).rstrip() for x in rows]
    while lines and not lines[-1]:
        lines.pop()
    return lines


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        print("\n".join(screen(f.read())))
