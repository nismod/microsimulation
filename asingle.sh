#!/bin/bash

# single job submission - args from cmd line TODO config file
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <region>"
  echo   e.g. $0 E09000001
  exit 1
fi

region=$1

if [ ! -f ~/apikey.sh ]; then
  echo "api key not found. Please specify your Nomisweb API key in ./apikey.sh, e.g.:"
  echo "export NOMIS_API_KEY=0x0123456789abcdef0123456789abcdef01234567"
  exit 1
fi
. ~/apikey.sh

# TODO check conda

qsub_params="-l h_rt=2:0:0"

export REGION=$region
echo Submitting job for $REGION
qsub -o ./logs -e ./logs $qsub_params arun.sh

