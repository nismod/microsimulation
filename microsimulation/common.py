"""
Microsimulation base class - common functionality
"""

import pandas as pd

import ukcensusapi.Nomisweb as Api_ew
import ukcensusapi.NRScotland as Api_sc
import microsimulation.utils as utils

# hack to add gender where Scottish table is not available (pending response from NRScotland)
def _hack_gender(table):
  # hack gender in (TODO microsynthesise from seed?)
  new = table.copy()
  new.OBS_VALUE = (table.OBS_VALUE/2).round().astype(int)
  new["C_SEX"] = 1 
  new_f = table.copy()
  new_f.OBS_VALUE = table.OBS_VALUE - new.OBS_VALUE
  new_f["C_SEX"] = 1
  new = new.append(new_f)
  assert(table.OBS_VALUE.sum() == new.OBS_VALUE.sum())
  print(new[new.C_SEX==1].OBS_VALUE.sum(), new[new.C_SEX==2].OBS_VALUE.sum())
  return new.reset_index(drop=True)

class Base(object):
  """
  Microsimulation base class - common functionality
  """

  def __init__(self, region, resolution, cache_dir):
    self.region = region
    self.resolution = resolution
    self.data_api_en = Api_ew.Nomisweb(cache_dir)
    self.data_api_sc = Api_sc.NRScotland(cache_dir)

  def get_census_data(self):
    if self.region[0] == "S":
      return self.__get_census_data_sc()
    elif self.region[0] == "N":
      raise NotImplementedError("NI support not yet implemented")
    else:
      return self.__get_census_data_ew()

  def __get_census_data_sc(self):

    # disaggregate LAD-level data?
    # age only, no gender
    qs103sc = self.data_api_sc.get_data("QS103SC", "MSOA11", self.region, category_filters={"QS103SC_0_CODE": range(1,102)})

    dc1117sc = _hack_gender(qs103sc)
    dc1117sc.rename(columns={"QS103SC_0_CODE": "C_AGE"}, inplace=True)
    dc1117sc = utils.cap_value(dc1117sc, "C_AGE", 86, "OBS_VALUE")

    # ethnicity
    dc2101sc = _hack_gender(self.data_api_sc.get_data("KS201SC", "MSOA11", self.region, category_filters={"KS201SC_0_CODE": [1,8,9,15,18,22]}))
    dc2101sc.rename(columns={"KS201SC_0_CODE": "C_ETHPUK11"}, inplace=True)
    
    print(dc1117sc.OBS_VALUE.sum(), dc2101sc.OBS_VALUE.sum())

    assert(dc1117sc.OBS_VALUE.sum() == dc2101sc.OBS_VALUE.sum())
    # dc6206sc = self.data_api_sc.get_data("DC6206SC", "MSOA11", self.region)
    raise NotImplementedError("Problem with MSOA-level detailed characteristics in Scottish census data")

#    print(dc1117sc.C_AGE.unique())

    return (dc1117sc, dc2101sc, None)

  def __get_census_data_ew(self):
    """
    Download/cache census data
    """

    # convert input string to enum
    resolution = self.data_api_en.GeoCodeLookup[self.resolution]

    if self.region in self.data_api_en.GeoCodeLookup.keys():
      region_codes = self.data_api_en.GeoCodeLookup[self.region]
    else:
      region_codes = self.data_api_en.get_lad_codes(self.region)
    if not region_codes:
      raise ValueError("no regions match the input: \"" + self.region + "\"")

    area_codes = self.data_api_en.get_geo_codes(region_codes, resolution)

    # Census: sex by age by MSOA
    table = "DC1117EW"
    query_params = {"MEASURES": "20100",
                    "date": "latest",
                    "C_AGE": "1...86",
                    "select": "GEOGRAPHY_CODE,C_SEX,C_AGE,OBS_VALUE",
                    "C_SEX": "1,2",
                    "geography": area_codes}

    # problem - data only available at MSOA and above
    dc1117ew = self.data_api_en.get_data(table, query_params)

    # Census: sex by ethnicity by MSOA
    table = "DC2101EW"
    query_params = {"MEASURES": "20100",
                    "date": "latest",
                    "C_AGE": "0",
                    "C_ETHPUK11": "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23",
                    "select": "GEOGRAPHY_CODE,C_SEX,C_ETHPUK11,OBS_VALUE",
                    "C_SEX": "1,2",
                    "geography": area_codes}
    # problem - data only available at MSOA and above
    dc2101ew = self.data_api_en.get_data(table, query_params)

    # This table contains only 16+ persons (under-16s do not have NS-SeC)
    table = "DC6206EW" 
    query_params = {"date": "latest",
                    "MEASURES": "20100",
                    "C_SEX": "1,2",
                    "C_ETHPUK11": "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23",
                    "C_NSSEC": "2...9,11,12,14,15,16",
                    "C_AGE": "1,2,3,4",
                    "select": "GEOGRAPHY_CODE,C_SEX,C_ETHPUK11,C_NSSEC,C_AGE,OBS_VALUE",
                    "geography": area_codes}
    dc6206ew = self.data_api_en.get_data(table, query_params)

    return (dc1117ew, dc2101ew, dc6206ew)

  def append_children(self, full_table, adults_table):
    """
      Append adult-only (16+) table (e.g DC6206) with children from full population table
    """
    # remember "17" census value means age 16
    children_table = full_table[full_table.C_AGE < 17].copy()
    children_table["C_NSSEC"] = 100 # 

    # rename DC6206 C_AGE (band) so as not to conflict with DC1117 C_AGE (single year)
    adults_table = adults_table.rename(columns={"C_AGE": "C_AGEBAND"})

    x = pd.concat([adults_table, children_table], axis=0, ignore_index=True)
    assert full_table.OBS_VALUE.sum() == x.OBS_VALUE.sum()
    return x

