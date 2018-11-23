#!/bin/bash

files=$(ls ../microsimulation/persistent_data/sc/*.csv)
dir=../microsimulation/persistent_data/sc

echo "LAD,x,y,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,avg,overall,overallPct" > raw.csv
grep "All households" $dir/*.csv >> raw.csv
sed -i 's:../microsimulation/persistent_data/sc/2016-house-proj-detailed-coun-princ_::g' raw.csv
sed -i 's/.csv:/,/g' raw.csv

cat raw.csv

#2016-house-proj-detailed-coun-princ_Aberdeen\ City.csv

 