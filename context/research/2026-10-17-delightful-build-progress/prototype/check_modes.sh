#!/bin/sh
# The prototype's own check, in the shape a judge check would take: run the same fake build in
# plain mode and on a pseudo-terminal, with a counting clock (each reading adds 7 "seconds"), replay
# the terminal bytes to the final screen, and require it to equal the plain output. Counts and
# compares; never times. Usage: check_modes.sh <shell> <work dir> [steps...]
set -u
HERE=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
SH=$1; W=$2; shift 2
rm -rf "$W"; mkdir -p "$W/plain" "$W/tty"
echo 1000 > "$W/clock.plain"; echo 1000 > "$W/clock.tty"
FAKE_CLOCK="$W/clock.plain" PROGRESS=plain "$SH" "$HERE/demo.sh" "$W/plain" "$@" > "$W/plain.out" 2>&1
echo "plain exit $?"
FAKE_CLOCK="$W/clock.tty" PROGRESS=tty TERM=xterm uv run --no-project python -I "$HERE/../pty_run.py" --raw "$W/tty.raw" "$SH" "$HERE/demo.sh" "$W/tty" "$@"
echo "tty exit $?"
uv run --no-project python -I "$HERE/replay_terminal.py" "$W/tty.raw" | sed "s/$(printf '\033')\[[0-9;]*m//g" > "$W/tty.screen"
if diff "$W/plain.out" "$W/tty.screen" > "$W/diff.txt"; then
  echo "final screen == plain output ($(wc -l < "$W/plain.out" | tr -d ' ') lines)"
else
  echo "DIFFERENT:"; cat "$W/diff.txt"
fi
echo "redraws on the terminal: $(LC_ALL=C tr -cd '\r' < "$W/tty.raw" | wc -c | tr -d ' ') carriage returns"
