# Findings detail: confirmed records (medium, high, critical impact)

Each section copies the final record's source path and target-neutral local reproduction. Dummy principals only; nothing here is live-probe guidance.

## 1. env= _PYTHON_SYSCONFIGDATA_PATH makes a module planted in a reused root run on `import pandas` in a later call

Fingerprint `runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules`. Overall severity low; impact medium; likelihood low.

### Ordered trace
   1. `src/wasi_python/_limits.py:139` (entrypoint, _check_inputs): The embedder's env keys are checked only for emptiness and '='; _PYTHON_SYSCONFIGDATA_PATH passes (called from runner.py:581).
   2. `src/wasi_python/_call.py:452` (propagation, _instance): wasi.env is BASE_ENV, HOME, then env= laid over them, unfiltered; the session opening does the same at _sessions.py:999.
   3. `recipes/reactor_bootstrap.py:143` (propagation, run): The reactor clears os.environ and copies the WASI environment into it for the program (the session setup does the same at line 240).
   4. `build/pandas-3.0.6/pandas/compat/_constants.py:21` (propagation, module level): `import pandas` calls sysconfig.get_config_var('HOST_GNU_TYPE') at import time.
   5. `build/Python-3.15.0/Lib/sysconfig/__init__.py:360` (propagation, _get_sysconfigdata): Reads _PYTHON_SYSCONFIGDATA_PATH from os.environ with no ignore_environment check (the zip's compiled sysconfig carries the same constant and no ignore_environment reference).
   6. `build/Python-3.15.0/Lib/sysconfig/__init__.py:343` (sink, _import_from_directory): PathFinder.find_spec(name, [path]) then spec.loader.exec_module(module): the module the earlier guest planted in the reused root runs.

### Evidence
   - `docs/explanation/security-model.md:9`: Policy: code planted in a root never runs at start-up or on import in a later call, on either binary.
   - `docs/explanation/security-model.md:82`: The only env= overrides listed as not protected are HOME and PYTHONTZPATH; no code-loading variable is named.
   - `recipes/reactor_main.c:179`: PyConfig_InitIsolatedConfig: the design relies on the interpreter ignoring environment-driven code paths; the guest reports sys.flags.ignore_environment=1 and a PYTHONPATH=/data control does not import the planted module.
   - `src/wasi_python/_places.py:176`: _check_import_path: the control that confines code-loading folders to read-only grants, which this variable bypasses.
   - `build/Python-3.15.0/Lib/sysconfig/__init__.py:361`: _import_from_directory(path, name) is used whenever the variable is set.
   - `scripts/python-wasi-cross:25`: The project's own cross-build wrapper exports _PYTHON_SYSCONFIGDATA_PATH, so a host shell that forwards it with --env is a plausible way the variable reaches a call.

### Principal and affected resource
- Attacker: A guest in call 1 with a writable root writes one file at /data/_sysconfigdata__wasi_wasm32-wasi.py; the embedder's later call on the same root, with env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'}, runs a program that only imports pandas, and the planted module runs.
- Invariant violated: Every folder the guest's interpreter loads code from is subject to the import_path rules (a read-only grant with nothing writable under or above it), or the runner refuses or drops an env= entry that would load code from elsewhere, as isolated mode already ignores PYTHONPATH.

### Native input and bounded instructions

Payload 1:

```
call 1: wasi_python.run(['-c', "import os; os.makedirs('/data', exist_ok=True); open('/data/_sysconfigdata__wasi_wasm32-wasi.py','w').write(\"import sys\\nsys.stderr.write('PLANTED-V03\\\\n')\\nbuild_time_vars={'installed_base':'/usr/local'}\\n\")"], root=R)
```

Payload 2:

```
call 2: wasi_python.run(['-c', 'import pandas; print("ok")'], root=R, env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'})
```

1. Confirm build/lane.lock is absent. The verifier's script is scratch/evidence/v03_check.py, run by scratch/driver.py with a 600 s subprocess timeout as: ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=<scratch>/home TMPDIR=<scratch>/tmp WASI_PYTHON_CACHE=<scratch>/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' .venv/bin/python -I <scratch>/evidence/v03_check.py <scratch>, with the root R at <scratch>/work/root. The target tree was not mounted read-only (this platform cannot enforce that) and no memory rlimit was applied; no grant or root pointed at the target.
2. Calls in order on the same root: plant; flags (sys.flags with the env entry); control_pandas_noenv (import pandas without the entry); env_pandas_snapshot and env_pandas_plain (import pandas with the entry, snapshot True and False); control_pythonpath (env PYTHONPATH=/data, import of a second planted module).
3. Read scratch/evidence/v03_result.json and v03_run.log for 'PLANTED-V03' on stderr per call.

