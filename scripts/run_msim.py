#!/usr/bin/env python3

# run script for static sequential microsynthesis

import sys
import time
import microsimulation.dynamic as Dynamic

#assert humanleague.version() > 1
CACHE_DIR = "./cache"
OUTPUT_DIR = "./data"

# The microsynthesis makes use of the following tables:
def main(region, resolution):

  # # start timing
  start_time = time.time()

  # TODO will fail if region specified as text 
  print("Microsimulation region:", region)
  print("Microsimulation resolution:", resolution)

  # init microsynthesis
  try:
    msim = Dynamic.Microsimulation(region, resolution, CACHE_DIR, OUTPUT_DIR)
  except Exception as e:
    print(e)
    return

  # generate the population
  #try:
  msim.run(startYear, endYear)
  #except Exception as e:
  #  print(e)
  #  return

  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":
  if len(sys.argv) != 5:
    print("usage:", sys.argv[0], "<region> <resolution> <startYear> <endYear>")
    print("e.g:", sys.argv[0], "E09000001 MSOA11 2001 2016")
  else:
    region = sys.argv[1]
    resolution = sys.argv[2]
    startYear = int(sys.argv[3])
    endYear = int(sys.argv[4])
    main(region, resolution)
