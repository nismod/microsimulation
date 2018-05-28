#!/usr/bin/env python3

""" run script for static sequential microsynthesis """

import time
import microsimulation.static as Static
import microsimulation.utils as utils

#assert humanleague.version() > 1
DEFAULT_CACHE_DIR = "./cache"
DEFAULT_OUTPUT_DIR = "./data"

def main(params):
  """ Run it """

  resolution = params["resolution"]
  ref_year = params["census_ref_year"]
  horizon_year = params["horizon_year"]
  variant = params["projection"]
  
  cache_dir = params["cache_dir"] if "cache_dir" in params else DEFAULT_CACHE_DIR
  output_dir = params["output_dir"] if "output_dir" in params else DEFAULT_OUTPUT_DIR

  use_fast_mode = params["mode"] == "fast"

  for region in params["regions"]:
    # start timing
    start_time = time.time()

    print("Static P Microsimulation: ", region, "@", resolution)

    # init microsynthesis
    try:
      ssm = Static.SequentialMicrosynthesis(region, resolution, variant, cache_dir, output_dir, use_fast_mode)
      ssm.run(ref_year, horizon_year)
    except Exception as e:
      print(e)
      return

    print(region, "done. Exec time(s): ", time.time() - start_time)
  print("all done")

if __name__ == "__main__":

  params = utils.get_config()
  main(params)