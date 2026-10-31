from pathlib import Path
PRE = (Path(__file__).parent / "lazy.py").read_text()
JOB = "import plotly.graph_objects as go; go.Figure(go.Scatter(x=[1,2], y=[3,4])).to_json()"
B = {
 "base": "pass",
 "full read": "import _zip_directory as z; z._fast(P)",
 "lazy read": "lazy_read(P)",
 "lazy read + load_all": "lazy_read(P).load_all()",
 "lazy eq": "import _zip_directory as z; f=z._fast(P); g=lazy_read(P); n=len(g); g.load_all(); print(n, len(f), f==g, list(f)==list(g), sorted(f)==sorted(g))",
 "full + import json": "install_full(); import json; json.dumps([1])",
 "lazy + import json": "install_lazy(); import json; json.dumps([1])",
 "full + import pandas": "install_full(); import pandas",
 "lazy + import pandas": "install_lazy(); import pandas; print(sorted(set(zipimport._zip_directory_cache[P]._segs) & {'numpy','pandas','dateutil','pytz','tzdata'}))",
 "full + plotly job": "install_full(); " + JOB,
 "lazy + plotly job": "install_lazy(); " + JOB,
 "lazy + plotly get_data": "install_lazy(); import pkgutil; print(len(pkgutil.get_data('plotly', 'package_data/plotly.min.js')))",
 "lazy + resources": "install_lazy(); import importlib.resources as r; print(len(r.files('plotly').joinpath('package_data/plotly.min.js').read_bytes()))",
 "lazy + metadata": "install_lazy(); import importlib.metadata as m; print(m.version('plotly'), len(m.packages_distributions()))",
 "full + metadata": "install_full(); import importlib.metadata as m; print(m.version('plotly'), len(m.packages_distributions()))",
 "lazy + iter_modules": "install_lazy(); import pkgutil; print(len(list(pkgutil.iter_modules())), 'plotly' in {m.name for m in pkgutil.iter_modules()})",
 "full + iter_modules": "install_full(); import pkgutil; print(len(list(pkgutil.iter_modules())), 'plotly' in {m.name for m in pkgutil.iter_modules()})",
 "count + import pandas": "install_counting(); import pandas; print(Counting.n_in, Counting.n_get, len([m for m in sys.modules]))",
 "count + plotly job": "install_counting(); " + JOB + "; print(Counting.n_in, Counting.n_get)",
}
CASES = {k: PRE + "\n" + v for k, v in B.items()}
