"""
Microsimulation by a sequence of microsynthesised populations
"""
import numpy as np
import pandas as pd
#from random import randint

import humanleague as hl
import ukpopulation.nppdata as nppdata
import ukpopulation.snppdata as snppdata
import ukpopulation.myedata as myedata
import microsimulation.utils as Utils
import microsimulation.common as Common

class SequentialMicrosynthesis(Common.Base):
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal
  constraints. This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo
  based microsimulation
  """

  def __init__(self, region, resolution, variant, cache_dir="./cache", output_dir="./data", fast_mode=False):

    Common.Base.__init__(self, region, resolution, cache_dir)

    self.output_dir = output_dir
    self.fast_mode = fast_mode
    self.variant = variant

    # init the population (projections) modules
    self.mye_api = myedata.MYEData(cache_dir)
    self.npp_api = nppdata.NPPData(cache_dir)
    self.snpp_api = snppdata.SNPPData(cache_dir)

    # validation
    if not self.variant in nppdata.NPPData.VARIANTS:
      raise ValueError(self.variant + " is not a known projection variant")
    if not isinstance(self.fast_mode, bool):
      raise ValueError("fast mode should be boolean")

    # TODO enable 2001 ref year?
    # (down)load the census 2011 tables
    self.__get_census_data()

  def run(self, ref_year, target_year):
    """
    Run the sequence
    """

    # TODO enable 2001 ref year?

    if ref_year != 2011:
      raise ValueError("(census) reference year must be 2011")

    if target_year < 2001:
      raise ValueError("2001 is the earliest supported target year")

    if target_year > self.npp_api.max_year():
      raise ValueError(str(self.npp_api.max_year()) + " is the current latest supported end year")

    if self.fast_mode:
      print("Running in fast mode. Rounded IPF populations may not exactly match the marginals")

    print("Starting microsynthesis sequence...")
    for year in Utils.year_sequence(ref_year, target_year):
      out_file = self.output_dir + "/ssm_" + self.region + "_" + self.resolution + "_" + self.variant + "_" + str(year) + ".csv"
      # this is inconsistent with the household microsynth (batch script checks whether output exists)
      # TODO make them consistent?
      # With dynamic update of seed for now just recompute even if file exists
      #if not os.path.isfile(out_file):
      if year < self.snpp_api.min_year(self.region):
        source = " [MYE]"
      elif year <= self.snpp_api.max_year(self.region):  
        source = " [SNPP]"
      else:
        source = " [XNPP]"
      print("Generating ", out_file, source, "... ",
            sep="", end="", flush=True)
      msynth = self.__microsynthesise(year)
      print("OK")
      msynth.to_csv(out_file, index_label="PID")

  def __microsynthesise(self, year): #LAD=self.region

    # Census/seed proportions for geography and ethnicity
    oa_prop = self.seed.sum((1, 2, 3)) / self.seed.sum()
    eth_prop = self.seed.sum((0, 1, 2)) / self.seed.sum()

    if year < self.snpp_api.min_year(self.region):
      age_sex = Utils.create_age_sex_marginal(Utils.adjust_pp_age(self.mye_api.filter(year, self.region)), self.region)
    elif year <= self.npp_api.max_year():
      # Don't attempt to apply NPP variant if before the start of the NPP data
      if year < self.npp_api.min_year():
        age_sex = Utils.create_age_sex_marginal(Utils.adjust_pp_age(self.snpp_api.filter(self.region, year)), self.region)
      else:
        age_sex = Utils.create_age_sex_marginal(Utils.adjust_pp_age(self.snpp_api.create_variant(self.variant, self.npp_api, self.region, year)), self.region)
    else:
      raise ValueError("Cannot microsimulate past NPP horizon year ({})", self.npp_api.max_year())

    # convert proportions/probabilities to integer frequencies
    oa = hl.prob2IntFreq(oa_prop, age_sex.sum())["freq"]
    eth = hl.prob2IntFreq(eth_prop, age_sex.sum())["freq"]
    # combine the above into a 2d marginal using QIS-I and census 2011 or later data as the seed
    oa_eth = hl.qisi(self.seed.sum((1, 2)), [np.array([0]), np.array([1])], [oa, eth])
    if not (isinstance(oa_eth, dict) and oa_eth["conv"]):
      raise RuntimeError("oa_eth did not converge")

    # now the full seeded microsynthesis
    if self.fast_mode:
      msynth = hl.ipf(self.seed, [np.array([0, 3]), np.array([1, 2])], [oa_eth["result"].astype(float), age_sex.astype(float)])
    else:
      msynth = hl.qisi(self.seed, [np.array([0, 3]), np.array([1, 2])], [oa_eth["result"], age_sex])
    if not msynth["conv"]:
      print(msynth)
      raise RuntimeError("msynth did not converge")
    #print(msynth["pop"])
    if self.fast_mode:
      print("updating seed to", year, " ", end="")
      self.seed = msynth["result"]
      msynth["result"] = np.around(msynth["result"]).astype(int)
    else:
      print("updating seed to", year, " ", end="")
      self.seed = msynth["result"].astype(float)
    rawtable = hl.flatten(msynth["result"]) #, c("OA", "SEX", "AGE", "ETH"))

    # col names and remapped values
    table = pd.DataFrame(columns=["Area", "DC1117EW_C_SEX", "DC1117EW_C_AGE", "DC2101EW_C_ETHPUK11"])
    table.Area = Utils.remap(rawtable[0], self.geog_map)
    table.DC1117EW_C_SEX = Utils.remap(rawtable[1], [1, 2])
    table.DC1117EW_C_AGE = Utils.remap(rawtable[2], range(1, 87))
    table.DC2101EW_C_ETHPUK11 = Utils.remap(rawtable[3], self.eth_map)

    # consistency checks (in fast mode just report discrepancies)
    self.__check(table, age_sex, oa_eth["result"])

    return table

  def __check(self, table, age_sex, oa_eth):

    failures = []

    # check area totals
    areas = oa_eth.sum(1)
    for i in range(0, len(areas)):
      if len(table[table.Area == self.geog_map[i]]) != areas[i]:
        failures.append("Area " + self.geog_map[i] + " total mismatch: "
                        + str(len(table[table.Area == self.geog_map[i]])) + " vs " + str(areas[i]))

    # check ethnicity totals
    eths = oa_eth.sum(0)
    for i in range(0, len(eths)):
      if len(table[table.DC2101EW_C_ETHPUK11 == self.eth_map[i]]) != eths[i]:
        failures.append("Ethnicity " + str(self.eth_map[i]) + " total mismatch: "
                        + str(len(table[table.DC2101EW_C_ETHPUK11 == self.eth_map[i]])) + " vs " + str(eths[i]))

    # check gender and age totals
    for sex in [0, 1]:
      for age in range(0, 86):
        #print( len(table[(table.DC1117EW_C_SEX == s+1) & (table.DC1117EW_C_AGE == a+1)]), age_sex[s,a])
        if len(table[(table.DC1117EW_C_SEX == sex+1) & (table.DC1117EW_C_AGE == age+1)]) != age_sex[sex, age]:
          failures.append("Age-gender " + str(age+1) + "/" + str(sex+1) + " total mismatch: "
                          + str(len(table[(table.DC1117EW_C_SEX == sex+1) & (table.DC1117EW_C_AGE == age+1)]))
                          + " vs " + str(age_sex[sex, age]))

    if failures and not self.fast_mode:
      print("\n".join(failures))
      raise RuntimeError("Consistency checks failed, see log for further details")

  def __get_census_data(self):

    (dc1117ew, dc2101ew, dc6206ew) = self.get_census_data()

    # add children to adult-only table
    #dc6206ew_adj = self.append_children(dc1117ew, dc6206ew)
    # For now we drop NS-SEC (not clear if needed)
    dc6206ew_adj = None

    self.geog_map = dc1117ew.GEOGRAPHY_CODE.unique()
    self.eth_map = dc2101ew.C_ETHPUK11.unique()
    #self.nssec_map = dc6206ew_adj.C_NSSEC.unique()

    # TODO seed with microdata
    self.cen11 = Utils.microsynthesise_seed(dc1117ew, dc2101ew, dc6206ew_adj)

    # seed defaults to census 11 data, updates as simulate past 2011
    self.seed = self.cen11.astype(float)

