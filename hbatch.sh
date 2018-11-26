#!/bin/bash

# Batch submission
# run like:
# qsub hbatch.sh <config-file>

runtime="01:00:00"
memory="2G"
logdir=./logs

#$ -cwd -V
#$ -l h_rt=01:00:00
#$ -l h_vmem=2G
#$ -m e
#$ -M a.p.smith@leeds.ac.uk
#$ -o ./logs
#$ -e ./logs

# Tell SGE that this is an array job, with "tasks" numbered from 1 to 38
#$ -t 1-38
# Restrict to max jobs (35 is all of them) 
#$ -tc 38

# check env is set up correctly
. ./check.sh

# source the LADs into groups of 10
. ./lad_array_grouped10.sh

if [ "$#" != "1" ]; then
  echo "usage: qsub $0 <config-file>" 
  exit 1 
fi

scripts/run_ssm_h.py -c $1 ${lads[$SGE_TASK_ID]}

