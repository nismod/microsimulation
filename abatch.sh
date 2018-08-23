#!/bin/bash

# This script must be run with qsub

#$ -cwd -V
#$ -l h_rt=48:00:00
#$ -l h_vmem=2G
#$ -m e
#$ -M a.p.smith@leeds.ac.uk
#$ -o ./logs
#$ -e ./logs

# Tell SGE that this is an array job, with "tasks" numbered from 0 to 34
#$ -t 1-348
# Restrict to max jobs 
#$ -tc 64

# check env is set up correctly
. ./check.sh

# get LAD codes
. ./lad_array_individual.sh

scripts/run_assignment.py -c config/ass_default.json ${lads[$SGE_TASK_ID]}
