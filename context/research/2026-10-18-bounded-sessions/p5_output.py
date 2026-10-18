"""P5: is every byte a turn wrote in the host's stream when the turn hands control back? The
streams are the runner's own (`_send_outputs`, `_Stream`), swapped for fresh ones at each door call."""
import sys; sys.path.insert(0, sys.argv[1])
import loop
N = 1 << 20
turns = [f"import sys\nsys.stdout.write('o' * {N} + '\\n'); sys.stderr.write('e' * {N // 2} + '\\n'); print('turn', {i})" for i in range(20)]
turns += ["print('small', 1)", "1/0", "print('after')"]
res, ended, tail = loop.session(turns)
sizes = [(len(o), len(e)) for o, e, _ in res]
want_o, want_e = N + 1 + len("turn 0\n"), N // 2 + 1
exact = sum(1 for i, (o, e) in enumerate(sizes[:20]) if o == N + 1 + len(f"turn {i}\n") and e == want_e)
print(f"P5: {exact} of 20 big turns had every byte in the swapped stream at the door call")
print("P5 small turns:", [(o.decode().strip(), e.decode().strip().splitlines()[-1:] ) for o, e, _ in res[20:]])
print("ended:", ended, "| bytes after the last turn:", len(tail[0]), len(tail[1]))
