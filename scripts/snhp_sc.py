
import pandas as pd 

snhp = pd.read_csv("raw.csv")

ref = pd.read_csv("./persistent_data/snhp2014.csv")
lookup = pd.read_csv("./persistent_data/sc/COUNCIL AREA 2011 LOOKUP.csv")
print(lookup)

# #snhp = snhp[snhp["Local Authority"] != "Scotland"]
snhp = snhp[snhp.columns].replace({",":""}, regex=True)[snhp.LAD != "Scotland"]
snhp["LAD"] = snhp.LAD.str.strip().replace({"Na h-Eileanan Siar": "Comhairle nan Eilean Siar"})
#snhp["2016"] = snhp["2016"].str.replace(",","")

snhp = snhp.merge(lookup[["CouncilArea2011Code", "CouncilArea2011Name"]], how="left", left_on="LAD", right_on="CouncilArea2011Name")
print(snhp.head())
print(snhp[snhp.LAD != snhp.CouncilArea2011Name])
snhp.drop(["x","y", "CouncilArea2011Name"], axis=1, inplace=True)

print(ref.head())
# for y in range(1991,2016):
#   snhp[str(y)] = None
# print(snhp.columns.values)
#snhp.to_csv("../microsimulation/persistent_data/snhp2016_sc.csv")


print(snhp.head())

# add missing 2011 data from census
from ukcensusapi import NRScotland
api_sc = NRScotland.NRScotland("./cache")
qs116 = api_sc.get_data("QS116SC", "S92000003", "LAD", category_filters={"QS116SC_0_CODE": 0}) \
  .drop("QS116SC_0_CODE", axis=1) \
  .rename({"OBS_VALUE": "2011"}, axis=1)
#print(qs116)
snhp = snhp.merge(qs116, left_on="CouncilArea2011Code", right_on="GEOGRAPHY_CODE").drop("CouncilArea2011Code", axis=1)
# print(snhp.groupby(["Local Authority"]).sum())
# # TODO lookup ONS codes

# print(type(snhp["2011"][0]))
# print(type(snhp["2016"][0]))

delta = (pd.to_numeric(snhp["2016"]) - snhp["2011"]) / 5
for y in range(2012,2016):
  snhp[str(y)] = (delta * (y-2011) + snhp["2011"]).astype(int)

ordered_cols = ['LAD', 'GEOGRAPHY_CODE', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020',
 '2021', '2022', '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030', '2031', '2032', '2033', '2034',
 '2035', '2036', '2037', '2038', '2039', '2040', '2041', 'avg', 'overall', 'overallPct']
snhp = snhp[ordered_cols]
print(snhp.head())
snhp.to_csv("../microsimulation/persistent_data/snhp2016_sc.csv", index=False)

# ref = ref.append(snhp, sort=False)
# print(ref)