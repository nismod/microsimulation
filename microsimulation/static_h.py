"""
Microsimulation by a sequence of microsynthesised populations
"""
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

    for year in Utils.year_sequence(base_year, target_year):
      out_file = self.output_dir + "/ssm_hh_" + self.region + "_" + self.resolution + "_" + str(year) + ".csv"
      # this is inconsistent with the household microsynth (batch script checks whether output exists)
      # TODO make them consistent?
      # With dynamic update of seed for now just recompute even if file exists
      print("Generating ", out_file, " [SNHP]", "... ",
            sep="", end="", flush=True)
      pop = int(self.snhp.loc[self.region, str(year)] / occupancy_factor)

      # crude sampling for now (perhaps quasirandom sampling within humanleague)
      # note we sample the census population, it is not updated to the previous year's sample
      sample = self.base_population.sample(n=pop, replace=True)
      # drop the old index column (which is no longer the index)
      sample = sample.reset_index().drop(columns=['HID','index'])
      self.__check(sample)
      #msynth = self.__microsynthesise(year)
      print("OK")
      sample.to_csv(out_file, index_label="HID")

  def __check(self, sample):

    failures = []

    # # check area totals
    # areas = self.base_population.Area.unique()
    # for a in areas:
    #   print(a, len(self.base_population[self.base_population.Area == a]), len(sample[sample.Area == a]))

    # # check type totals
    # categories = self.base_population.LC4402_C_TYPACCOM.unique()
    # for cat in categories:
    #   print(cat, len(self.base_population[self.base_population.LC4402_C_TYPACCOM == cat]), len(sample[sample.LC4402_C_TYPACCOM == cat]))

    # # check tenure totals
    # categories = self.base_population.LC4402_C_TENHUK11.unique()
    # for cat in categories:
    #   print(cat, len(self.base_population[self.base_population.LC4402_C_TENHUK11 == cat]), len(sample[sample.LC4402_C_TENHUK11 == cat]))

    if failures and not self.fast_mode:
      print("\n".join(failures))
      raise RuntimeError("Consistency checks failed, see log for further details")

  def __get_snhp_data(self):
    """
    Loads preprocessed raw subnational household projection data (currently 2014-based)
    """
    self.snhp = pd.read_csv(self.input_dir + "/snhp" + str(SequentialMicrosynthesisH.SNHP_YEAR) + ".csv")
    self.snhp = self.snhp.set_index("AreaCode")
    #print(self.snhp.head())

  def __get_base_populationdata(self):
    """
    Loads the microsynthesised household base population
    Assumes csv file in upstream_dir, prefixed by "hh_" 
    """
    filename = self.upstream_dir + "/hh_" + self.region + "_" + self.resolution + ".csv"
    self.base_population=pd.read_csv(filename)
    print("Loaded base population from " + filename)
    #print(self.base_population.head())

