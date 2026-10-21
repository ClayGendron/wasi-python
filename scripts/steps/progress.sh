# Sourced by scripts/build.sh: how the build shows where it is. It defines functions
# only. Nothing here changes what a step sees: no export, no file a step reads, no descriptor.
#
# Two ways to show it. Plain (a pipe, a file, CI, TERM unset or dumb, --plain, BUILD_PROGRESS=plain)
# prints the permanent lines only. Terminal mode prints the same lines, colour on the leading word
# unless NO_COLOR is set, and one status line below them that a background ticker redraws in place
# with CR and ESC[K. Each permanent line first erases the status line, so the terminal ends showing
# the plain output. The status line holds only the driver's own words and numbers, never log text.
#
# Durations are whole seconds. Permanent lines read the clock through progress_clock, which runs
# ${BUILD_CLOCK:-date +%s} (a check sets a counting script); the ticker reads `date +%s` itself.

P_ESC=$(printf '\033')

progress_clock() { ${BUILD_CLOCK:-date +%s}; }

progress_fmt() { # seconds -> 7s, 3m02s, 1h04m
  if [ "$1" -lt 60 ]; then printf '%ds' "$(($1 < 0 ? 0 : $1))"
  elif [ "$1" -lt 3600 ]; then printf '%dm%02ds' $(($1 / 60)) $(($1 % 60))
  else printf '%dh%02dm' $(($1 / 3600)) $(($1 % 3600 / 60)); fi
}

# stdout-is-a-terminal(yes|no) TERM CI-is-set(non-empty if so) --plain(yes|no) BUILD_PROGRESS
progress_mode_for() { # -> tty|plain
  if [ "$1" = yes ] && [ -n "$2" ] && [ "$2" != dumb ] && [ -z "$3" ] && [ "$4" != yes ] \
    && [ "$5" != plain ]; then
    echo tty
  else
    echo plain
  fi
}

progress_colour_for() { # mode NO_COLOR -> yes|no (no-color.org: any non-empty value turns it off)
  if [ "$1" = tty ] && [ -z "$2" ]; then echo yes; else echo no; fi
}

progress_glyphs_for() { # mode LC_ALL LC_CTYPE LANG -> utf8|ascii; the first one set decides
  _g_loc=${2:-${3:-${4:-}}}
  case "$1:$_g_loc" in
    tty:*[Uu][Tt][Ff]-8*|tty:*[Uu][Tt][Ff]8*) echo utf8;;
    *) echo ascii;;
  esac
}

# A log's text as it may reach the screen: printable ASCII and tab only, whole CSI sequences
# (ESC [ parameters intermediates final) dropped first, so `ESC[31mred` shows as `red`.
progress_clean() {
  LC_ALL=C sed "s,$P_ESC\[[0-?]*[ -/]*[@-~],,g" | LC_ALL=C tr -cd '\11\12\40-\176'
}

progress_last() { # step timings-file -> its newest `ok` seconds, or nothing
  [ -f "$2" ] || return 0
  awk -F '\t' -v s="$1" '$2 == s && $3 == "ok" { t = $4 } END { if (t != "") print t }' "$2"
}

# Seconds left: the running step's estimate less its elapsed time (never below 0), plus each later
# step's estimate; every estimate counts as at least 1 s. Nothing when an estimate is missing (-) or
# the running step has passed ten times its estimate.
progress_left() { # elapsed estimate later-estimates...
  _l_el=$1
  _l_est=$2
  shift 2
  [ "$_l_est" != - ] || return 0
  [ "$_l_est" -ge 1 ] || _l_est=1
  [ "$_l_el" -le $((_l_est * 10)) ] || return 0
  _l_left=$((_l_est - _l_el))
  [ "$_l_left" -ge 0 ] || _l_left=0
  for _l_e in "$@"; do
    [ "$_l_e" != - ] || return 0
    [ "$_l_e" -ge 1 ] || _l_e=1
    _l_left=$((_l_left + _l_e))
  done
  echo "$_l_left"
}

# The mode's settings, from progress_mode_for and the caller's locale read before LC_ALL=C.
progress_setup() { # mode NO_COLOR LC_ALL LC_CTYPE LANG
  P_MODE=$1
  P_COLOUR=$(progress_colour_for "$1" "$2")
  P_GLYPHS=$(progress_glyphs_for "$1" "$3" "$4" "$5")
  P_TPID=""
}

# A permanent line: on a terminal the status line is erased first, and the leading word coloured.
progress_line() { # word SGR-colour rest
  [ "$P_MODE" = plain ] || printf '\r%s[K' "$P_ESC"
  if [ "$P_COLOUR" = yes ]; then
    printf '%s[%sm%s%s[0m %s\n' "$P_ESC" "$2" "$1" "$P_ESC" "$3"
  else
    printf '%s %s\n' "$1" "$3"
  fi
}

