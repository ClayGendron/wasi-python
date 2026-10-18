#!/bin/sh
# Spec 040, acceptance criterion 1: step 10's gate stops the build, with one line, when the
# launcher is not installed and when an installed launcher has no clang-cpp mode. Inside this
# folder's container on linux/amd64, with /src (the change, read-only), /cache (the downloads) and
# /out, as decision1-x86_64.sh. Each case runs step 10 in its own clone, changed only as named.
set -u
one() { # name, then a sed program for 10_tools.sh, or "" and a launcher file
  name=$1
  R=/work/$name
  rm -rf "$R"
  git clone -q /src "$R"
  for f in /cache/*; do
    [ -f "$f" ] && cp "$f" "$R/downloads/"
  done
  git -C "$R" checkout -q downloads/SHA256SUMS
  [ -z "$2" ] || sed -i "$2" "$R/scripts/steps/10_tools.sh"
  [ -z "${3:-}" ] || cp "$3" "$R/scripts/clang-emulated"
  (cd "$R" && sh scripts/00_download.sh > /dev/null 2>&1 && sh scripts/steps/10_tools.sh > "/out/$name.txt" 2>&1)
  echo "$name: exit $?; $(grep -c . "/out/$name.txt") lines; last: $(tail -n 1 "/out/$name.txt")"
}
# 1. The native clang is never replaced by a link to the launcher.
one no-launcher '/^  rm -f "\$NATIVE"$/d; /^  ln -s "\$CSDK\/bin\/clang-emulated" "\$NATIVE"$/d'
# 2. The launcher as the draft contract had it: `++` names in g++ mode, every other name in none.
sed '/^case "\$(basename "\$0")" in$/,/^esac$/c\
case "$(basename "$0")" in\
  *++) run -no-canonical-prefixes --driver-mode=g++ "$@";;\
  *) run -no-canonical-prefixes "$@";;\
esac' /src/scripts/clang-emulated > /tmp/draft-launcher
one no-cpp-mode "" /tmp/draft-launcher
diff /src/scripts/clang-emulated /tmp/draft-launcher > /out/no-cpp-mode.diff
grep -c 'driver-mode=cpp' /tmp/draft-launcher
# 3. No empty cache in the guest's root: qemu's -L falls through to the host's /etc/ld.so.cache,
#    and the loader maps it (the container's own cache, which Debian's image ships).
one host-cache '/^  : > "\$T\/aarch64-root\/etc\/ld.so.cache"$/d'
