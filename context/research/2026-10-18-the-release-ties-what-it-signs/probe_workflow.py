import re, sys, yaml
for path in sys.argv[1:]:
    wf = yaml.safe_load(open(path))
    jobs = wf["jobs"]
    print("==", path.rsplit("/",1)[-1], "workflow permissions:", wf.get("permissions"))
    problems = []
    for name, job in jobs.items():
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        text = yaml.safe_dump(job)
        for j, o in re.findall(r"needs\.([\w-]+)\.outputs\.([\w-]+)", text):
            if j not in needs: problems.append(f"{name}: reads needs.{j} but does not need it")
            elif o not in (jobs[j].get("outputs") or {}): problems.append(f"{name}: {j} has no output {o}")
        for step in job.get("steps", []):
            u = step.get("uses", "")
            if u and not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", u): problems.append(f"{name}: unpinned {u}")
            w = step.get("with") or {}
            if u.startswith("actions/download-artifact@"):
                if "name" in w or "artifact-ids" not in w: problems.append(f"{name}: download by name {w.get('name')}")
                elif w.get("digest-mismatch") != "error": problems.append(f"{name}: digest-mismatch not error")
            if u.startswith("astral-sh/setup-uv@") and w.get("enable-cache") is not False:
                problems.append(f"{name}: setup-uv cache {w.get('enable-cache')!r}")
            if "run" in step and "${{ needs." in step["run"]: problems.append(f"{name}: needs.* in run")
        print(f"  {name}: needs={needs} env={job.get('environment')} perms={job.get('permissions')} outputs={sorted(job.get('outputs') or {})}")
    print("  problems:", len(problems)); [print("   -", p) for p in problems]
