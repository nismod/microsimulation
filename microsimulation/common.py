"""
Microsimulation base class - common functionality
"""

import pandas as pd
import numpy as np

import ukcensusapi.Nomisweb as Api_ew
import ukcensusapi.NRScotland as Api_sc
import humanleague as hl
import microsimulation.utils as utils

class Base(object):
    """
    Microsimulation base class - common functionality
    """

    def __init__(self, region, resolution, cache_dir):
        self.region = region
        self.resolution = resolution
        self.data_api_en = Api_ew.Nomisweb(cache_dir)
        self.data_api_sc = Api_sc.NRScotland(cache_dir)

    def get_census_data(self):
        if self.region[0] == "S":
            return self.__get_census_data_sc()
        elif self.region[0] == "N":
            raise NotImplementedError("NI support not yet implemented")
        else:
            return self.__get_census_data_ew()

    def __get_census_data_sc(self):

        print("Synthesising Scottish DC1117/DC2101 tables from LAD-level seeds and univariate data")

        # age only, no gender
        qs103sc = self.data_api_sc.get_data("QS103SC", self.region, self.resolution, category_filters={"QS103SC_0_CODE": range(1,102)})
        qs103sc = utils.cap_value(qs103sc, "QS103SC_0_CODE", 86, "OBS_VALUE")
        # sex only
        qs104sc = self.data_api_sc.get_data("QS104SC", self.region, self.resolution, category_filters={"QS104SC_0_CODE": [1,2]})

        ngeogs = len(qs103sc.GEOGRAPHY_CODE.unique())
        nages = len(qs103sc.QS103SC_0_CODE.unique())
        nsexes = 2

        # Get a LAD-level seed population by age and gender
        dc1117lad = self.data_api_sc.get_data("DC1117SC", self.region, "LAD", category_filters={"DC1117SC_0_CODE": [1,2], "DC1117SC_1_CODE": range(1,102)})
        dc1117lad = utils.cap_value(dc1117lad, "DC1117SC_1_CODE", 86, "OBS_VALUE")
        dc1117seed = utils.unlistify(dc1117lad, ["DC1117SC_0_CODE", "DC1117SC_1_CODE"], [2, 86], "OBS_VALUE").astype(float)
        # expand to all geogs within LAD
        dc1117seed = np.dstack([dc1117seed] * ngeogs).T

        ga = utils.unlistify(qs103sc, ["GEOGRAPHY_CODE", "QS103SC_0_CODE"], [ngeogs, nages], "OBS_VALUE")
        gs = utils.unlistify(qs104sc, ["GEOGRAPHY_CODE", "QS104SC_0_CODE"], [ngeogs, nsexes], "OBS_VALUE")
        msynth = hl.qisi(dc1117seed, [np.array([0,1]), np.array([0,2])], [ga,gs])
        #msynth = hl.qis([np.array([0,1]), np.array([0,2])], [ga,gs])
        utils.check_result(msynth)
        # TODO pending humanleague seed consistency check
        assert dc1117seed.shape == msynth["result"].shape

        dc1117sc = utils.listify(msynth["result"], "OBS_VALUE", ["GEOGRAPHY_CODE", "C_AGE", "C_SEX"])
        dc1117sc.GEOGRAPHY_CODE = utils.remap(dc1117sc.GEOGRAPHY_CODE, qs103sc.GEOGRAPHY_CODE.unique())
        dc1117sc.C_AGE = utils.remap(dc1117sc.C_AGE, qs103sc.QS103SC_0_CODE.unique())
        dc1117sc.C_SEX = utils.remap(dc1117sc.C_SEX, [1, 2])
        #print(dc1117sc.head())

        # These ETH codes are slightly different to E&W codes...
        # ETH Totals = [1,8,9,15,18,22]
        #eths = [2,3,4,5,6,7,8,10,11,12,13,14,16,17,19,20,21,23,24]
        eths = [1,8,9,15,18,22]
        ks201sc = self.data_api_sc.get_data("KS201SC", self.region, self.resolution, category_filters={"KS201SC_0_CODE": eths})
        neths = len(ks201sc.KS201SC_0_CODE.unique())

        # Get a LAD-level seed population by age and gender
        dc2101lad = self.data_api_sc.get_data("DC2101SC", self.region, "LAD", category_filters={"DC2101SC_0_CODE": eths, "DC2101SC_1_CODE": [1,2], "DC2101SC_2_CODE": 0})
        dc2101seed = utils.unlistify(dc2101lad, ["DC2101SC_1_CODE", "DC2101SC_0_CODE"], [2, neths], "OBS_VALUE").astype(float)
        # expand to all geogs within LAD
        dc2101seed = np.dstack([dc2101seed] * ngeogs).T

        #print(ks201sc.head())
        ge = utils.unlistify(ks201sc, ["GEOGRAPHY_CODE", "KS201SC_0_CODE"], [ngeogs, neths], "OBS_VALUE")
        # TODO use a LAD-level seed population
        msynth = hl.qisi(dc2101seed, [np.array([0,1]), np.array([0,2])], [ge,gs])
        utils.check_result(msynth)
        assert dc2101seed.shape == msynth["result"].shape

        dc2101sc = utils.listify(msynth["result"], "OBS_VALUE", ["GEOGRAPHY_CODE", "C_ETHPUK11", "C_SEX"])
        dc2101sc.GEOGRAPHY_CODE = utils.remap(dc2101sc.GEOGRAPHY_CODE, qs103sc.GEOGRAPHY_CODE.unique())
        dc2101sc.C_ETHPUK11 = utils.remap(dc2101sc.C_ETHPUK11, ks201sc.KS201SC_0_CODE.unique())
        dc2101sc.C_SEX = utils.remap(dc2101sc.C_SEX, [1, 2])
        #print(dc2101sc.head())


        assert dc1117sc.OBS_VALUE.sum() == dc2101sc.OBS_VALUE.sum()

        #print(self.data_api_sc.get_metadata("DC6206SC", "LAD"))
        # TODO Aberdeen has 174869 in this table
        # dc6206sc = self.data_api_sc.get_data("DC6206SC", self.region, "LAD", category_filters={"DC6206SC_1_CODE": 0,
        #                                                                                        "DC6206SC_0_CODE": [1,2,3,4,5,6],
        #                                                                                        "DC6206SC_2_CODE": [1,2,3,4,5,6,7,8,9]})
        #print(dc6206sc.OBS_VALUE.sum())
        #print(dc6206sc.DC6206SC_2_CODE.unique())
        # # dc6206sc = self.data_api_sc.get_data("DC6206SC", "MSOA11", self.region)
        # #raise NotImplementedError("Problem with MSOA-level detailed characteristics in Scottish census data")

        return (dc1117sc, dc2101sc, None)

    def __get_census_data_ew(self):
        """
        Download/cache census data
        """
        # convert input string to enum
        resolution = self.data_api_en.GeoCodeLookup[self.resolution]

        region_codes = self.data_api_en.get_lad_codes(self.region)

        if not region_codes:
            raise ValueError("no regions match the input: \"" + self.region + "\"")

        area_codes = self.data_api_en.get_geo_codes(region_codes, resolution)

        # Census: sex by age by MSOA
        table = "DC1117EW"
        query_params = {"MEASURES": "20100",
                        "date": "latest",
                        "C_AGE": "1...86",
                        "select": "GEOGRAPHY_CODE,C_SEX,C_AGE,OBS_VALUE",
                        "C_SEX": "1,2",
                        "geography": area_codes}

        # problem - data only available at MSOA and above
        dc1117ew = self.data_api_en.get_data(table, query_params)

        # Census: sex by ethnicity by MSOA
        table = "DC2101EW"
        query_params = {"MEASURES": "20100",
                        "date": "latest",
                        "C_AGE": "0",
                        "C_ETHPUK11": "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23",
                        "select": "GEOGRAPHY_CODE,C_SEX,C_ETHPUK11,OBS_VALUE",
                        "C_SEX": "1,2",
                        "geography": area_codes}
        # problem - data only available at MSOA and above
        dc2101ew = self.data_api_en.get_data(table, query_params)

        # This table contains only 16+ persons (under-16s do not have NS-SeC)
        table = "DC6206EW"
        query_params = {"date": "latest",
                        "MEASURES": "20100",
                        "C_SEX": "1,2",
                        "C_ETHPUK11": "2,3,4,5,7,8,9,10,12,13,14,15,16,18,19,20,22,23",
                        "C_NSSEC": "2...9,11,12,14,15,16",
                        "C_AGE": "1,2,3,4",
                        "select": "GEOGRAPHY_CODE,C_SEX,C_ETHPUK11,C_NSSEC,C_AGE,OBS_VALUE",
                        "geography": area_codes}
        dc6206ew = self.data_api_en.get_data(table, query_params)

        return (dc1117ew, dc2101ew, dc6206ew)

    def append_children(self, full_table, adults_table):
        """
          Append adult-only (16+) table (e.g DC6206) with children from full population table
        """
        # remember "17" census value means age 16
        children_table = full_table[full_table.C_AGE < 17].copy()
        children_table["C_NSSEC"] = 100 #

        # rename DC6206 C_AGE (band) so as not to conflict with DC1117 C_AGE (single year)
        adults_table = adults_table.rename(columns={"C_AGE": "C_AGEBAND"})

        x = pd.concat([adults_table, children_table], axis=0, ignore_index=True)
        assert full_table.OBS_VALUE.sum() == x.OBS_VALUE.sum()
        return x

