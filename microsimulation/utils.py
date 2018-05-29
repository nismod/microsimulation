"""
utility functions
"""

import argparse
import json
import numpy as np
import humanleague as hl

def get_config():
  parser = argparse.ArgumentParser(description="static sequential (population) microsimulation")

  parser.add_argument("-c", "--config", type=str, metavar="config-file", help="the model configuration file (json). See config/ssm_example.json")
  parser.add_argument("regions", type=str, nargs="+", metavar="LAD", help="ONS code for LAD (multiple LADs can be set).")

  args = parser.parse_args()

  with open(args.config) as config_file:
    params = json.load(config_file)
  # add the regions
  params["regions"] = args.regions
  return params

def relEqual(x, y, tol = 2**-26): 
  """
  Simple test for relative equality of floating point within tolerance
  Default tolerance is sqrt double epsilon i.e. about 7.5 significant figures
  """
  if y == 0:
    return x == 0
  return abs(float(x) / float(y) - 1.) < tol

def create_age_sex_marginal(est, lad):
  """
  Generate age-by-sex marginal from estimated (MYE/SNPP) data
  """
  # TODO remove gender and age size hard-coding...
  tmp = est[est.GEOGRAPHY_CODE == lad].drop("GEOGRAPHY_CODE", axis=1)
  marginal = unlistify(tmp, ["GENDER", "C_AGE"], [2, 86], "OBS_VALUE")
  return marginal

# this is a copy-paste from household_microsynth
def unlistify(table, columns, sizes, values):
  """
  Converts an n-column table of counts into an n-dimensional array of counts
  """
  pivot = table.pivot_table(index=columns, values=values)
  # order must be same as column order above
  array = np.zeros(sizes, dtype=int)
  array[pivot.index.labels] = pivot.values.flat
  return array

# this is a copy-paste from household_microsynth
def remap(indices, mapping):
  """
  Converts array of index values back into category values
  """
  values = []
  for i in range(0, len(indices)):
    values.append(mapping[indices[i]])
  return values


def adjust_mye_age(mye):
  """
  Makes mid-year estimate/snpp data conform with census age categories:
  - subtract 100 from age (so that "1" means under 1)
  - aggregate 86,87,88,89,90,91 into 86 (meaning 85+)
  """
  # keep track of some totals
  pop = mye.OBS_VALUE.sum()
  pop_m = mye[mye.GENDER == 1].OBS_VALUE.sum()
  pop_a = mye[mye.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum()

  mye.C_AGE -= 100

  mye_adj = mye[mye.C_AGE < 86].copy()
  mye_over85 = mye[mye.C_AGE > 85].copy()

  #print(myeOver85.head(12))

  agg86 = mye_over85.pivot_table(index=["GEOGRAPHY_CODE", "GENDER"], values="OBS_VALUE", aggfunc=sum)
  agg86["C_AGE"] = 86
  agg86 = agg86.reset_index()
  agg86.to_csv("wtf.csv")

  mye_adj = mye_adj.append(agg86, ignore_index=True)

  # ensure the totals in the adjusted table match the originals (within precision)
  assert relEqual(mye_adj.OBS_VALUE.sum(), pop)
  assert relEqual(mye_adj[mye_adj.GENDER == 1].OBS_VALUE.sum(), pop_m)
  assert relEqual(mye_adj[mye_adj.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum(), pop_a)

  return mye_adj


def adjust_pp_age(pp):
  """
  Makes (s)npp data conform with census age categories:
  - subtract 100 from age (so that "1" means under 1)
  - aggregate 86,87,88,89,90,91 into 86 (meaning 85+)
  """
  # keep track of some totals
  pop = pp.OBS_VALUE.sum()
  pop_m = pp[pp.GENDER == 1].OBS_VALUE.sum()
  pop_a = pp[pp.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum()

  pp.C_AGE += 1

  mye_adj = pp[pp.C_AGE < 86].copy()
  mye_over85 = pp[pp.C_AGE > 85].copy()

  #print(myeOver85.head(12))

  agg86 = mye_over85.pivot_table(index=["GEOGRAPHY_CODE", "GENDER", "PROJECTED_YEAR_NAME"], values="OBS_VALUE", aggfunc=sum)
  agg86["C_AGE"] = 86
  agg86 = agg86.reset_index()

  mye_adj = mye_adj.append(agg86, ignore_index=True)

  # ensure the totals in the adjusted table match the originals (within precision)
  assert relEqual(mye_adj.OBS_VALUE.sum(), pop)
  assert relEqual(mye_adj[mye_adj.GENDER == 1].OBS_VALUE.sum(), pop_m)
  assert relEqual(mye_adj[mye_adj.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum(), pop_a)

  return mye_adj


def microsynthesise_seed(dc1117ew, dc2101ew, dc6206ew):
  """
  Microsynthesise a seed population from census data
  """
  n_geog = len(dc1117ew.GEOGRAPHY_CODE.unique())
  n_sex = len(dc1117ew.C_SEX.unique())
  n_age = len(dc1117ew.C_AGE.unique())
  cen11sa = unlistify(dc1117ew, ["GEOGRAPHY_CODE", "C_SEX", "C_AGE"], [n_geog, n_sex, n_age], "OBS_VALUE")

  n_eth = len(dc2101ew.C_ETHPUK11.unique())
  cen11se = unlistify(dc2101ew, ["GEOGRAPHY_CODE", "C_SEX", "C_ETHPUK11"], [n_geog, n_sex, n_eth], "OBS_VALUE")

  # TODO use microdata (national or perhaps regional) Mistral/persistent_data/seed_ASE_EW.csv
  # - requires unified age structure

  # microsynthesise these two into a 4D seed (if this has a lot of zeros can have big impact on microsim)
  print("Synthesising 2011 seed population...", end='')
  msynth = hl.qis([np.array([0, 1, 2]), np.array([0, 1, 3])], [cen11sa, cen11se])
  assert msynth["conv"]
  print("OK")
  return msynth["result"]


def year_sequence(start_year, end_year):
  """
  returns a sequence from start_year to end_year inclusive
  year_sequence(2001,2005) = [2001, 2002, 2003, 2004, 2005]
  year_sequence(2005,2001) = [2005, 2004, 2003, 2002, 2001]
  """
  if start_year == end_year:
    return [start_year]

  if start_year < end_year:
    return list(range(start_year, end_year + 1))

  return list(range(start_year, end_year - 1, -1))
