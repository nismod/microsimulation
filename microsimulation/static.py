import numpy as np
import pandas as pd
#from random import randint

import ukcensusapi.Nomisweb as Api
import humanleague as hl
import microsimulation.utils as Utils

class SequentialMicrosynthesis:
  """
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal constraints
  This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo based microsimulation
  """

  def __init__(self, region, resolution, cache_dir = "./cache"):
    self.data_api = Api.Nomisweb(cache_dir)

    self.region = region
    # convert input string to enum
    self.resolution = resolution

    # (down)load the census 2011 tables
    self.__get_census_data()

    # (down)load the mid-year estimates 
    self.__get_mye_data()

  def run(self, startYear, endYear):

    if startYear > endYear:
      raise ValueError("end year must be greater than or equal to start year")

    if startYear < 2001:
      raise ValueError("2001 is the earliest supported start year")
      
    if endYear > 2016:
      raise ValueError("2016 is the current latest supported end year")

    for y in range(startYear, endYear+1):
      print(y)

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

    # cen11sa = xtabs(OBS_VALUE~GEOGRAPHY_CODE+C_SEX+C_AGE, DC1117EW)
    # cen11se = xtabs(OBS_VALUE~GEOGRAPHY_CODE+C_SEX+C_ETHPUK11, DC2101EW)

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
    self.mye[2001] = self.data_api.get_data("MYE01EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS14"
    self.mye[2002] = self.data_api.get_data("MYE02EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS13"
    self.mye[2003] = self.data_api.get_data("MYE03EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS12"
    self.mye[2004] = self.data_api.get_data("MYE04EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS11"
    self.mye[2005] = self.data_api.get_data("MYE05EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS10"
    self.mye[2006] = self.data_api.get_data("MYE06EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS9"
    self.mye[2007] = self.data_api.get_data("MYE07EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS8"
    self.mye[2008] = self.data_api.get_data("MYE08EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS7"
    self.mye[2009] = self.data_api.get_data("MYE09EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS6"
    self.mye[2010] = self.data_api.get_data("MYE10EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS5"
    self.mye[2011] = self.data_api.get_data("MYE11EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS4"
    self.mye[2012] = self.data_api.get_data("MYE12EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS3"
    self.mye[2013] = self.data_api.get_data("MYE13EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS2"
    self.mye[2014] = self.data_api.get_data("MYE14EW", table_internal, queryParams)
    queryParams["date"] = "latestMINUS1"
    self.mye[2015] = self.data_api.get_data("MYE15EW", table_internal, queryParams)
    queryParams["date"] = "latest"
    self.mye[2016] = self.data_api.get_data("MYE16EW", table_internal, queryParams)

    adjust_mye_age(self.mye[2016])
    #self.mye[2016].to_csv("mye.csv")

def adjust_mye_age(myedata):
  total = myedata.OBS_VALUE.sum()
  print(total)
  myedata.AGE -= 100
  #print(myedata.head())
  to_aggregate = myedata[myedata.AGE >= 86].copy()
  myedata = myedata[myedata.AGE < 86].copy()

  agg = to_aggregate.pivot_table(index=["GEOGRAPHY_CODE","GENDER"], values="OBS_VALUE", aggfunc=sum)
  print(agg)
  # remove age column
  #to_aggregate = to_aggregate.drop('AGE', axis=1)
  # aggregate by geog/gender
  # to_aggregate["AGE"] = 86
  # to_aggregate = to_aggregate.groupby(["GEOGRAPHY_CODE","GENDER"]).sum()
  # print(to_aggregate)

  agg.reset_index(level=["GEOGRAPHY_CODE","GENDER"])

  #to_aggregate = to_aggregate.AGE.replace(531, 86)
  #print(to_aggregate.head())

  myedata = myedata.append(agg)

  myedata.to_csv("mye.csv")


# # Knock MYE data into shape
# adjustMyeAge = function(df) {
  
#   # check we preserve the correct total
#   total = sum(df$OBS_VALUE)
  
#   df$AGE = df$AGE - 100
  
#   # merge ages 85+ 
#   df[df$AGE==86,]$OBS_VALUE = df[df$AGE==86,]$OBS_VALUE + df[df$AGE==87,]$OBS_VALUE + df[df$AGE==88,]$OBS_VALUE +
#                               df[df$AGE==89,]$OBS_VALUE + df[df$AGE==90,]$OBS_VALUE + df[df$AGE==91,]$OBS_VALUE
#   # remove now-duplicated rows
#   df = df[df$AGE<87,]
  
#   # check total is preserved
#   stopifnot(sum(df$OBS_VALUE) == total)
  
#   return(df)
# }


# createAgeSexMarginal = function(df, LAD) {
#   marginal = xtabs(OBS_VALUE~GENDER+AGE, df[df$GEOGRAPHY_CODE==LAD,])
#   return(marginal)
# }
  #def create_age_sex_marginal(self, data, lad):
  #  marginal = Utils.unlistify(data, data.columns, )


# mye01 = adjustMyeAge(mye01)
# mye02 = adjustMyeAge(mye02)
# mye03 = adjustMyeAge(mye03)
# mye04 = adjustMyeAge(mye04)
# mye05 = adjustMyeAge(mye05)
# mye06 = adjustMyeAge(mye06)
# mye07 = adjustMyeAge(mye07)
# mye08 = adjustMyeAge(mye08)
# mye09 = adjustMyeAge(mye09)
# mye10 = adjustMyeAge(mye10)
# mye11 = adjustMyeAge(mye11)
# mye12 = adjustMyeAge(mye12)
# mye13 = adjustMyeAge(mye13)
# mye14 = adjustMyeAge(mye14)
# mye15 = adjustMyeAge(mye15)
# mye16 = adjustMyeAge(mye16)

# nLADs = length(unique(mye12$GEOGRAPHY_CODE))

# # Now have consistent estimates for 2011-2016 by gender by age by LAD

# oaProp = apply(cen11, 1, sum) / sum(cen11)
# ethProp = apply(cen11, 4, sum) / sum(cen11)
