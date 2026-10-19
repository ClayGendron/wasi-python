import sys, re
p = sys.argv[1]
s = open(p).read()
def once(old, new):
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new)
once("""/* The result of decoding the timeout. Values are in clock ticks. Non-negative
 * values are valid.
 */
#define RE_NO_TIMEOUT -1""", """/* The result of decoding the timeout. Values are in clock ticks. Non-negative
 * values are valid.
 *
 * Clock ticks are kept in a long long, not in a Py_ssize_t: CLOCKS_PER_SEC may
 * be 10**9 (WASI) where Py_ssize_t has 32 bits, and a 32-bit Py_ssize_t holds
 * only about 2,147 seconds of ticks even at 10**6 per second.
 */
typedef long long RE_Ticks;

#define RE_NO_TIMEOUT -1""")
once("    Py_ssize_t timeout; /* The timeout in clock ticks. */", "    RE_Ticks timeout; /* The timeout in clock ticks. */")
once("    if ((Py_ssize_t)(clock() - state->start_time) < state->timeout)", "    if ((RE_Ticks)(clock() - state->start_time) < state->timeout)")
once("  visible_captures, bool match_all, Py_ssize_t timeout) {", "  visible_captures, bool match_all, RE_Ticks timeout) {")
once("  match_all, Py_ssize_t timeout) {", "  match_all, RE_Ticks timeout) {")
once("  pos, PyObject* endpos, int concurrent, Py_ssize_t timeout) {", "  pos, PyObject* endpos, int concurrent, RE_Ticks timeout) {")
once("""Py_LOCAL_INLINE(Py_ssize_t) decode_timeout(PyObject* timeout) {
    double value;
""", """Py_LOCAL_INLINE(RE_Ticks) decode_timeout(PyObject* timeout) {
    double value;
""")
once("""    return value >= 0.0 ? (Py_ssize_t)(value * CLOCKS_PER_SEC) : RE_NO_TIMEOUT;""",
"""    /* A negative value, NaN, or one too large for any clock: no timeout. */
    if (!(value >= 0.0) || value * CLOCKS_PER_SEC >= (double)LLONG_MAX)
        return RE_NO_TIMEOUT;

    return (RE_Ticks)(value * CLOCKS_PER_SEC);""")
n = s.count("    Py_ssize_t tim;\n")
assert n == 9, n
s = s.replace("    Py_ssize_t tim;\n", "    RE_Ticks tim;\n")
open(p, "w").write(s)
