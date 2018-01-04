\
import numpy as np
import pandas as pd
#from random import randint

import ukcensusapi.Nomisweb as Api

class Base(object):

  def __init__(self, region, resolution, cache_dir):
    self.region = region
    self.resolution = resolution
    self.data_api = Api.Nomisweb(cache_dir)

  # this is a copy-paste from static.py, factor into utils or a common base class
  def get_census_data(self):

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

    return (DC1117EW, DC2101EW)

  
  # def microsynthesise(self, DC1117EW, DC2101EW):

  #   n_geog = len(DC1117EW.GEOGRAPHY_CODE.unique())
  #   n_sex = len(DC1117EW.C_SEX.unique())
  #   n_age = len(DC1117EW.C_AGE.unique())
  #   cen11sa = Utils.unlistify(DC1117EW, ["GEOGRAPHY_CODE","C_SEX","C_AGE"], [n_geog,n_sex,n_age], "OBS_VALUE")

  #   n_eth = len(DC2101EW.C_ETHPUK11.unique())
  #   cen11se = Utils.unlistify(DC2101EW, ["GEOGRAPHY_CODE","C_SEX","C_ETHPUK11"], [n_geog,n_sex,n_eth], "OBS_VALUE")

  #   # microsynthesise these two into a 4D seed (if this has a lot of zeros can have big impact on microsim)
  #   print("Synthesising seed population...", end='')
  #   msynth = hl.qis([np.array([0,1,2]),np.array([0,1,3])], [cen11sa, cen11se])
  #   assert msynth["conv"]
  #   print("OK")
  #   return msynth["result"]

  