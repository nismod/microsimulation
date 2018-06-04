
import pandas as pd

years = range(2011,2051)

lad = "E07000041"
projs = ["ppp", "hhh"]

for year in years:
  filep = "./data/ssm_" + lad + "_MSOA11_" + projs[0] + "_" + str(year) + ".csv"
  fileh = "./data/ssm_" + lad + "_MSOA11_" + projs[1] + "_" + str(year) + ".csv"
  dfp = pd.read_csv(filep)
  dfh = pd.read_csv(fileh)
  print(year, len(dfp), len(dfh))