import statsmodels.api as sm
print("statsmodels.api imports")
for name in ("spector", "longley"):
    try:
        print(name, sm.datasets.__dict__[name].load_pandas().data.shape)
    except Exception as e:
        print(name, type(e).__name__, str(e).split(".zip/")[-1])
