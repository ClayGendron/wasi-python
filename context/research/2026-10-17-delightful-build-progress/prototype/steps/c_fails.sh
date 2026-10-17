n=1; while [ $n -le 30 ]; do echo "noise line $n mentions strerror"; n=$((n + 1)); done
echo "ERROR: link failed: undefined symbol: __cxa_throw" >&2
exit 1
