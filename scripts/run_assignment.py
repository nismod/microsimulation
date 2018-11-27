#!/usr/bin/env python3

""" run_assignment.py """

import os
import sys
import time
import argparse
import microsimulation.assignment as Assignment
import microsimulation.utils as utils
import cProfile, pstats

DEFAULT_DATA_DIR = "./data"

def main(params):
  """ Run it """

  # start timing
  start_time = time.time()

  # TODO will fail if region specified as text

  h_res = params["household_resolution"]
  p_res = params["person_resolution"]
  year = params["year"]
  variant = params["projection"]
  strict = params["strict"]

  print("Assignment region(s):", params["regions"])
  print("Assignment resolution: {} (H) / {} (P)".format(h_res, p_res)) 
  print("Projection:", variant)
  print("Strict assignment mode:", strict)
  print("Assignment year:", year)

  data_dir = params["data_dir"] if "data_dir" in params else DEFAULT_DATA_DIR

  for region in params["regions"]:
    # init assignment algorithm
    #try:
    # TODO variant / cfg json
    ass = Assignment.Assignment(region, h_res, p_res, year, variant, strict, data_dir)
    ass.run()
    # except Exception as e:
    #   print("ERROR:", e)
    #   return

  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":

  params = utils.get_config()

  if "profile" in params and params["profile"]:
    print("*** Profile mode ***")
    profiler = cProfile.Profile()
    profiler.enable()
    profiler.run("main(params)") 
    profiler.disable()
    filename = "profile.%d.out" % os.getpid()
    print("writing profile stats to %s" % filename)
    pstats.Stats(profiler, stream=open(filename, 'w')).sort_stats("cumulative").print_stats()
  else:
    main(params)