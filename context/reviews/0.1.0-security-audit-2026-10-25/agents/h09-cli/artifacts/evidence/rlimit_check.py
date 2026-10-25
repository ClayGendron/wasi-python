"""The CLI's descriptor-limit raise: soft lowered to 256 under a hard limit, then raised."""
import json, resource
from wasi_python import cli
r = resource.RLIMIT_NOFILE
before = resource.getrlimit(r)
resource.setrlimit(r, (256, before[1]))
lowered = resource.getrlimit(r)
cli._raise_descriptor_limit()
after = resource.getrlimit(r)
out = {"initial": before, "lowered": lowered, "after_raise": after}
open("context/reviews/0.1.0-security-audit-2026-10-25/agents/h09-cli/scratch/evidence/rlimit_check.json", "w").write(json.dumps(out))
print(out)
