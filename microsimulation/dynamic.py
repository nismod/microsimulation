"""
Dynamic Microsimulation (Monte-Carlo based projection of population)
"""

#import numpy as np
import pandas as pd
#from random import randint

#import ukcensusapi.Nomisweb as Api
import humanleague as hl
import microsimulation.utils as Utils
import microsimulation.common as Common

class Microsimulation(Common.Base):
  """
  Dynamic MC microsimulation
  Performs a sequence of 1y timesteps evolving the population randomly according to prescribed rates of fertility,
  mortality and migration
  """
  def __init__(self, region, resolution, cache_dir="./cache", output_dir="./data"):

    Common.Base.__init__(self, region, resolution, cache_dir)

    self.output_dir = output_dir

    # load fertility by LAD by age by eth
    # load mortality by LAD by sex by age by eth
    # load migration by LAD by age
    # TODO UK-wide data (temporarily using Tower Hamlets data only)
    fertility_table = pd.read_csv("./persistent_data/tmp_fertility.csv")
    mortality_table = pd.read_csv("./persistent_data/tmp_mortality.csv")

    print(fertility_table.head())
    print(mortality_table.head())
    n_age = len(fertility_table.Age.unique())
    n_eth = len(fertility_table.Ethnicity.unique())
    n_sex = len(fertility_table.Sex.unique())

    self.fertility = Utils.unlistify(fertility_table, ["Age", "Ethnicity", "Sex"], [n_age, n_eth, n_sex], "Rate")
    print(self.fertility)
    self.mortality = Utils.unlistify(mortality_table, ["Sex", "Age", "Ethnicity"], [n_sex, n_age, n_eth], "Rate")
    print(self.mortality)

    (dc1117ew, dc2101ew, dc6206ew) = self.get_census_data()
    
    # TODO NS-SeC ...

    self.geog_map = dc1117ew.GEOGRAPHY_CODE.unique()
    self.eth_map = dc2101ew.C_ETHPUK11.unique()

    msynth = Utils.microsynthesise_seed(dc1117ew, dc2101ew, dc6206ew)

    rawtable = hl.flatten(msynth) #, c("OA", "SEX", "AGE", "ETH"))
    # col names and remapped values
    self.msim = pd.DataFrame(columns=["Area", "DC1117EW_C_SEX", "DC1117EW_C_AGE", "DC2101EW_C_ETHPUK11"])
    self.msim.Area = Utils.remap(rawtable[0], self.geog_map)
    self.msim.DC1117EW_C_SEX = Utils.remap(rawtable[1], [1, 2])
    self.msim.DC1117EW_C_AGE = Utils.remap(rawtable[2], range(1, 87))
    self.msim.DC2101EW_C_ETHPUK11 = Utils.remap(rawtable[3], self.eth_map)


  def run(self, start_year, end_year):
    """
    Project the population
    """

    # TODO resolve how to deal with pre-2011 years (2001 data)
    if start_year > end_year:
      raise ValueError("end year must be greater than or equal to start year")

    if start_year < 2001:
      raise ValueError("2001 is the earliest supported start year")

    if end_year > 2016:
      raise ValueError("2016 is the current latest supported end year")

    print("Starting microsimulation...")
    for year in range(start_year, end_year+1):
      out_file = self.output_dir + "/msim_" + self.region + "_" + self.resolution + "_" + str(year) + ".csv"
      print("Generating ", out_file, "... ", sep="", end="", flush=True)
      # TODO check file doesnt exist here? or in the script?
      self.msim = self.__timestep(self.msim)
      print("OK")
      self.msim.to_csv(out_file)
    #print(self.msynth)
    # print(self.resolution)

  # Timestepping (1y hard-coded)
  def __timestep(self, msim):
    # TODO
    n = len(msim)

    return msim
