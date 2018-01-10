"""
Microsimulation base class - common functionality
"""

import ukcensusapi.Nomisweb as Api

class Base(object):
  """
  Microsimulation base class - common functionality
  """

  def __init__(self, region, resolution, cache_dir):
    self.region = region
    self.resolution = resolution
    self.data_api = Api.Nomisweb(cache_dir)

  def get_census_data(self):
    """
    Download/cache census data
    """

    # convert input string to enum
    resolution = self.data_api.GeoCodeLookup[self.resolution]

    if self.region in self.data_api.GeoCodeLookup.keys():
      region_codes = self.data_api.GeoCodeLookup[self.region]
    else:
      region_codes = self.data_api.get_lad_codes(self.region)
    if not region_codes:
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
    dc1117ew = self.data_api.get_data(table, table_internal, query_params)

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
    dc2101ew = self.data_api.get_data(table, table_internal, query_params)

    return (dc1117ew, dc2101ew)
