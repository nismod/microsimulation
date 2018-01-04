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

    # load fertility by LAD by age by eth
    # load mortality by LAD by sex by age by eth
    # load migration by LAD by age

  def run(self, startYear, endYear):

    # TODO resolve how to deal with pre-2011 years (2001 data)
    if startYear > endYear:
      raise ValueError("end year must be greater than or equal to start year")

    if startYear < 2001:
      raise ValueError("2001 is the earliest supported start year")
      
    if endYear > 2016:
      raise ValueError("2016 is the current latest supported end year")

    #super(Microsimulation, self).get_census_data() required for nontrivial inheritance
    (DC1117EW, DC2101EW) = self.get_census_data()

    self.geog_map = DC1117EW.GEOGRAPHY_CODE.unique()
    self.eth_map = DC2101EW.C_ETHPUK11.unique()

    self.msynth = Utils.microsynthesise(DC1117EW, DC2101EW)

    # Census 2011 proportions for geography and ethnicity
    oaProp = self.msynth.sum((1,2,3)) / self.msynth.sum()
    ethProp = self.msynth.sum((0,1,2)) / self.msynth.sum()

    print("Starting microsimulation...")
    msim = self.msynth
    for y in range(startYear, endYear+1):
      out_file = self.output_dir + "/msim_" + self.region + "_" + self.resolution + "_" + str(y) + ".csv"
      print("Generating ", out_file, "... ", sep="", end="", flush=True)
      # TODO check file doesnt exist here? or in the script?
      #msim = self.__timestep(msim, oaProp, ethProp)
      print("OK")
      #msim.to_csv(out_file)
    #print(self.msynth)
    # print(self.resolution)