"""
Microsimulation by a sequence of microsynthesised populations
"""
import numpy as np
import pandas as pd
#from random import randint

import humanleague as hl
import microsimulation.utils as Utils
import microsimulation.common as Common

class SequentialMicrosynthesis(Common.Base):
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal
  constraints. This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo
  based microsimulation
  """

  # Define the year that SNPP was based on (assumeds can then project to SNPP_YEAR+25)
  SNPP_YEAR = 2014

  def __init__(self, region, resolution, cache_dir="./cache", output_dir="./data", fast_mode=False):

    Common.Base.__init__(self, region, resolution, cache_dir)

    self.output_dir = output_dir
    self.fast_mode = fast_mode

    # (down)load the mid-year estimates
    self.__get_mye_data()

    # load the subnational population projections
    self.__get_snpp_data()

    # TODO enable 2001 ref year
    # (down)load the census 2011 tables
    self.__get_census_data()

  def run(self, ref_year, target_year):
    """
    Run the sequence
    """

    # TODO enable 2001 ref year
    # if ref_year != 2001 or ref_year != 2011:
    #   raise ValueError("(census) reference year must be either 2001 or 2011")

    if ref_year != 2011:
      raise ValueError("(census) reference year must be 2011")

    if target_year < 2001:
      raise ValueError("2001 is the earliest supported target year")

    if target_year > SequentialMicrosynthesis.SNPP_YEAR + 25:
      raise ValueError(str(SequentialMicrosynthesis.SNPP_YEAR + 25) + " is the current latest supported end year")

    if self.fast_mode:
      print("Running in fast mode. Rounded IPF populations may not exactly match the marginals")

    print("Starting microsynthesis sequence...")
    for year in Utils.year_sequence(ref_year, target_year):
      out_file = self.output_dir + "/ssm_" + self.region + "_" + self.resolution + "_" + str(year) + ".csv"
      # this is inconsistent with the household microsynth (batch script checks whether output exists)
      # TODO make them consistent?
      # With dynamic update of seed for now just recompute even if file exists
      #if not os.path.isfile(out_file):
      print("Generating ", out_file, " [MYE] " if year < SequentialMicrosynthesis.SNPP_YEAR else " [SNPP]", "... ",
            sep="", end="", flush=True)
      msynth = self.__microsynthesise(year)
      print("OK")
      msynth.to_csv(out_file)
      # else:
      #   print("Already exists:", out_file)
      #   if year > 2011:
      #     # TODO load file, pivot and use as seed
      #     print("Warning: not using latest population as seed")

  def __microsynthesise(self, year): #LAD=self.region

    # Census/seed proportions for geography and ethnicity
    oa_prop = self.seed.sum((1, 2, 3)) / self.seed.sum()
    eth_prop = self.seed.sum((0, 1, 2)) / self.seed.sum()

    if year < self.SNPP_YEAR:
      age_sex = Utils.create_age_sex_marginal(self.mye[year], self.region, "OBS_VALUE")
    else:
      age_sex = Utils.create_age_sex_marginal(self.snpp, self.region, "X"+str(year))

    # convert proportions/probabilities to integer frequencies
    oa = hl.prob2IntFreq(oa_prop, age_sex.sum())["freq"]
    eth = hl.prob2IntFreq(eth_prop, age_sex.sum())["freq"]
    # combine the above into a 2d marginal using QIS-I and census 2011 or later data as the seed
    oa_eth = hl.qisi(self.seed.sum((1, 2)), [np.array([0]), np.array([1])], [oa, eth])
    if not (isinstance(oa_eth, dict) and oa_eth["conv"]):
      raise RuntimeError("oa_eth did not converge")

    # now the full seeded microsynthesis
    if self.fast_mode:
      msynth = hl.ipf(self.seed, [np.array([0, 3]), np.array([1, 2])], [oa_eth["result"].astype(float),
                                                                                       age_sex.astype(float)])
    else:
      msynth = hl.qisi(self.seed, [np.array([0, 3]), np.array([1, 2])], [oa_eth["result"], age_sex])
    if not msynth["conv"]:
      raise RuntimeError("msynth did not converge")

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

  def __get_mye_data(self):
    """
    Gets Mid-year population estimate data for 2001-2016
    Single year of age by gender by geography, at Local Authority scale
    """
    table_internal = "NM_2002_1" # 2016-based MYE
    query_params = {
      "gender": "1,2",
      "age": "101...191",
      "MEASURES": "20100",
      "select": "geography_code,gender,age,obs_value",
      "geography": "1879048193...1879048573,1879048583,1879048574...1879048582"
    }

    # store as a dictionary keyed by year
    self.mye = {}

    query_params["date"] = "latestMINUS15"
    self.mye[2001] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS14"
    self.mye[2002] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS13"
    self.mye[2003] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS12"
    self.mye[2004] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS11"
    self.mye[2005] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS10"
    self.mye[2006] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS9"
    self.mye[2007] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS8"
    self.mye[2008] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS7"
    self.mye[2009] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS6"
    self.mye[2010] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS5"
    self.mye[2011] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS4"
    self.mye[2012] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS3"
    self.mye[2013] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS2"
    self.mye[2014] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latestMINUS1"
    self.mye[2015] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))
    query_params["date"] = "latest"
    self.mye[2016] = Utils.adjust_mye_age(self.data_api.get_data(table_internal, query_params))

  def __get_snpp_data(self):
    """
    Loads preprocessed raw subnational population projection data (currently 2014-based)
    Download from: https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationprojections/datasets/localauthoritiesinenglandz1/2014based/snppz1population.zip
    See the R script scripts/preprocess_snpp.R
    """
    # TODO download from nomisweb? (NM_2006_1 - 2014-based SNPPs)
    self.snpp = pd.read_csv(self.data_api.cache_dir + "snpp" + str(SequentialMicrosynthesis.SNPP_YEAR) + ".csv")