progress_say() { # a permanent line with no coloured word
  [ "$P_MODE" = plain ] || printf '\r%s[K' "$P_ESC"
  printf '%s\n' "$1"
}

progress_ok() { # step seconds log
  progress_line ok 32 "$1: $(tail -n 1 "$3" | progress_clean | cut -c1-120) [$(progress_fmt "$2")]"
}

# A failure: a FAILED header, the log's last 20 lines, a GitHub annotation when GITHUB_ACTIONS is
# set, and last the one ERROR line, whose reason is the log's last line starting `ERROR`.
progress_failed() { # step exit seconds log shown-log
  _f_why=$(LC_ALL=C grep '^ERROR' "$4" | tail -n 1 | progress_clean)
  [ -n "$_f_why" ] || _f_why="exit $2"
  progress_line FAILED 31 "$1: exit $2 after $(progress_fmt "$3"); the last 20 lines of $5:"
  tail -n 20 "$4" | progress_clean | awk '{ print "  | " $0 }'
  if [ -n "${GITHUB_ACTIONS:-}" ]; then
    # The reason holds no CR or LF once cleaned; % is the one byte left to encode.
    printf '::error title=build step %s failed::%s\n' "$1" "$(printf '%s' "$_f_why" | sed 's/%/%25/g')"
  fi
  progress_line ERROR 31 "$1: $_f_why (log: $5)"
}

progress_row() { # timings-file run step status seconds
  printf '%s\t%s\t%s\t%s\n' "$2" "$3" "$4" "$5" >> "$1"
}

progress_size() { # bytes -> 12 KiB, 41 MiB
  if [ "$1" -lt 1048576 ]; then echo "$(($1 / 1024)) KiB"; else echo "$(($1 / 1048576)) MiB"; fi
}

# The status line, redrawn four times a second after a quiet first half second, until the build
# stops it or is gone. It runs with set +e, opens fd 3 on its own standard output (the terminal) for
# `stty size`, and draws each frame with one write.
progress_ticker() { # k n step log estimate later-estimates...
  set +e
  trap - EXIT HUP
  exec 3>&1
  _t_k=$1 _t_n=$2 _t_step=$3 _t_log=$4 _t_est=$5
  shift 5
  _t_dot='-'
  [ "$P_GLYPHS" != utf8 ] || _t_dot='·'
  _t_t0=$(date +%s)
  _t_i=0
  sleep 0.5
  while kill -0 "$P_PID" 2> /dev/null; do
    _t_el=$(( $(date +%s) - ${_t_t0:-0} ))
    _t_txt="[$_t_k/$_t_n] $_t_step $(progress_fmt "$_t_el")"
    [ -z "$_t_est" ] || _t_txt="$_t_txt / ~$(progress_fmt "$_t_est")"
    if [ "$_t_step" = 00_download ]; then
      _t_part=$(ls -t "$HERE"/downloads/*.part 2> /dev/null | head -n 1)
      if [ -f "$_t_part" ]; then
        _t_name=$(basename "$_t_part" .part | LC_ALL=C tr -cd 'A-Za-z0-9._+-')
        _t_txt="$_t_txt @ fetching $_t_name $(progress_size "$(wc -c < "$_t_part" | tr -cd 0-9)")"
      fi
    else
      _t_sub=$(LC_ALL=C sed -n 's/^\[\([0-9][0-9]*\)\/\([0-9][0-9]*\)\].*/\1\/\2/p' "$_t_log" \
        2> /dev/null | tail -n 1)
      case "$_t_sub" in ''|*[!0-9/]*) ;; *) _t_txt="$_t_txt @ [$_t_sub]";; esac
    fi
    _t_left=$(progress_left "$_t_el" "${_t_est:--}" "$@")
    [ -z "$_t_left" ] || _t_txt="$_t_txt @ ~$(progress_fmt "$_t_left") left"
    _t_cols=$(stty size <&3 2> /dev/null)
    _t_cols=${_t_cols#* }
    case "$_t_cols" in ''|0|*[!0-9]*) _t_cols=${COLUMNS:-};; esac
    case "$_t_cols" in ''|0|*[!0-9]*) _t_cols=80;; esac
    _t_w=$((_t_cols - 3))  # width - 1, less the spinner and its space
    if [ "$_t_w" -ge 1 ]; then
      if [ "$P_GLYPHS" = utf8 ]; then
        case $((_t_i % 10)) in
          0) _t_sp='⠋';; 1) _t_sp='⠙';; 2) _t_sp='⠹';; 3) _t_sp='⠸';; 4) _t_sp='⠼';;
          5) _t_sp='⠴';; 6) _t_sp='⠦';; 7) _t_sp='⠧';; 8) _t_sp='⠇';; *) _t_sp='⠏';;
        esac
      else
        case $((_t_i % 4)) in 0) _t_sp='|';; 1) _t_sp='/';; 2) _t_sp='-';; *) _t_sp='\';; esac
      fi
      # Cut while every character is one byte, then put the separator glyph in.
      _t_txt=$(printf '%s' "$_t_txt" | cut -c1-"$_t_w" | sed "s/@/$_t_dot/g")
      printf '\r%s %s%s[K' "$_t_sp" "$_t_txt" "$P_ESC" || exit 0
    fi
    _t_i=$((_t_i + 1))
    sleep 0.25
  done
}

