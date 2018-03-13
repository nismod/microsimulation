#!/usr/bin/env python3

""" run_assignment.py """

import time
import argparse
import microsimulation.assignment as Assignment

H_DATA_DIR = "../household_microsynth/data"
P_DATA__DIR = "./data"

def main(params):
  """ Run it """

  # start timing
  start_time = time.time()

  # TODO will fail if region specified as text
  print("Assignment region:", params.region)
  print("Assignment resolution (hard-coded): OA11(H)/MSOA11(P)", )
  print("Assignment resolution:", params.year)

  # init assignment algorithm
  #try:
  ass = Assignment.Assignment(params.region, params.year, H_DATA_DIR, P_DATA__DIR)
  #except Exception as e:
  #  print(e)
  #  return

  # generate the population
  try:
    ass.run()
  except Exception as e:
    print("ERROR:", e)
    return



  print("Done. Exec time(s): ", time.time() - start_time)

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="static sequential (population) microsimulation")

  parser.add_argument("region", type=str, help="the ONS code of the local authority district (LAD) to be covered by the microsynthesis, e.g. E09000001")
  # currently assuming OA11 resolution for households and MSOA for people
  parser.add_argument("year", type=int, help="the reference (i.e. census) year for the microsimulation (either 2001 or 2011)")
  
  args = parser.parse_args()

  main(args)