### Observed output
The guest reports sys.flags.ignore_environment=1 and isolated=1. Without the env entry, import pandas printed ok and the planted module did not run. With env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'}, import pandas printed ok and stderr held 'PLANTED-V03' on both the snapshot and the plain binary. The PYTHONPATH=/data control failed with ModuleNotFoundError, so isolated mode does ignore the documented variable but not this private one. The verifier did not test other packages; the hunter's record also reports scipy, sklearn, joblib and statsmodels.api.

### Conditions and containment
   - system_configuration: The trusted embedder passes env containing _PYTHON_SYSCONFIGDATA_PATH naming a guest folder that an earlier call could write (a reused root, a writable grant or a writable mount), for example forwarded from a cross-build shell with the CLI's --env _PYTHON_SYSCONFIGDATA_PATH.
   - data_state: An earlier, less trusted call on the same root or writable folder left `_sysconfigdata__wasi_wasm32-wasi.py` there.
   - user_interaction: The later program imports pandas (or another package that reads sysconfig config vars at import), or calls sysconfig.get_config_var(s).

### Remediation and regression case
Refuse env keys that make the guest interpreter load code from a folder, at least _PYTHON_SYSCONFIGDATA_PATH, in _limits._check_inputs before any work, with a message pointing to import_path; add a regression check that plants the module in call 1 and asserts that call 2 with the entry raises ValueError. As defence in depth the reactor bootstrap can drop the key from os.environ, as isolated mode drops PYTHONPATH. Name the variable in the security model's not-protected or refused list either way.

Proposed change to `src/wasi_python/_limits.py`:

```python
_CODE_FOLDER_ENV = frozenset({"_PYTHON_SYSCONFIGDATA_PATH"})  # sysconfig execs a module from this folder
...
            if not name or "=" in name:
                raise ValueError("env key: illegal environment variable name")  # never quoted
            if name in _CODE_FOLDER_ENV:
                raise ValueError(
                    "env key: _PYTHON_SYSCONFIGDATA_PATH loads code from a folder; "
                    "name a read-only grant in import_path instead"
                )
```

## 2. A guest can override a keyword a class tool's constructor binds with a partial or partialmethod

Fingerprint `src/wasi_python/tools.py:_bound_keywords:class-construction-partial-unfixed`. Overall severity low; impact medium; likelihood low.

### Ordered trace
   1. `src/wasi_python/_call.py:1263` (entrypoint, _door): Untrusted guest code calls the imported host::call door; after admit, the frame bytes are copied out of guest linear memory and handed to the tool frame host.
   2. `src/wasi_python/_tool_host.py:1000` (propagation, _ToolHost._call_answer): The args object is checked against the tool's explicit schema; an open schema ({"type": "object"}), additionalProperties true, or a properties map naming the keyword accepts role.
   3. `src/wasi_python/_tool_host.py:1004` (propagation, _ToolHost._call_answer): The bound-keyword refusal tests each argument against t._fixed, which is empty for the class tool, so role passes.
   4. `src/wasi_python/tools.py:469` (propagation, _bound_keywords): At registration the walk reached type.__call__, a C slot, and returned no fixed keywords without reading the class's __init__ or __new__.
   5. `src/wasi_python/_tool_host.py:232` (propagation, _Work.__call__): The gate receives a deep copy of the arguments with role in it, contrary to the documented contract.
   6. `src/wasi_python/_tool_host.py:258` (sink, _Work.__call__): t.fn(**args) calls the class; type.__call__ runs the partial-bound __init__ or __new__, whose keyword merge lets the guest's role replace the embedder's bound role.

