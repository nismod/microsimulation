"""
utility functions
"""

import argparse
import json
import numpy as np
import pandas as pd
import humanleague as hl

def get_config():
  parser = argparse.ArgumentParser(description="static sequential (population/household) microsimulation")

  parser.add_argument("-c", "--config", required=True, type=str, metavar="config-file", help="the model configuration file (json). See config/*_example.json")
  parser.add_argument("regions", type=str, nargs="+", metavar="LAD", help="ONS code for LAD (multiple LADs can be set).")

  args = parser.parse_args()

  with open(args.config) as config_file:
    params = json.load(config_file)
  # add the regions
  params["regions"] = args.regions
  return params

def relEqual(x, y, tol = 2**-26): 
  """
  Simple test for relative equality of floating point within tolerance
  Default tolerance is sqrt double epsilon i.e. about 7.5 significant figures
  """
  if y == 0:
    return x == 0
  return abs(float(x) / float(y) - 1.) < tol

def create_age_sex_marginal(est, lad):
  """
  Generate age-by-sex marginal from estimated (MYE/SNPP) data
  """
  # TODO remove gender and age size hard-coding...
  tmp = est[est.GEOGRAPHY_CODE == lad].drop("GEOGRAPHY_CODE", axis=1)
  marginal = unlistify(tmp, ["GENDER", "C_AGE"], [2, 86], "OBS_VALUE")
  return marginal

# this is a copy-paste from household_microsynth
def unlistify(table, columns, sizes, values):
  """
  Converts an n-column table of counts into an n-dimensional array of counts
  """
  pivot = table.pivot_table(index=columns, values=values)
  # order must be same as column order above
  array = np.zeros(sizes, dtype=int)
  array[tuple(pivot.index.codes)] = pivot.values.flat
  return array

def listify(array, valuename, colnames):
  """
  converts a multidimensional numpy array into a pandas dataframe with colnames[0] referring to dimension 0, etc
  and valuecolumn containing the array values
  """
  multiindex = pd.MultiIndex.from_product([range(i) for i in array.shape])
  colmapping = {"level_"+str(i): colnames[i] for i in range(len(colnames))}

  return pd.DataFrame({valuename: pd.Series(index=multiindex, data=array.flatten())}).reset_index().rename(colmapping, axis=1)

# this is a copy-paste from household_microsynth
def remap(indices, mapping):
  """
  Converts array of index values back into category values
  """
  # values = []
  # for i in range(0, len(indices)):
  #   values.append(mapping[indices[i]])

  values = [mapping[indices[i]] for i in range(len(indices))]

  return values

def check_and_invert(columns, excluded):
  """
  Returns the subset of column names that is not in excluded
  """
  if isinstance(excluded, str):
    excluded = [excluded]

  included = columns.tolist()
  for exclude in excluded:
    if exclude in included:
      included.remove(exclude)
  return included

# TODO there is a lot of commonality in the 3 functions below
def cap_value(table, colname, maxval, sumcolname):
  """
  Aggregates values in column colname 
  """
  table_under = table[table[colname] < maxval].copy()
  table_over = table[table[colname] >= maxval].copy().groupby(check_and_invert(table.columns.values, [colname, sumcolname]))[sumcolname].sum().reset_index()
  table_over[colname] = maxval

  return table_under.append(table_over, sort=False)

