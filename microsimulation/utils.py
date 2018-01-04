# utility functions

import numpy as np
import pandas as pd
import humanleague as hl

def create_age_sex_marginal(mye, lad):
  # TODO remove gender and age size hard-coding...
  tmp = mye[mye.GEOGRAPHY_CODE==lad].drop("GEOGRAPHY_CODE", axis=1)
  marginal = unlistify(tmp, ["GENDER", "AGE"], [2,86], "OBS_VALUE")
  return marginal

# this is a copy-paste from household_microsynth
def unlistify(table, columns, sizes, values):
  """
  Converts an n-column table of counts into an n-dimensional array of counts 
  """
  pivot = table.pivot_table(index=columns, values=values)
  # order must be same as column order above
  a = np.zeros(sizes, dtype=int)
  a[pivot.index.labels] = pivot.values.flat
  return a

# this is a copy-paste from household_microsynth
def remap(indices, mapping):
  """
  Converts array of index values back into category values
  """
  values = []
  for i in range(0,len(indices)):
    values.append(mapping[indices[i]])
  return values


def adjust_mye_age(mye):
  """ 
  Makes mid-year estimate data conform with census age categories:
  - subtract 100 from age (so that "1" means under 1)
  - aggregate 86,87,88,89,90,91 into 86 (meaning 85+)
  """
  # keep track of some totals
  pop = mye.OBS_VALUE.sum()
  popM = mye[mye.GENDER==1].OBS_VALUE.sum()
  popA = mye[mye.GEOGRAPHY_CODE=="E06000015"].OBS_VALUE.sum()

  mye.AGE -= 100

  myeAdj = mye[mye.AGE<86].copy()
  myeOver85 = mye[mye.AGE>85].copy()

  #print(myeOver85.head(12))

  agg85 = myeOver85.pivot_table(index=["GEOGRAPHY_CODE","GENDER"], values="OBS_VALUE", aggfunc=sum)
  agg85["AGE"] = 86
  agg85 = agg85.reset_index()

  myeAdj = myeAdj.append(agg85)
  
  # ensure the totals in the adjusted table match the originals
  assert myeAdj.OBS_VALUE.sum() == pop
  assert myeAdj[myeAdj.GENDER==1].OBS_VALUE.sum() == popM
  assert myeAdj[myeAdj.GEOGRAPHY_CODE=="E06000015"].OBS_VALUE.sum() == popA

  return myeAdj

def microsynthesise(DC1117EW, DC2101EW):

    n_geog = len(DC1117EW.GEOGRAPHY_CODE.unique())
    n_sex = len(DC1117EW.C_SEX.unique())
    n_age = len(DC1117EW.C_AGE.unique())
    cen11sa = unlistify(DC1117EW, ["GEOGRAPHY_CODE","C_SEX","C_AGE"], [n_geog,n_sex,n_age], "OBS_VALUE")

    n_eth = len(DC2101EW.C_ETHPUK11.unique())
    cen11se = unlistify(DC2101EW, ["GEOGRAPHY_CODE","C_SEX","C_ETHPUK11"], [n_geog,n_sex,n_eth], "OBS_VALUE")

    # microsynthesise these two into a 4D seed (if this has a lot of zeros can have big impact on microsim)
    print("Synthesising seed population...", end='')
    msynth = hl.qis([np.array([0,1,2]),np.array([0,1,3])], [cen11sa, cen11se])
    assert msynth["conv"]
    print("OK")
    return msynth["result"]

