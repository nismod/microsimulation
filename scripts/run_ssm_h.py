#!/usr/bin/env python3

""" run script for static sequential microsynthesis """

import time
import argparse
import microsimulation.static_h as StaticH

#assert humanleague.version() > 1
INPUT_DIR = "./persistent_data"
OUTPUT_DIR = "./data"

def main(params):
  """ Run it """

  # start timing
  start_time = time.time()

  # TODO will fail if region specified as text
  print("Static Microsimulation region:", params.region)
  print("Static Microsimulation resolution:", params.resolution)

  # init microsynthesis
  try:
    ssm = StaticH.SequentialMicrosynthesisH(params.region, params.resolution, params.upstream_dir, INPUT_DIR, OUTPUT_DIR)
  except Exception as e:
    print(e)
    return

  # generate the population
  try:
    ssm.run(params.ref_year, params.target_year)
  except Exception as e:
    print("ERROR:", e)
    return

  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="static sequential (population) microsimulation")

  parser.add_argument("region", type=str, help="the ONS code of the local authority district (LAD) to be covered by the microsynthesis, e.g. E09000001")
  parser.add_argument("resolution", type=str, help="the geographical resolution of the microsynthesis (e.g. OA11, LSOA11, MSOA11)")
  parser.add_argument("upstream_dir", type=str, help="the location of the upstream model output (i.e microsynthesised base population)")
  parser.add_argument("ref_year", type=int, help="the reference (i.e. census) year for the microsimulation (either 2001 or 2011)")
  parser.add_argument("target_year", type=int, help="the target (end) year for the microsimulation (max 2039)")
  #parser.add_argument("-f", "--fast", action='store_const', const=True, default=False, help="use imprecise (but fast) generation")

  args = parser.parse_args()

  main(args)
