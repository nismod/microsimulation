#!/bin/bash

# Batch submission

# TODO check:
# conda env
# nomis key

runtime="01:00:00"
memory="2G"
logdir=./logs

#$ -cwd -V
#$ -l h_rt=01:00:00
#$ -l h_vmem=2G
#$ -m e
#$ -M a.p.smith@leeds.ac.uk
#$ -o logs
#$ -e logs

# Tell SGE that this is an array job, with "tasks" numbered from 1 to 35
#$ -t 1-35
# Restrict to max jobs (35 is all of them) 
#$ -tc 35

# source the LAD arrays
. ./lad_array.sh

scripts/run_ssm_h.py -c config/ssm_h_default.py ${lads[$SGE_TASK_ID]}
