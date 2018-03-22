""" assignment.py """

import pandas as pd
import numpy as np


class Assignment:
  """
  Assignment of people (narrow detail at low geog resolution) to households (broad detail at high geog resolution)
  """

  # Treat under 18s as dependent children
  ADULT_AGE = 18

  def __init__(self, region, year, strictmode, data_dir):

    #Common.Base.__init__(self, region, resolution, cache_dir)
    self.region = region
    self.year = year

    # write pop back to
    self.output_dir = data_dir

    h_file = data_dir + "/ssm_hh_" + region + "_OA11_" + str(year) + ".csv"
    p_file = data_dir + "/ssm_" + region + "_MSOA11_" + str(year) + ".csv"

    self.h_data = pd.read_csv(h_file, index_col="HID")

    self.p_data = pd.read_csv(p_file, index_col="PID")

    # index of household in persons table
    self.p_data["HID"] = pd.Series(-1, self.p_data.index)
    # index of HRP(person) in household table
    self.h_data["HRPID"] = pd.Series(-1, self.h_data.index)
    # flag to indicate if household is complete 
    self.h_data["FILLED"] = pd.Series(False, self.h_data.index)

    self.strictmode = strictmode
    if self.strictmode:
      print("Strict assignment mode IGNORED - assignment will fail if not enough people in any category of the sample population")
    else:
      print("Relaxed assignment mode - assignment will sample as many people as it can in any category of the sample population")
      
    #print(h_data.head())
    #print(p_data.head())

    # get OA<->MSOA mapping
    self.geog_lookup = pd.read_csv("../../Mistral/persistent_data/oa2011codes.csv")

    # distributions of various people by age/sex/ethnicity from microdata
    self.hrp_dist = pd.read_csv("./data/hrp_dist.csv")
    self.partner_hrp_dist = pd.read_csv("./data/partner_hrp_dist.csv")

    # make it deterministic
    np.random.seed(12345)

  def run(self):
    """
    Run the sequence
    """

    eths = self.h_data.LC4202EW_C_ETHHUK11.unique()
    #eths = [eths[1]]
    #print(eths)
    # we have different eth resolution in the (micro)datasets
    eth_mapping = {-1:-1, 2:2, 3:3, 4:4, 5:4, 7:5, 8:5, 9:5, 10:5, 12:6, 13:6, 14:6, 15:6, 16:6, 18:7, 19:7, 20:7, 22:8, 23:8}
