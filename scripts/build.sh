#!/bin/sh
# Build the artifact set from pinned inputs (spec 003): one line per step, the full log under
# build/logs/<step>.log; on a terminal, a status line below them says where it is (spec 027).
#
#   scripts/build.sh                 every step, in order
#   scripts/build.sh 60 70 80 90     only the named steps (by number or full name)
#   scripts/build.sh --from 60       that step and every later one
#   scripts/build.sh --resume        the step the newest run did not finish, and every later one
#   scripts/build.sh --list          each step, what it does, and its newest time
#   scripts/build.sh --check         the preflight alone; every build runs it first
#   --plain (with any of them)       no status line and no colour; a pipe or CI gets the same
#
# Downloads come first: scripts/00_download.sh fetches and verifies every pin. Every step runs in
# the foreground with the same environment, stdin and argv in every mode. Nothing is skipped on its
# own: each step removes and remakes its outputs.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
# The caller's locale decides the status line's glyphs: read before LC_ALL=C below.
P_LC_ALL=${LC_ALL:-} P_LC_CTYPE=${LC_CTYPE:-} P_LANG=${LANG:-}
export SOURCE_DATE_EPOCH=1767225600  # 2026-01-01T00:00:00Z: a constant, so rebuilds are equal
export UV_CACHE_DIR="$HERE/build/uv-cache"
export PYTHONHASHSEED=0
export LC_ALL=C  # one collation on every host: each step's `sort` orders bytes alike (spec 012)
. "$HERE/scripts/steps/remove.sh"
. "$HERE/scripts/steps/progress.sh"

ALL="00_download 10_tools 20_cpython 30_zlib 35_stdlib_libs 36_xml_libs 37_plot_libs 40_numpy 50_pandas 53_regex 54_lxml 55_matplotlib 60_link 70_zip 80_snapshot 90_artifacts"
P_TIMINGS=$HERE/build/logs/timings.tsv

usage() {
  cat << 'EOF'
usage: scripts/build.sh [--plain] [STEP... | --from STEP | --resume]
       scripts/build.sh [--plain] --list | --check | --help
  STEP       a step by number or full name; only the named steps run
  --from     that step and every later one
  --resume   the step the newest run did not finish, and every later one
  --list     each step, what it does, and its newest time
  --check    the preflight alone (host, tools, free space); every build runs it first
  --plain    no status line and no colour, as in a pipe or CI
  --help     this text
EOF
}

bad() { # the usage, then one ERROR line; exit 2
  usage
  echo "ERROR build: $1"
  exit 2
}

pick() { # named steps, --from and --resume go alone
  if [ -n "$P_PICK" ] && { [ "$P_PICK" != "$1" ] || [ "$1" != named ]; }; then
    bad "named steps, --from and --resume go alone"
  fi
  P_PICK=$1
}

find_step() { # want -> P_FOUND, the step's full name
  P_FOUND=""
  for s in $ALL; do
    case "$s" in "$1"|"$1"_*) P_FOUND=$s;; esac
  done
  [ -n "$P_FOUND" ] || bad "no step $1 (steps: $ALL)"
}

script_of() { # step -> its script
  case "$1" in
    00_*) echo "$HERE/scripts/00_download.sh";;
    *) echo "$HERE/scripts/steps/$1.sh";;
  esac
}

steps_from() { # step -> that step and every later one
  on=no
  for s in $ALL; do
    [ "$s" != "$1" ] || on=yes
    [ "$on" = no ] || printf '%s ' "$s"
  done
}

P_PLAIN=no P_DO=build P_PICK="" P_NAMED="" P_FROM=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plain) P_PLAIN=yes;;
    --list|--check|--help)
      [ "$P_DO" = build ] || bad "--list, --check and --help go alone"
      P_DO=${1#--};;
    --from)
      [ "$#" -ge 2 ] || bad "--from needs a step"
      pick from
      find_step "$2"
      P_FROM=$P_FOUND
      shift;;
    --resume) pick resume;;
    -*) bad "no option $1";;
    *)
      pick named
      find_step "$1"
      P_NAMED="$P_NAMED $P_FOUND";;
  esac
  shift
done

if [ "$P_DO" != build ] && [ -n "$P_PICK" ]; then
  bad "--$P_DO takes no steps"
fi

if [ "$P_DO" = help ]; then
  usage
  exit 0
fi

if [ -t 1 ]; then P_TTY=yes; else P_TTY=no; fi
progress_setup "$(progress_mode_for "$P_TTY" "${TERM:-}" "${CI+set}" "$P_PLAIN" "${BUILD_PROGRESS:-}")" \
  "${NO_COLOR:-}" "$P_LC_ALL" "$P_LC_CTYPE" "$P_LANG"

if [ "$P_DO" = list ]; then
  for step in $ALL; do
    last=$(progress_last "$step" "$P_TIMINGS")
    [ -z "$last" ] || last=" [$(progress_fmt "$last")]"
    what=$(progress_what "$(script_of "$step")" $((80 - 16 - ${#last})))  # a line fits 80 columns
    printf '%-15s %s%s\n' "$step" "$what" "$last"
  done
  exit 0
fi

case "$P_PICK" in
  "") STEPS=$ALL;;
  named) STEPS=$P_NAMED;;
  from) STEPS=$(steps_from "$P_FROM");;
  resume)
    # The newest run's last row: if it is not `ok`, that step and every later one.
    row=$(tail -n 1 "$P_TIMINGS" 2> /dev/null || :)
    row_status=$(printf '%s\n' "$row" | cut -f 3)
    if [ -z "$row" ] || [ "$row_status" = ok ]; then
      echo "nothing to resume"
      exit 2
    fi
    find_step "$(printf '%s\n' "$row" | cut -f 2)"
    STEPS=$(steps_from "$P_FOUND");;
