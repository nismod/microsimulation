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

# get LAD codes
. ./lad_array.sh

scripts/run_ssm.py -c config/ssm_default.json ${lads[$SGE_TASK_ID]}
