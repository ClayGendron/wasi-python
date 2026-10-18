"""Run a few guest probes natively (host CPython 3.15, the same package versions) for parity.

guest_probe_probes.py is the PDF and PROBES definitions cut from guest_probe.py (not kept here)."""
import sys
sys.path[:0] = [f"{sys.argv[1]}/pkgs/{n}" for n in (
    "numpy pandas python-dateutil six tzdata networkx pypdf beautifulsoup4 soupsieve html5lib "
    "webencodings typing-extensions pyyaml mpmath patsy packaging charset-normalizer xmltodict").split()]
import guest_probe_probes as gp  # noqa: E402
for name in ("networkx", "pypdf", "html5lib", "pyyaml", "mpmath", "xmltodict", "charset-normalizer"):
    print("==", name, flush=True)
    try:
        exec(gp.PROBES[name], {})
    except Exception as e:
        print(type(e).__name__, e)
