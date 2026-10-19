"""scipy.odr is not in this build (spec 037, Decision 9; decision 28).

It needs ODRPACK, which is Fortran, and no Fortran compiler targets wasm32-wasip1; scipy deprecated
the module for removal in 1.19, and with `_without-fortran` its build installs none of it. This
stand-in is packed as `scipy/odr.py`, so the import says why.
"""

raise ImportError(
    "scipy.odr is not in this build: it needs a Fortran compiler, which wasm32-wasip1 does not "
    "have; scipy deprecated it for removal in 1.19"
)
