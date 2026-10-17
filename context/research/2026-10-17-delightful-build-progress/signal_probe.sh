#!/bin/sh
# Does a shell's background job ignore SIGINT? POSIX says an asynchronous list in a shell without
# job control ignores SIGINT and SIGQUIT; shells differ. Prints one line per shell found.
for s in /bin/dash /bin/sh /bin/bash /bin/zsh /usr/bin/dash; do
  [ -x "$s" ] || continue
  "$s" -c 'sleep 3 & pid=$!; kill -INT $pid; sleep 0.3
    if kill -0 $pid 2>/dev/null; then r=survived; else r=died; fi
    kill $pid 2>/dev/null; wait; echo "$0: background job $r SIGINT"' "$s"
done
