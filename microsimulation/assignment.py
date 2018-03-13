""" assignment.py """

import pandas as pd


class Assignment:
  """
  Assignment of people (narrow detail at low geog resolution) to households (broad detail at high geog resolution)
  """

  # Define the year that SNPP was based on (assumeds can then project to SNPP_YEAR+25)
  SNPP_YEAR = 2014

  def __init__(self, region, year, h_data_dir, p_data_dir):

    #Common.Base.__init__(self, region, resolution, cache_dir)
    self.region = region
    self.year = year

    # write pop back to 
    self.output_dir = p_data_dir

    h_file = h_data_dir + "/hh_" + region + "_OA11_" + str(year) + ".csv"
    p_file = p_data_dir + "/ssm_" + region + "_MSOA11_" + str(year) + ".csv"

    self.h_data = pd.read_csv(h_file, index_col="HID")

    self.p_data = pd.read_csv(p_file, index_col="PID")

    #print(h_data.head())
    #print(p_data.head())

    # get OA<->MSOA mapping
    self.geog_lookup = pd.read_csv("../../Mistral/persistent_data/oa2011codes.csv")


  def run(self):
    """
    Run the sequence
    """

    self.p_data["HID"] = pd.Series(-1, self.p_data.index)



    msoas = self.p_data.Area.unique()
    print(msoas)

    for msoa in msoas:
      oas = self.geog_lookup[self.geog_lookup.msoa==msoa].oa.values

      print(oas)

      # do not want a copy!
      hrps = self.p_data[(self.p_data.Area==msoa) & (self.p_data.DC1117EW_C_AGE > 16)]

      print(hrps.head())

    # for (msoa in msoas) {
    #   oas = lookup[lookup$msoa==msoa,]$oa

    #   hrp = p[Area == msoa & DC1117EW_C_AGE > 16]
      
    #   # dont consider unoccupied dwellings yet
    #   oh = h[h$Area %in% oas & h$LC4408_C_AHTHUK11>0,]
    #   nh = nrow(oh)
      
    #   # sample HRPs
    #   s = hrp[sample(nrow(hrp), nh, replace=F),]
      
    #   for (i in 1:nrow(s)) {
    #     p[p$PID==s[i,]$PID,]$HID = oh[i,]$HID
    #   }
      
    #   # single-occupant households 
    #   #h1 = sample(h[Area %in% oas], nh
    # }

    print(self.p_data.head())