### Evidence
   - `src/wasi_python/tools.py:439`: Docstring of _bound_keywords: keywords a partial binds are found wherever inspect.signature may meet one on its way to the function; each is fixed and refused in a frame.
   - `src/wasi_python/tools.py:466`: A class target goes to type(target).__call__ and stops at the C-slot check (line 469), so a partial in __init__ or __new__ is never collected.
   - `src/wasi_python/tools.py:364`: tool() computes fixed = _bound_keywords(name, fn) once; it is the only source of Tool._fixed.
   - `src/wasi_python/tools.py:418`: _given refuses a schema naming a fixed keyword only through the computed fixed set, so a schema naming role is accepted for the class.
   - `src/wasi_python/_tool_host.py:1004`: The frame-time refusal relies on t._fixed alone.
   - `docs/how-to/tools.md:65`: Promise: a keyword the partial binds is fixed, not in the schema, and a frame that names it is refused.
   - `docs/how-to/tools.md:71`: Promise: the gate's arguments hold no keyword a partial binds.
   - `tests/checks/test_v1_4_embedding.py:3517`: The regression test covers nested partials, a __wrapped__ chain, a bound partialmethod and refuses an unbound partialmethod, but has no class whose constructor binds a keyword.

### Principal and affected resource
- Attacker: Untrusted guest code in wasi_python.run(tools=[...], gate=...) sends a raw tool-protocol frame through _host.call naming a keyword the embedder bound in the tool class's constructor.
- Invariant violated: A keyword bound by a partial or partialmethod on a class's construction path (its __new__ or __init__, found through the MRO, through staticmethod or classmethod wrappers, nested partials and __wrapped__ links) is in Tool._fixed, or the class is refused at tool() as an unbound partialmethod already is. tool() then refuses a given schema that names the keyword, and a frame that names it is answered invalid_arguments without the gate or the constructor running.

### Native input and bounded instructions

Payload 1:

```
class AccountPM(dict):
    def _init(self, q, role="user"): dict.__init__(self, q=q, role=role)
    __init__ = functools.partialmethod(_init, role="viewer")
tool(AccountPM, name="acct_pm", input_schema={"type": "object"})
```

Payload 2:

```
class AccountP(dict):
    __init__ = functools.partial(_initp, role="viewer")  # Python 3.14
```

Payload 3:

```
class AccountNew:
    __new__ = staticmethod(functools.partial(_new, role="viewer"))  # _new returns a dict
```

Payload 4:

```
import _host; _host.call(b'{"v":1,"id":1,"op":"call","tool":"acct_pm","args":{"q":"x","role":"admin"}}')
```

Payload 5:

```
Control: tool(functools.partial(orders, user_id=42), name="orders", input_schema={"type": "object"}) and a frame with args {"q":"x","user_id":1}
```

1. Verifier-owned harness: scratch/evidence/v02_class_ctor_partial.py, output scratch/evidence/v02_class_ctor_partial.out.json (stderr in v02_class_ctor_partial.err.txt), run with the repository's .venv (Python 3.14.2, wasmtime-py 49.0.0) and the checkout's build/artifacts set.
2. Run under ulimit -t 300 -f 4000000 -n 4096, env -i with PATH=/usr/bin:/bin and HOME, TMPDIR and WASI_PYTHON_CACHE in the verifier's scratch, sandbox-exec denying network, python -I, and a 240 s subprocess.run timeout from a trusted driver. build/lane.lock was absent. The target was not mounted read-only (the platform cannot enforce it); no grant or root pointed at it, and nothing was written under it.
3. Host side: register AccountPM, AccountP and AccountNew each with input_schema={"type": "object"}, plus the plain-partial control orders, in one wasi_python.run(['-c', prog], tools=[...], gate=gate, deadline_s=60) call with a gate that records call.arguments and allows. Also call tool() on each class with a schema whose properties name role, and on the partial with a schema naming user_id.
4. Guest side: send through _host.call a frame naming role='admin' to each class tool, one without role, then user_id=1 and a call without user_id to the control.
5. Read the guest's answers, the host log of what the gate and each constructor received, Tool._fixed, and done.tools.outcomes.

### Observed output
Each of the three class tools answered ok with value {"q": "x", "role": "admin"}; the host log shows the gate received {"q": "x", "role": "admin"} and each constructor ran with role='admin'; the record's outcome was ok. Without role the constructor ran with the bound role='viewer'. Tool._fixed was [] for all three, inspect.signature showed '(q, *, role='viewer')', and tool() accepted a schema whose properties name role. In the same run the control's user_id=1 frame was answered invalid_arguments ('unknown argument user_id') with neither the gate nor the handler running, and tool() refused a schema naming user_id. A callable instance whose __call__ is a partialmethod is refused at tool(), so only the class construction path is unguarded.

