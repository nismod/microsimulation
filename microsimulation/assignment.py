""" assignment.py """

import pandas as pd
import numpy as np


class Assignment:
  """
  Assignment of people (narrow detail at low geog resolution) to households (broad detail at high geog resolution)
  """

  # Treat under 18s as dependent children
  ADULT_AGE = 18

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

    self.p_data["HID"] = pd.Series(-1, self.p_data.index)
    self.h_data["FILLED"] = pd.Series(False, self.p_data.index)

    #print(h_data.head())
    #print(p_data.head())

    # get OA<->MSOA mapping
    self.geog_lookup = pd.read_csv("../../Mistral/persistent_data/oa2011codes.csv")

    # make it deterministic
    np.random.seed(12345)

  def run(self):
    """
    Run the sequence
    """

    eths = self.h_data.LC4202EW_C_ETHHUK11.unique()
    #eths = [eths[1]]
    #print(eths)
    # we have different eth resolution in the datasets
    eth_mapping = {-1:-1, 2:2, 3:3, 4:4, 5:4, 7:5, 8:5, 9:5, 10:5, 12:6, 13:6, 14:6, 15:6, 16:6, 18:7, 19:7, 20:7, 22:8, 23:8}
#    self.p_data.replace({"DC2101EW_C_ETHPUK11": eth_mapping})
    self.p_data.DC2101EW_C_ETHPUK11.replace(eth_mapping, inplace=True)
    #print(self.p_data.DC2101EW_C_ETHPUK11.unique())
    #assert len(eths) == len(self.p_data.DC2101EW_C_ETHPUK11.unique())

    self.__stats()

    msoas = self.p_data.Area.unique()

    for msoa in msoas:
      oas = self.geog_lookup[self.geog_lookup.msoa == msoa].oa.values

      print(msoa + ":", oas)

      # first fill communal establishments
      self.__fill_communal(msoa, oas)

      for eth in eths:
        if eth < 0:
          continue

        print("eth", eth)

        # to ensure we dont inadvertently modify a copy rather than the original data just use index
        h_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
                              & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                              & (self.h_data.FILLED == False)].index

        if len(h_ref) == 0:
          continue

        # sample adults of the appropriate ethnicity for HRP
        p_ref = self.p_data.loc[(self.p_data.Area == msoa)
                              & (self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) # 18 actually means 17, so this IS 18 or over
                              & (self.p_data.DC2101EW_C_ETHPUK11 == eth)
                              & (self.p_data.HID == -1)].index

        if len(p_ref) == 0:
          continue

        # assign persons to houses
        n_hh = len(h_ref)
        if len(p_ref) < n_hh:
          print("warning: out of (HRP) people with matching ethnicity", n_hh, len(p_ref))
          continue

        # mark people as assigned
        p_sample = np.random.choice(p_ref, n_hh, replace=False)
        self.p_data.loc[p_sample, "HID"] = h_ref[0:n_hh]
        print("assigned", n_hh, "HRPs")

        # mark single-occupant houses as filled
        h1_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4202EW_C_ETHHUK11 == eth) & (self.h_data.LC4408_C_AHTHUK11 == 1)].index
        self.h_data.loc[h1_ref, "FILLED"] = True

        # resample adults for non-single adult households (might need to/should relax ethnicity)
        p2_ref = self.p_data.loc[(self.p_data.Area == msoa) 
                              & (self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) # 18 actually means 17, so this IS 18 or over
                              & (self.p_data.DC2101EW_C_ETHPUK11 == eth)
                              & (self.p_data.HID == -1)].index

        h2_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
                           & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                           & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
                           & (self.h_data.FILLED == False)].index

        n_hh = len(h2_ref)
        if len(p2_ref) < n_hh:
          print("warning: out of (adult) people with matching ethnicity", n_hh, len(p2_ref))
          n_hh = len(p2_ref)
          #continue
        
        # mark people as assigned
        p2_sample = np.random.choice(p2_ref, n_hh, replace=False)
        self.p_data.loc[p2_sample, "HID"] = h2_ref[0:n_hh] # TODO remove [0:n_hh]?
        print("assigned", n_hh, "adults")

        #self.p_data.to_csv("./p_int"+str(eth)+".csv")

        # mark 2 person households as filled 
        h2only_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
                           & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                           & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
                           & (self.h_data.LC4404EW_C_SIZHUK11 == 2)
                           & (self.h_data.FILLED == False)].index

        self.h_data.loc[h2only_ref, "FILLED"] = True

        # Add a child to couple households of size 3 and mark filled
        self.__sample_child(msoa, oas, eth, 3)
        # Add a second child to couple households of size 4+
        self.__sample_child(msoa, oas, eth, 4, mark_filled=False) # 4 means "4 or more"

        self.__sample_single_parent_child(msoa, oas, eth, 2)
        self.__sample_single_parent_child(msoa, oas, eth, 3)
        self.__sample_single_parent_child(msoa, oas, eth, 4, mark_filled=False) # 4 means "4 or more"
        
        #self.__stats()

      # fill multi-person residences
      self.__fill_multi(msoa, oas, 2)
      self.__fill_multi(msoa, oas, 3)
      self.__fill_multi(msoa, oas, 4, mark_filled=False)

      self.__stats()


      # LC4408_C_AHTHUK11
      # "1": "One person household",  1 adult, 0 children
      # "2": "Married or same-sex civil partnership couple household", 2 adults, >=0 children
      # "3": "Cohabiting couple household",                            2 adults, >=0 children
      # "4": "Lone parent household", 1 adults, >0 children
      # "5": "Multi-person household" >2 adults >=0 children

      self.p_data.to_csv("pass.csv")
      self.h_data.to_csv("hass.csv")

      self.check()

  def __sample_single_parent_child(self, msoa, oas, eth, nocc, mark_filled=True):
    # pool of unallocated children of specfic or mixed enthnicity
    c1_ref = self.p_data.loc[(self.p_data.Area == msoa) 
                           & (self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE) # 18 actually means 17, so this IS 17 or under
                           & (self.p_data.DC2101EW_C_ETHPUK11.isin([eth, 5]))
                           & (self.p_data.HID == -1)].index

    # pool of single-parent households of specific ethnicity
    hsp_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
                            & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                            & (self.h_data.LC4408_C_AHTHUK11 == 4)
                            & (self.h_data.FILLED == False)].index

    if len(c1_ref) == 0:
      print("no children found")
      return

    if len(hsp_ref) > 0:

      n_hh = len(hsp_ref)
      if len(c1_ref) < n_hh:
        print("warning: single parent out of (child", nocc-1, ") people with matching ethnicity, need", n_hh, "got", len(c1_ref))
        n_hh = len(c1_ref)
        #return

      print("sampled", n_hh, "children")
      c1_sample = np.random.choice(c1_ref, n_hh, replace=False)
      # mark single-parent houses as filled where nocc reached
      hsp2_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
                              & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                              & (self.h_data.LC4408_C_AHTHUK11 == 4)
                              & (self.h_data.LC4404EW_C_SIZHUK11 == nocc)
                              & (self.h_data.FILLED == False)].index
      if mark_filled:
        self.h_data.loc[hsp2_ref, "FILLED"] = True

      self.p_data.loc[c1_sample, "HID"] = hsp_ref[0:n_hh]


  def __sample_child(self, msoa, oas, eth, nocc, mark_filled=True):
    # sample one child for two-parent households
    c1_ref = self.p_data.loc[(self.p_data.Area == msoa) 
                            & (self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE) # 18 actually means 17, so this IS 17 or under
                            & (self.p_data.DC2101EW_C_ETHPUK11.isin([eth, 5]))
                            & (self.p_data.HID == -1)].index

    if len(c1_ref) > 0:
      hc_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
                              & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                              & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
                              & (self.h_data.FILLED == False)].index

      n_hh = len(hc_ref)
      if len(c1_ref) < n_hh:
        print("warning: out of (child", nocc-2, ") people with matching ethnicity", n_hh, len(c1_ref))
        n_hh = len(c1_ref)
        #return

      c1_sample = np.random.choice(c1_ref, n_hh, replace=False)
      # mark single-occupant houses as filled where nocc = 2
      hocc_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
                              & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                              & (self.h_data.LC4408_C_AHTHUK11 == 4)
                              & (self.h_data.LC4404EW_C_SIZHUK11 == nocc)
                              & (self.h_data.FILLED == False)].index

      if mark_filled:
        self.h_data.loc[hocc_ref, "FILLED"] = True

      self.p_data.loc[c1_sample, "HID"] = hc_ref[0:n_hh]
      print("sampled", n_hh, "children")


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

  #  "QS420EW - Communal establishment management and type - Communal establishments",
  # 2,6,11,14,22...34
  # "2": "Medical and care establishment: NHS: Total",
  # "6": "Medical and care establishment: Local Authority: Total",
  # "11": "Medical and care establishment: Registered Social Landlord/Housing Association: Total",
  # "14": "Medical and care establishment: Other: Total",
  # "22": "Other establishment: Defence",
  # "23": "Other establishment: Prison service",
  # "24": "Other establishment: Approved premises (probation/bail hostel)",
  # "25": "Other establishment: Detention centres and other detention",
  # "26": "Other establishment: Education",
  # "27": "Other establishment: Hotel: guest house; B&B; youth hostel",
  # "28": "Other establishment: Hostel or temporary shelter for the homeless",
  # "29": "Other establishment: Holiday accommodation (for example holiday parks)",
  # "30": "Other establishment: Other travel or temporary accommodation",
  # "31": "Other establishment: Religious",
  # "32": "Other establishment: Staff/worker accommodation only",
  # "33": "Other establishment: Other",
  # "34": "Establishment not stated"
  # assume ages:
  # 2,6,11,14: 75+
  # 22-26: 18-24
  # 27-34: 16+


  def __fill_multi(self, msoa, oas, occupant, mark_filled=True):

    h_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
                         #& (self.h_data.LC4408_C_SIZHUK >= occupant)
                         & (self.h_data.LC4408_C_AHTHUK11 == 5)
                         & (self.h_data.FILLED == False)].index

    p_ref = self.p_data.loc[(self.p_data.Area == msoa)
                          & (self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) # 18 actually means 17, so this IS 18 or over
                          & (self.p_data.HID == -1)].index

    n_hh = len(h_ref)
    if len(p_ref) < n_hh:
      print("warning: out of multi-people, need", n_hh, "got", len(p_ref))

    # mark people as assigned
    p_sample = np.random.choice(p_ref, n_hh, replace=False)
    self.p_data.loc[p_sample, "HID"] = h_ref[0:n_hh]
    print("assigned", n_hh, "multi-person", occupant)

    # mark single-occupant houses as filled
    hf_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4408_C_AHTHUK11 == 5) & (self.h_data.LC4404EW_C_SIZHUK11 == occupant)].index
    self.h_data.loc[hf_ref, "FILLED"] = True

  def __fill_communal(self, msoa, oas):

    # to ensure we dont inadvertently modify a copy rather than the original data just use index
    c_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) & (self.h_data.QS420EW_CELL > -1)].index

    # remember C_AGE=1 means 0
    for index in c_ref:
      ctype = self.h_data.loc[index, "QS420EW_CELL"]
      if ctype < 22:
        p_ref = self.p_data.loc[(self.p_data.Area == msoa) & (self.p_data.HID < 0) & (self.p_data.DC1117EW_C_AGE > 75)].index
      elif ctype < 27:
        p_ref = self.p_data.loc[(self.p_data.Area == msoa) & (self.p_data.HID < 0) & (self.p_data.DC1117EW_C_AGE > 18) & (self.p_data.DC1117EW_C_AGE < 26)].index
      else:
        p_ref = self.p_data.loc[(self.p_data.Area == msoa) & (self.p_data.HID < 0) & (self.p_data.DC1117EW_C_AGE > 16)].index

      nocc = int(self.h_data.loc[index, "CommunalSize"])

      #print("Communal", index, ":", ctype, nocc, "from", len(p_ref))

      # No of occupants can be zero, if so just mark as filled and move on
      if nocc > 0:
        # randomly pick occupants
        p_sample = np.random.choice(p_ref, nocc, replace=False)
        # assing a dwelling ref to people
        self.p_data.loc[p_sample, "HID"] = index
      # mark the communal residence as filled
      self.h_data.loc[index, "FILLED"] = True
      print("assigned", nocc, "communal residents")


  def __stats(self):
    print("P:", len(self.p_data[self.p_data.HID > 0]) / len(self.p_data))
    print("H:", len(self.h_data[self.h_data.FILLED]) / len(self.h_data))
    print("P rem:", len(self.p_data[self.p_data.HID == -1]))
    # ignore pylint saying use not/is False - it doesnt work
    print("H rem:", len(self.h_data[self.h_data.FILLED == False]), "(", len(self.h_data[self.h_data.LC4408_C_AHTHUK11 == -1]), ")")


  def check(self):

    print("CHECKING...")
    print("filled occupied households", len(self.h_data[self.h_data.FILLED == True]), "of", len(self.h_data[self.h_data.LC4408_C_AHTHUK11 > 0]))
    print("communal residences not filled:", len(self.h_data[(self.h_data.CommunalSize >= 0) 
                                                           & (self.h_data.FILLED == False)]))

    print("single-occupant households not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 == 1)
                                                                  & (self.h_data.FILLED == False)]))

    print("single-parent one-child households not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 == 4)
                                                                          & (self.h_data.LC4404EW_C_SIZHUK11 == 2) 
                                                                          & (self.h_data.FILLED == False)]))

    print("single-parent two-child households not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 == 4)
                                                                          & (self.h_data.LC4404EW_C_SIZHUK11 == 3) 
                                                                          & (self.h_data.FILLED == False)]))

    print("single-parent 3+-child households not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 == 4)
                                                                         & (self.h_data.LC4404EW_C_SIZHUK11 == 4) 
                                                                         & (self.h_data.FILLED == False)]))

    print("couple households with no children not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11.isin([2,3])) 
                                                                          & (self.h_data.LC4404EW_C_SIZHUK11 == 2) 
                                                                          & (self.h_data.FILLED == False)]))

    print("couple households with one child not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11.isin([2,3]))
                                                                        & (self.h_data.LC4404EW_C_SIZHUK11 == 3) 
                                                                        & (self.h_data.FILLED == False)]))

    print("couple households with 2+ children not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11.isin([2,3]))
                                                                          & (self.h_data.LC4404EW_C_SIZHUK11 == 4) 
                                                                          & (self.h_data.FILLED == False)]))

    print("mixed households not filled:", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 == 5) 
                                                        & (self.h_data.FILLED == False)]))

    print("adults not assigned", len(self.p_data[(self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) & (self.p_data.HID == -1)]))
    print("children not assigned", len(self.p_data[(self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE) & (self.p_data.HID == -1)]))
