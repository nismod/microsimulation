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
      pass

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

    # assignment does shallow copy, need to use .copy() to avoid this getting query_params fields
    common_params = {"MEASURES": "20100",
                    "date": "latest",
                    "geography": area_codes}

    # LC4402EW - Accommodation type by type of central heating in household by tenure
    table = "NM_887_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_CENHEATHUK11"] = "1,2"
    query_params["C_TYPACCOM"] = "2...5"
    query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_CENHEATHUK11,C_TYPACCOM,OBS_VALUE"
    self.lc4402 = self.data_api.get_data("LC4402EW", table, query_params)

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
