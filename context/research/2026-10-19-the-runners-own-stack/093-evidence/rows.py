"""Spec 093's evidence: the old and the new session row, as is and with the guest ending first."""
import subprocess, sys
sys.path.insert(0, sys.argv[1])
from checks.test_v1_2_hostile_guest import ABANDONED_TURN_CHILD as NEW

OLD = sys.argv[2]
look = 'print("busy while its guest runs"'
old_first = OLD.replace(look, "for t in alive:\n    t.join(60)\n" + look, 1)
# New row, Windows order: the caller looks only once the guest's turn has returned.
new_first = NEW.replace(
    "        if mine:\n            gate.wait(60)",
    "        if mine:\n            back.set()\n            gate.wait(60)", 1,
).replace("entered, gate = threading.Event(), threading.Event()",
          "entered, gate, back = threading.Event(), threading.Event(), threading.Event()", 1
).replace(look, "back.wait(60)\n" + look, 1)
assert old_first != OLD and new_first.count("back") == 3
rows = [("old as is", OLD), ("old, guest ends first", old_first),
        ("new as is", NEW), ("new, guest ends first", new_first)]
for name, prog in rows[int(sys.argv[3]):]:
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, timeout=200)
    print(name, "|", out.returncode, "|", out.stdout.strip().splitlines()[1:], out.stderr[-200:])
