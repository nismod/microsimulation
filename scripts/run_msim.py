#!/usr/bin/env python3

""" run script for static sequential microsynthesis """

import time
import argparse
import microsimulation.dynamic as Dynamic

#assert humanleague.version() > 1
CACHE_DIR = "./cache"
OUTPUT_DIR = "./data"

def main(params):
  """ Run it """

  # start timing
  start_time = time.time()

  # TODO will fail if region specified as text
  print("Microsimulation region:", params.region)
  print("Microsimulation resolution:", params.resolution)

  # init microsynthesis
  try:
    msim = Dynamic.Microsimulation(params.region, params.resolution, CACHE_DIR, OUTPUT_DIR)
  except Exception as e:
    print(e)
    return

  # generate the population
  #try:
  msim.run(params.start_year, params.end_year)
  #except Exception as e:
  #  print(e)
  #  return

  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":

  print("DEPRECATED")

  parser = argparse.ArgumentParser(description="dynamic (population) microsimulation")

  parser.add_argument("region", type=str, help="the ONS code of the local authority district (LAD) to be covered by the microsynthesis, e.g. E09000001")
  parser.add_argument("resolution", type=str, help="the geographical resolution of the microsynthesis (e.g. OA11, LSOA11, MSOA11)")
  parser.add_argument("start_year", type=int, help="the start year for the microsimulation (min 2001)")
  parser.add_argument("end_year", type=int, help="the end year for the microsimulation (max 2039)")

  args = parser.parse_args()

  #main(args)
