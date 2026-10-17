# A research prototype, not the build: one way a POSIX sh driver could show progress (memo
# 2026-10-17-delightful-build-progress.md, "What it decides"). Sourced; it defines functions only.
#
# The step always runs in the foreground, with the driver's environment and stdout/stderr to its log,
# in both modes. On a terminal a background "ticker" redraws a live region (status line plus the
# log's last lines) until the step ends; then the region is erased and one permanent line is
# printed. The permanent lines are the plain mode's lines, so the two modes say the same thing.
#
#   PROGRESS=auto|tty|plain   auto: tty when stdout is a terminal, TERM is set and not dumb, CI unset
#   NO_COLOR=<non-empty>      no colour (no-color.org)
#   progress_now              the clock; a test replaces it with a counter (it counts, never times)

progress_now() { date +%s; }

progress_init() { # total-steps timings-file
  P_TOTAL=$1; P_TIMINGS=$2; P_DONE=0; P_T0=$(progress_now)
  P_MODE=${PROGRESS:-auto}
  if [ "$P_MODE" = auto ]; then
    P_MODE=plain
    if [ -t 1 ] && [ -n "${TERM:-}" ] && [ "$TERM" != dumb ] && [ -z "${CI:-}" ]; then P_MODE=tty; fi
  fi
  P_ESC=$(printf '\033'); P_BOLD=""; P_DIM=""; P_RED=""; P_GREEN=""; P_OFF=""
  if [ "$P_MODE" = tty ] && [ -z "${NO_COLOR:-}" ]; then
    P_BOLD="$P_ESC[1m"; P_DIM="$P_ESC[2m"; P_RED="$P_ESC[31m"; P_GREEN="$P_ESC[32m"; P_OFF="$P_ESC[0m"
  fi
  P_TAIL=${PROGRESS_TAIL_LINES:-4}
  : > "$P_TIMINGS.new"
}

progress_fmt() { # seconds -> 7s, 3m02s, 1h04m
  if [ "$1" -lt 60 ]; then printf '%ds' "$1"
  elif [ "$1" -lt 3600 ]; then printf '%dm%02ds' $(($1 / 60)) $(($1 % 60))
  else printf '%dh%02dm' $(($1 / 3600)) $(($1 % 3600 / 60)); fi
}

progress_prev() { # step -> seconds it took last time, or nothing
  [ -f "$P_TIMINGS" ] && awk -F '\t' -v s="$1" '$1 == s && $2 == "ok" { t = $3 } END { if (t != "") print t }' "$P_TIMINGS"
}

# Printable ASCII only: a log line from an upstream build system never reaches the terminal as an
# escape sequence, and cutting by bytes never splits a character.
progress_clean() { LC_ALL=C tr -cd '\11\12\40-\176' | LC_ALL=C tr '\11' ' '; }

progress_sub() { # log -> the step's own progress: ninja's last [n/N], else its last line
  LC_ALL=C grep -E '^\[[0-9]+/[0-9]+\]' "$1" 2>/dev/null | tail -n 1 | sed -E 's/^(\[[0-9]+\/[0-9]+\]).*/\1/'
}

progress_ticker() { # step log  (background; its own wall clock, for display only; stops at the next frame after TERM)
  stop=0; trap 'stop=1' TERM
  prev=$(progress_prev "$1"); i=0; t0=$(date +%s)
  cols=$(stty size 2> /dev/null <&1 | cut -d ' ' -f 2); cols=${cols:-${COLUMNS:-80}}
  w=$((cols - 6))
  while [ "$stop" = 0 ]; do
    el=$(( $(date +%s) - t0 ))
    case $((i % 4)) in 0) sp='|';; 1) sp='/';; 2) sp='-';; *) sp='\';; esac
    eta=""; [ -n "$prev" ] && eta=" / ~$(progress_fmt "$prev")"
    sub=$(progress_sub "$2")
    line="$sp $1  $(progress_fmt "$el")$eta  ${sub}  [$((P_DONE + 1))/$P_TOTAL]"
    head=$(printf '%s' "$line" | cut -c1-"$cols")
    tail=$(tail -n "$P_TAIL" "$2" 2> /dev/null | progress_clean | cut -c1-"$w")
    n=1
    printf '\r%s[K%s%s%s\n' "$P_ESC" "$P_BOLD" "$head" "$P_OFF"
    if [ -n "$tail" ]; then  # the frame is built in memory: the ticker writes nothing to disk
      n=$((n + $(printf '%s\n' "$tail" | wc -l)))
      printf '%s\n' "$tail" | while IFS= read -r l; do
        printf '%s[K%s  | %s%s\n' "$P_ESC" "$P_DIM" "$l" "$P_OFF"
      done
    fi
    printf '%s[%dA' "$P_ESC" "$n"   # back to the region's first line
    i=$((i + 1)); sleep 0.2
  done
}

progress_step() { # name script log -> the step's exit code
  name=$1; script=$2; log=$3; start=$(progress_now); tpid=""
  [ "$P_MODE" = plain ] || { progress_ticker "$name" "$log" & tpid=$!; }
  trap 'progress_stop_ticker; printf "\nINTERRUPTED %s (log: %s)\n" "$name" "$log"; exit 130' INT TERM
  set +e; sh "$script" > "$log" 2>&1; rc=$?; set -e
  progress_stop_ticker; trap - INT TERM
  secs=$(( $(progress_now) - start ))
  if [ "$rc" = 0 ]; then
    P_DONE=$((P_DONE + 1))
    printf '%sok%s %s: %s [%s]\n' "$P_GREEN" "$P_OFF" "$name" "$(tail -n 1 "$log" | progress_clean | cut -c1-100)" "$(progress_fmt "$secs")"
    printf '%s\tok\t%s\n' "$name" "$secs" >> "$P_TIMINGS.new"
  else
    printf '%sERROR%s %s: exit %s after %s; the last %s lines of %s:\n' "$P_RED" "$P_OFF" "$name" "$rc" "$(progress_fmt "$secs")" "${PROGRESS_FAIL_LINES:-20}" "$log"
    tail -n "${PROGRESS_FAIL_LINES:-20}" "$log" | progress_clean | sed 's/^/  | /'
    why=$(LC_ALL=C grep -E '^ERROR' "$log" | tail -n 1 | progress_clean | cut -c1-160)
    printf '%sERROR%s %s: %s (log: %s)\n' "$P_RED" "$P_OFF" "$name" "${why:-exit $rc}" "$log"
    printf '%s\terror\t%s\n' "$name" "$secs" >> "$P_TIMINGS.new"
  fi
  return "$rc"
}

progress_stop_ticker() {
  [ -n "${tpid:-}" ] || return 0
  kill -TERM "$tpid" 2> /dev/null; wait "$tpid" 2> /dev/null
  printf '\r%s[J' "$P_ESC"     # erase the live region; the permanent line goes where it began
  tpid=""
}

progress_finish() { # artifacts-dir
  mv "$P_TIMINGS.new" "$P_TIMINGS"
  printf 'done: %s steps in %s\n' "$P_DONE" "$(progress_fmt $(( $(progress_now) - P_T0 )))"
  if [ -f "$1/SHA256SUMS" ]; then
    for a in python.wasm python-snapshot.wasm python-stdlib.zip; do
      [ -f "$1/$a" ] && printf '  %-22s %10s bytes  %s\n' "$a" "$(wc -c < "$1/$a" | tr -d ' ')" \
        "$(awk -v a="$a" '$2 == a { print substr($1, 1, 16) }' "$1/SHA256SUMS")"
    done
  fi
  printf 'next: uv run pytest -m "not slow"\n'
}
