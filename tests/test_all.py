from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import microsimulation.common as Common
import microsimulation.static as Static
import microsimulation.dynamic as Dynamic
#import microsimulation.utils as Utils

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test_static(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsim = Static.SequentialMicrosynthesis(region, resolution, cache)
    microsim.run(2011, 2012)

  # City of London MSOA (one geog area)
  def test_dynamic(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsim = Dynamic.Microsimulation(region, resolution, cache)
    microsim.run(2011, 2012)
    #self.assertTrue(False)

