# Sourced by scripts/build.sh and scripts/steps/common.sh. Removes each path, retrying:
# macOS Finder can write a .DS_Store into a folder while rm empties it, which fails the rm with
# "Directory not empty". Three attempts, no sleep; only the last one's error is shown.
remove() {
  for p in "$@"; do
    rm -rf "$p" 2>/dev/null || rm -rf "$p" 2>/dev/null || rm -rf "$p" || true
    if [ -e "$p" ] || [ -L "$p" ]; then
      echo "ERROR: cannot remove $p" >&2
      exit 1
    fi
  done
}
