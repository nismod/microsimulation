#!/usr/bin/env python3

""" run script for static sequential microsynthesis """

import time
import microsimulation.static_h as StaticH
import microsimulation.utils as utils

#assert humanleague.version() > 1
DEFAULT_INPUT_DIR = "./persistent_data"
DEFAULT_OUTPUT_DIR = "./data"
DEFAULT_CACHE_DIR = "./cache"

def main(params):
  """ Run it """

  resolution = params["resolution"]
  ref_year = params["census_ref_year"]
  horizon_year = params["horizon_year"]
  variant = params["projection"]

  # upstream defaults to input  
  upstream_dir = params["upstream_dir"] if "upstream_dir" in params else DEFAULT_INPUT_DIR
  input_dir = params["input_dir"] if "input_dir" in params else DEFAULT_INPUT_DIR
  output_dir = params["output_dir"] if "output_dir" in params else DEFAULT_OUTPUT_DIR
  cache_dir = params["cache_dir"] if "cache_dir" in params else DEFAULT_CACHE_DIR

  for region in params["regions"]:
    try:
      # start timing
      start_time = time.time()

      print("Static H Microsimulation ", region, "@", resolution)
      # init microsynthesis
      ssm = StaticH.SequentialMicrosynthesisH(region, resolution, cache_dir, upstream_dir, input_dir, output_dir)
      # generate the population
      ssm.run(ref_year, horizon_year)

      print("Done. Exec time(s): ", time.time() - start_time)
    except RuntimeError as error: 
      print(region, "FAILED: ", error)  
  print("All Done.")

if __name__ == "__main__":

  params = utils.get_config()
  main(params)
