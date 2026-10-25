"""Bounded local check (h14-poll-oneoff): a raw WAT guest, run through wasi_python.run with an
Artifacts set whose module is this guest, calls the runner's shadowed poll_oneoff with crafted
pointers, counts, subscription tags, clock ids, flags and timeouts. Around each call the guest
fills its 6-page working area with 0xAA, copies it to a mirror, calls poll_oneoff, then counts
every byte that changed, and every changed byte outside [out_ptr, out_ptr + 32 * nevents) and
[nevents_ptr, nevents_ptr + 4) (nothing allowed on an error). It writes a PRE0 record (errno,
nevents) straight after the call and a FULL record (counts, first and last changed address,
the first 64 bytes at out_ptr when they lie in memory) after the scan, both to stdout.

usage: check_poll.py <mode> <out.json>   mode: A | A-mounts | B | B-abs | C
"""

import json
import struct
import sys
from pathlib import Path

REPO = Path(".")
PAGE = 65536
MIRROR, W, SIZE = PAGE, 7 * PAGE, 6 * PAGE
END = 13 * PAGE  # 851968, the first address past the guest's memory
TEMPLATES = 4096
M32 = 0xFFFFFFFF
EINVAL, ENOMEM, EBADF, EFAULT = 28, 48, 8, 21


def clock(ud, cid, timeout, flags=0, precision=0):
    return struct.pack("<QB7xIxxxxQQH6x", ud, 0, cid, timeout, precision, flags)


def fdsub(ud, tag, fd):
    return struct.pack("<QB7xI28x", ud, tag, fd)


def tagged(ud, tag):
    return struct.pack("<QB39x", ud, tag)


IN, OUT, NEV = W + 1024, W + 16384, W + 64
ONE = clock(1, 1, 0)


