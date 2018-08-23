#!/bin/bash

# This script must be run with qsub

#$ -cwd -V
#$ -l h_rt=48:00:00
#$ -l h_vmem=2G
#$ -m e
#$ -M a.p.smith@leeds.ac.uk
#$ -o ./logs
#$ -e ./logs

# check env is set up correctly
. ./check.sh

if [ "$#" != "3" ]; then
  echo "usage: qsub $0 <config-file> <lad-code>" 
  exit 1 
fi

scripts/run_assignment.py -c $1 $2