progress_stop() { # stop the ticker, if one runs, and erase its line
  [ -n "${P_TPID:-}" ] || return 0
  kill "$P_TPID" 2> /dev/null || :
  wait "$P_TPID" 2> /dev/null || :
  P_TPID=""
  printf '\r%s[K' "$P_ESC"
}

progress_refuse() { # reason: the preflight's one ERROR line, then exit 1
  P_ENDED=yes
  progress_line ERROR 31 "preflight: $1"
  exit 1
}

# Before any step, in a second: the host key (scripts/line.sh), the host tools on PATH (curl is
# checked by the download step, where it fetches), and on a first build (no build/tools yet) at
# least 2.5 GiB free under build/: its own folders took 1.77 GiB.
progress_preflight() {
  _p_key=$( (. "$HERE/scripts/line.sh" && printf '%s' "$HOST_KEY") 2>&1 ) \
    || progress_refuse "$(printf '%s\n' "$_p_key" | tail -n 1 | sed 's/^ERROR: //')"
  _p_missing=""
  _p_n=0
  for _p_tool in cc make shasum tar gzip xz sed uv git stty df; do
    if command -v "$_p_tool" > /dev/null 2>&1; then
      _p_n=$((_p_n + 1))
    else
      _p_missing="$_p_missing, $_p_tool"
    fi
  done
  [ -z "$_p_missing" ] || progress_refuse "no ${_p_missing#, } on PATH"
  _p_dir=$HERE/build
  while [ ! -d "$_p_dir" ]; do _p_dir=$(dirname "$_p_dir"); done
  _p_kib=$(df -Pk "$_p_dir" 2> /dev/null | awk 'NR == 2 { print $4 }')
  case "$_p_kib" in ''|*[!0-9]*) progress_refuse "df -Pk gives no free space for $_p_dir";; esac
  _p_gib=$(awk -v k="$_p_kib" 'BEGIN { printf "%.1f", k / 1048576 }')
  if [ ! -d "$HERE/build/tools" ] && [ "$_p_kib" -lt 2621440 ]; then
    progress_refuse "$_p_gib GiB free under build/; a first build needs 2.5 GiB"
  fi
  progress_say "preflight: $_p_key; $_p_n tools; $_p_gib GiB free"
}

# The last lines of a passing build. Only a build that ran step 90 points at build/artifacts/ (a
# named step removes it), with each artifact's size and the start of its SHA256SUMS hash.
progress_summary() { # steps-run seconds steps
  case " $3 " in
    *" 90_artifacts "*)
      progress_say "done: $1 steps in $(progress_fmt "$2"); the artifact set is in build/artifacts/"
      for _s_name in python.wasm python-snapshot.wasm python-stdlib.zip; do
        _s_file=$HERE/build/artifacts/$_s_name
        [ -f "$_s_file" ] || continue
        _s_hash=$(awk -v a="$_s_name" '$2 == a { print substr($1, 1, 16) }' \
          "$HERE/build/artifacts/SHA256SUMS" 2> /dev/null || :)
        progress_say "  $_s_name $(wc -c < "$_s_file" | tr -cd 0-9) bytes  $_s_hash"
      done
      progress_say 'next: uv run pytest -m "not slow"'
      ;;
    *) progress_say "done: $1 steps in $(progress_fmt "$2"):$(printf ' %s' $3)";;
  esac
}

# For --list: a step script's header comment -> its first sentence, without the `Step NN: ` the
# list shows already, cut at a word (and marked `...`) to fit `max` characters.
progress_what() { # script max
  awk -v max="$2" '
    NR == 1 && /^#!/ { next }
    /^#/ { sub(/^# ?/, ""); text = text (text == "" ? "" : " ") $0; next }
    { exit }
    END {
      sub(/^Step [0-9]+: */, "", text)
      if (match(text, /\.( |$)/)) text = substr(text, 1, RSTART)
      if (length(text) > max) {
        text = substr(text, 1, max - 2)
        sub(/ [^ ]*$/, "", text)
        sub(/[,;:(]$/, "", text)
        text = text "..."
      }
      print text
    }' "$1"
}
