# Sourced with HERE set to the repository: scripts/line.conf checked against its grammar and loaded,
# then PYTHON_MM (3.15) and PYTHON_TAG (315) derived from PYTHON_VERSION (spec 005, Decision 2).
LINE_CONF="$HERE/scripts/line.conf"
if grep -v -E '^(#.*|[A-Z][A-Z0-9_]*=[A-Za-z0-9._+-]+)$' "$LINE_CONF" > /dev/null; then
  echo "ERROR: scripts/line.conf has a line that is not NAME=value or a # comment" >&2
  exit 1
fi
. "$LINE_CONF"
PYTHON_MM=${PYTHON_VERSION%.*}
PYTHON_TAG=$(printf '%s' "$PYTHON_MM" | tr -d .)
