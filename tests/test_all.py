from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import microsimulation.common as Common
import microsimulation.static as Static
import microsimulation.static_h as StaticH
import microsimulation.dynamic as Dynamic
import microsimulation.assignment as Assignment

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test_static(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsim = Static.SequentialMicrosynthesis(region, resolution, cache)
    microsim.run(2011, 2012)

  def test_static_h(self):
    region = "E09000001"
    resolution = "OA11"
    # requires output from upstream model
    upstream_dir = "../household_microsynth/data/"
    input_dir = "./persistent_data/"
    downstream_dir = "./data/"
    microsim = StaticH.SequentialMicrosynthesisH(region, resolution, upstream_dir, input_dir, downstream_dir)
    microsim.run(2011, 2039)

    #self.assertTrue(False)

  # City of London MSOA (one geog area)
  def test_dynamic(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsim = Dynamic.Microsimulation(region, resolution, cache)
    microsim.run(2011, 2012)
    #self.assertTrue(False)

  # City of London assignment 
  def test_z_assign(self):
    region = "E09000001"
    year = 2011
    data_dir = "./data"
    assign = Assignment.Assignment(region, year, False, data_dir)
    assign.run()
    #self.assertTrue(False)

