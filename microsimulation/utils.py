# utility functions

import numpy as np
import pandas as pd


# this is a copy-paste from household_microsynth
def unlistify(table, columns, sizes, values):
  pivot = table.pivot_table(index=columns, values=values)
  # order must be same as column order above
  a = np.zeros(sizes, dtype=int)
  a[pivot.index.labels] = pivot.values.flat
  return a

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