### Conditions and containment
   - system_configuration: The embedder registers a class (a type whose metaclass __call__ is type.__call__) as a tool, with __init__ that is a functools.partialmethod, __init__ that is a functools.partial (Python 3.14 makes it a method descriptor), or __new__ that is a staticmethod over a functools.partial, binding an authority keyword such as a role or user id.
   - system_configuration: The tool's explicit input_schema lets the keyword through: no properties (open), additionalProperties not false, or a properties map naming it, which tool() refuses for every other binding shape. A derived schema is not reachable: tool() refuses a class without an explicit schema for lack of hints.
   - authentication_level: The attacker is the untrusted guest code, or the model driving it, which can send any frame through the door.

### Remediation and regression case
In _bound_keywords, when the target is a class, read its construction path as type.__call__ runs it: inspect.getattr_static(cls, '__new__') and inspect.getattr_static(cls, '__init__') (MRO included), unwrap staticmethod and classmethod through __func__, and then walk each member with the same loop the function already uses (partial keywords collected, nested partials and __wrapped__ followed), treating a partialmethod as its .func plus .keywords rather than refusing it. Do this whatever the metaclass __call__ is: a Python metaclass __call__ that delegates to super().__call__() still runs __init__ with the guest's keywords, and the hunter's patch skips that case (in the verifier's run it returned [] for such a class, where inspect.signature shows only (*a, **k)). A simpler fail-closed alternative is to refuse at tool() any class whose __new__ or __init__ is a partial or partialmethod, as an unbound partialmethod is refused today. Add to test_bound_keywords_are_fixed_however_the_partial_is_reached a class with a partialmethod __init__, a 3.14 partial __init__ and a staticmethod-partial __new__, under an open schema and under a schema naming the keyword, expecting refusal at tool() or invalid_arguments with neither gate nor constructor called.

Proposed change to `src/wasi_python/tools.py`:

```python
    if isinstance(fn, type):
        # type.__call__ (or a metaclass's __call__ that defers to it) runs the class's own
        # __new__ and __init__: a partial bound there is fixed too.
        for attr in ("__new__", "__init__"):
            member = inspect.getattr_static(fn, attr, None)
            member = getattr(member, "__func__", member)  # staticmethod, classmethod
            if isinstance(member, functools.partialmethod):
                found.update(member.keywords)
                member = member.func
            if isinstance(member, functools.partial) or getattr(member, "__wrapped__", None) is not None:
                found.update(_bound_keywords(name, member))
    # ... then the existing walk from fn, adding its keywords to found
```

## 3. Metered engine on wasmtime-py 49.0.0 drops the fuel of C++ work that ends in a caught exception (GHSA-m63x-6p34-q65x), so guest Python can run far past its fuel cap

Fingerprint `wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine`. Overall severity low; impact medium; likelihood low.

### Ordered trace
   1. `src/wasi_python/runner.py:115` (entrypoint, run): wasi_python.run takes an untrusted guest program (argv) with fuel and deadline_s; deadline_s=None means no wall-clock limit, so fuel is the only CPU bound.
   2. `scripts/steps/55_matplotlib.sh:102` (propagation, kiwisolver _cext build): kiwisolver's seven C++ files are compiled with CXX_EH (line 50: -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions), so the extension's catch of kiwi::UnsatisfiableConstraint around solver.addConstraint is a try_table catch. recipes/wasi-scipy.cross line 44 sets the same flags (plus -wasm-enable-sjlj), and the numpy, pandas, matplotlib, plot-libs and sklearn cross files also pass -fwasm-exceptions for the other C++ packages.
   3. `scripts/steps/60_link.sh:129` (propagation, link): python.wasm is linked with -fwasm-exceptions; the hunter counted 44,791 try_table in 7,905 functions.
   4. `uv.lock:1049` (propagation, wasmtime pin): wasmtime resolves to 49.0.0 (installed in .venv), inside the advisory's affected range.
   5. `src/wasi_python/_engines.py:122` (propagation, _engine): cfg.consume_fuel = metered; wasm exceptions and the compiler are left at their defaults (epoch_interruption is also on, line 123).
   6. `src/wasi_python/_call.py:618` (sink, _drive): store.set_fuel(fuel) sets the instruction cap; fuel_used is read at line 511 through _fuel_used (line 554). On 49.0.0 both miss callee work that unwinds to a try_table catch.

### Evidence
   - `context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json:1`: The advisory: with fuel enabled, the catch path of a call inside try_table can drop the callee's fuel, which it says allows exponential amplification in general. Affects 49.0.0; fixed in 49.0.1. Workaround: epoch interruption.
   - `src/wasi_python/_engines.py:122`: consume_fuel on the metered engine; no override of wasm exceptions.
   - `pyproject.toml:18`: dependencies = ["wasmtime>=49,<50"].
   - `src/wasi_python/runner.py:176`: run()'s fuel parameter: 'A cap on the guest's executed instructions; past it the call ends "out of fuel".'
   - `SECURITY.md:24`: The runner uses wasmtime-py 49.0.0 and no wasmtime-py release yet carries a later wasmtime; the handled-advisories list does not include GHSA-m63x-6p34-q65x.
   - `SECURITY.md:18`: In scope: a guest that runs past its deadline, fuel, memory or output cap.
   - `scripts/steps/55_matplotlib.sh:50`: CXX_EH="-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions" for the kiwisolver, matplotlib and contourpy C++ code.

### Principal and affected resource
- Attacker: An untrusted guest Python program run by an embedder through wasi_python.run with a fuel cap and deadline_s=None.
- Invariant violated: A fuel cap bounds the guest's executed instructions, and fuel_used counts them, whatever path the guest's code takes, including C++ exceptions caught inside a compiled-in package. run()'s docstring calls fuel 'a cap on the guest's executed instructions', and SECURITY.md lists a guest that runs past its fuel cap as in scope.

### Native input and bounded instructions

Payload 1:

```
# Guest: N-variable equality chain in kiwisolver, then K calls of one mode; prints loop time.
import sys, time
import kiwisolver as kw
n, k, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
solver = kw.Solver()
v = [kw.Variable("v%d" % i) for i in range(n + 1)]
solver.addConstraint(v[0] == 0)
for i in range(n):
    solver.addConstraint(v[i + 1] == v[i] + 1)
caught = 0
t0 = time.perf_counter()
for j in range(k):
    if mode == "fail":
        try:
            solver.addConstraint(v[n] == -1 - j)
        except kw.UnsatisfiableConstraint:
            caught += 1
    elif mode == "weak":
        c = (v[n] == -1 - j) | "weak"
        solver.addConstraint(c)
        solver.removeConstraint(c)
    elif mode == "ok":
        # The same required equality on the chain's end, but consistent with it: no throw.
        c = v[n] == n
        solver.addConstraint(c)
        solver.removeConstraint(c)
    elif mode == "py":
        sum(range(n * 20))
print("loop_s=%.4f caught=%d" % (time.perf_counter() - t0, caught))
```

Payload 2:

```
import wasi_python; r = wasi_python.run(['-c', GUEST, N, K, MODE], fuel=FUEL, deadline_s=None); print(r.exit_code, r.trapped, r.fuel_used, r.stdout)
```

Payload 3:

```
(module
  (tag $t)
  (func $burn_throw (param $n i32)
    (loop $l
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (i32.gt_s (local.get $n) (i32.const 0))))
    (throw $t))
  (func $burn_ret (param $n i32)
    (loop $l
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (i32.gt_s (local.get $n) (i32.const 0)))))
  (func (export "thrown") (param $r i32) (param $n i32)
    (loop $outer
      (block $h
        (try_table (catch $t $h)
          (call $burn_throw (local.get $n))))
      (local.set $r (i32.sub (local.get $r) (i32.const 1)))
      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))
  (func (export "returned") (param $r i32) (param $n i32)
    (loop $outer
      (block $h
        (try_table (catch $t $h)
          (call $burn_ret (local.get $n))))
      (local.set $r (i32.sub (local.get $r) (i32.const 1)))
      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))
)
```

1. Confirm build/lane.lock is absent and build/artifacts holds the shipped set (MANIFEST lists kiwisolver 1.5.1); confirm .venv has wasmtime 49.0.0.
2. Write the first payload to a guest file; from a host script under the audit's sandbox wrapper (network denied, empty environment, HOME, TMPDIR and a mode-0700 WASI_PYTHON_CACHE under scratch, CPU and file-size rlimits), call wasi_python.run(['-c', guest, N, K, MODE], fuel=FUEL, deadline_s=None) as in the second payload.
3. Run N:K:MODE = 200:0:none, 200:500:fail, 200:500:ok, 200:500:weak, 2000:0:none, 2000:500:fail, 2000:500:ok, 2000:500:weak, 2000:500:py, 6000:0:none, 6000:500:fail, 6000:500:py with fuel=10**13; per-call fuel of a mode is (fuel_used - fuel_used of N:0:none) / K; compare with the loop_s the guest prints.
4. Run 2000:20000:fail, 2000:20000:ok and 2000:20000:weak with fuel=2200000000.
5. Engine-level control: run the third payload (WAT) on wasmtime-py 49.0.0 with consume_fuel, calling 'thrown' and 'returned' with r=100, n=100000, and under the pinned wasmtime CLI 49.0.3 with -W fuel=N,exceptions=y --invoke thrown, finding the smallest N that completes.

### Observed output
Proposer's run, failing addConstraint, fuel per call / wall per call: N=200 18,619 / 9.8 us; N=2000 18,112 / 59 us; N=6000 17,162 / 190 us. Independent re-run (fresh guest and host scripts): N=200 18,744 / 9.6 us; N=2000 19,581 / 58 us; N=6000 18,357 / 184 us. Setup fuel (N:0:none): 79,699,507; 1,635,065,251; 15,271,669,312. Same-shape no-throw control (ok): N=200 140,067 / 9.6 us; N=2000 1,552,404 / 127 us. Weak add/remove: N=200 950,942 / 44 us; N=2000 65,972,562 / 2.29 ms. Pure-Python control: 6,049,028,364 fuel in 0.5748 s (N=2000, 1.05e10 fuel/s) and 35,212,385,994 in 3.8875 s (N=6000, 9.1e9 fuel/s); failing calls at N=6000: 9,178,617 fuel in 0.0921 s, 1.0e8 fuel/s. Cap 2.2e9: 2000:20000:fail exited 0, trapped None, fuel_used 2,017,914,692 (proposer 2,017,052,943), loop 1.1842 s, 20,000 caught; 2000:20000:ok and 2000:20000:weak each trapped 'out of fuel'. WAT: on wasmtime-py 49.0.0 'thrown' r=100 n=100000 used 1,101 fuel and 'returned' 80,001,201; the CLI 49.0.3 trapped 'all fuel consumed' at 80,001,284 and completed at 80,001,285.

### Conditions and containment
   - third_party_dependency: wasmtime-py 49.0.0 (wasmtime 49.0.0, Cranelift), the only version the pin admits today.
   - system_configuration: The embedder passes fuel and relies on it as the bound: deadline_s=None, a fuel cap much tighter than the deadline, or fuel_used used for accounting. With the default 60 s deadline, wall time stays bounded.
   - data_state: The guest runs code that reaches a caught C++ exception (or longjmp) in a compiled-in package after material work; kiwisolver's unsatisfiable addConstraint is one plain-Python way.

### Remediation and regression case
Raise the wasmtime floor to a wasmtime-py carrying wasmtime 49.0.1 or later (or move to 50.x) as soon as one is published. Until then, do not let fuel stand alone as the bound: when fuel is given on 49.0.0, require a finite deadline_s (refuse or warn on deadline_s=None), since epoch interruption is the advisory's workaround and is unaffected; this bounds wall time but cannot make fuel count correctly. List GHSA-m63x-6p34-q65x in SECURITY.md as unmitigated, and say that on 49.0.0 fuel and fuel_used under-count work that ends in a caught C++ exception or longjmp. Disabling wasm exceptions is not an option, because the build depends on them. Add a check, counted in fuel only, that runs the kiwisolver loop above and asserts that the failing call's per-call fuel grows with N as the same-shape no-throw call's does; on 49.0.0 it fails, so it enters as a known gap closed by the floor raise, and the defect cannot return unseen.
