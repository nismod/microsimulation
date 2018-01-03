import numpy as np
import pandas as pd
#from random import randint

import ukcensusapi.Nomisweb as Api
import humanleague as hl
import microsimulation.utils as Utils
import microsimulation.common as Common

class Microsimulation(Common.Base):
  """
  Dynamic MC microsimulation 
  Performs a sequence of 1y timesteps evolving the population randomly according to prescribed rates of fertility, mortality and migration
  """
  def __init__(self, region, resolution, cache_dir="./cache", output_dir ="./data"):

    # Seriously?
    #super(Microsimulation, self).__init__(region, resolution, cache_dir)
    Common.Base.__init__(self, region, resolution, cache_dir)

    self.output_dir = output_dir

  def run(self, startYear, endYear):

    if startYear > endYear:
      raise ValueError("end year must be greater than or equal to start year")

    if startYear < 2001:
      raise ValueError("2001 is the earliest supported start year")
      
    if endYear > 2016:
      raise ValueError("2016 is the current latest supported end year")

    #super(Microsimulation, self).get_census_data() required for nontrivial inheritance
    (DC1117EW, DC2101EW) = self.get_census_data()

    print(len(DC1117EW))
    print(len(DC2101EW))
    # print(self.resolution)