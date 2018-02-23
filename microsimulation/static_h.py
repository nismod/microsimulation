"""
Microsimulation by a sequence of microsynthesised populations
"""
import os.path
import numpy as np
import pandas as pd
#from random import randint

import humanleague as hl
import microsimulation.utils as Utils
import microsimulation.common as Common

class SequentialMicrosynthesisH:
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal
  constraints. This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo
  based microsimulation
  """

  # Define the year that SNPP was based on (assumeds can then project to SNPP_YEAR+25)
  SNHP_YEAR = 2014

  def __init__(self, region, resolution, upstream_dir, input_dir, output_dir, fast_mode=False):

    self.region = region
    self.resolution = resolution
    self.upstream_dir = upstream_dir
    self.input_dir = input_dir
    self.output_dir = output_dir
    self.fast_mode = fast_mode

    # load the subnational household projections
    self.__get_snhp_data()


  def run(self, base_year, target_year):
    """
    Run the sequence
    """
    # (down)load the census 2011 tables
    self.__get_base_populationdata()

    census_occ = len(self.base_population[self.base_population.LC4402_C_TYPACCOM > 0])
    census_all = len(self.base_population)
    print("Base population: ", census_all) 

    # occupancy factor - proportion of dwellings that are occupied by housholds
    # assume this proportion stays roughly constant over the simulation period
    occupancy_factor = census_occ / census_all
    print("Occupancy factor: ", occupancy_factor) 

    print(self.snhp.loc[self.region, str(base_year)] / census_occ)

    if target_year < base_year:
      raise ValueError("2001 is the earliest supported target year")

    if target_year > SequentialMicrosynthesisH.SNHP_YEAR + 25:
      raise ValueError(str(SequentialMicrosynthesisH.SNHP_YEAR + 25) + " is the current latest supported end year")

    if self.fast_mode:
      print("Running in fast mode. Rounded IPF populations may not exactly match the marginals")

    print("Starting microsynthesis sequence...")

    #population = self.base_population.copy()

    for year in Utils.year_sequence(base_year, target_year):
      out_file = self.output_dir + "/ssm_hh_" + self.region + "_" + self.resolution + "_" + str(year) + ".csv"
      # this is inconsistent with the household microsynth (batch script checks whether output exists)
      # TODO make them consistent?
      # With dynamic update of seed for now just recompute even if file exists
      #if not os.path.isfile(out_file):
      print("Generating ", out_file, " [SNHP]", "... ",
            sep="", end="", flush=True)
      pop = int(self.snhp.loc[self.region, str(year)] / occupancy_factor)

      # crude sampling for now (perhaps quasirandom sampling within humanleague)
      # note we sample the census population, it is not updated to the previous year's sample
      sample = self.base_population.sample(n=pop, replace=True)
      #msynth = self.__microsynthesise(year)
      print("OK")
      sample.to_csv(out_file)
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

  def __get_snhp_data(self):
    """
    Loads preprocessed raw subnational household projection data (currently 2014-based)
    """
    self.snhp = pd.read_csv(self.input_dir + "snhp" + str(SequentialMicrosynthesisH.SNHP_YEAR) + ".csv")
    self.snhp = self.snhp.set_index("AreaCode")
    #print(self.snhp.head())

  def __get_base_populationdata(self):
    """
    Loads the microsynthesised household base population
    Assumes csv file in upstream_dir, prefixed by "hh_" 
    """
    filename = self.upstream_dir + "hh_" + self.region + "_" + self.resolution + ".csv"
    self.base_population=pd.read_csv(filename)
    print("Loaded base population from " + filename)
    #print(self.base_population.head())

