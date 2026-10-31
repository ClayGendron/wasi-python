from pathlib import Path
PRE = (Path(__file__).parent / "lazy2.py").read_text()
JOB = "import plotly.graph_objects as go; go.Figure(go.Scatter(x=[1,2], y=[3,4])).to_json()"
B = {
 "base": "pass",
 "full read": "import _zip_directory as z; z._fast(P)",
 "lazy read": "lazy_read(P)",
 "lazy read + load_all": "zipimport._zip_directory_cache[P] = lazy_read(P); load_all()",
 "lazy eq": "import _zip_directory as z\nf=z._fast(P); g=lazy_read(P); n=len(g); zipimport._zip_directory_cache[P]=g; load_all()\nfo, go_ = folder_orders(f), folder_orders(g)\nprint(n, len(f), f==g, list(f)==list(g), fo==go_, [k for k in fo if fo[k]!=go_.get(k)][:5])",
 "full + import pandas": "install_full(); import pandas",
 "lazy + import pandas": "install_lazy(); import pandas; print(len(_loaded[P]), sorted(_loaded[P]))",
 "full + plotly job": "install_full(); " + JOB,
 "lazy + plotly job": "install_lazy(); " + JOB + "; print(len(_loaded[P]))",
 "lazy + get_data first": "install_lazy(); import pkgutil; print(len(pkgutil.get_data('plotly', 'package_data/plotly.min.js')))",
 "lazy + namespace pkg": "install_lazy(); import mpl_toolkits.mplot3d; print(mpl_toolkits.mplot3d.__name__)",
 "lazy + invalidate": "install_lazy(); import plotly.io; import importlib; importlib.invalidate_caches(); import plotly.colors; print(sorted(_loaded[P]))",
 "lazy + iter_modules": "install_lazy(); import pkgutil, plotly; print(len(list(pkgutil.iter_modules())), len(list(pkgutil.iter_modules(plotly.__path__))))",
 "full + iter_modules": "install_full(); import pkgutil, plotly; print(len(list(pkgutil.iter_modules())), len(list(pkgutil.iter_modules(plotly.__path__))))",
 "lazy + metadata": "install_lazy(); import importlib.metadata as m; print(m.version('plotly'), len(list(m.distributions())))",
 "full + metadata": "install_full(); import importlib.metadata as m; print(m.version('plotly'), len(list(m.distributions())))",
}
CASES = {k: PRE + "\n" + v for k, v in B.items()}
