"""F3: a writer adds a file after each unlink (by a hook, so nothing is timed). With the budget the
walk stops; the writer's additions are capped at 50,000 so the unbounded case ends too.
usage: t_writer.py WORK"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proto_walk2 as p
work = sys.argv[1]
real_unlink = os.unlink
for budget in (10_000, 2**20):
    base = os.path.join(work, f"b{budget}")
    os.makedirs(os.path.join(base, "tree", "d"))
    open(os.path.join(base, "tree", "d", "f0"), "w").close()
    added = [0]
    def u(path, *, dir_fd=None):
        real_unlink(path, dir_fd=dir_fd)
        if added[0] < 50_000:
            added[0] += 1
            open(os.path.join(base, "tree", "d", f"w{added[0]}"), "w").close()
    for k in p.ops: p.ops[k] = 0
    p.BUDGET[0] = budget
    os.unlink = u
    try:
        pfd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
        ok = p.remove_tree("tree", pfd)
        os.close(pfd)
    finally:
        os.unlink = real_unlink
    print(f"budget {budget}: returned {ok}, unlinks {p.ops['unlink']}, listings {p.ops['scandir']}, writer added {added[0]}")
