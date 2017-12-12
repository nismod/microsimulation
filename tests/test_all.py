from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import microsimulation.static as Static
#import microsimulation.utils as Utils

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test1(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsim = Static.SequentialMicrosynthesis(region, resolution, cache)
    microsim.run(2011, 2012)

    #print(microsim.mye[2016])

