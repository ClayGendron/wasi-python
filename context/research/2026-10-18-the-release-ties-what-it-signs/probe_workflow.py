"""Spec 057's probe of a release workflow, with PyYAML: downloads by id with a guard before each,
cache off, commit pins, defined outputs, no ${{ in run:, the two rebuild jobs alike."""
import re, sys, yaml

FORBIDDEN_WITH = {"name", "pattern", "github-token", "run-id", "repository", "merge-multiple", "skip-decompress"}
for path in sys.argv[1:]:
    raw = open(path).read()
    wf = yaml.safe_load(raw)
    jobs = wf["jobs"]
    problems = []
    if re.search(r"gh run download|actions/github-script|/actions/artifacts", raw):
        problems.append("another way to fetch an artifact")
    for name, job in jobs.items():
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        for j, o in re.findall(r"needs\.([\w-]+)\.outputs\.([\w-]+)", yaml.safe_dump(job)):
            if j not in needs: problems.append(f"{name}: reads needs.{j} but does not need it")
            elif o not in (jobs[j].get("outputs") or {}): problems.append(f"{name}: {j} has no output {o}")
        guarded = set()
        for step in job.get("steps", []):
            u, w = step.get("uses", ""), step.get("with") or {}
            if u and not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", u): problems.append(f"{name}: unpinned {u}")
            if "run" in step:
                if "${{" in step["run"]: problems.append(f"{name}: ${{{{ in a run: script")
                if '"" | *[!0-9]*)' in step["run"]:
                    guarded |= {v.strip() for v in (step.get("env") or {}).values()}
            if u.startswith("actions/download-artifact@"):
                bad = FORBIDDEN_WITH & set(w)
                if bad or "artifact-ids" not in w: problems.append(f"{name}: download not by id alone {sorted(bad)}")
                elif w["artifact-ids"].strip() not in guarded: problems.append(f"{name}: no guard before {w['artifact-ids']}")
                if w.get("digest-mismatch") != "error": problems.append(f"{name}: digest-mismatch not error")
            if u.startswith("astral-sh/setup-uv@") and w.get("enable-cache") is not False:
                problems.append(f"{name}: setup-uv cache {w.get('enable-cache')!r}")
    a, b = jobs.get("rebuild-linux-arm64"), jobs.get("rebuild-linux-x86-64")
    if a is None or b is None:
        problems.append("no rebuild-linux-arm64 and rebuild-linux-x86-64 jobs")
    else:
        norm = lambda j, r: yaml.safe_dump({k: v for k, v in j.items() if k not in ("name", "runs-on", "timeout-minutes")}).replace(r, "RUNNER")
        if norm(a, "ubuntu-24.04-arm") != norm(b, "ubuntu-24.04"): problems.append("the rebuild jobs differ beyond runner, time limit and names")
    print("==", path.rsplit("/", 1)[-1], "problems:", len(problems))
    for p in problems: print("   -", p)
