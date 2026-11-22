# Draft: a repository security advisory for wasi-python on Windows

A draft for the owner to publish from the repository's Security tab (Advisories, "New draft security advisory"), once specification 202's check 3a has run on the Windows leg and 0.1.6 is out. 3a was red on wasmtime-py 50.0.1 (pull request #129, run 45037617781, Windows leg `own-hostile`: all eight calls read the canary), so it applies; publishing it is the owner's call. The fields below are in the order GitHub's form asks for them; 3a's finding is written into the Impact. Delete this paragraph and the notes at the end before publishing.

---

**Title:** Sandbox escape on Windows through a drive-prefixed file name

**Ecosystem:** pip. **Package:** `wasi-python`.

**Affected versions:** `<= 0.1.5`

**Patched versions:** `0.1.6`

**Severity:** High. Take the vector from wasmtime's GHSA-f2pq-268w-886c (CVSS 4.0, 7.5), since the flaw and its preconditions are wasmtime's.

**CWE:** CWE-22, improper limitation of a pathname to a restricted directory.

**Description:**

### Impact

On Windows, any guest program run by `wasi_python.run`, a `Session` or the `wasi-python` command can name a host file outside the folders it was given. It uses a path component with a drive prefix, such as `/usr/local/lib/C:secret`. Windows reads `C:secret` relative to the current folder of drive C, not relative to the folder the guest named.

This reaches every call, including one given no folders at all. Each call has folders of the runtime's own, among them the standard library's folder at `/usr/local/lib`, which is read-only. Through them, any guest can read files outside its folders. Through a writable folder, or with `root=True`, it can also create, change, rename or remove them. On 0.1.5 on Windows, a guest read a file outside its folders in every kind of call: with no folders given, with a read-only folder, with a writable folder, and with `root=True`, with or without a mount. In the call given no folders, it read through the runtime's own folders alone.

Only Windows hosts are affected. macOS and Linux are not, since a colon is an ordinary character in a file name there. Folders given as the runner's own mounts are not affected either: the runner has always refused a `:` in their names. The flaw is in the engine, wasmtime, which the runner passes its host folders to. It is wasmtime's advisory [GHSA-f2pq-268w-886c](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-f2pq-268w-886c).

### Patches

wasi-python 0.1.6 requires wasmtime-py 51, which bundles wasmtime 51.0.0. That engine refuses a `:` in any path on Windows. No wasmtime-py release on the 50 line carries the fix, so upgrading wasi-python is the only way to get it.

```
pip install --upgrade "wasi-python>=0.1.6"
```

### Workarounds

None. Upgrade to 0.1.6. Giving the guest no folders does not help, because every call has the runtime's own folders.

Setting the host process's current folder, and the current folder of every drive, to a folder that holds nothing you need to protect narrows what a drive-relative name reaches. It does not stop the escape.

An embedder who drives the artifact set (`python.wasm`, the snapshot) with their own wasmtime needs wasmtime 51.0.0 or later, or 50.0.3, 49.0.7, 48.0.10 or 36.0.22.

### References

- wasmtime's advisory: https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-f2pq-268w-886c
- The fix in wasmtime: "Disallow colons in all paths on Windows" (bytecodealliance/wasmtime#15373, released in 50.0.3 and carried by 51.0.0).
- The 0.1.6 release notes: [link, once published].

**Credits:** wasmtime's advisory credits its finder. This advisory credits no one else.

---

## Notes for the owner (delete before publishing)

- **3a was red, so publish.** Its Windows leg read the canary outside the guest's folders in all eight calls on wasmtime-py 50.0.1 (run 45037617781). 3a checked reads; that a writable folder or `root=True` could also write outside is inferred from the same resolution, not run.
- **The empty-write advisory** (GHSA-5m8g-xhq4-4h93) did not reach the runner: WASIp1 never passes an empty write to the output stream. It belongs in no advisory of ours.
- **Timing.** wasmtime's advisory has been public since 2026-11-19, so the flaw is already known. Publishing with 0.1.6, not before it, gives users the fix in the same message.
