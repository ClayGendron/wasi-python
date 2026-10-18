import hashlib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.utils import estimator_html_repr
from sklearn.utils.discovery import all_estimators
import sklearn
html = estimator_html_repr(make_pipeline(StandardScaler(), LogisticRegression()))
import re
html = re.sub(r"sk-(container|estimator)-id-\d+", "ID", html)
print("from zip:", ".zip/" in sklearn.__file__, "html", len(html), hashlib.sha256(html.encode()).hexdigest()[:16])
print("all_estimators", len(all_estimators()))
