"""import pandas, read a small CSV, group it."""
import sys
import pandas as pd
df = pd.read_csv(sys.argv[1])
print(len(df))
print(df.groupby("region")["sales"].agg(["sum", "mean", "count"]).round(3).to_string())
