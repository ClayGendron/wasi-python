"""scripts/same_bytes.py and scripts/compare_sets.py: what "the same bytes" admits under spec 037,
Decision 17, and every way two bodies or two sets may not pass, each naming its rule.

The fixtures are two named ducc0 bodies from two python.wasm builds that differ only there, with
the instruction offsets the pinned llvm-objdump printed for them (tests/unit/fixtures/)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))
import compare_sets  # noqa: E402
import same_bytes as sb  # noqa: E402

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "same_bytes_ducc0.json").read_text())
FUNCS = FIXTURE["functions"]
PAIRS = [(f["name"], base64.b64decode(f["a"]), base64.b64decode(f["b"])) for f in FUNCS]
NAMES = tuple(f["name"] for f in FUNCS)


def _refused(rule: int, call, *args) -> str:
    with pytest.raises(sb.Refused) as e:
        call(*args)
    assert e.value.rule == rule, str(e.value)
    return str(e.value)


# --- the decoder -------------------------------------------------------------------------------


@pytest.mark.parametrize("which", ["a", "b"])
@pytest.mark.parametrize("index", range(len(FUNCS)), ids=["rfftpass", "make_shared"])
def test_the_decoder_finds_llvm_objdumps_instruction_boundaries(index, which) -> None:
    f = FUNCS[index]
    _, insns = sb.decode(base64.b64decode(f[which]))
    assert [i.start for i in insns] == f[f"{which}_objdump_offsets"]


@pytest.mark.parametrize(
    ("body", "what"),
    [
        (bytes([0, 0x06, 0x40, 0x0B, 0x0B]), "legacy EH opcode try"),
        (bytes([0, 0x02, 0x40, 0x19, 0x0B, 0x0B]), "legacy EH opcode catch_all"),
        (bytes([0, 0x41, 0x80, 0x80, 0x80, 0x80, 0x80, 0x00, 0x1A, 0x0B]), "LEB longer"),
        (bytes([0, 0x41, 0x80, 0x80, 0x80, 0x80, 0x10, 0x1A, 0x0B]), "out of range for s32"),
        (bytes([0, 0x20, 0xFF, 0xFF, 0xFF, 0xFF, 0x1F, 0x1A, 0x0B]), "out of range for u32"),
        (bytes([0, 0x42, *[0x80] * 10, 0x00, 0x1A, 0x0B]), "LEB longer"),
        (bytes([0, 0x41]), "truncated"),
        (bytes([0, 0x02, 0x40, 0x0B]), "unbalanced end"),
        (bytes([0, 0x0B, 0x0B]), "not its last byte"),
        (bytes([0, 0x05, 0x0B]), "else outside an if"),
        (bytes([0, 0x28, 0x42, 0, 0, 0x1A, 0x0B]), "multi-memory memarg"),
        (bytes([0, 0xFE, 0x03, 0x00, 0x0B]), "atomics"),
        (bytes([0, 0x17, 0x0B]), "opcode 0x17"),
        (bytes([0, 0xFC, 0x20, 0x0B]), "opcode 0xfc 32"),
    ],
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_the_decoder_fails_closed(body, what) -> None:
    assert what in _refused(4, sb.decode, body)


def test_a_truncated_fixture_body_is_refused_not_a_traceback() -> None:
    _, a, _ = PAIRS[0]
    _refused(4, sb.compare_bodies, a[: len(a) // 2], a[: len(a) // 2])


# --- two bodies --------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "a", "b"), PAIRS, ids=["rfftpass", "make_shared"])
def test_the_two_real_variants_are_the_same_bytes(name, a, b) -> None:
    assert a != b
    sb.compare_bodies(a, b)
    sb.compare_bodies(b, a)
    sb.compare_bodies(a, a)


def _insns(body: bytes) -> list[sb.Insn]:
    return sb.decode(body)[1]


CONTROL = {0x02, 0x03, 0x04, 0x05, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x1F}


def _moved_past_a_call(body: bytes) -> list[bytes]:
    """The review's counter-example (F1): a try_table moved past the straight-line instructions
    after it, through a call and the local.set of its result, so the call leaves its handler."""
    insns, out = _insns(body), []
    for n, tt in enumerate(insns):
        if tt.op != sb.TRY_TABLE:
            continue
        m = n + 1
        while m + 1 < len(insns) and insns[m].op not in CONTROL and insns[m].op != 0x10:
            m += 1
        if insns[m].op == 0x10 and insns[m + 1].op in (0x21, 0x1A):
            cut = insns[m + 1].end
            out.append(body[: tt.start] + body[tt.end : cut] + body[tt.start : tt.end] + body[cut:])
    return out


def test_the_reviews_mutant_fails_the_handler_rule() -> None:
    _, a, _ = PAIRS[0]
    mutants = _moved_past_a_call(a)
    assert mutants
    for mutant in mutants:
        assert len(mutant) == len(a) and sb.shape(mutant).stripped == sb.shape(a).stripped
    messages = [_refused(8, sb.compare_bodies, a, m) for m in mutants]
    # In some mutant a call has lost its handler.
    assert any("(0 of them" not in m for m in messages), messages


def _replace(body: bytes, insn: sb.Insn, new: bytes) -> bytes:
    return body[: insn.start] + new + body[insn.end :]


def test_a_changed_immediate_fails_the_byte_rule() -> None:
    _, a, b = PAIRS[0]
    const = next(i for i in _insns(b) if i.op == 0x41 and 0 < i.args[0] < 60)
    _refused(6, sb.compare_bodies, a, _replace(b, const, bytes([0x41, const.args[0] + 1])))


def test_a_changed_call_target_fails_the_byte_rule() -> None:
    _, a, b = PAIRS[0]
    call = next(i for i in _insns(b) if i.op == 0x10)
    width, value = call.end - call.start - 1, call.args[0] ^ 1
    leb = bytes((value >> (7 * k)) & 0x7F | (0x80 if k < width - 1 else 0) for k in range(width))
    _refused(6, sb.compare_bodies, a, _replace(b, call, bytes([0x10]) + leb))


def test_an_added_or_removed_instruction_fails_the_byte_rule() -> None:
    _, a, b = PAIRS[0]
    first = _insns(b)[0]
    added = b[: first.start] + bytes([0x01]) + b[first.start :]
    assert "bytes long" in _refused(6, sb.compare_bodies, a, added)
    nop_free = next(i for i in _insns(b) if i.op == 0x20)
    removed = _replace(b, nop_free, b"")
    _refused(6, sb.compare_bodies, a, removed)


def test_every_changed_catch_target_fails() -> None:
    _, a, b = PAIRS[0]
    tried = 0
    for tt in (i for i in _insns(b) if i.op == sb.TRY_TABLE):
        (kind, _, label), *rest = tt.args[1]
        if rest or kind not in sb.CATCH_ALL_KINDS or label >= 0x7F:
            continue
        new = bytes([0x1F, 0x40, 1, kind, label + 1])
        if len(new) != tt.end - tt.start:
            continue
        tried += 1
        with pytest.raises(sb.Refused) as e:
            sb.compare_bodies(a, _replace(b, tt, new))
        assert e.value.rule in (4, 5, 8), str(e.value)
    assert tried > 10


def test_a_try_table_with_a_block_type_is_refused() -> None:
    _, a, b = PAIRS[0]
    tt = next(i for i in _insns(b) if i.op == sb.TRY_TABLE)
    typed = b[: tt.start + 1] + bytes([0x7F]) + b[tt.start + 2 :]
    assert "block type" in _refused(5, sb.compare_bodies, a, typed)


def test_a_branch_to_a_try_table_is_refused() -> None:
    body = bytes([0, 0x1F, 0x40, 0, 0x0C, 0, 0x0B, 0x0B])
    assert "targets a try_table" in _refused(5, sb.compare_bodies, body, body)
    catch = bytes([0, 0x02, 0x40, 0x1F, 0x40, 1, 2, 0, 0x1F, 0x40, 1, 2, 0, 0x0B, 0x0B, 0x0B, 0x0B])
    assert "targets a try_table" in _refused(5, sb.compare_bodies, catch, catch)


def test_other_locals_fail_the_byte_rule() -> None:
    _, a, b = PAIRS[0]
    assert b[0] < 0x80 and b[1] < 0x7F  # one LEB byte each: the declarations' and first count
    other = b[:1] + bytes([b[1] + 1]) + b[2:]
    assert "local declarations" in _refused(6, sb.compare_bodies, a, other)


# --- two binaries ------------------------------------------------------------------------------


def _uleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _section(sid: int, payload: bytes) -> bytes:
    return bytes([sid]) + _uleb(len(payload)) + payload


def _vec(items: list[bytes]) -> bytes:
    return _uleb(len(items)) + b"".join(items)


def _name(s: str) -> bytes:
    return _uleb(len(s.encode())) + s.encode()


def _padded(n: int) -> bytes:
    """`n` as a LEB one byte longer than it needs: the same value, other bytes."""
    plain = bytearray(_uleb(n))
    plain[-1] |= 0x80
    return bytes(plain) + b"\x00"


def module(
    bodies: list[bytes],
    names: list[str],
    producers: bytes = b"x",
    pad_body: int | None = None,
    pad_code: bool = False,
) -> bytes:
    """A module of functions of type () -> () with these bodies and names, beside a custom section;
    the decoder never checks types, so the fixture bodies stand in it as they are."""
    functions = _vec([b"\x00"] * len(bodies))
    sizes = [_padded(len(b)) if k == pad_body else _uleb(len(b)) for k, b in enumerate(bodies)]
    code = _vec([size + b for size, b in zip(sizes, bodies, strict=True)])
    code_section = bytes([10]) + _padded(len(code)) + code if pad_code else _section(10, code)
    name_map = _vec([_uleb(i) + _name(n) for i, n in enumerate(names)])
    names_section = _name("name") + bytes([1]) + _uleb(len(name_map)) + name_map
    return (
        b"\0asm\x01\0\0\0"
        + _section(1, _vec([b"\x60\x00\x00"]))
        + _section(3, functions)
        + code_section
        + _section(0, names_section)
        + _section(0, _name("producers") + producers)
    )


PLAIN = bytes([0, 0x0B])
OTHER = bytes([0, 0x01, 0x0B])


def test_two_binaries_differing_only_in_named_bodies_are_the_same_bytes() -> None:
    (n1, a1, b1), (n2, a2, b2) = PAIRS
    a = module([PLAIN, a1, a2], ["plain", n1, n2])
    b = module([PLAIN, b1, b2], ["plain", n1, n2])
    assert sb.compare(a, b, NAMES) == [n1, n2]
    assert sb.compare(a, a, NAMES) == []


def test_a_differing_body_of_an_unnamed_function_is_refused() -> None:
    (n1, a1, b1), _ = PAIRS
    a = module([PLAIN, a1], ["plain", n1])
    b = module([OTHER, a1], ["plain", n1])
    assert "plain, which the recipe does not name" in _refused(3, sb.compare, a, b, (n1,))


def test_a_name_that_matches_twice_is_refused() -> None:
    (n1, a1, b1), _ = PAIRS
    a = module([a1, a1], [n1, n1])
    b = module([b1, a1], [n1, n1])
    assert "2 functions are named" in _refused(3, sb.compare, a, b, (n1,))
    assert "0 functions are named" in _refused(3, sb.compare, a, b, ("absent",))


@pytest.mark.parametrize(
    "padding", [{"pad_body": 0}, {"pad_code": True}], ids=["a body size", "the code size"]
)
def test_a_padded_size_leb_with_no_named_body_differing_is_refused(padding) -> None:
    """The implementation review's I1: the same bodies under other size bytes are other bytes."""
    (n1, a1, _), _ = PAIRS
    a = module([PLAIN, a1], ["plain", n1])
    b = module([PLAIN, a1], ["plain", n1], **padding)
    assert a != b
    assert "outside every function body" in _refused(3, sb.compare, a, b, (n1,))


