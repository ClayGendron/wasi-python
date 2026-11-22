# Draft: a repository security advisory for wasi-python on Windows

A draft for the owner to publish from the repository's Security tab (Advisories, "New draft security advisory"), once specification 202's check 3a has run on the Windows leg and 0.1.6 is out. The fields below are in the order GitHub's form asks for them. Fill in the two bracketed facts from what check 3a found, then delete this paragraph and the notes at the end.

---

**Title:** Sandbox escape on Windows through a drive-prefixed file name

**Ecosystem:** pip. **Package:** `wasi-python`.

**Affected versions:** `<= 0.1.5`

**Patched versions:** `0.1.6`

**Severity:** High. Take the vector from wasmtime's GHSA-f2pq-268w-886c (CVSS 4.0, 7.5), since the flaw and its preconditions are wasmtime's.

**CWE:** CWE-22, improper limitation of a pathname to a restricted directory.

**Description:**

### Impact

On Windows, a guest program run by `wasi_python.run`, a `Session` or the `wasi-python` command, and given any host folder, can name a file outside that folder. It uses a path component with a drive prefix, such as `./C:secret`. Windows reads `C:secret` relative to the current folder of drive C, not relative to the granted folder.

Through a read-only grant, the guest can read files outside the grant. Through a writable grant, it can also create, change, rename or remove them. [Check 3a found: the calls that reached outside the grant on 0.1.5.]

Only Windows hosts are affected. macOS and Linux are not, since a colon is an ordinary character in a file name there. Folders given as the runner's own mounts are not affected either: the runner has always refused a `:` in their names. The flaw is in the engine, wasmtime, which the runner passes plain host folders to. It is wasmtime's advisory [GHSA-f2pq-268w-886c](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-f2pq-268w-886c).

### Patches

wasi-python 0.1.6 requires wasmtime-py 51, which bundles wasmtime 51.0.0. That engine refuses a `:` in any path on Windows. No wasmtime-py release on the 50 line carries the fix, so upgrading wasi-python is the only way to get it.

```
pip install --upgrade "wasi-python>=0.1.6"
```

### Workarounds

Until you can upgrade, on Windows:

- Give the guest no host folders. Use in-memory mounts, or no files at all.
- Or run the host process with its current folder, and the current folder of every drive, set to a folder that holds nothing you need to protect. This narrows what a drive-relative name reaches, but it does not stop it.

An embedder who drives the artifact set (`python.wasm`, the snapshot) with their own wasmtime needs wasmtime 50.0.3, 49.0.7, 48.0.10, 36.0.22 or 51.0.0 or later.

### References

- wasmtime's advisory: https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-f2pq-268w-886c
- The fix in wasmtime: "Disallow colons in all paths on Windows" (bytecodealliance/wasmtime#15373, released in 50.0.3 and carried by 51.0.0).
- The 0.1.6 release notes: [link, once published].

**Credits:** wasmtime's advisory credits its finder. This advisory credits no one else.

---

## Notes for the owner (delete before publishing)

- **Whether to publish at all depends on 3a.** If 3a's Windows leg was green on wasmtime-py 50.0.1, 0.1.5 was not reached. Then don't publish this. The release notes say the fix is carried, and that is all.
- **The empty-write advisory** (GHSA-5m8g-xhq4-4h93, Moderate, memory growth on Windows) is a denial of service, not an escape. It can go in this advisory as a second item, or only in the release notes. The recommendation is the release notes only, unless check 3b reproduced it.
- **Timing.** wasmtime's advisory has been public since 2026-11-19, so the flaw is already known. Publishing with 0.1.6, not before it, gives users the fix in the same message.
