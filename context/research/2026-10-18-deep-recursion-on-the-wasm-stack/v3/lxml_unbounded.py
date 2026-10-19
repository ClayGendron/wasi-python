"""The four lxml shapes of lxml_edges.py, unbounded, for stackmin.py (smallest stack with no trap)."""
import importlib.util, os
_s = importlib.util.spec_from_file_location("e", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lxml_edges.py"))
_e = importlib.util.module_from_spec(_s); _s.loader.exec_module(_e)
CASES = {k: v[0](10**6) for k, v in _e.CASES.items()}
