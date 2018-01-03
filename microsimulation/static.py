import numpy as np
import pandas as pd
#from random import randint

import ukcensusapi.Nomisweb as Api
import humanleague as hl
import microsimulation.utils as Utils
import microsimulation.common as Common

class SequentialMicrosynthesis(Common.Base):
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal constraints
  This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo based microsimulation
  """

  def __init__(self, region, resolution, cache_dir = "./cache", output_dir = "./data"):

    Common.Base.__init__(self, region, resolution, cache_dir)

    self.output_dir = output_dir

    # (down)load the mid-year estimates 
    self.__get_mye_data()

    # (down)load the census 2011 tables
    self.__get_census_data()

  def run(self, startYear, endYear):

    if startYear > endYear:
      raise ValueError("end year must be greater than or equal to start year")

    if startYear < 2001:
      raise ValueError("2001 is the earliest supported start year")
      
    if endYear > 2016:
      raise ValueError("2016 is the current latest supported end year")

    # Census 2011 proportions for geography and ethnicity
    oaProp = self.cen11.sum((1,2,3)) / self.cen11.sum()
    ethProp = self.cen11.sum((0,1,2)) / self.cen11.sum()

    print("Starting microsynthesis sequence...")
    for y in range(startYear, endYear+1):
      out_file = self.output_dir + "/ssm_" + self.region + "_" + self.resolution + "_" + str(y) + ".csv"
      print("Generating ", out_file, "... ", sep="", end="", flush=True)
      # TODO check file doesnt exist here? or in the script?
      msynth = self.__microsynthesise(y, oaProp, ethProp)
      print("OK")
      msynth.to_csv(out_file)

      #write.csv(msynth, "../data/SSM.csv", row.names = F)

  def __microsynthesise(self, year, oaProp, ethProp): #LAD=self.region

    age_sex = Utils.create_age_sex_marginal(self.mye[year], self.region) 

    # convert proportions/probabilities to integer frequencies
    oa = hl.prob2IntFreq(oaProp, age_sex.sum())["freq"]
    eth = hl.prob2IntFreq(ethProp, age_sex.sum())["freq"]
    # combine the above into a 2d marginal using QIS-I and census 2011 data as the seed
    oa_eth = hl.qisi(self.cen11.sum((1,2)).astype(float), [np.array([0]),np.array([1])], [oa, eth])
    assert oa_eth["conv"]

    # now the full seeded microsynthesis
    msynth = hl.qisi(self.cen11.astype(float), [np.array([0,3]),np.array([1,2])], [oa_eth["result"], age_sex])
    assert msynth["conv"]
    rawtable = hl.flatten(msynth["result"]) #, c("OA", "SEX", "AGE", "ETH"))
    # TODO col names and remapped values
    table = pd.DataFrame(columns=["Area","DC1117EW_C_SEX","DC1117EW_C_AGE","DC2101EW_C_ETHPUK11"])
    table.Area = Utils.remap(rawtable[0], self.geog_map)
    table.DC1117EW_C_SEX = Utils.remap(rawtable[1], [1,2])
    table.DC1117EW_C_AGE = Utils.remap(rawtable[2], range(1,87))
    table.DC2101EW_C_ETHPUK11 = Utils.remap(rawtable[3], self.eth_map)

#   check = humanleague::ipf(cen11, list(c(1,4),c(2,3)), list(oa_eth$result, age_sex))
    # consistency checks 
    self.__check(table, age_sex, oa_eth["result"], year)
    return table    

  def __check(self, table, age_sex, oa_eth, year):
    # check area totals
    areas = oa_eth.sum(1)
    for i in range(0,len(areas)):
      assert len(table[table.Area == self.geog_map[i]]) == areas[i]

    # check ethnicity totals
    eths = oa_eth.sum(0)
    for i in range(0,len(eths)):
      assert len(table[table.DC2101EW_C_ETHPUK11 == self.eth_map[i]]) == eths[i]
    
    # check gender and age totals
    for s in [0,1]:
      for a in range(0,86):
        #print( len(table[(table.DC1117EW_C_SEX == s+1) & (table.DC1117EW_C_AGE == a+1)]), age_sex[s,a])
        assert len(table[(table.DC1117EW_C_SEX == s+1) & (table.DC1117EW_C_AGE == a+1)]) == age_sex[s,a]

  def __get_census_data(self):

    (DC1117EW, DC2101EW) = self.get_census_data()

    self.geog_map = DC1117EW.GEOGRAPHY_CODE.unique()
    self.eth_map = DC2101EW.C_ETHPUK11.unique()

    n_geog = len(DC1117EW.GEOGRAPHY_CODE.unique())
    n_sex = len(DC1117EW.C_SEX.unique())
    n_age = len(DC1117EW.C_AGE.unique())
    cen11sa = Utils.unlistify(DC1117EW, ["GEOGRAPHY_CODE","C_SEX","C_AGE"], [n_geog,n_sex,n_age], "OBS_VALUE")

    n_eth = len(DC2101EW.C_ETHPUK11.unique())
    cen11se = Utils.unlistify(DC2101EW, ["GEOGRAPHY_CODE","C_SEX","C_ETHPUK11"], [n_geog,n_sex,n_eth], "OBS_VALUE")

    # microsynthesise these two into a 4D seed (if this has a lot of zeros can have big impact on microsim)
    print("Synthesising seed population...", end='')
    msynth = hl.qis([np.array([0,1,2]),np.array([0,1,3])], [cen11sa, cen11se])
    assert msynth["conv"]
    print("OK")
    # TODO more checks?
    self.cen11 = msynth["result"]

  def __get_mye_data(self):
    """
    Gets Mid-year population estimate data for 2001-2016
    Single year of age by gender by geography, at Local Authority scale
    """

    table_internal = "NM_2002_1"
    queryParams = {
      "gender": "1,2",
      "age": "101...191",
      "MEASURES": "20100",
      "select": "geography_code,gender,age,obs_value",
      "gender": "1,2",
      "geography": "1879048193...1879048573,1879048583,1879048574...1879048582"
    }

    # store as a dictionary keyed by year
    self.mye = {}

    queryParams["date"] = "latestMINUS15"
    self.mye[2001] = Utils.adjust_mye_age(self.data_api.get_data("MYE01EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS14"
    self.mye[2002] = Utils.adjust_mye_age(self.data_api.get_data("MYE02EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS13"
    self.mye[2003] = Utils.adjust_mye_age(self.data_api.get_data("MYE03EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS12"
    self.mye[2004] = Utils.adjust_mye_age(self.data_api.get_data("MYE04EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS11"
    self.mye[2005] = Utils.adjust_mye_age(self.data_api.get_data("MYE05EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS10"
    self.mye[2006] = Utils.adjust_mye_age(self.data_api.get_data("MYE06EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS9"
    self.mye[2007] = Utils.adjust_mye_age(self.data_api.get_data("MYE07EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS8"
    self.mye[2008] = Utils.adjust_mye_age(self.data_api.get_data("MYE08EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS7"
    self.mye[2009] = Utils.adjust_mye_age(self.data_api.get_data("MYE09EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS6"
    self.mye[2010] = Utils.adjust_mye_age(self.data_api.get_data("MYE10EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS5"
    self.mye[2011] = Utils.adjust_mye_age(self.data_api.get_data("MYE11EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS4"
    self.mye[2012] = Utils.adjust_mye_age(self.data_api.get_data("MYE12EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS3"
    self.mye[2013] = Utils.adjust_mye_age(self.data_api.get_data("MYE13EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS2"
    self.mye[2014] = Utils.adjust_mye_age(self.data_api.get_data("MYE14EW", table_internal, queryParams))
    queryParams["date"] = "latestMINUS1"
    self.mye[2015] = Utils.adjust_mye_age(self.data_api.get_data("MYE15EW", table_internal, queryParams))
    queryParams["date"] = "latest"
    self.mye[2016] = Utils.adjust_mye_age(self.data_api.get_data("MYE16EW", table_internal, queryParams))



