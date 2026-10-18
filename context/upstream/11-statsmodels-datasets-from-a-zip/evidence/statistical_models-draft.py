"""Golden job draft (spec 045): statsmodels regressions, tests and time series on its own datasets."""

import warnings
from importlib.metadata import version

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula as sm_formula
import statsmodels.formula.api as smf
from statsmodels.nonparametric.smoothers_lowess import lowess
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf, adfuller, pacf

D = ".9g"  # direct results
IT = ".6g"  # iterative results


def f(x, k=D):
    return format(float(x) + 0.0, k)


def fs(xs, k=D):
    return "[" + ", ".join(f(x, k) for x in np.ravel(np.asarray(xs, dtype=float))) + "]"


names = ["statsmodels", "scipy", "numpy", "pandas", "patsy", "formulaic", "interface-meta", "wrapt"]
print("versions", " ".join(f"{n}={version(n)}" for n in names))

longley = sm.datasets.longley.load_pandas()
print("longley", longley.data.shape, list(longley.data.columns))
X = sm.add_constant(longley.exog)
ols = sm.OLS(longley.endog, X).fit()
print("ols params", fs(ols.params))
print("ols bse", fs(ols.bse))
print("ols rsquared", f(ols.rsquared), "adj", f(ols.rsquared_adj), "F", f(ols.fvalue), "p(F)", f(ols.f_pvalue))
print("ols aic", f(ols.aic), "bic", f(ols.bic), "condition number", f(ols.condition_number, IT))
print("ols conf_int", fs(ols.conf_int(0.05)))
print("ols tvalues", fs(ols.tvalues), "pvalues", fs(ols.pvalues))
print("ols durbin-watson", f(sm.stats.durbin_watson(ols.resid)))
print(ols.summary().tables[1].as_text())
robust = sm.OLS(longley.endog, X).fit(cov_type="HC1")
print("ols HC1 bse", fs(robust.bse))

data = longley.data
p = smf.ols("TOTEMP ~ GNP + POP + UNEMP", data=data).fit()
sm_formula.options.formula_engine = "formulaic"
fz = smf.ols("TOTEMP ~ GNP + POP + UNEMP", data=data).fit()
engine_used = type(fz.model.data.model_spec).__module__.split(".")[0]
sm_formula.options.formula_engine = "patsy"
print("formula params", fs(p.params), "engine", engine_used, "patsy equals formulaic:", bool(np.allclose(p.params.to_numpy(), fz.params.to_numpy(), rtol=1e-12, atol=0)))
print("anova", fs(anova_lm(p, typ=2)["F"].to_numpy()[:-1]))

anes = sm.datasets.anes96.load_pandas().data
logit = smf.logit("vote ~ age + educ + income + selfLR", data=anes).fit(disp=0, method="newton", tol=1e-12, maxiter=100)
print("logit params", fs(logit.params, IT), "llf", f(logit.llf, IT), "converged", logit.mle_retvals["converged"])

rand = sm.datasets.randhie.load_pandas()
glm = sm.GLM(rand.endog, sm.add_constant(rand.exog), family=sm.families.Poisson()).fit(tol=1e-12, maxiter=200)
print("glm poisson params", fs(glm.params[:4], IT), "deviance", f(glm.deviance, IT))

rng = np.random.Generator(np.random.PCG64(20261017))
a, b = rng.normal(0.0, 1.0, 40), rng.normal(0.4, 1.0, 40)
t = sm.stats.ttest_ind(a, b)
print("ttest_ind", fs(t))
reject, corrected, _, _ = multipletests([0.01, 0.02, 0.03, 0.2, 0.5], method="fdr_bh")
print("fdr_bh", reject.tolist(), fs(corrected))

nile = sm.datasets.nile.load_pandas().data["volume"].to_numpy()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    arima = ARIMA(nile, order=(1, 0, 1)).fit(method_kwargs={"gtol": 1e-12, "xtol": 1e-12, "ftol": 1e-12, "maxiter": 1000})
print("arima params", fs(arima.params, IT), "aic", f(arima.aic, IT))
print("arima forecast", fs(arima.forecast(3), IT))
fixed = ARIMA(nile, order=(1, 0, 1)).filter([919.0, 0.8, -0.4, 15000.0])
print("arima fixed-params llf", f(fixed.llf), "forecast", fs(fixed.forecast(2)))

sun = sm.datasets.sunspots.load_pandas().data["SUNACTIVITY"].to_numpy()
adf = adfuller(sun, maxlag=8, autolag=None, result_object=False)
print("adfuller stat", f(adf[0]), "p", f(adf[1]))
print("acf", fs(acf(sun, nlags=4)), "pacf", fs(pacf(sun, nlags=4)))

co2 = sm.datasets.co2.load_pandas().data["co2"].resample("MS").mean().ffill()
stl = STL(co2, seasonal=13).fit()
print("stl trend tail", fs(stl.trend.to_numpy()[-3:]), "seasonal tail", fs(stl.seasonal.to_numpy()[-3:]))
ses = SimpleExpSmoothing(co2.to_numpy(), initialization_method="known", initial_level=float(co2.iloc[0])).fit(smoothing_level=0.3, optimized=False)
print("simple exponential smoothing forecast", fs(ses.forecast(2)))

x = np.linspace(0.0, 6.0, 60)
y = np.sin(x) + 0.1 * np.cos(7 * x)
print("lowess", fs(lowess(y, x, frac=0.3, it=2)[[0, 30, 59], 1]))
kde = sm.nonparametric.KDEUnivariate(a)
kde.fit(bw=0.5, gridsize=64)
print("kde density at grid 0, 32", f(kde.density[0]), f(kde.density[32]))
