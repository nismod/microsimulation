#!/usr/bin/env python3

# run script for Household microsynthesis

import sys
import time
import microsimulation.static as Static

#assert humanleague.version() > 1
CACHE_DIR = "./cache"

# The microsynthesis makes use of the following tables:
def main(region, resolution):

  # # start timing
  start_time = time.time()

  print("Static Microsimulation region:", region)
  print("Static Microsimulation resolution:", resolution)

  # init microsynthesis
  try:
    ssm = Static.SequentialMicrosynthesis(region, resolution, CACHE_DIR)
  except Exception as e:
    print(e)
    return

  # generate the population
  try:
    ssm.run()
  except Exception as e:
    print(e)
    return

  print("Done. Exec time(s): ", time.time() - start_time)


if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<region> <resolution>")
    print("e.g:", sys.argv[0], "E09000001 OA11")
  else:
    REGION = sys.argv[1]
    RESOLUTION = sys.argv[2]
    main(REGION, RESOLUTION)