@pytest.mark.parametrize(
    "padding", [{"pad_body": 0}, {"pad_code": True}], ids=["a body size", "the code size"]
)
def test_a_padded_size_leb_beside_a_differing_named_body_is_refused(padding) -> None:
    """I1 again: B must be A with B's differing named bodies spliced in, nothing more."""
    (n1, a1, b1), _ = PAIRS
    a = module([PLAIN, a1], ["plain", n1])
    b = module([PLAIN, b1], ["plain", n1], **padding)
    assert "outside the named bodies" in _refused(3, sb.compare, a, b, (n1,))


def test_a_differing_non_code_section_is_refused() -> None:
    (n1, a1, b1), _ = PAIRS
    a = module([a1], [n1])
    b = module([b1], [n1], producers=b"y")
    _refused(2, sb.compare, a, b, (n1,))


def _root(tmp_path: Path, sdk: str = "33", llvm: str = "4434dabb") -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "downloads").mkdir()
    (tmp_path / "recipes").mkdir()
    real = (paths.REPO / "scripts" / "line.conf").read_text()
    conf = real.replace("WASI_SDK_VERSION=33", f"WASI_SDK_VERSION={sdk}").replace(
        "LLVM_COMMIT=4434dabb", f"LLVM_COMMIT={llvm}"
    )
    (tmp_path / "scripts" / "line.conf").write_text(conf)
    for rel in ("downloads/SHA256SUMS", "recipes/same_bytes_exceptions.toml"):
        (tmp_path / rel).write_text((paths.REPO / rel).read_text())
    return tmp_path


