import re, sys
cands = ["openpyxl","xlsxwriter","xlrd","python-docx","python-pptx","pypdf","pypdf2","pdfminer.six","pdfplumber","pymupdf","reportlab","lxml","beautifulsoup4","html5lib","pyyaml","tomli-w","jinja2","markupsafe","tabulate","python-dateutil","pytz","tzdata","regex","charset-normalizer","chardet","networkx","sympy","mpmath","statsmodels","patsy","scikit-learn","joblib","threadpoolctl","seaborn","plotly","altair","bokeh","pillow","pyarrow","polars","duckdb","numexpr","bottleneck","pydantic","attrs","more-itertools","toolz","rich","tqdm","requests","httpx","xarray","scikit-image","opencv-python","opencv-python-headless","wordcloud","nltk","textblob","faker","shapely","geopandas","folium","tiktoken","orjson","docx2txt","odfpy","pyxlsb","tables","h5py","numba","imageio","kaleido","matplotlib","scipy","numpy","pandas"]
def norm(n): return re.sub(r"[-_.]+","-",n).lower()
names=set()
for line in open(sys.argv[1]):
    line=line.strip()
    if not line or line.startswith("#"): continue
    m=re.match(r"([A-Za-z0-9_.\-]+)",line)
    if m: names.add(norm(m.group(1)))
print("present:", " ".join(c for c in cands if norm(c) in names))
print("absent:", " ".join(c for c in cands if norm(c) not in names))