esac

# Every exit stops the ticker and erases its line. A signal is recorded: the running step ends
# first (Ctrl-C reaches it through the process group; a TERM or HUP to this shell alone waits for
# it), its own line is printed, and the build stops before the next step with 130, 143 or 129.
P_PID=$$ P_SIG="" P_ENDED="" P_STEP=""
signal_code() {
  case "$P_SIG" in INT) echo 130;; TERM) echo 143;; *) echo 129;; esac
}
interrupted() { # step [after]: the one INTERRUPTED line, then the signal's exit code
  P_ENDED=yes
  progress_line INTERRUPTED 31 "$1"
  exit "$(signal_code)"
}
on_exit() {
  progress_stop
  if [ -n "$P_SIG" ] && [ -z "$P_ENDED" ]; then
    if [ -n "$P_STEP" ]; then
      interrupted "$P_STEP (log: build/logs/$P_STEP.log)"
    else
      interrupted build
    fi
  fi
}
trap on_exit EXIT
trap 'P_SIG=INT' INT
trap 'P_SIG=TERM' TERM
trap 'P_SIG=HUP' HUP

mkdir -p "$HERE/build/logs"
progress_preflight
if [ "$P_DO" = check ]; then
  P_ENDED=yes
  exit 0
fi

# Every Python a step runs is the pinned one (spec 079, Decision 4). Step 10's shim for it,
# build/tools/host-python/, comes first on each step's PATH (common.sh). Behind it this folder
# shadows, with the refusing stand-in scripts/refuse-python, every python*, pypy*, pip*, pydoc*
# and idle* file the caller's PATH holds, and a fixed list besides; the first link of a name wins.
# Empty and relative PATH entries are dropped: they resolve against each step's own folder, where
# no sweep can see. A step that ran a stand-in fails, even if it swallowed the refusal.
P_NOPY=$HERE/build/no-host-python
P_UNPINNED=$HERE/build/logs/unpinned-python.log
remove "$P_NOPY"
mkdir -p "$P_NOPY"
shadow() { # a name: link it to the stand-in unless a link of that name is there already
  [ -e "$P_NOPY/$1" ] || [ -L "$P_NOPY/$1" ] || ln -s "$HERE/scripts/refuse-python" "$P_NOPY/$1"
}
P_KEPT="" P_IFS=$IFS
IFS=:
set -f
for p_dir in $PATH; do
  set +f
  case "$p_dir" in
    "$P_NOPY") ;;
    /*)
      P_KEPT="${P_KEPT:+$P_KEPT:}$p_dir"
      for p_file in "$p_dir"/python* "$p_dir"/pypy* "$p_dir"/pip* "$p_dir"/pydoc* "$p_dir"/idle*; do
        if [ -f "$p_file" ] && [ -x "$p_file" ]; then
          shadow "${p_file##*/}"
        fi
      done;;
  esac
  set -f
done
set +f
IFS=$P_IFS
for p_name in python python2 python2.7 python3; do shadow "$p_name"; done
p_n=0
while [ "$p_n" -le 20 ]; do
  shadow "python3.$p_n"
  p_n=$((p_n + 1))
done
export PATH="$P_NOPY:$P_KEPT"

n=$(set -- $STEPS; echo "$#")
P_T0=$(progress_clock)
P_RUN="$P_T0-$$"
k=0
for step in $STEPS; do
  k=$((k + 1))
  if [ -n "$P_SIG" ]; then
    progress_row "$P_TIMINGS" "$P_RUN" "$step" interrupted 0
    interrupted "before $step"  # it never started, so this run wrote no log for it
  fi
  script=$(script_of "$step")
  case "$step" in
    00_*) ;;
    # A rebuild never leaves an older set that looks current.
    *) remove "$HERE/build/artifacts" "$HERE/build/artifacts.new";;
  esac
  log="$HERE/build/logs/$step.log"
  estimate=$(progress_last "$step" "$P_TIMINGS")
  later="" i=0
  for s in $STEPS; do
    i=$((i + 1))
    if [ "$i" -gt "$k" ]; then
      e=$(progress_last "$s" "$P_TIMINGS")
      later="$later ${e:--}"
    fi
  done
  start=$(progress_clock)
  if [ "$P_MODE" = tty ]; then
    progress_ticker "$k" "$n" "$step" "$log" "$estimate" $later &
    P_TPID=$!
  fi
  rc=0
  P_STEP=$step  # from here this run has written the step's log
  remove "$P_UNPINNED"
  sh "$script" > "$log" 2>&1 || rc=$?
  if [ "$rc" -eq 0 ] && [ -e "$P_UNPINNED" ]; then
    echo "ERROR: $step ran an unpinned Python (build/logs/unpinned-python.log)" >> "$log"
    rc=1
  fi
  end=$(progress_clock)
  progress_stop
  seconds=$((end - start))
  if [ "$rc" -eq 0 ]; then
    progress_row "$P_TIMINGS" "$P_RUN" "$step" ok "$seconds"
    progress_ok "$step" "$seconds" "$log"
  elif [ -n "$P_SIG" ]; then
    progress_row "$P_TIMINGS" "$P_RUN" "$step" interrupted "$seconds"
    interrupted "$step (log: build/logs/$step.log)"
  else
    progress_row "$P_TIMINGS" "$P_RUN" "$step" error "$seconds"
    P_ENDED=yes
    progress_failed "$step" "$rc" "$seconds" "$log" "build/logs/$step.log"
    exit 1
  fi
done
[ -z "$P_SIG" ] || interrupted "after $step: every step had finished"
P_ENDED=yes
end=$(progress_clock)
progress_summary "$k" "$((end - P_T0))" "$STEPS"
