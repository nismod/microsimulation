#!/bin/bash

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
if [ "$SGE_O_HOME" == "" ]; then 
  echo "No SGE env defined, has this script been submitted via e.g. qsub?"
  exit 1
fi

# Check we are in a conda env - should be activated manually
#source activate <env-name>
if [ "$CONDA_DEFAULT_ENV" == "" ]; then
  echo Error, no conda env activated
  exit 1
fi
echo Conda environment is: $CONDA_DEFAULT_ENV