def test_the_recipe_holds_for_this_line_and_names_each_function_once() -> None:
    (exception,) = sb.load_recipe()
    assert exception.artifacts == ("python.wasm", "python-snapshot.wasm")
    assert len(exception.functions) == len(set(exception.functions)) == 9
    assert set(NAMES) <= set(exception.functions)


@pytest.mark.parametrize(("sdk", "llvm"), [("34", "4434dabb"), ("33", "fd76c9bd")])
def test_a_recipe_whose_toolchain_is_not_the_lines_is_refused(tmp_path, sdk, llvm) -> None:
    root = _root(tmp_path, sdk, llvm)
    _refused(1, sb.load_recipe, root)


def test_a_recipe_whose_scipy_pin_is_not_the_lines_is_refused(tmp_path) -> None:
    root = _root(tmp_path)
    sums = root / "downloads" / "SHA256SUMS"
    sums.write_text(sums.read_text().replace("52c4b742", "00000000"))
    assert "scipy-1.18.1.tar.gz" in _refused(1, sb.load_recipe, root)


# --- two sets and their wheels -----------------------------------------------------------------


def _sums(files: dict[str, bytes]) -> bytes:
    return "".join(f"{hashlib.sha256(d).hexdigest()}  {n}\n" for n, d in files.items()).encode()


