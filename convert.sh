#!/bin/bash

if [ "$#" != "2" ]; then
  echo usage: convert from_col to_col
  exit 1
fi 

from=$1
to=$2

files=$(grep -l $from data/*.csv)

echo $from "->" $to:
for file in $files; do
  echo " " $file
  sed -i "s/$from/$to/g" $file
done