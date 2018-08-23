#!/bin/bash

# This script must be run with qsub

#$ -cwd -V
#$ -l h_rt=01:00:00
#$ -l h_vmem=2G
#$ -m e
#$ -M a.p.smith@leeds.ac.uk
#$ -o ./logs
#$ -e ./logs

# Tell SGE that this is an array job, with "tasks" numbered from 0 to 34
#$ -t 1-35
# Restrict to max jobs (35 is all of them) 
#$ -tc 35

# check Nomis API key is set
if [ ! -f ~/apikey.sh ]; then
  echo "api key not found. Please specify your Nomisweb API key in ~/apikey.sh, e.g.:"
  echo "export NOMIS_API_KEY=0x0123456789abcdef0123456789abcdef01234567"
  exit 1
fi
. ~/apikey.sh

# Unload the python modules as they can conflict with the conda env
module unload python-libs
module unload python

# Check we're in SGE env (i.e. this script submitted with qsub/qrsh)
if [ "$SGE_O_HOME" == ""]; do
  echo "No SGE env defined, has this script been submitted via e.g. qsub?"
  exit 1
done

# Check we are in a conda env - should be activated manually
#source activate <env-name>
if [ "$CONDA_DEFAULT_ENV" == "" ]; then
  echo Error, no conda env activated
  exit 1
fi

# get LAD codes
. ./lad_array.sh

scripts/run_ssm.py -c config/ssm_default.json ${lads[$SGE_TASK_ID]}
