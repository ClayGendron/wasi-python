#!/bin/sh
# Apply the carried patches of one source tree: scripts/steps/apply_patches.sh TREE DIR
#
# The build runs it right after a step unpacks a pinned tarball; the judge runs the same script on
# a fresh extraction, so the two can never apply differently. It sources only remove.sh. Each
# DIR/NNNN-*.patch is applied in name order by git, with the caller's git configuration, attributes
# and environment cleared (each of them can change the bytes or skip a patch with exit 0), and no
# patch may be skipped or land at an offset: each is made against exactly its tarball. A changed
# file gets back its tarball mtime and an added one the newest file's, so no make rule sees a newer
# input. git's output goes to standard output (the step's log); a failure is one ERROR line.
set -eu

die() {
  echo "ERROR: $*" >&2
  exit 1
}

[ "$#" -eq 2 ] || die "usage: apply_patches.sh TREE PATCH_DIR"
[ -d "$1" ] || die "no tree $1"
TREE=$(CDPATH= cd "$1" && pwd -P)  # absolute: with a relative tree git ignores the ceiling
# git would read a repository inside the tree, with its own configuration and attributes.
[ ! -e "$TREE/.git" ] && [ ! -L "$TREE/.git" ] || die "$TREE holds .git; a source tree is never a repository"
[ -d "$2" ] || exit 0              # no patches for this tree
DIR=$(CDPATH= cd "$2" && pwd -P)

set -- "$DIR"/[0-9][0-9][0-9][0-9]-*.patch
[ -e "$1" ] || exit 0  # an empty folder: the glob matched nothing

. "$(dirname "$0")/remove.sh"  # removals retry
WORK=$(mktemp -d)
trap 'remove "$WORK"' EXIT
mkdir "$WORK/home"
git_clean() {
  env -i PATH="$PATH" HOME="$WORK/home" XDG_CONFIG_HOME="$WORK/home" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES="$(dirname "$TREE")" \
    git -c core.quotePath=false -C "$TREE" "$@"
}

# The newest file of the tree as unpacked: an added file takes its mtime.
NEWEST=$(find "$TREE" -type f | LC_ALL=C sort | {
  n=""
  while IFS= read -r f; do
    if [ -z "$n" ] || [ "$f" -nt "$n" ]; then n=$f; fi
  done
  printf '%s' "$n"
})

for patch in "$@"; do
  name=$(basename "$patch")
  # Remember the mtime of every file the patch changes (the last field of --numstat).
  : > "$WORK/touched"
  git_clean apply --numstat "$patch" > "$WORK/numstat" 2>&1 || {
    cat "$WORK/numstat"
    die "$name: not a patch git can read"
  }
  cut -f3 "$WORK/numstat" > "$WORK/touched"
  n=0
  while IFS= read -r rel; do
    n=$((n + 1))
    if [ -f "$TREE/$rel" ]; then touch -r "$TREE/$rel" "$WORK/mtime.$n"; fi
  done < "$WORK/touched"
  if ! git_clean apply --whitespace=nowarn --verbose "$patch" > "$WORK/out" 2>&1; then
    cat "$WORK/out"
    die "$name does not apply to $(basename "$TREE")"
  fi
  cat "$WORK/out"
  if grep -Eq "^Skipped patch '|^Hunk #[0-9]+ succeeded at [0-9]+ \(offset " "$WORK/out"; then
    die "$name was skipped or applied at an offset: re-make it against $(basename "$TREE")"
  fi
  n=0
  while IFS= read -r rel; do
    n=$((n + 1))
    if [ -f "$WORK/mtime.$n" ]; then
      touch -c -r "$WORK/mtime.$n" "$TREE/$rel"  # -c: a file the patch deleted stays deleted
    elif [ -f "$TREE/$rel" ] && [ -n "$NEWEST" ]; then
      touch -r "$NEWEST" "$TREE/$rel"
    fi
  done < "$WORK/touched"
  echo "applied $name"
done
