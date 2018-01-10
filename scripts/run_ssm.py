#!/usr/bin/env python3

# run script for static sequential microsynthesis

import sys
import time
import microsimulation.static as Static

#assert humanleague.version() > 1
CACHE_DIR = "./cache"
OUTPUT_DIR = "./data"

# The microsynthesis makes use of the following tables:
def main():

  # # start timing
  start_time = time.time()

  # TODO will fail if region specified as text 
  print("Static Microsimulation region:", region)
  print("Static Microsimulation resolution:", resolution)

  # init microsynthesis
  try:
    ssm = Static.SequentialMicrosynthesis(region, resolution, CACHE_DIR, OUTPUT_DIR, fast_mode)
  except Exception as e:
    print(e)
    return

  # generate the population
  try:
    ssm.run(startYear, endYear)
  except Exception as e:
    print("ERROR:", e)
    return

  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":
  if len(sys.argv) != 5 and len(sys.argv) != 6:
    print("usage:", sys.argv[0], "<region> <resolution> <startYear> <endYear> [--fast]")
    print("e.g:", sys.argv[0], "E09000001 MSOA11 2001 2039")
  else:
    region = sys.argv[1]
    resolution = sys.argv[2]
    startYear = int(sys.argv[3])
    endYear = int(sys.argv[4])
    fast_mode = True if len(sys.argv) == 6 and sys.argv[5] == "--fast" else False
    main()