def adjust_mye_age(mye):
  """
  Makes mid-year estimate/snpp data conform with census age categories:
  - subtract 100 from age (so that "1" means under 1)
  - aggregate 86,87,88,89,90,91 into 86 (meaning 85+)
  """
  # keep track of some totals
  pop = mye.OBS_VALUE.sum()
  pop_m = mye[mye.GENDER == 1].OBS_VALUE.sum()
  pop_a = mye[mye.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum()

  # this modifies argument!
  mye.C_AGE -= 100

  mye_adj = mye[mye.C_AGE < 86].copy()
  mye_over85 = mye[mye.C_AGE > 85].copy()

  #print(myeOver85.head(12))

  agg86 = mye_over85.pivot_table(index=["GEOGRAPHY_CODE", "GENDER"], values="OBS_VALUE", aggfunc=sum)
  agg86["C_AGE"] = 86
  agg86 = agg86.reset_index()

  mye_adj = mye_adj.append(agg86, ignore_index=True, sort=False)

  # ensure the totals in the adjusted table match the originals (within precision)
  assert relEqual(mye_adj.OBS_VALUE.sum(), pop)
  assert relEqual(mye_adj[mye_adj.GENDER == 1].OBS_VALUE.sum(), pop_m)
  assert relEqual(mye_adj[mye_adj.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum(), pop_a)

  return mye_adj


def adjust_pp_age(pp):
  """
  Makes (s)npp data conform with census maximum categories:
  - aggregate 85,86,87,88,89,90 into 85 (meaning >=85)
  """
  # keep track of some totals
  pop = pp.OBS_VALUE.sum()
  pop_m = pp[pp.GENDER == 1].OBS_VALUE.sum()
  pop_a = pp[pp.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum()

  #pp.C_AGE += 1

  mye_adj = pp[pp.C_AGE < 85].copy()
  mye_over85 = pp[pp.C_AGE > 84].copy()

  #print(myeOver85.head(12))

  agg86 = mye_over85.pivot_table(index=["GEOGRAPHY_CODE", "GENDER", "PROJECTED_YEAR_NAME"], values="OBS_VALUE", aggfunc=sum)
  agg86["C_AGE"] = 85
  agg86 = agg86.reset_index()

  mye_adj = mye_adj.append(agg86, ignore_index=True, sort=False)

  # ensure the totals in the adjusted table match the originals (within precision)
  assert relEqual(mye_adj.OBS_VALUE.sum(), pop)
  assert relEqual(mye_adj[mye_adj.GENDER == 1].OBS_VALUE.sum(), pop_m)
  assert relEqual(mye_adj[mye_adj.GEOGRAPHY_CODE == "E06000015"].OBS_VALUE.sum(), pop_a)

  return mye_adj

def check_result(msynth):
  if isinstance(msynth, str):
    raise ValueError(msynth)
  elif not msynth["conv"]:
    print(msynth)
    raise ValueError("convergence failure")


def microsynthesise_seed(dc1117, dc2101, dc6206):
  """
  Microsynthesise a seed population from census data
  """
  n_geog = len(dc1117.GEOGRAPHY_CODE.unique())
  n_sex = 2 #len(dc1117.C_SEX.unique())
  n_age = len(dc1117.C_AGE.unique())
  cen11sa = unlistify(dc1117, ["GEOGRAPHY_CODE", "C_SEX", "C_AGE"], [n_geog, n_sex, n_age], "OBS_VALUE")
  n_eth = len(dc2101.C_ETHPUK11.unique())
  cen11se = unlistify(dc2101, ["GEOGRAPHY_CODE", "C_SEX", "C_ETHPUK11"], [n_geog, n_sex, n_eth], "OBS_VALUE")

  # TODO use microdata (national or perhaps regional) Mistral/persistent_data/seed_ASE_EW.csv
  # - requires unified age structure

  # microsynthesise these two into a 4D seed (if this has a lot of zeros can have big impact on microsim)
  print("Synthesising 2011 seed population...", end='')
  msynth = hl.qis([np.array([0, 1, 2]), np.array([0, 1, 3])], [cen11sa, cen11se])
  check_result(msynth)
  print("OK")
  return msynth["result"]


def year_sequence(start_year, end_year):
  """
  returns a sequence from start_year to end_year inclusive
  year_sequence(2001,2005) = [2001, 2002, 2003, 2004, 2005]
  year_sequence(2005,2001) = [2005, 2004, 2003, 2002, 2001]
  """
  if start_year == end_year:
    return [start_year]

  if start_year < end_year:
    return list(range(start_year, end_year + 1))

  return list(range(start_year, end_year - 1, -1))


def do_rescale(spenser_2018):

  pd_dir = "./persistent_data/"

  # Read in the oa lookup file to combine LSOAs into MSOAs
  oa_lookup = pd.read_csv(pd_dir + "OA_to_LSOA_to_MSOA_to_LAD_December_2017.csv", header=0)
  #oa_lookup = pd.read_csv("./persistent_data/OA_to_LSOA_to_MSOA_to_LAD_December_2017.csv", header=0)

  output = []
  for gender in range(1, 3):
    # gender: males == 1, females == 2

    # Split spenser data by gender (will add together at the end)
    spenser_split = spenser_2018.loc[spenser_2018['DC1117EW_C_SEX'] == gender]

    # Get the correct ONS file
    if gender == 1:
      ons = pd.read_csv(pd_dir + "males_lsoa_2018.csv")
    else:
      ons = pd.read_csv(pd_dir + "females_lsoa_2018.csv")

    # Calculate summary statistics about spenser that are required in rescale
    regions, ethtot, ethprop, num_ethgroups, prim_ethgroup = spenser_rescale_prep(spenser_split)

    # Reshape ONS data wide to long (and other things)
    ons_long = ons_rescale_prep(regions, ons, oa_lookup)

    # Do the rescale
    rescaled_ind = rescale(num_ethgroups, ons_long, ethprop, prim_ethgroup)

    # Reattach gender information
    rescaled_ind['DC1117EW_C_SEX'] = gender

    output.append(rescaled_ind)

  # Concatenate the resulting dataframes together (male and female)
  final = pd.concat(output)

  # Now need to sort by Area, Sex, and Age, and reattach a PID
  final.sort_values(by=['Area', 'DC1117EW_C_SEX', 'DC1117EW_C_AGE', 'DC2101EW_C_ETHPUK11'],
                    inplace=True)
  final.reset_index(inplace=True)
  # Docker build uses python 3.5 (based on continuumio/anaconda3 image) so can't call ignore_index=True in sort_values
  # This wasn't possible until pandas v1.0.0 (https://pandas.pydata.org/pandas-docs/stable/whatsnew/v1.0.0.html)

  # LAST STEP!!!!! Rearrange the order of the columns
  final = final[['Area', 'DC1117EW_C_SEX', 'DC1117EW_C_AGE', 'DC2101EW_C_ETHPUK11']]

  return final


def spenser_rescale_prep(spenser_2018):

  # Remove PID & gender (data already split into male and female)
  spenser = spenser_2018.drop('DC1117EW_C_SEX', axis=1)

  # Extract MSOAs from SPENSER to subset the ONS data
  regions = pd.Series(spenser_2018.Area.unique())

  # Get the ethnicity distribution from SPENSER
  # The following dataframe contains data grouped by Area, Age, and ethnicity, and the number of individuals
  # i.e. the number of white males aged 0 in the Area E02002330 = 27
  ethtot = spenser.groupby(['Area', 'DC1117EW_C_AGE', 'DC2101EW_C_ETHPUK11']).size()

  # We need proportions so we can apply new counts and keep the same distribution
  ethprop = ethtot.groupby(level=[0, 1]).apply(lambda x: x / x.sum()).reset_index(name='Ethnic_Proportion')

  num_ethgroups = ethprop.groupby(['Area', 'DC1117EW_C_AGE']).size().reset_index(name='# Ethnic Groups')

  # Drop the Area and calculate the most common ethnic group per age. This is for the imputation later
  primary_ethgroup = spenser.drop('Area', axis=1)
  primary_ethgroup = primary_ethgroup.groupby('DC1117EW_C_AGE').agg(lambda x: x.value_counts().index[0]).reset_index()

  return regions, ethtot, ethprop, num_ethgroups, primary_ethgroup


def ons_rescale_prep(regions, ons, oa_lookup):

  # Only need to keep LSOAs and MSOAs
  oa_l2m = oa_lookup[['LSOA11CD', 'MSOA11CD']]

  # Merge lookup onto ONS files to aggregate LSOAs
  ons_oa = pd.merge(left=ons,
                      right=oa_l2m,
                      how='left',
                      left_on='Area Codes',
                      right_on='LSOA11CD')

  # Drop duplicate rows from the merge
  ons_oa = ons_oa.drop_duplicates()

  # Now aggregate the MSOAs and sum
  ons_msoa = ons_oa.groupby('MSOA11CD').agg('sum').reset_index()

  # Subset the data to include only the MSOAs from the SPENSER data
  # female_subset = female[female['Area Codes'].isin(regions)]
  ons_msoa = ons_msoa[ons_msoa['MSOA11CD'].isin(regions)]

  # Replacing column names to include 'age_' prefix (for reshape) and change ages to fit SPENSER dataset
  # SPENSER data age index starts at 1, whilst ONS starts at 0. Replacing ONS index to fit SPENSER
  colnames = ['MSOA11CD']
  for x in range(1, 91):
    colnames.append('age_' + str(x))
  colnames.append('age_91')

  # Now replace
  ons_msoa.columns = colnames

  # Aggregate the ages 85+ to match SPENSER output, then drop unnecessary cols
  ons_msoa['age_86'] = ons_msoa[['age_86', 'age_87', 'age_88', 'age_89', 'age_90', 'age_91']].sum(axis=1)
  ons_msoa = ons_msoa.drop(['age_87', 'age_88', 'age_89', 'age_90', 'age_91'], axis=1)

  # Now need to reshape the ONS data from wide to long
  ons_long = pd.wide_to_long(ons_msoa, stubnames='age_', i='MSOA11CD', j='Age').reset_index()
  # Rename value column after reshape
  ons_long.rename(columns={'age_': 'Count'}, inplace=True)
  # Sort data by MSOA and Age
  ons_long.sort_values(by=['MSOA11CD', 'Age'], axis=0, inplace=True)
  ons_long.reset_index(inplace=True)

  return ons_long


def rescale(num_ethgroups, ons, ethprop, prim_ethgroup, ethtot=None):

  #TODO: DO WE NEED THIS? Should we merge with ethtot instead of num_ethgroups?

  # First need to merge the dataframes on MSOA and Age, then keep only rows in ONS data ONLY
  merged = pd.merge(left=num_ethgroups,
                    right=ons,
                    how='right',  # Ensure we keep rows that exist in ONS and not in SPENSER data
                    left_on=['Area', 'DC1117EW_C_AGE'],
                    right_on=['MSOA11CD', 'Age'],
                    indicator=True)  # Check the merge

  # Remove the SPENSER columns to be replaced
  merged = merged.drop(axis=1, columns=['Area', 'DC1117EW_C_AGE'])
  # Reorder the columns
  merged = merged[['MSOA11CD', 'Age', '# Ethnic Groups', 'Count', '_merge']]
  # Rename to fit SPENSER format
  merged = merged.rename(columns={'MSOA11CD': 'Area', 'Age': 'DC1117EW_C_AGE', '# Ethnic Groups': 'ethGroups'})

  # Merge ethnic proportions dataset onto merged
  merg_prop = pd.merge(left=merged,
                       right=ethprop,
                       how='outer',
                       on=['Area', 'DC1117EW_C_AGE'])
  # If this merge has worked correctly, individual rows in merged should have been duplicated to produce
  # 1 row per MSOA, per Age, per ethnic group, with a count attached

  # Now impute missing values
  imputed = impute_missing(merg_prop, prim_ethgroup)

  # Get the new counts by multiplying total (Count) by ethnic proportion and round to nearest whole number
  imputed['newCount'] = imputed['Count'].mul(imputed['Ethnic_Proportion'])
  imputed['newCount'] = imputed['newCount'].round(0)

  # Now we need to expand the dataset of counts into a dataset of individuals, with 1 row per person
  # Duplicate the rows based on the value in Count
  final_ind = imputed.reindex(imputed.index.repeat(imputed['newCount'])).reset_index()

  # Drop unnecessary columns and rename other to fit original format
  final_ind.drop(columns=['index', 'Count', 'Ethnic_Proportion', 'newCount'], inplace=True)
  final_ind.rename(columns={'DC2101EW_C_ETHPUK11_x': 'DC2101EW_C_ETHPUK11'}, inplace=True)

  return final_ind


def impute_missing(merg_prop, prim_ethgroup):

  imputed_ind = pd.merge(left=merg_prop,
                         right=prim_ethgroup,
                         how='left',
                         on='DC1117EW_C_AGE')

  # Replace missing ethnicity values in imputed_ind with replacement from prim_ethgroup
  imputed_ind['DC2101EW_C_ETHPUK11_x'].fillna(value=imputed_ind['DC2101EW_C_ETHPUK11_y'], inplace=True)

  # Drop the original DC2101EW_C_ETHPUK11 as it contains missing values, along with other columns no longer needed
  imputed_ind.drop(columns=['DC2101EW_C_ETHPUK11_y', '_merge', 'ethGroups'], inplace=True)
  # Fill null values in Ethnic_Proportion with 1.0, as they are being filled with the most common ethnic group only
  imputed_ind['Ethnic_Proportion'].fillna(value=1.00000, inplace=True)  # maintain 5 sig figs

  return imputed_ind
