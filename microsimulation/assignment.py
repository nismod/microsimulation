""" assignment.py """

import pandas as pd
import numpy as np


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

    eths = self.h_data.LC4202EW_C_ETHHUK11.unique()
    print(eths)
    # we have different eth resolution in the datasets
    eth_mapping = { -1:-1, 2:2, 3:3, 4:4, 5:4, 7:5, 8:5, 9:5, 10:5, 12:6, 13:6, 14:6, 15:6, 16:6, 18:7, 19:7, 20:7, 22:8, 23:8 }
#    self.p_data.replace({"DC2101EW_C_ETHPUK11": eth_mapping})
    self.p_data.DC2101EW_C_ETHPUK11.replace(eth_mapping, inplace=True)
    print(self.p_data.DC2101EW_C_ETHPUK11.unique())
    #assert len(eths) == len(self.p_data.DC2101EW_C_ETHPUK11.unique())


    self.p_data["HID"] = pd.Series(-1, self.p_data.index)
    self.h_data["FILLED"] = pd.Series(False, self.p_data.index)

    msoas = self.p_data.Area.unique()

    for msoa in msoas:
      oas = self.geog_lookup[self.geog_lookup.msoa==msoa].oa.values

      print(msoa + ":", oas)

      for eth in eths:
        if eth < 0: continue

        # to ensure we dont inadvertently modify a copy rather than the original data just use index
        h_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4202EW_C_ETHHUK11 == eth)].index

        p_ref = self.p_data.loc[(self.p_data.Area==msoa) & (self.p_data.DC1117EW_C_AGE > 16) & (self.p_data.DC2101EW_C_ETHPUK11 == eth)].index

        # assign persons to houses
        p_sample = np.random.choice(p_ref, len(h_ref), replace=False)

        self.p_data.loc[p_sample, "HID"] = h_ref

        #print(len(h_ref))
        #print(len(p_ref))
        #print(len(p_sample))

      # mark single-occupant houses as filled
      h_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4408_C_AHTHUK11 == 1)].index
      self.h_data.loc[h_ref, "FILLED"] = True

      print("P:", len(self.p_data[self.p_data.HID>0]) / len(self.p_data))
      print("H:", len(self.h_data[self.h_data.FILLED]) / len(self.h_data))
      print("P rem:", len(self.p_data[self.p_data.HID==-1]))
      print("H rem:", len(self.h_data[self.h_data.FILLED==False]))

      self.p_data.to_csv("pass.csv")
      self.h_data.to_csv("hass.csv")

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

 #   print(self.p_data.head())


# Selected household ethnicities
# LC4202EW_C_ETHHUK11 = {
#       "2": "White: English/Welsh/Scottish/Northern Irish/British",
#       "3": "White: Irish",
#       "4": "White: Other White",
#       "5": "Mixed/multiple ethnic group",
#       "6": "Asian/Asian British",
#       "7": "Black/African/Caribbean/Black British",
#       "8": "Other ethnic group"
#     }, 
# Selected people ethnicities "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23"
# DC2101EW_C_ETHPUK11 = {
#     "2": "White: English/Welsh/Scottish/Northern Irish/British",
#     "3": "White: Irish",
#     "4": "White: Gypsy or Irish Traveller",
#     "5": "White: Other White",
#     "7": "Mixed/multiple ethnic group: White and Black Caribbean",
#     "8": "Mixed/multiple ethnic group: White and Black African",
#     "9": "Mixed/multiple ethnic group: White and Asian",
#     "10": "Mixed/multiple ethnic group: Other Mixed",
#     "12": "Asian/Asian British: Indian",
#     "13": "Asian/Asian British: Pakistani",
#     "14": "Asian/Asian British: Bangladeshi",
#     "15": "Asian/Asian British: Chinese",
#     "16": "Asian/Asian British: Other Asian",
#     "18": "Black/African/Caribbean/Black British: African",
#     "19": "Black/African/Caribbean/Black British: Caribbean",
#     "20": "Black/African/Caribbean/Black British: Other Black",
#     "22": "Other ethnic group: Arab",
#     "23": "Other ethnic group: Any other ethnic group"

#
