"""
Microsimulation by a sequence of microsynthesised populations
"""
import pandas as pd
#from random import randint

#import humanleague as hl
import ukpopulation.snhpdata as SNHPData 
import microsimulation.utils as Utils

class SequentialMicrosynthesisH:
  """
  Static microsimulation based on a sequence of microsyntheses
  Performs a sequence of static microsyntheses using census data as a seed populations and mid-year-estimates as marginal
  constraints. This is the simplest microsimulation model and is intended as a comparison/calibration for Monte-Carlo
  based microsimulation
  """

  # Define the year that SNPP was based on (assumeds can then project to SNPP_YEAR+25)
  
  def __init__(self, region, resolution, cache_dir, upstream_dir, input_dir, output_dir):

    self.region = region
    self.resolution = resolution
    self.upstream_dir = upstream_dir
    self.input_dir = input_dir
    self.output_dir = output_dir

    self.scotland = False
    if self.region[0] == "S":
      self.scotland = True

    # load the subnational household projections
    self.snhpdata = SNHPData.SNHPData(cache_dir)
    # old way (needed for pre-2014/6 data for Wales/Scotland/NI)
    if not self.scotland:
      self.snhp_fallback = pd.read_csv(self.input_dir + "/snhp2014.csv", index_col="AreaCode")
    else:
      self.snhp_fallback = pd.read_csv(self.input_dir + "/snhp2016_sc.csv", index_col="GEOGRAPHY_CODE")

    # load the output from the microsynthesis (census 2011 based)
    self.base_population = self.__get_base_populationdata()

  def run(self, base_year, target_year):
    """
    Run the sequence
    """
    census_occ = len(self.base_population[self.base_population.LC4402_C_TYPACCOM > 0])
    census_all = len(self.base_population)
    print("Base population (census-all):", census_all)
    print("Base population (census-occ):", census_occ)
    print("SNHP availability: %d-%d" % (self.snhpdata.min_year(self.region), self.snhpdata.max_year(self.region)))
    #print(self.snhp.head())
    basepop = int(self.__get_snhp(base_year))
    print("SNHP base population (occ):", basepop, "(", basepop / census_occ - 1, ")")

    # occupancy factor - proportion of dwellings that are occupied by housholds
    # assume this proportion stays roughly constant over the simulation period
    occupancy_factor = census_occ / census_all
    print("Occupancy factor: ", occupancy_factor) 

    # we sample 1-dissolution_rate WITH REPLACEMENT to preserve this proportion of the population
    # then sample the remainder without replacement to represent newly formed households
    dissolution_rate = 0.01
    print("Dissolution rate: ", dissolution_rate) 
    

    if target_year < base_year:
      raise ValueError("2001 is the earliest supported target year")

    if target_year > self.snhpdata.max_year(self.region):
      raise ValueError("%d is the current latest supported end year" % self.snhpdata.max_year(self.region))

    # if self.fast_mode:
    #   print("Running in fast mode. Rounded IPF populations may not exactly match the marginals")

    print("Starting microsynthesis sequence...")

    population = self.base_population.copy()

    for year in Utils.year_sequence(base_year, target_year):
      out_file = self.output_dir + "/ssm_hh_" + self.region + "_" + self.resolution + "_" + str(year) + ".csv"
      # this is inconsistent with the household microsynth (batch script checks whether output exists)
      # TODO make them consistent?
      # With dynamic update of seed for now just recompute even if file exists
      print("Generating ", out_file, " [SNHP]", "... ",
            sep="", end="", flush=True)
      # workaround for pre-projection years
      pop = int(self.__get_snhp(year) / occupancy_factor)

      # 1-dissolution_rate applied to existing population
      persisting = int(len(population) * (1.0 - dissolution_rate))
      sample = population.sample(n=persisting, replace=False)
      # TODO how to deal with housing shrinkage?
      if pop > persisting:
        newlyformed = population.sample(n=pop-persisting, replace=False)
        sample = sample.append(newlyformed, ignore_index=True)
      # append with ignore_index means steps below not necessary
      # drop the old index column (which is no longer the index)
      #sample = sample.reset_index().drop(columns=['HID']) # ,'index'
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

    # if failures and not self.fast_mode:
    #   print("\n".join(failures))
    #   raise RuntimeError("Consistency checks failed, see log for further details")

  def __get_snhp(self, year):
    """
    Fetches subnational household projection data (mostly 2016-based) as a backup for missing years before the proection data starts 
    England data starts in 2011 so not a problem, 
    """
    if year >= self.snhpdata.min_year(self.region) and year <= self.snhpdata.max_year(self.region):
      return self.snhpdata.aggregate(self.region, year).OBS_VALUE[0]
    else:
      return self.snhp_fallback.loc[self.region, str(year)]

  def __get_base_populationdata(self):
    """
    Loads the microsynthesised household base population
    Assumes csv file in upstream_dir, prefixed by "hh_" 
    """
    filename = self.upstream_dir + "/hh_" + self.region + "_" + self.resolution + "_2011.csv"
    data=pd.read_csv(filename, index_col="HID")
    print("Loaded base population from " + filename)
    #print(self.base_population.head())
    return data
