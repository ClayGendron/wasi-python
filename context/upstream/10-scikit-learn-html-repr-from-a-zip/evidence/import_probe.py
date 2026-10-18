import sys
for stmt in ("import sklearn", "import sklearn.base", "from sklearn.linear_model import LinearRegression", "import statsmodels.api"):
    try:
        exec(stmt)
        print(stmt, "-> ok")
    except Exception as e:
        print(stmt, "->", type(e).__name__, str(e).split("/probes/")[-1])
import sklearn
print("sklearn from zip:", ".zip/" in sklearn.__file__)