def _wheel(path: Path, files: dict[str, bytes]) -> Path:
    entries = {compare_sets.ARTIFACTS + n: d for n, d in files.items()}
    entries[compare_sets.ARTIFACTS + "SHA256SUMS"] = _sums(files)
    entries["wasi_python/runner.py"] = b"print()\n"
    record = (
        "".join(compare_sets._record_line(n, d) + "\n" for n, d in entries.items())
        + "wasi_python-1.dist-info/RECORD,,\n"
    )
    entries["wasi_python-1.dist-info/RECORD"] = record.encode()
    with zipfile.ZipFile(path, "w") as z:
        for n, d in entries.items():
            z.writestr(zipfile.ZipInfo(n, (2026, 1, 1, 0, 0, 0)), d)
    return path


def _set(folder: Path, files: dict[str, bytes], write: bool = True) -> Path:
    folder.mkdir()
    (folder / "SHA256SUMS").write_bytes(_sums(files))
    for n, d in files.items():
        if write:
            (folder / n).write_bytes(d)
    return folder


RECIPE_NAMES = sb.load_recipe()[0].functions
REST = [n for n in RECIPE_NAMES if n not in NAMES]


def _files(variant: int) -> dict[str, bytes]:
    """A set whose binaries hold every recipe function once: the fixture pairs' bodies, picked by
    `variant`, and a plain body for the rest."""
    pick = 1 if variant == 0 else 2
    bodies = [PLAIN] + [p[pick] for p in PAIRS] + [PLAIN] * len(REST)
    names = ["plain", *NAMES, *REST]
    return {
        "python.wasm": module(bodies, names),
        "python-snapshot.wasm": module(bodies, names, producers=b"snapshot"),
        "python-stdlib.zip": b"zip",
        "MANIFEST": b"manifest\n",
    }


def test_identical_sets_and_wheels_pass(tmp_path) -> None:
    files = _files(0)
    a, b = _set(tmp_path / "a", files), _set(tmp_path / "b", files)
    wa, wb = _wheel(tmp_path / "a.whl", files), _wheel(tmp_path / "b.whl", files)
    assert compare_sets.compare_sets(a, b, (wa, wb)) == []


