# utility functions

import numpy as np
import pandas as pd

# this is a copy-paste from household_microsynth (which doesnt work with later pandas versions)
def unlistify(table, columns, sizes, values):
  pivot = table.pivot_table(index=columns, values=values)
  # order must be same as column order above
  a = np.zeros(sizes, dtype=int)
  a[pivot.index.labels] = pivot.values.flat
  return a


