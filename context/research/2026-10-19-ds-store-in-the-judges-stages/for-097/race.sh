#!/bin/sh
# Spec 097's race, reproduced by hand: litter rewritten between `git add` and the unstage.
set -u
W=$1
rm -rf "$W"
mkdir -p "$W/t/sub"
cd "$W/t" || exit 1
g() { env -i PATH="$PATH" HOME="$W" GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null git "$@"; }
g init -q
echo 'int f;' > sub/a.c
printf 'A' > .DS_Store
g add -A --force
printf 'BB' > .DS_Store
echo "1. git rm -q --cached after a rewrite:"
g rm -q --cached -- .DS_Store; echo "   exit $?"
echo "2. git update-index --force-remove:"
g update-index --force-remove -- .DS_Store; echo "   exit $?"; g ls-files --cached | tr '\n' ' '; echo
echo "3. git rm -q --cached -f after a rewrite:"
g add -A --force; printf 'CCC' > .DS_Store
g rm -q --cached -f -- .DS_Store; echo "   exit $?"; g ls-files --cached | tr '\n' ' '; echo
g rm -q --cached -r . >/dev/null
echo "4. git add -A --force with an unreadable litter file:"
chmod 000 .DS_Store
g add -A --force; echo "   exit $?"
g rm -q --cached -r . >/dev/null 2>&1
echo "5. the same, litter excluded by pathspec (from a NUL file):"
printf '.\0:(exclude,glob)**/.DS_Store\0:(exclude,glob)**/.DS_Store/**\0:(exclude,glob)**/._*\0' > "$W/specs"
printf 'x' > sub/._a.c
g add -A --force --pathspec-from-file="$W/specs" --pathspec-file-nul; echo "   exit $?"; g ls-files --cached | tr '\n' ' '; echo
chmod 600 .DS_Store