def test_a_rebuild_differing_in_the_named_functions_passes_from_its_wheel(tmp_path) -> None:
    a = _set(tmp_path / "a", _files(0))
    b = _set(tmp_path / "b", _files(1), write=False)  # only SHA256SUMS, as in the release job
    wa, wb = _wheel(tmp_path / "a.whl", _files(0)), _wheel(tmp_path / "b.whl", _files(1))
    report = compare_sets.compare_sets(a, b, (wa, wb))
    assert [r.split(":")[0] for r in report] == ["python.wasm", "python-snapshot.wasm"]
    assert compare_sets.main([str(a), str(b), "--wheels", str(wa), str(wb)]) == 0


def test_a_rebuild_whose_binary_is_not_its_own_line_fails(tmp_path) -> None:
    a = _set(tmp_path / "a", _files(0))
    stale = dict(_files(1))
    b = _set(tmp_path / "b", stale)
    (b / "python.wasm").write_bytes(_files(0)["python.wasm"][:-1] + b"z")
    with pytest.raises(compare_sets.Differs, match="not its own SHA256SUMS line"):
        compare_sets.compare_sets(a, b)


@pytest.mark.parametrize("variant", [0, 1], ids=["no binary differs", "the binaries differ"])
@pytest.mark.parametrize(
    "reformat",
    [lambda t: t.replace(b"\n", b"\r\n"), lambda t: t[:-1]],
    ids=["CRLF", "no last newline"],
)
def test_a_rebuilds_sha256sums_in_other_bytes_fails(tmp_path, variant, reformat) -> None:
    """The implementation review's I2: SHA256SUMS is compared as bytes, with only the exception
    lines' digests replaced."""
    a = _set(tmp_path / "a", _files(0))
    b = _set(tmp_path / "b", _files(variant))
    (b / "SHA256SUMS").write_bytes(reformat((b / "SHA256SUMS").read_bytes()))
    with pytest.raises(compare_sets.Differs, match="SHA256SUMS"):
        compare_sets.compare_sets(a, b)


def test_any_other_differing_file_fails(tmp_path) -> None:
    a = _set(tmp_path / "a", _files(0))
    other = dict(_files(0), MANIFEST=b"other\n")
    b = _set(tmp_path / "b", other)
    with pytest.raises(compare_sets.Differs, match="MANIFEST differs and no exception"):
        compare_sets.compare_sets(a, b)


def test_a_binary_that_fails_the_rules_fails_the_set(tmp_path) -> None:
    a = _set(tmp_path / "a", _files(0))
    bad = dict(_files(0))
    bad["python.wasm"] = module(
        [OTHER, *[p[1] for p in PAIRS], *[PLAIN] * len(REST)], ["plain", *NAMES, *REST]
    )
    b = _set(tmp_path / "b", bad)
    with pytest.raises(compare_sets.Differs, match="rule 3"):
        compare_sets.compare_sets(a, b)
    assert compare_sets.main([str(a), str(b)]) == 1


def test_a_wheel_differing_elsewhere_fails(tmp_path) -> None:
    a = _set(tmp_path / "a", _files(0))
    b = _set(tmp_path / "b", _files(1), write=False)
    wa, wb = _wheel(tmp_path / "a.whl", _files(0)), _wheel(tmp_path / "b.whl", _files(1))
    data = io.BytesIO()
    with zipfile.ZipFile(wb) as src, zipfile.ZipFile(data, "w") as dst:
        for info in src.infolist():
            body = src.read(info)
            dst.writestr(info, b"print(1)\n" if info.filename.endswith("runner.py") else body)
    wb.write_bytes(data.getvalue())
    with pytest.raises(compare_sets.Differs, match="runner.py"):
        compare_sets.compare_sets(a, b, (wa, wb))


def test_a_wheel_that_differs_though_sha256sums_does_not_fails(tmp_path) -> None:
    files = _files(0)
    a, b = _set(tmp_path / "a", files), _set(tmp_path / "b", files)
    wa = _wheel(tmp_path / "a.whl", files)
    wb = _wheel(tmp_path / "b.whl", files)
    with zipfile.ZipFile(wb, "a") as z:
        z.comment = b"other"
    with pytest.raises(compare_sets.Differs):
        compare_sets.compare_sets(a, b, (wa, wb))
