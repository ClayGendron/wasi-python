"""Spec 071 criterion 4, metered (fuel=10**11), outside pytest: each kind's completing and deep run."""
import re, sys
src = open(sys.argv[1]).read()
ns = {}
start = src.index("LIMIT_FREE = ")
end = src.index("@pytest.mark.parametrize(\"kind\"")
exec(src[start:end], ns)
import wasi_python
for kind, (program, good, deep, either) in ns["LIMITS"].items():
    ok = wasi_python.run(["-c", program.format(n=good)], fuel=10**11)
    bad = wasi_python.run(["-c", program.format(n=deep)], fuel=10**11)
    after = wasi_python.run(["-c", "print('ok')"], fuel=10**11)
    print(kind, "| good", ok.exit_code, ok.trapped, ok.stdout.decode().strip()[:20],
          "| deep", bad.exit_code, bad.trapped, bad.stdout.decode().strip()[:30], "| after", after.stdout.decode().strip())
