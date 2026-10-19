"""PJ (spec 068, after its pre-build review's F1): which soft descriptor limits this host lets a
process set for itself, from a lowered 256. The command (`wasi-python run`) would raise its own
soft limit to its hard limit at start; this shows what that call does on macOS, where the hard
limit is unlimited."""

import resource

R = resource.RLIMIT_NOFILE
print("start", resource.getrlimit(R), "RLIM_INFINITY", resource.RLIM_INFINITY)
hard = resource.getrlimit(R)[1]
for target in (hard, 10**7, 1048576, 122880, 10240):
    resource.setrlimit(R, (256, hard))
    try:
        resource.setrlimit(R, (target, hard))
        print("from 256, set", target, "->", resource.getrlimit(R))
    except (ValueError, OSError) as e:
        print("from 256, set", target, "refused:", type(e).__name__, e)
