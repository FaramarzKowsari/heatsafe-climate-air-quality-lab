# %%
import pandas as pd
from heatsafe.core.models import ClimateRecord
from heatsafe.core.climate import analyze_climate_trend
frame=pd.read_csv("../data/synthetic/climate_daily.csv")
records=[ClimateRecord(**row) for row in frame.to_dict(orient="records")]
result=analyze_climate_trend(records)
print(result.ols_slope_c_per_decade,result.bootstrap_ci_c_per_decade)