def cases_a():
    c = []  # (label, in, out, n, nev, subs bytes or None, bulk count, expect)
    add = lambda label, subs, in_=IN, out=OUT, n=None, nev=NEV, bulk=0, expect=None: c.append(
        (label, in_, out, (len(subs) // 48 if subs else bulk) if n is None else n, nev, subs, bulk, expect)
    )
    add("baseline: one monotonic clock, timeout 0", ONE, expect=0)
    add("in_ptr = END-48 (array ends exactly at memory end)", ONE, in_=END - 48, expect=0)
    add("in_ptr = END-47 (one byte past)", ONE, in_=END - 47, expect=EFAULT)
    add("out_ptr = END-32 (event ends exactly at memory end)", ONE, out=END - 32, expect=0)
    add("out_ptr = END-31", ONE, out=END - 31, expect=EFAULT)
    add("nevents_ptr = END-4", ONE, nev=END - 4, expect=0)
    add("nevents_ptr = END-3", ONE, nev=END - 3, expect=EFAULT)
    add("in_ptr = 0xFFFFFFD0 (in+48 wraps to 0 in 32 bits)", None, in_=0xFFFFFFD0, n=1, expect=EFAULT)
    add("in_ptr = 0xFFFFFFFF", None, in_=0xFFFFFFFF, n=1, expect=EFAULT)
    add("in_ptr = 0x80000000 (negative i32)", None, in_=0x80000000, n=1, expect=EFAULT)
    add("out_ptr = 0xFFFFFFE0 (out+32 wraps to 0)", ONE, out=0xFFFFFFE0, expect=EFAULT)
    add("nevents_ptr = 0xFFFFFFFC (nev+4 wraps to 0)", ONE, nev=0xFFFFFFFC, expect=EFAULT)
    add("in_ptr = END (zero bytes left)", None, in_=END, n=1, expect=EFAULT)
    add("n = 0", ONE, n=0, expect=EINVAL)
    add("n = 4097", ONE, n=4097, expect=ENOMEM)
    add("n = 0x80000000 (negative i32)", ONE, n=0x80000000, expect=ENOMEM)
    add("n = 0xFFFFFFFF (-1)", ONE, n=0xFFFFFFFF, expect=ENOMEM)
    add("n = 4096 clocks in bounds (196608-byte array, 131072-byte events)", None, in_=W,
        out=W + 196608, nev=W + 196608 + 131072, bulk=4096, expect=0)
    add("n = 4096, out_ptr one byte short of room for 4096 events", None, in_=W,
        out=END - 131072 + 1, nev=W + 196608 + 4, bulk=4096, expect=EFAULT)
    add("n = 2 with in_ptr = END-48 (count is in subscriptions, not bytes)", ONE, in_=END - 48,
        n=2, expect=EFAULT)
    add("n = 3, out_ptr room for 2 events, only 1 clock due", clock(1, 1, 0) + clock(2, 1, 10**9)
        + clock(3, 1, 10**9), out=END - 64, expect=EFAULT)
    add("misaligned in_ptr (+1)", ONE, in_=IN + 1, expect=0)
    add("misaligned out_ptr (+1)", ONE, out=OUT + 1, expect=0)
    add("misaligned nevents_ptr (+1)", ONE, nev=NEV + 1, expect=0)
    add("out_ptr == in_ptr, n = 2", clock(11, 1, 0) + clock(12, 1, 0), out=IN, expect=0)
    add("nevents_ptr inside the event (out+8)", ONE, nev=OUT + 8, expect=0)
    add("nevents_ptr == in_ptr", ONE, nev=IN, expect=0)
    add("unknown tag 3", tagged(1, 3), expect=EINVAL)
    add("unknown tag 255", tagged(1, 255), expect=EINVAL)
    add("ready fd then unknown tag (no partial write)", fdsub(1, 1, 0) + tagged(2, 7), expect=EINVAL)
    add("ready fd then bad clock id (no partial write)", fdsub(1, 1, 0) + clock(2, 9, 0), expect=EINVAL)
    for cid in (2, 3, 4, 0xFFFFFFFF):
        add(f"clock id {cid:#x}", clock(1, cid, 0), expect=EINVAL)
    add("fd_read stdin", fdsub(5, 1, 0), expect=0)
    add("fd_write stdout", fdsub(6, 2, 1), expect=0)
    add("fd_write stderr", fdsub(7, 2, 2), expect=0)
    add("fd_read stdout", fdsub(1, 1, 1), expect=EBADF)
    add("fd_write stdin", fdsub(1, 2, 0), expect=EBADF)
    add("fd_read fd 3", fdsub(1, 1, 3), expect=EBADF)
    for fd in (4, 5, 6, 99, 0x7FFFFFFF, 0xFFFFFFFF):
        add(f"fd_read fd {fd:#x}", fdsub(20, 1, fd), expect=None)
    add("ready fd and a 10 s clock (no wait, fd only)", fdsub(8, 1, 0) + clock(9, 1, 10 * 10**9), expect=0)
    add("clock flags 0xFFFE (unknown bits, relative)", clock(1, 1, 0, flags=0xFFFE), expect=0)
    add("abstime realtime 0 (past)", clock(1, 0, 0, flags=1), expect=0)
    add("abstime monotonic 1 (past)", clock(1, 1, 1, flags=1), expect=0)
    add("relative 1 ms", clock(1, 1, 1_000_000), expect=0)
    add("two clocks, timeout 0, same userdata", clock(4, 1, 0) + clock(4, 1, 0), expect=0)
    add("5 ms, 1 ms, 1 ms: two due", clock(1, 1, 5_000_000) + clock(2, 1, 1_000_000)
        + clock(3, 0, 1_000_000), expect=0)
    add("precision 2**64-1 ignored", clock(1, 1, 0, precision=2**64 - 1), expect=0)
    return c


def cases_huge(abs_=False):
    sub = clock(1, 1, 2**64 - 1, flags=1 if abs_ else 0)
    return [(f"{'abstime monotonic' if abs_ else 'relative'} timeout 2**64-1", IN, OUT, 1, NEV, sub, 0, None)]


def i32(v):
    return f"(i32.const {v & M32})"


def wat(cases):
    data, at, calls = b"", TEMPLATES, []
    for i, (label, in_, out, n, nev, subs, bulk, _) in enumerate(cases):
        src = cp = 0
        if subs:
            src = at
            data += subs
            at += len(subs)
            cp = max(0, min(len(subs), END - in_)) if in_ < END else 0
        dump = 1 if out + 64 <= END else 0
        calls.append(f"    (call $case {i32(i)} {i32(in_)} {i32(out)} {i32(n)} {i32(nev)} {i32(src)} "
                     f"{i32(cp)} {i32(bulk)} {i32(dump)})")
    assert at < 0x8000
    esc = "".join(f"\\{b:02x}" for b in data)
    return f"""(module
  (import "wasi_snapshot_preview1" "poll_oneoff" (func $poll (param i32 i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_write" (func $fd_write (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 13)
  (data (i32.const {TEMPLATES}) "{esc}")
  (func $emit (param $p i32) (param $len i32)
    (i32.store (i32.const 256) (local.get $p))
    (i32.store (i32.const 260) (local.get $len))
    (drop (call $fd_write (i32.const 1) (i32.const 256) (i32.const 1) (i32.const 384))))
  (func $bulk (param $at i32) (param $count i32) (local $i i32) (local $p i32)
    (memory.fill (local.get $at) (i32.const 0) (i32.mul (local.get $count) (i32.const 48)))
    (block $done (loop $l
      (br_if $done (i32.ge_u (local.get $i) (local.get $count)))
      (local.set $p (i32.add (local.get $at) (i32.mul (local.get $i) (i32.const 48))))
      (i64.store (local.get $p) (i64.extend_i32_u (i32.add (local.get $i) (i32.const 1))))
      (i32.store (i32.add (local.get $p) (i32.const 16)) (i32.const 1))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $l))))
  (func $case (param $id i32) (param $in i32) (param $out i32) (param $n i32) (param $nev i32)
              (param $src i32) (param $cp i32) (param $bulkn i32) (param $dump i32)
    (local $e i32) (local $k i32) (local $i i32) (local $a i64) (local $total i32)
    (local $outside i32) (local $first i32) (local $last i32)
    (local $lo i64) (local $hi i64) (local $nlo i64) (local $nhi i64)
    (memory.fill (i32.const {W}) (i32.const 0xAA) (i32.const {SIZE}))
    (if (local.get $cp) (then (memory.copy (local.get $in) (local.get $src) (local.get $cp))))
    (if (local.get $bulkn) (then (call $bulk (local.get $in) (local.get $bulkn))))
    (memory.copy (i32.const {MIRROR}) (i32.const {W}) (i32.const {SIZE}))
    (local.set $e (call $poll (local.get $in) (local.get $out) (local.get $n) (local.get $nev)))
    (if (i32.eqz (local.get $e)) (then (local.set $k (i32.load (local.get $nev)))))
    (i32.store (i32.const 512) (i32.const 0x30455250))
    (i32.store (i32.const 516) (local.get $id))
    (i32.store (i32.const 520) (local.get $e))
    (i32.store (i32.const 524) (local.get $k))
    (call $emit (i32.const 512) (i32.const 16))
    (local.set $lo (i64.extend_i32_u (local.get $out)))
    (local.set $hi (i64.add (local.get $lo) (i64.mul (i64.extend_i32_u (local.get $k)) (i64.const 32))))
    (local.set $nlo (i64.extend_i32_u (local.get $nev)))
    (local.set $nhi (i64.add (local.get $nlo) (i64.const 4)))
    (if (local.get $e) (then (local.set $nhi (local.get $nlo)) (local.set $hi (local.get $lo))))
    (local.set $first (i32.const -1))
    (block $d (loop $l
      (br_if $d (i32.ge_u (local.get $i) (i32.const {SIZE})))
      (if (i32.ne (i32.load8_u (i32.add (i32.const {W}) (local.get $i)))
                  (i32.load8_u (i32.add (i32.const {MIRROR}) (local.get $i))))
        (then
          (local.set $total (i32.add (local.get $total) (i32.const 1)))
          (if (i32.eq (local.get $first) (i32.const -1))
            (then (local.set $first (i32.add (i32.const {W}) (local.get $i)))))
          (local.set $last (i32.add (i32.const {W}) (local.get $i)))
          (local.set $a (i64.extend_i32_u (i32.add (i32.const {W}) (local.get $i))))
          (if (i32.eqz (i32.or
                (i32.and (i64.ge_u (local.get $a) (local.get $lo)) (i64.lt_u (local.get $a) (local.get $hi)))
                (i32.and (i64.ge_u (local.get $a) (local.get $nlo)) (i64.lt_u (local.get $a) (local.get $nhi)))))
            (then (local.set $outside (i32.add (local.get $outside) (i32.const 1)))))))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $l)))
    (memory.fill (i32.const 1024) (i32.const 0) (i32.const 96))
    (i32.store (i32.const 1024) (i32.const 0x4c4c5546))
    (i32.store (i32.const 1028) (local.get $id))
    (i32.store (i32.const 1032) (local.get $e))
    (i32.store (i32.const 1036) (local.get $k))
    (i32.store (i32.const 1040) (local.get $total))
    (i32.store (i32.const 1044) (local.get $outside))
    (i32.store (i32.const 1048) (local.get $first))
    (i32.store (i32.const 1052) (local.get $last))
    (if (local.get $dump) (then (memory.copy (i32.const 1056) (local.get $out) (i32.const 64))))
    (call $emit (i32.const 1024) (i32.const 96)))
  (func (export "run") (result i32)
{chr(10).join(calls)}
    (i32.const 0)))
"""


def parse(stdout, cases):
    recs, pos = {}, 0
    while pos + 16 <= len(stdout):
        magic = stdout[pos:pos + 4]
        if magic == b"PRE0":
            _, cid, e, k = struct.unpack_from("<4I", stdout, pos)
            recs.setdefault(cid, {})["pre"] = {"errno": e, "nevents": k}
            pos += 16
        elif magic == b"FULL":
            _, cid, e, k, total, outside, first, last = struct.unpack_from("<8I", stdout, pos)
            dump = stdout[pos + 32:pos + 96]
            evs = []
            for j in range(min(k, 2)):
                ev = dump[32 * j:32 * j + 32]
                if len(ev) == 32:
                    ud, err, typ, nbytes, flags = struct.unpack("<QHB5xQH6x", ev)
                    evs.append({"userdata": ud, "error": err, "type": typ, "nbytes": nbytes,
                                "flags": flags, "pad_hex": (ev[11:16] + ev[26:32]).hex()})
            recs.setdefault(cid, {})["full"] = {
                "errno": e, "nevents": k, "changed": total, "changed_outside_allowed": outside,
                "first_changed": None if first == M32 else first,
                "last_changed": None if total == 0 else last, "events": evs}
            pos += 96
        else:
            raise SystemExit(f"bad record at {pos}")
    rows = []
    for i, (label, in_, out, n, nev, subs, bulk, expect) in enumerate(cases):
        r = recs.get(i, {})
        e = r.get("pre", {}).get("errno")
        rows.append({"case": i, "label": label, "in_ptr": in_, "out_ptr": out, "n": n,
                     "nevents_ptr": nev, "expect_errno": expect, "errno": e,
                     "as_expected": None if expect is None else e == expect, **r})
    return rows


def main():
    mode, out_json = sys.argv[1], Path(sys.argv[2])
    import wasmtime
    import wasi_python
    from wasi_python import Artifacts

    cases = {"A": cases_a, "A-mounts": cases_a, "B": cases_huge, "B-abs": lambda: cases_huge(True),
             "C": cases_huge}[mode]()
    text = wat(cases)
    work = out_json.parent.parent / "work"
    work.mkdir(exist_ok=True)
    binary = work / f"poll_guest_{mode}.wasm"
    binary.write_bytes(wasmtime.wat2wasm(text))
    arts = Artifacts(snapshot=binary, plain=binary,
                     stdlib_zip=REPO / "build/artifacts/python-stdlib.zip",
                     manifest=REPO / "build/artifacts/MANIFEST")
    kw = {"artifacts": arts, "snapshot": False, "cache_dir": False}
    kw["deadline_s"] = {"A": 20.0, "A-mounts": 20.0, "B": 0.5, "B-abs": 0.5, "C": None}[mode]
    if mode == "A-mounts":
        import importlib.util
        spec = importlib.util.spec_from_file_location("hfiles", REPO / "tests/harness/files.py")
        H = importlib.util.module_from_spec(spec)
        sys.modules["hfiles"] = H
        spec.loader.exec_module(H)
        kw["mounts"] = [wasi_python.Mount(H.MemoryProvider(), "/m")]
    done = wasi_python.run(["poll"], **kw)
    rows = parse(done.stdout, cases)
    result = {"mode": mode, "deadline_s": kw["deadline_s"], "mounts": mode == "A-mounts",
              "exit_code": done.exit_code, "trapped": done.trapped, "stderr": done.stderr[:400].decode("latin-1"),
              "memory_end": END, "cases": rows,
              "unexpected": [r["case"] for r in rows if r["as_expected"] is False],
              "any_change_outside_allowed": [r["case"] for r in rows
                                             if r.get("full", {}).get("changed_outside_allowed")]}
    out_json.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("mode", "exit_code", "trapped", "unexpected",
                                              "any_change_outside_allowed")}))


if __name__ == "__main__":
    main()
