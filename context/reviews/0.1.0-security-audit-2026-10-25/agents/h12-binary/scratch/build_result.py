import json
A = 'agents/h12-binary/artifacts/evidence/'
RUN = (' Run under ulimit -t 300 -f 4000000 -n 4096, env -i (PATH, HOME, TMPDIR, WASI_PYTHON_CACHE under scratch), '
       'sandbox-exec deny network*, the venv Python with -I; the target was not mounted read-only (not enforceable on this platform); '
       'no grant or root pointed at the target.')
U1 = 'build%2Fartifacts%2Fpython.wasm%23imports::scripts%2Fsteps%2F60_link.sh%23link::build%2Fartifacts::ATTACK-CLASSES.md%23Obvious%20things'
U2 = 'build%2Fartifacts%2Fpython-stdlib.zip%23entries::scripts%2Fmake_stdlib_zip.py%23members::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23Library%2C%20plugin%2C%20and%20executable%20search-order%20trust'
def chk(paths, inv, method, result, art=None):
    return {'agent_id': 'h12-binary', 'reviewed_paths': paths, 'invariant': inv, 'method': method,
            'result': result, 'artifact': (A + art) if art else None}
u1 = [
 chk(['build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm', 'recipes/hostmodule.c'],
     'The guest imports nothing beyond WASI preview1 and the one door host::call, and exports only the entry points the runner calls.',
     'local',
     'Own LEB128 section parser (wasm_inspect.py). Both binaries: 43 function imports, 42 from wasi_snapshot_preview1 plus host.call; no memory, table, global or tag import; no fd_renumber, sock_open or sock_connect (sock_accept/recv/send/shutdown are imported but no socket descriptor is preopened). python.wasm exports 7 (memory, _initialize, wizer.initialize, run, turn, shutdown, host_alloc); the snapshot exports 5 (no _initialize, no wizer.initialize), so a snapshot cannot be re-initialized. Exports are reachable only by the host.' + RUN,
     'wasm_sections_python.json'),
 chk(['build/artifacts/python-snapshot.wasm'],
     'The snapshot carries the same import and export surface as the plain binary minus its initializers.',
     'local', 'Snapshot section table parsed: same 43 imports in the same order and types, export section 48 bytes with 5 exports; code section byte-identical in size (74,345,066), data section 15,843,534 bytes against 10,747,266 for the plain binary.',
     'wasm_sections_snapshot.json'),
 chk(['build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm', 'src/wasi_python/_call.py'],
     'No threads, atomics or shared memory, and linear memory bounded by the runner, as the threat model assumes.',
     'local',
     'target_features on both: +bulk-memory, +bulk-memory-opt, +call-indirect-overlong, +exception-handling, +extended-const, +multivalue, +mutable-globals, +nontrapping-fptoint, +reference-types, +sign-ext, +simd128; no atomics, shared-mem, memory64 or multimemory. One defined memory, flags 0 (not shared, 32-bit), min 640 pages, no declared maximum; the runner caps it with store.set_limits(memory_size=memory_bytes) when a cap is set (src/wasi_python/_call.py:417-418). One funcref table, min = max = 47,157, so it cannot grow. Producers: clang 23.1.0 wasi-sdk (llvm 895aa2c8). No .debug_* or sourceMappingURL section.',
     'wasm_sections_python.json'),
 chk(['build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm'],
     'No br_table reaches the ~256k targets that GHSA-mghf-wjfp-p5xm (Cranelift aarch64, fixed in wasmtime 49.0.4; the runner pins 49.0.0) needs.',
     'local',
     'llvm-objdump -d (pinned wasi-sdk 34) piped to brtable_count.py, which decodes the LEB128 count from the encoded bytes: 20,151 br_table instructions on each binary; the largest has 3,202 targets plus the default (3,203 labels), at 0x15dfa5 (plain) and 0x15df84 (snapshot); histogram tops out in the 2,048-4,095 bucket (2 instructions). About 80 times below the advisory threshold. The runner compiles only these two checked binaries (_engines.py:189-200 re-hashes the bytes it compiles) and its own small constant WAT modules (_call.py:1002, 1014; _engines.py:64), none containing br_table.',
     'brtable.txt'),
 chk(['build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm', 'build/artifacts/MANIFEST', 'scripts/steps/80_snapshot.sh'],
     'No build-host path, user name, environment value or secret is embedded in either binary or the snapshot heap.',
     'local',
     'Regex scan of both whole files: 0 hits for /Users/<name>, /home/<name>, /private/tmp|var, /var/folders, GitHub workspace paths, the owner name, PEM private keys, AWS, PyPI, Slack or bearer tokens; the one gh?_ hit is the HiGHS symbol ghs_getDualUnboundednessDirectionExist. 0 hits for HOME=, PATH=/, USER=, TMPDIR= or the wizer-root path in the snapshot. 31 distinct absolute paths are assert __FILE__ strings under the fixed container prefix /wasi-python-build/build/ and /src/src/llvm-project/libcxxabi (no user or host identity). MANIFEST x-wizer line names the root generically.',
     'path_scan_wasm.txt'),
 chk(['build/artifacts/SHA256SUMS', 'build/artifacts/MANIFEST', 'build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm', 'build/artifacts/python-stdlib.zip'],
     'The local set equals its SHA256SUMS and is the set the 0.1.0 release acceptance judged.',
     'local',
     'shasum -c: 75 OK, 0 failing (LICENSES, MANIFEST, both binaries, the zip). SHA256SUMS hash 3339091f...0fa20 equals set_sums of the last release-tier acceptance (commit d33f0383, an ancestor of the release commit 2cd47507 with no change under scripts/, recipes/ or downloads/). MANIFEST x-snapshot-zip equals the zip hash a7b8f7cb.... The published v0.1.0 SHA256SUMS (read-only gh release download) lists only the tarball a6a4ae70... and the wheel 3bfb0dcc...; the tarball was not downloaded (outside this brief), so per-file equality with published bytes is returned as uncovered, not as a fact.',
     'integrity.txt'),
 chk(['recipes/reactor_main.c', 'build/artifacts/python-snapshot.wasm', 'build/artifacts/python.wasm', 'docs/explanation/security-model.md'],
     'The snapshot fixed hash secret is documented, and the plain binary gets a fresh secret; entropy seen by guest code is real on both.',
     'local',
     'Guest probe, two runs per binary: snapshot=True gives sys.flags.hash_randomization=0 and identical hash("abc")=69611762 and hash(b"wasi")=-1232729172 in both runs; snapshot=False gives hash_randomization=1 and different hashes per run. random.getrandbits(64) and os.urandom(8) differ across runs on both binaries; random is not pre-imported in the snapshot. Source: init_interpreter(1) sets use_hash_seed=1, hash_seed=0 (reactor_main.c:179-186), which zeroes _Py_HashSecret (Python/bootstrap_hash.c:563-566); run, turn and shutdown clear the entropy and clock pin before any Python runs (reactor_main.c:382, 483, 556) and wizer.initialize clears it before the snapshot is taken. sys.hash_info: siphash13, width 32. Effect (quadratic dict/set work until the deadline) is listed in docs/explanation/security-model.md:101, so not a finding.' + RUN,
     'guest_config.json'),
 chk(['recipes/reactor_main.c', 'recipes/reactor_bootstrap.py', 'scripts/steps/80_snapshot.sh', 'scripts/steps/60_link.sh'],
     'The link and snapshot steps leave no state that lets one call influence another: preopens reset, door stubbed only at build time, only four WASI calls wrapped.',
     'source',
     'wizer.initialize calls __wasilibc_reset_preopens() so the snapshot preopen at / is rebuilt from the runtime table on first use (reactor_main.c:306-309); Wizer ran with unknown-imports-trap=y, inherit-std*=n, cache=n (80_snapshot.sh:18); the link wraps only clock_time_get, random_get, path_filestat_get, fd_filestat_get, iconv*, fcntl, freopen (60_link.sh:169) and does not add exports beyond the reactor ones; run and turn exclude each other per instance (reactor_main.c:383-388, 485-488). The runner instantiates a fresh store per call.',
     None),
]
u2 = [
 chk(['build/artifacts/python-stdlib.zip', 'scripts/make_stdlib_zip.py'],
     'The stdlib zip carries no link, traversal name, duplicate, start-up hook, installer, native code or credential.',
     'local',
     'zip_inspect.py over the outer zip: 6,262 entries, 0 directory entries, all unix mode 0o100644 regular, 0 symlinks, 0 duplicate names, 0 case-folded duplicates, 0 absolute/backslash/colon/./../NUL names, 0 .pth, 0 pyvenv.cfg, 0 sitecustomize or usercustomize, no pip, ensurepip, setuptools, distutils, venv or .whl, no .so/.dylib/.dll/.pyd/.wasm/.cwasm; 5,384 .pyc; one inner archive matplotlib/mpl-data.zip (204 entries, all regular, none refused by the runner guard, no Windows-awkward names). site.pyc is present but site does not run (sys.flags.no_site=1). Credential-shaped names are tokenizer modules and secrets.pyc only; the only test folders are library modules (numpy/testing, sympy/testing, narwhals/testing, array_api_extra/testing). make_stdlib_zip.py refuses a name from two inputs (lines 422-423) and writes every member with a fixed date and 0o100644 (lines 303-306).',
     'zip_inventory.txt'),
 chk(['build/artifacts/python-stdlib.zip'],
     'No build-host path or secret in any decompressed member.',
     'local',
     'zip_content_scan.py over every member and the inner archive: 0 /Users/, /private/, /var/folders/, workspace paths, owner name, PEM private keys or token patterns; 6 /home/<name>/ hits are upstream docstrings and METADATA URLs; 4 /wasi-python-build/ hits are the fixed container prefix in _sysconfigdata and numpy/scipy/contourpy build-config modules.',
     'zip_content_scan.txt'),
 chk(['recipes/reportlab_start_up_stand_in.py', 'scripts/steps/70_zip.sh', 'build/artifacts/python-stdlib.zip'],
     "reportlab never executes ~/.reportlab_mods or ~/.reportlab_settings from a writable HOME.",
     'local',
     'The zip carries reportlab_mods.pyc and reportlab_settings.pyc at top level (70_zip.sh:199-200), so reportlab/__init__.py and rl_config.py take the import branch and never reach _fake_import or open(~/.reportlab_settings) (checked in the pinned reportlab-5.0.1 wheel). reportlab.local_rl_mods and local_rl_settings resolve inside the read-only zip package. Runtime: with HOME=/ on a reused root holding planted .reportlab_mods and .reportlab_settings, importing reportlab and reportlab.rl_config ran neither, on both binaries.' + RUN,
     'planted_root.json'),
 chk(['build/artifacts/python-stdlib.zip'],
     'No module in the zip runs code from a home, cwd or environment-named file at import time beyond the documented cases.',
     'local',
     'zip_exec_scan.py lists 72 .pyc whose constants name both a home/cwd/env source and a code-running call; reviewing the non-trivial ones (site, pdb, sympy.interactive.session, trace, sysconfig, matplotlib, reportlab) finds code run only when a program starts it (pdb .pdbrc and site, documented or not run) or data reads (matplotlibrc, documented).',
     'zip_exec_scan.txt'),
 chk(['recipes/reactor_main.c', 'recipes/reactor_bootstrap.py', 'build/artifacts/python.wasm', 'build/artifacts/python-snapshot.wasm'],
     'The guest import path is the zip alone, site is off, and the environment cannot add path entries or start-up files.',
     'local',
     'Both binaries, two runs each, with env PYTHONPATH=/planted, PYTHONSTARTUP=/x.py, PYTHONHASHSEED=123, PYTHONINSPECT=1: sys.path == ["/usr/local/lib/python315.zip"]; flags isolated=1, ignore_environment=1, no_site=1, no_user_site=1, safe_path=True, inspect=0, dont_write_bytecode=1; meta_path Builtin, Frozen, PathFinder; /usr/local/lib lists only python315.zip; sys.prefix /usr/local. Source: PyConfig_InitIsolatedConfig with module_search_paths_set=1 and site_import=0 (reactor_main.c:179-192); script mode does not prepend the script folder (reactor_bootstrap.py _run_file).' + RUN,
     'guest_config.json'),
 chk(['src/wasi_python/_zip.py', 'src/wasi_python/_places.py'],
     'Code planted on a reused root never runs at start-up or on import.',
     'local',
     'Reused root under scratch planted with sitecustomize, usercustomize, tempfile.py, matplotlib/__init__.py, reportlab_mods.py, helper.py, x.pth, pyvenv.cfg, .pythonrc.py, lib/python3.15/{tempfile.py,site-packages/sitecustomize.py}, usr/local/lib/python3.15/..., usr/lib/python3.15/tempfile.py, .local user site, a dummy lib/python315.zip. -c importing tempfile, reportlab, reportlab.rl_config, matplotlib, sqlite3, pdb, sympy; /script.py importing helper; -m helper: on both binaries no planted file ran, every module came from /usr/local/lib/python315.zip, helper was not found.' + RUN,
     'planted_root.json'),
 chk(['src/wasi_python/_zip.py'],
     "The runner's mpl-data extraction cannot write outside its private data folder.",
     'source',
     '_member_parts (_zip.py:108-119) refuses empty, absolute, backslash, colon and empty/./.. components; _extract_data (_zip.py:122-163) refuses any member whose recorded type is not a regular file, refuses a name that is both file and folder, makes each folder with _real_folder (unlinks a link, never follows) and writes each file by mkstemp in its parent then os.replace, after removing a link at the destination; _remove_extra and _data_intact walk without following links. The input is the private copy re-hashed to the checked digest (_zip.py:275-276) and the folder is 0700 under the temp folder, granted read-only. The current inner archive has 204 entries, none refused (zip_inventory.txt).',
     None),
]
rp1 = sorted({p for c in u1 for p in c['reviewed_paths']})
rp2 = sorted({p for c in u2 for p in c['reviewed_paths']})
result = {
 'units': [
  {'coverage_id': U1, 'disposition': 'covered', 'reviewed_paths': rp1, 'checks': u1, 'candidate_fingerprints': [], 'unresolved': []},
  {'coverage_id': U2, 'disposition': 'covered', 'reviewed_paths': rp2, 'checks': u2, 'candidate_fingerprints': [], 'unresolved': []},
 ],
 'candidates': [],
 'hardening': [
  "The snapshot's zeroed _Py_HashSecret also fixes pyexpat's hash salt (build/Python-3.15.0/Python/bootstrap_hash.c:563-566 zeroes the whole secret; Modules/pyexpat.c:1544-1547 salts each parser from _Py_HashSecret.expat), so xml.etree, minidom and plistlib parsers on snapshot=True can be flooded with crafted names as dicts can. Same effect as the documented dict/set item (quadratic CPU until the deadline); docs/explanation/security-model.md:101 could name XML parsing alongside dict and set keys.",
  "_zip._member_parts (src/wasi_python/_zip.py:108-119) does not refuse Windows-reserved names (CON, NUL, COM1...), components ending in a dot or space, or names equal under case folding; the shipped inner archive holds none (checked), and its input is the checked set, so this matters only for a caller-supplied artifacts= set. Refusing them would make the guard hold on its own.",
  "Both binaries keep 31 assert __FILE__ strings and the zip four build-config modules under the fixed container prefix /wasi-python-build/; no user or host identity, but -ffile-prefix-map (and the host_neutral rewrite already used for _sysconfigdata) could drop them.",
  "reactor_main.c starts with pinned=1, so the load-time constructors (mimalloc and wasi-libc state) of the plain binary, not only the snapshot, see zeroed entropy; guest code always sees real entropy (checked). Inside-guest allocator randomness is not a host boundary; note only.",
  "The br_table maximum (3,203 labels against ~256k for GHSA-mghf-wjfp-p5xm) is measured by hand; a per-build check would keep it true until the runner moves to wasmtime-py 49.0.4 or later.",
  "Locally, build/artifacts/python-stdlib.zip has link count 5: research work trees under build/ (output-capture-costs, rust-spike-perf, scratch-wt50, concurrency-probe) hard-link it as lib/python315.zip. Developer environment only; the runner re-hashes the zip before each copy, so a write through one of those links would be refused, not used."
 ],
 'uncovered': [
  {'surface': 'wasi-python-0.1.0-wasm32-wasip1.tar.xz and wasi_python-0.1.0-py3-none-any.whl published on the v0.1.0 GitHub release',
   'boundary': "The release's packaging of the artifact set into the tarball and wheel against the set the release acceptance judged (set_sums 3339091f49b6cf94aaf90d5a68c281c3f1cc3384450f3cb94b768d8274d0fa20)",
   'subsystem': 'release',
   'attack_class': 'SUPPLY-CHAIN-AND-RELEASE.md#Cache, artifact, and workspace trust mixing',
   'starting_paths': ['.github/workflows/release.yml', 'build/artifacts/SHA256SUMS', 'release/set_key.py'],
   'reason': "The published SHA256SUMS names only the tarball and the wheel; confirming that the tarball's and the wheel's inner SHA256SUMS equal the accepted set needs the 78 MB and 98 MB assets, which this brief does not allow downloading. A unit allowed to fetch the release assets read-only can settle it deterministically."}
 ]
}
s = json.dumps(result, indent=1)
open('context/reviews/0.1.0-security-audit-2026-10-25/agents/h12-binary/scratch/result.json', 'w').write(s)
print(len(s))
