import numpy as np
import pandas as pd
#from random import randint

import ukcensusapi.Nomisweb as Api
import humanleague as hl
import microsimulation.utils as Utils

class SequentialMicrosynthesis:
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal constraints
  This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo based microsimulation
  """

  def __init__(self, region, resolution, cache_dir = "./cache"):
    self.data_api = Api.Nomisweb(cache_dir)

    self.region = region
    # convert input string to enum
    self.resolution = resolution

    # (down)load the mid-year estimates 
    # TODO why is e.g. City of London missing
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
      print(y)
      msynth = self.microsynthesise(y, oaProp, ethProp)
      #write.csv(msynth, "../data/SSM.csv", row.names = F)


  def microsynthesise(self, year, oaProp, ethProp): #LAD=self.region
    ageSex = create_age_sex_marginal(self.mye[year], self.region) 

    # convert proportions/probabilities to integer frequencies
    oa = hl.prob2IntFreq(oaProp, ageSex.sum())["freq"]
    eth = hl.prob2IntFreq(ethProp, ageSex.sum())["freq"]
    # combine the above into a 2d marginal using QIS-I and census 2011 data as the seed
    oa_eth = hl.qisi(self.cen11.sum((1,2)).astype(float), [np.array([0]),np.array([1])], [oa, eth])
    assert oa_eth["conv"]

    # now the full seeded microsynthesis
    msynth = hl.qisi(self.cen11.astype(float), [np.array([0,3]),np.array([1,2])], [oa_eth["result"], ageSex])
    print(msynth)
    assert msynth["conv"]
#   check = humanleague::ipf(cen11, list(c(1,4),c(2,3)), list(oa_eth$result, ageSex))

# microsynthesise = function(oaProp, ethProp, mye, LAD, cen) {
  
#   # MYE for LA gives age-sex marginal
#   ageSex = createAgeSexMarginal(mye, LAD)
  
#   # rescale OA & eth marginals according to MYE data and integerising,
#   oa = humanleague::prob2IntFreq(oaProp, sum(ageSex))$freq
#   eth = humanleague::prob2IntFreq(ethProp, sum(ageSex))$freq
#   # combine the above into a 2d marginal using QIS-I
#   oa_eth = humanleague::qisi(apply(cen11, c(1,4), sum), list(1,2), list(oa, eth))
#   stopifnot(oa_eth$conv)
  
#   # 6. apply QISI
#   #msynth = humanleague::qisi(cen11, list(c(1),c(2,3),c(4)), list(oa, ageSex, eth))
#   #msynth = humanleague::qisi(cen11, list(c(1,4),c(2,3)), list(oa_eth$result, ageSex))
#   # Much faster, for testing
#   # is this good enough? (we've captured the geog-eth census11 structure in the oa_eth marginal 
#   # probably not - mean sq error (vs IPF) is ~100x higher than QISI
#   #msynth = humanleague::qis(list(c(1,4),c(2,3)), list(oa_eth$result, ageSex))
#   msynth = humanleague::qisi(cen11, list(c(1,4),c(2,3)), list(oa_eth$result, ageSex))
#   #msynthi = xtabs(~OA+SEX+AGE+ETH, read.csv("../data/Exeter/SSM01.csv",stringsAsFactors = F))
#   check = humanleague::ipf(cen11, list(c(1,4),c(2,3)), list(oa_eth$result, ageSex))
  
#   print(paste("QISI MSE:", sum((msynth$result - check$result)^2)/prod(dim(msynth$result))))
#   #print(paste("QISI MSE:", sum((msynthi - check$result)^2)/prod(dim(msynthi))))
  
#   saved = msynth
#   stopifnot(msynth$conv)
#   table = flatten(msynth$result, c("OA", "SEX", "AGE", "ETH"))

#   checkMicrosynthesis(oa, eth, msynth, table, mye, ageSex) 

#   return(table)
# }

  def __get_census_data(self):

    # convert input string to enum
    resolution = self.data_api.GeoCodeLookup[self.resolution]

    if self.region in self.data_api.GeoCodeLookup.keys():
      region_codes = self.data_api.GeoCodeLookup[self.region]
    else:
      region_codes = self.data_api.get_lad_codes(self.region)
      if not len(region_codes):
        raise ValueError("no regions match the input: \"" + self.region + "\"")

    area_codes = self.data_api.get_geo_codes(region_codes, resolution)
     
    # Census: sex by age by MSOA
    table = "DC1117EW"
    table_internal = "NM_792_1"
    query_params = {"MEASURES": "20100",
                    "date": "latest",
                    "C_AGE": "1...86",
                    "select": "GEOGRAPHY_CODE,C_SEX,C_AGE,OBS_VALUE",
                    "C_SEX": "1,2",
                    "geography": area_codes}

    # problem - data only available at MSOA and above
    DC1117EW = self.data_api.get_data(table, table_internal, query_params)

    # Census: sex by ethnicity by MSOA
    table = "DC2101EW"
    table_internal = "NM_651_1"
    query_params = {"MEASURES": "20100",
                    "date": "latest",
                    "C_AGE": "0",
                    "C_ETHPUK11": "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23",
                    "select": "GEOGRAPHY_CODE,C_SEX,C_ETHPUK11,OBS_VALUE",
                    "C_SEX": "1,2",
                    "geography": area_codes}
    # problem - data only available at MSOA and above
    DC2101EW = self.data_api.get_data(table, table_internal, query_params)

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


def create_age_sex_marginal(mye, lad):
  # TODO remove gender and age size hard-coding...
  tmp = mye[mye.GEOGRAPHY_CODE==lad].drop("GEOGRAPHY_CODE", axis=1)
  marginal = Utils.unlistify(tmp, ["GENDER", "AGE"], [2,86], "OBS_VALUE")
  return marginal


# nLADs = length(unique(mye12$GEOGRAPHY_CODE))

# # Now have consistent estimates for 2011-2016 by gender by age by LAD

# oaProp = apply(cen11, 1, sum) / sum(cen11)
# ethProp = apply(cen11, 4, sum) / sum(cen11)
