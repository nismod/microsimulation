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


def rescale_2018(regions):
  """
  This function produces marginals for IPF from the ONS LSOA level counts dataset from 2018.
  The marginals produced are counts by age and sex, and the proportion of the total in each
  region.
  :param regions: The list of MSOA level geography regions within the microsimulation target.
  :return: age_sex: A [2,86] ndArray of counts broken down by sex by age.
          oa_prop: The proportion of the population within each MSOA.
  """

  # Read in the oa lookup file to combine LSOAs into MSOAs
  pd_dir = "./persistent_data/"
  oa_lookup = pd.read_csv(pd_dir + "OA_to_LSOA_to_MSOA_to_LAD_December_2017.csv", header=0)
  oa_l2m = oa_lookup[['LSOA11CD', 'MSOA11CD']]  # Only need to keep LSOAs and MSOAs

  # ONS data is split into male and female
  ons_m = pd.read_csv(pd_dir + "males_lsoa_2018.csv")
  ons_f = pd.read_csv(pd_dir + "females_lsoa_2018.csv")
  ons_list = [ons_m, ons_f]

  age_sex = pd.DataFrame()
  oa_counts_list = []

  # Work with male and female files separately, then combine the age_sex marginals into a [2,86] dataframe
  # 1 row per gender (0 - male, 1 - female)
  for ons in ons_list:
    oa_count, age_array = get_2018_ONS_age_counts(ons, oa_l2m, regions)
    # Store
    age_sex = age_sex.append(age_array.transpose(), ignore_index=True)
    oa_counts_list.append(oa_count)

  # Now aggregate for all ages 85+
  age_sex[85] = age_sex[[85, 86, 87, 88, 89, 90]].sum(axis=1)
  age_sex = age_sex.drop([86, 87, 88, 89, 90], axis=1)

  age_sex = age_sex.to_numpy()

  # Now oa_prop
  oa_prop = get_2018_ONS_oa_prop(oa_counts_list)

  return age_sex, oa_prop


def get_2018_ONS_age_counts(ons, oa_l2m, geog_map):
  """
  Function that calculates the counts by age of the population in the target region, for a
  single gender
  :param ons: LSOA level single gender dataset of population counts by age
  :param oa_l2m: Lookup file for LSOA to MSOA
  :return: Population counts by single year of age (top coded at 85)
  """

  # Merge lookup onto ONS files to aggregate LSOAs
  ons_oa = pd.merge(left=ons,
                    right=oa_l2m,
                    how='left',
                    left_on='Area Codes',
                    right_on='LSOA11CD')

  # Duplicates created in the merge
  ons_oa = ons_oa.drop_duplicates()
  # Now aggregate the LSOAs to get to MSOA level totals
  ons_msoa = ons_oa.groupby('MSOA11CD').agg('sum').reset_index()
  # Subset the data to include only the MSOAs in the region currently running
  ons_msoa = ons_msoa[ons_msoa['MSOA11CD'].isin(geog_map)].reset_index()

  # Aggregate to get counts by age
  ons_agg = ons_msoa.sum(axis=0)
  ons_agg.drop(labels=['index', 'MSOA11CD'], inplace=True)

  # Make sure dtype is numeric & reset index to fix weird indexing issues after append
  ons_agg = pd.to_numeric(ons_agg).reset_index(drop=True)
  ons_df = pd.DataFrame(ons_agg)

  return ons_msoa, ons_df


def get_2018_ONS_oa_prop(oa_counts_list):
  """
  Returns the proportion by population within each MSOA in the target region
  :param oa_counts_list: List of counts by region by age, separately by gender
  :return: Proportion of the population within each MSOA
  """

  # Combine the male and female specific oa_counts dataframes
  oa_counts = pd.concat(objs=[oa_counts_list[0], oa_counts_list[1]]).reset_index()
  oa_counts = oa_counts.drop(['level_0', 'index'], axis=1)

  # Groupby the geog code and sum to get counts by age in each region
  oa_counts = oa_counts.groupby('MSOA11CD').sum()

  # Now sum over all the ages
  oa_counts = oa_counts.sum(axis=1)

  # Calculate the proportion
  oa_prop = oa_counts / oa_counts.sum(axis=0)
  # Convert to numpy array and then done
  oa_prop = oa_prop.to_numpy()

  return oa_prop

