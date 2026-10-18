"""The guest program of the drafting runs (spec 043): a Delaunay triangulation that fails inside
qhull, one that succeeds, and what a writable root's /dev holds before and after. The runs gave
the guest a writable root, and for the `dev` runs a `dev/keep` file in it, so /dev existed as a
plain folder of the host's."""

import os

import matplotlib.tri as mtri


def dev():
    return sorted(os.listdir("/dev")) if os.path.isdir("/dev") else "no /dev"


print("dev before", dev())
try:
    mtri.Triangulation([0, 1, 2, 3], [0, 1, 2, 3])
except RuntimeError as e:
    print("collinear:", str(e)[:60])
print("good", mtri.Triangulation([0, 1, 0, 1], [0, 0, 1, 1]).triangles.shape)
print("dev after", dev())
if os.path.exists("/dev/null"):
    print("dev/null bytes", os.path.getsize("/dev/null"))
