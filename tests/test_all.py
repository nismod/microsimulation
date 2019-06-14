""" 
Test harness
"""
from unittest import TestCase

import microsimulation.static as Static
import microsimulation.static_h as StaticH
import microsimulation.assignment as Assignment

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test_static(self):
    region = "E07000041"
    resolution = "MSOA11"
    variant = "ppp"
    cache = "./cache"
    microsim = Static.SequentialMicrosynthesis(region, resolution, variant, False, cache, "./data", True)
    microsim.run(2011, 2012)

  def test_static_sc(self):
    region = "S12000030"
    resolution = "MSOA11"
    variant = "ppp"
    cache = "./cache"
    microsim = Static.SequentialMicrosynthesis(region, resolution, variant, False, cache, "./data", True)
    microsim.run(2011, 2012)

  def test_static_h(self):
    region = "E09000001"
    resolution = "OA11"
    # requires output from upstream model
    cache_dir = "./cache"
    upstream_dir = "../household_microsynth/data/"
    input_dir = "./persistent_data/"
    downstream_dir = "./data/"
    microsim = StaticH.SequentialMicrosynthesisH(region, resolution, cache_dir, upstream_dir, input_dir, downstream_dir)
    microsim.run(2011, 2039)

    #self.assertTrue(False)

  # City of London assignment 
  def test_z_assign(self):
    region = "E09000001"
    h_res = "OA11"
    p_res = "MSOA11"
    variant = "ppp"
    year = 2011
    strict_mode = False
    data_dir = "./data"
    assign = Assignment.Assignment(region, h_res, p_res, year, variant, strict_mode, data_dir)
    assign.run()
    #self.assertTrue(False)

