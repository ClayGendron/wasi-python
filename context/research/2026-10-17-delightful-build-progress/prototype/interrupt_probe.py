"""Press Ctrl-C during a step, on a real pseudo-terminal, and report what is left running.

Usage: uv run --no-project python -I interrupt_probe.py <shell> <demo.sh> <work dir>
The demo runs as a session leader with the pty as its controlling terminal, so a ^C byte becomes
SIGINT for the foreground process group, as at a keyboard. Prints the exit code, the screen's last
lines, and whether the step's `sleep 31.5` or the ticker survived.
"""

import fcntl
import os
import subprocess
import sys
import termios
import time


def main() -> int:
    shell, demo, work = sys.argv[1:4]
    master, slave = os.openpty()

    def child_setup() -> None:
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    env = dict(os.environ, PROGRESS="tty", TERM="xterm")
    proc = subprocess.Popen(
        [shell, demo, work, "d_long"], stdin=slave, stdout=slave, stderr=slave,
        preexec_fn=child_setup, env=env,
    )
    os.close(slave)
    time.sleep(1.5)  # the probe waits for the step to start; nothing is measured
    os.write(master, b"\x03")
    out = b""
    while True:
        try:
            data = os.read(master, 65536)
        except OSError:
            break
        if not data:
            break
        out += data
    code = proc.wait()
    time.sleep(0.5)
    left = subprocess.run(["pgrep", "-f", "sleep 31.5"], capture_output=True, text=True).stdout
    ticker = subprocess.run(["pgrep", "-f", "sleep 0.2"], capture_output=True, text=True).stdout
    text = out.decode("utf-8", "replace").replace("\x1b", "<ESC>").replace("\r\n", "\n")
    print(f"{shell}: exit {code}")
    print("  last line:", text.strip().splitlines()[-1].replace("\r", "<CR>")[-120:])
    print("  step's sleep left running:", "yes " + left.strip() if left.strip() else "no")
    print("  ticker left running:", "yes" if ticker.strip() else "no")
    return 0


if __name__ == "__main__":
    sys.exit(main())