#    self.p_data.replace({"DC2101EW_C_ETHPUK11": eth_mapping})
    # TODO rename column to be clear categories are now microdata ones
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

      # LC4408_C_AHTHUK11
      # "1": "One person household",                                   1 adult, 0 children
      # "2": "Married or same-sex civil partnership couple household", 2 adults, >=0 children
      # "3": "Cohabiting couple household",                            2 adults, >=0 children
      # "4": "Lone parent household",                                  1 adults, >0 children
      # "5": "Multi-person household"                                  >2 adults >=0 children

      # sample couples using weights - hetero low age diff same eth bias

      # sample children based on eth(s) of parents

      for eth in eths:
        if eth < 0:
          continue

        print("eth", eth)

        self.__sample_hrp_by_eth(msoa, oas, eth)

        # mark single-occupant houses as filled
        h1_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4202EW_C_ETHHUK11 == eth) & (self.h_data.LC4408_C_AHTHUK11 == 1)].index
        self.h_data.loc[h1_ref, "FILLED"] = True

        # # mark 2 person couple households as filled 
        # h2only_ref = self.h_data.loc[(self.h_data.Area.isin(oas)) 
        #                    & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
        #                    & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
        #                    & (self.h_data.LC4404EW_C_SIZHUK11 == 2)
        #                    & (self.h_data.FILLED == False)].index

        # self.h_data.loc[h2only_ref, "FILLED"] = True

        # # Add a child to couple households of size 3 and mark filled
        # self.__sample_child(msoa, oas, eth, 3)
        # # Add a second child to couple households of size 4+
        # self.__sample_child(msoa, oas, eth, 4, mark_filled=False) # 4 means "4 or more"

        # self.__sample_single_parent_child(msoa, oas, eth, 2)
        # self.__sample_single_parent_child(msoa, oas, eth, 3)
        # self.__sample_single_parent_child(msoa, oas, eth, 4, mark_filled=False) # 4 means "4 or more"
        
        #self.__stats()

      # fill multi-person residences
      # self.__fill_multi(msoa, oas, 2)
      # self.__fill_multi(msoa, oas, 3)
      # self.__fill_multi(msoa, oas, 4, mark_filled=False)

      self.__stats()
      self.__sample_partner(msoa, oas)
      self.__stats()

      h_file = self.output_dir + "/ass_hh_" + self.region + "_OA11_" + str(self.year) + ".csv"
      p_file = self.output_dir + "/ass_" + self.region + "_MSOA11_" + str(self.year) + ".csv"
      self.p_data.to_csv("pass.csv")
      self.h_data.to_csv("hass.csv")

      self.check()

  def __sample_hrp_by_eth(self, msoa, oas, eth):
    # get all the households in the area with a HRP of this eth 
    h_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
                          & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
                          & (self.h_data.FILLED == False)].index

    n_hh = len(h_ref)

    if n_hh == 0:
      return

    # sample from microdata distribution of HRPs for this eth
    hrp_eth_dist= self.hrp_dist.loc[self.hrp_dist.ethhuk11==eth]
    hrp_sample = hrp_eth_dist.sample(n_hh, weights=hrp_eth_dist.n, replace=True).index

    #print(hrp_sample)
    
    # now assign HRPs from the population with the sampled age/sex/eth characteristics
    h_index = 0
    for sample_idx in hrp_sample:

      #print("sample_idx",sample_idx)
      sex = hrp_eth_dist.loc[sample_idx, "sex"]
      age = hrp_eth_dist.loc[sample_idx, "age"]

      #print(sample_idx, age, sex, eth)

      p_ref = self.p_data.loc[(self.p_data.Area == msoa)
                            & (self.p_data.DC1117EW_C_AGE == age)
                            & (self.p_data.DC1117EW_C_SEX == sex) 
                            & (self.p_data.DC2101EW_C_ETHPUK11 == eth)
                            & (self.p_data.HID == -1)].index

      # get closest fit if no exact
      if len(p_ref) == 0:
        p_ref = self.get_closest_match(msoa, age, sex, eth)
     
      if len(p_ref) == 0:
        print("not found:", age, sex, eth) #, hrp_eth_dist[sample_idx])
      else: # just take first available person
        self.p_data.loc[p_ref[0], "HID"] = h_ref[h_index]
        self.h_data.loc[h_ref[h_index], "HRPID"] = p_ref[0]

      h_index += 1

  # TODO generalise, or be explicit about what its matching closest to
  def get_closest_match(self, msoa, age, sex, eth):
    # remove age then find closest
    p_ref = self.p_data.loc[(self.p_data.Area == msoa)
                          & (self.p_data.DC1117EW_C_SEX == sex) 
                          & (self.p_data.DC2101EW_C_ETHPUK11 == eth)
                          & (self.p_data.HID == -1)].index

    if len(p_ref) == 0:
      return []
    diffs = abs(self.p_data.loc[p_ref].DC1117EW_C_AGE - age)

    # return as array
    return [diffs.idxmin()]

  # def __sample_partner_by_eth(self, msoa, oas, eth):
  #   # resample adults for non-single adult households (might need to/should relax ethnicity)
  #   p2_ref = self.p_data.loc[(self.p_data.Area == msoa) 
  #                         & (self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) # 18 actually means 17, so this IS 18 or over
  #                         & (self.p_data.DC2101EW_C_ETHPUK11 == eth)
  #                         & (self.p_data.HID == -1)].index

  #   h2_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
  #                       & (self.h_data.LC4202EW_C_ETHHUK11 == eth)
  #                       & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
  #                       & (self.h_data.FILLED == False)].index

  #   n_hh = len(h2_ref)
  #   if len(p2_ref) < n_hh:
  #     if self.strictmode:
  #       raise RuntimeError("error: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
  #     else:
  #       #warnings.warn("warning: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
  #       print("warning: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
  #       n_hh = len(p2_ref)
  #     #continue
    
  #   # mark people as assigned
  #   p2_sample = np.random.choice(p2_ref, n_hh, replace=False)
  #   self.p_data.loc[p2_sample, "HID"] = h2_ref[0:n_hh] # TODO remove [0:n_hh]?
  #   print("assigned", n_hh, "adults")

  def __sample_partner(self, msoa, oas):

    # get all couple households in area
    h2_ref = self.h_data.loc[(self.h_data.Area.isin(oas))
                        & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
                        & (self.h_data.FILLED == False)].index

    # loop over households
    for idx in h2_ref:
      # get HRP
      hrpid = self.h_data.loc[idx,"HRPID"]
      hrp_age = self.p_data.loc[hrpid, "DC1117EW_C_AGE"]
      hrp_sex = self.p_data.loc[hrpid, "DC1117EW_C_SEX"]
      hrp_eth = self.p_data.loc[hrpid, "DC2101EW_C_ETHPUK11"]
      #print(hrp_age, hrp_sex, hrp_eth)
      # sample partner dist for HRP age and ethnicity
      dist = self.partner_hrp_dist.loc[(self.partner_hrp_dist.agehrp == hrp_age)
                                     & (self.partner_hrp_dist.ethhuk11 == hrp_eth)]

      partner_sample = dist.sample(1, weights=dist.n).index
      age = self.partner_hrp_dist.loc[partner_sample, "age"]
      sex = self.partner_hrp_dist.loc[partner_sample, "samesex"]
      # if self.partner_hrp_dist.loc[partner_sample, "samesex"] == True:
      #   sex = hrp_sex
      # else:
      #   sex = 2 - hrp_sex
      eth = self.partner_hrp_dist.loc[partner_sample, "ethnicityew"]
      print(hrp_age, hrp_sex, hrp_eth, "->", age, sex, eth)
                  


    # n_hh = len(h2_ref)
    # if len(p2_ref) < n_hh:
    #   if self.strictmode:
    #     raise RuntimeError("error: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
    #   else:
    #     #warnings.warn("warning: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
    #     print("warning: out of (adult) people with matching ethnicity:" + str(n_hh) + " of " + str(len(p2_ref)))
    #     n_hh = len(p2_ref)
    #   #continue
    
    # # mark people as assigned
    # p2_sample = np.random.choice(p2_ref, n_hh, replace=False)
    # self.p_data.loc[p2_sample, "HID"] = h2_ref[0:n_hh] # TODO remove [0:n_hh]?
    # print("assigned", n_hh, "adults")



  def __sample_single_parent_child(self, msoa, oas, eth, nocc, mark_filled=True):
    # pool of unallocated children of specfic or mixed? enthnicity
    c1_ref = self.p_data.loc[(self.p_data.Area == msoa) 
                           & (self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE) # 18 actually means 17, so this IS 17 or under
                           & (self.p_data.DC2101EW_C_ETHPUK11.isin([eth,5]))
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
                            & (self.p_data.DC2101EW_C_ETHPUK11.isin([eth,5]))
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
                              & (self.h_data.LC4408_C_AHTHUK11.isin([2, 3]))
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
      n_hh = len(p_ref)

    if not n_hh: 
      return

    # mark people as assigned
    p_sample = np.random.choice(p_ref, n_hh, replace=False)
    self.p_data.loc[p_sample, "HID"] = h_ref[0:n_hh]
    print("assigned", n_hh, "multi-person", occupant)

    # mark single-occupant houses as filled
    hf_ref = self.h_data[(self.h_data.Area.isin(oas)) & (self.h_data.LC4408_C_AHTHUK11 == 5) & (self.h_data.LC4404EW_C_SIZHUK11 == occupant)].index
    self.h_data.loc[hf_ref, "FILLED"] = True

  # TODO use microdata rather than rough assumptions about age dist
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
    print("H:", len(self.h_data[self.h_data.FILLED]) / len(self.h_data[self.h_data.LC4408_C_AHTHUK11 > 0]))
    print("P rem:", len(self.p_data[self.p_data.HID == -1]))
    # ignore pylint saying use not/is False - it doesnt work
    print("H rem:", len(self.h_data[(self.h_data.FILLED == False)
                                  & (self.h_data.LC4408_C_AHTHUK11 > 0)]), "(+", len(self.h_data[self.h_data.LC4408_C_AHTHUK11 == -1]), ")")

  def check(self):

    print("CHECKING...")
    print("occupied households not filled", len(self.h_data[(self.h_data.LC4408_C_AHTHUK11 > 0) & (self.h_data.FILLED == False)]), 
      "of", len(self.h_data[self.h_data.LC4408_C_AHTHUK11 > 0]))
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

    print("adults not assigned", len(self.p_data[(self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE) & (self.p_data.HID == -1)]),
      "of", len(self.p_data[self.p_data.DC1117EW_C_AGE > Assignment.ADULT_AGE]))

    print("children not assigned", len(self.p_data[(self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE) & (self.p_data.HID == -1)]),
      "of", len(self.p_data[self.p_data.DC1117EW_C_AGE <= Assignment.ADULT_AGE]))
