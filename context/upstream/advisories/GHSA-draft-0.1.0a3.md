# Draft: GitHub security advisory for wasi-python, covering 0.1.0a1 to 0.1.0a3

- **For:** the owner, who publishes it after 0.1.0a4 is on PyPI and 0.1.0a3 is yanked (decision
  87). The agent drafted it. Nothing has been filed, published or yanked.
- **Where it is filed:** github.com/claygendron/wasi_python → Security → Advisories → New draft
  security advisory (the repository `SECURITY.md` points to).
- **Shape:** one advisory for both upstream issues, at the higher severity. GitHub's form takes
  one severity per advisory and several CWEs. Two advisories, one per GHSA, would also be
  correct. The owner chooses.
- **Before publishing, check:** 0.1.0a4 is on PyPI, and its wheel's `wasi_python/mounts.py`
  carries `GUARDED` (spec 048); 0.1.0a3 is yanked (the Patches section says so). Edit
  "Patched versions" if the version differs.

Everything between the two rules below is the text for the form. The "Where each claim comes
from" section after it is for the owner, not for posting.

---

## Form fields

- **Title:** Sandbox escape on macOS and host memory disclosure through wasmtime 49.0.0's WASI
  (GHSA-m9f7-9w4p-gv38, GHSA-96f6-r43r-8c24)
- **CVE ID:** none yet. The two wasmtime advisories have none either. Request one through the
  form, or leave it empty (the owner decides).
- **Ecosystem:** pip
- **Package name:** `wasi-python`
- **Affected versions:** `<= 0.1.0a3`
- **Patched versions:** `0.1.0a4`
- **Severity:** High. CVSS v4.0 vector, the same as wasmtime's own advisory for the escape:
  `CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:P/VC:H/VI:H/VA:L/SC:H/SI:H/SA:L` (wasmtime's record scores
  it 8.8; GitHub's calculator recomputes it from the vector).
- **Weaknesses:** CWE-61 (UNIX Symbolic Link (Symlink) Following); CWE-908 (Use of Uninitialized
  Resource)
- **Credits:** none needed. The project found both issues itself, while testing against
  wasmtime's published advisories.

## Description

### Summary

wasi-python's runner (`wasi_python.run`, `run_async` and the `wasi-python run` command) runs its
guest on wasmtime-py, and wasi-python 0.1.0a3 and earlier require `wasmtime>=49,<50`. The only
wasmtime-py release in that range is 49.0.0. It bundles wasmtime 49.0.0, which has two WASI
preview 1 bugs that wasmtime has since fixed. Both reach a wasi-python guest:

- **GHSA-m9f7-9w4p-gv38 (high), a filesystem sandbox escape on macOS and FreeBSD.** A guest
  that can write in any folder it was given can move a host folder from outside its sandbox into
  it. It can then read and write that folder.
- **GHSA-96f6-r43r-8c24 (low), host memory disclosure.** Each directory listing copies up to
  three bytes of uninitialized host memory per entry into the guest.

wasi-python 0.1.0a4 fixes both in the runner, on every call, and with any wasmtime 49 release.
No wasmtime-py release carries a fixed wasmtime yet.

### Details

**The escape (GHSA-m9f7-9w4p-gv38).** wasmtime 49.0.0 implements `path_rename` so that a
trailing `/` on a path is passed on to the host's `renameat`. On macOS and FreeBSD, `renameat`
follows a symbolic link that ends in `/`. A guest that can write somewhere can therefore do this
with ordinary Python:

```python
os.symlink("../outside", "up")
os.rename("up/", "stolen")
```

The kernel follows `up/` out of the sandbox and moves the host folder it points to into the
sandbox, as `stolen`. The guest never opens a path through the link, so the refusal of links
on open does not apply. The rename only works within one filesystem. Within it, the guest can
reach any folder the host process can open. wasmtime fixed this in 49.0.3. Linux and Windows hosts are not affected.

Which calls had a writable place:

- **0.1.0a1:** every call. The caller's `root` was the guest's writable `/`.
- **0.1.0a2:** every call. A call with no `root` got a fresh writable `/` in the system's
  temporary folder.
- **0.1.0a3:** a call with `root=True` (`--private-root`), a host-path `root` (`--root`), or a
  grant with `writable=True` (`--grant-writable`). A call with none of these, which is the
  default, has nothing writable and cannot start the escape. Neither can read-only grants.

**The disclosure (GHSA-96f6-r43r-8c24).** wasmtime 49.0.0's `fd_readdir` writes each directory
entry from a buffer whose three padding bytes, after `d_type`, are never set. So up to three
bytes of host-process memory per entry reach the guest's buffer. This happens on every listing:
the stdlib folder the runner always provides, a root, and every grant, read-only or not. It
affects every call on every platform. wasmtime fixed this in 49.0.2.

**The fix in 0.1.0a4.** The runner now serves `path_rename` and `fd_readdir` itself and forwards
each to wasmtime, on every call. A rename with a
trailing `/` on either path now needs a source that is a folder, judged without following the
source's own link. Otherwise it fails with `ENOTDIR`, or with the source's own error, such as
`ENOENT`. A folder is then renamed by its plain name. This is wasmtime 49.0.3's rule. After each
listing, the runner zeroes the padding bytes. Each guard stays in place until wasi-python's
published `wasmtime` requirement admits only fixed versions.

### Impact

- **Who:** an application that uses wasi-python 0.1.0a3 or earlier to run code it does not
  trust, such as code written by a model or an agent.
- **The escape:** on a macOS or FreeBSD host, that code can take any folder on the same
  filesystem that the host process can open, move it into the sandbox, and read and change it.
  The folder disappears from its original place. With 0.1.0a1 and 0.1.0a2 this needs no special
  setting. With 0.1.0a3 it needs a writable root or a writable grant.
- **The disclosure:** on any host, the guest can read up to three bytes of uninitialized
  host-process memory for each directory entry it lists. It cannot choose which memory.
- Neither issue lets the guest run code on the host, use the network, or go past its fuel,
  memory or time limits.

### Patches

Upgrade to wasi-python **0.1.0a4** (`pip install --upgrade --pre wasi-python`). The fix is in the
runner and works with the wasmtime 49.0.0 that pip installs. 0.1.0a3 has been yanked on PyPI.
0.1.0a1 and 0.1.0a2 were published only as GitHub release assets, and they are affected too.

### Workarounds

If you cannot upgrade:

- **For the escape, with 0.1.0a3:** on macOS and FreeBSD, give untrusted code no writable place.
  That means no `root=True` or `--private-root`, no host-path `root` or `--root`, and no
  `writable=True` grant or `--grant-writable`. The default call and read-only grants are not
  affected. Or run the host on Linux or Windows.
- **For the escape, with 0.1.0a1 or 0.1.0a2:** every call has a writable root, so the only
  workaround is a Linux or Windows host. Upgrading is strongly recommended.
- **For the disclosure:** there is no workaround by configuration. Upgrade.

### References

- wasmtime advisory GHSA-m9f7-9w4p-gv38:
  https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-m9f7-9w4p-gv38 (fixed in
  wasmtime 49.0.3, 48.0.6 and 36.0.18)
- wasmtime advisory GHSA-96f6-r43r-8c24:
  https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-96f6-r43r-8c24 (fixed in
  wasmtime 49.0.2, 48.0.4 and 36.0.17)
- wasi-python 0.1.0a4 release notes: `CHANGELOG.md`, "Security: the sandbox holds on wasmtime
  49.0.0"
- wasi-python `SECURITY.md`, "Upstream advisories the runner handles"

---

## Where each claim comes from (for the owner; not for posting)

| claim | source | label |
|---|---|---|
| a1 to a3 require `wasmtime>=49,<50` (the `run` extra) | `git show v0.1.0a{1,2,3}:pyproject.toml` | READ |
| wasmtime-py 49.0.0 is the only release in range; it bundles wasmtime 49.0.0 | PyPI JSON, 2026-10-18 (`['48.0.0', '49.0.0']`); `v0.1.0a3:uv.lock` pins 49.0.0; facts sheet 12, fact 1 | EXECUTED; READ |
| the escape: mechanism, macOS and FreeBSD only, fixed in 49.0.3 | `context/research/2026-10-18-wasmtime-49-advisories.md` §1; `advisories/GHSA-m9f7-9w4p-gv38.json` | READ |
| the escape works through a wasi-python guest with a writable grant and with `root=True`; read-only grants refuse `os.symlink` (EPERM) | the memo's `repro/transcript.txt`; spec 048, "Seen failing first" (criteria 1 and 2) | EXECUTED (on main's frozen sets `s-8d84b3b190fe9bce` and `s-0cdc7b2bd78db6f5`, darwin-arm64, wasmtime-py 49.0.0) |
| it stays within one filesystem (`/etc` gives EPERM) | memo §1, `repro/guest_root.py` | EXECUTED |
| a1 and a2: every call has a writable `/` | `v0.1.0a1:src/wasi_python/runner.py:104` and `v0.1.0a2:…:440` call `wasi.preopen_dir(str(guest_root), "/")`, and wasmtime-py 49.0.0's `preopen_dir` defaults to `fs_mutable=True` (`context/prior_art/wasmtime-py/wasmtime/_wasi.py:172`); a2's default root is `tempfile.mkdtemp` (`runner.py:269`) | READ; **that a1 and a2 are exploitable is INFERRED, not run** |
| a3: only `root=True`, a host root or a writable grant | `v0.1.0a3:src/wasi_python/runner.py:1647` (`preopen_dir(..., p.writable)`); a3 CHANGELOG "nothing is writable by default"; a3 `cli.py` options | READ; a3 itself was not run (INFERRED from the same code path as the sets above) |
| the disclosure: up to 3 bytes per entry, every listing, fixed in 49.0.2 | facts sheet 12 (fact 3, `evidence/padding.txt`: 995 of 1,000 calls); spec 048, The problem | EXECUTED (there) |
| the fix in 0.1.0a4, the rule, zeroing, removal condition | `CHANGELOG.md` 0.1.0a4; spec 048 Decisions 1 to 5 and Landing notes; build review `context/reviews/048-the-sandbox-holds-2026-10-18.md` | READ |
| neither issue gives code execution, network, or limit bypass | memo §2 (the guest imports only preview 1 and `host::call`); the advisories' own scope | INFERRED |
| CVSS vector, score 8.8, CWE-61; CWE-908 and 2.1 for the low one | the two advisory JSON files under the memo's `advisories/` | READ |
| only 0.1.0a3 is on PyPI; a1 and a2 are GitHub releases | PyPI JSON for `wasi-python`; `gh release list` | EXECUTED 2026-10-18 |
| fixed versions in other lines (48.0.6, 36.0.18; 48.0.4, 36.0.17) | the advisory JSON `patched_versions` | READ |

**CVSS reasoning.** wasmtime's vector is kept, because the runner adds no precondition that
wasmtime's own analysis lacks. AV:N: the untrusted code usually arrives from elsewhere, such as
model output. AC:L: two ordinary calls. AT:P: the host must be macOS or FreeBSD, and in 0.1.0a3
the call must have a writable place. PR:L and UI:P: someone must give the attacker's code to an
application that runs it. VC/VI:H: the guest reads and writes the moved folder. VA:L: the
runner keeps working. SC/SI:H: the host filesystem outside the sandbox is the subsequent system.
SA:L, as wasmtime set it. One could argue SA:H, because the moved folder vanishes from its
place for other host programs; that would raise the score. For 0.1.0a1 and 0.1.0a2, AT:P still
holds (the platform), even though no setting is needed. The low disclosure alone would be
wasmtime's 2.1 (`VC:L`, the rest none). One advisory takes the higher.

**After publishing:** the owner may want `SECURITY.md`'s "Upstream advisories the runner
handles" to link the published advisory. That is a later change, not this draft.
