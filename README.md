*[work-in-progress]*

# microsimulation
Static and dynamic, population and household, microsimulation models. Current status:
- [X] static population microsimulation: refinement/testing
- [ ] dynamic population microsimulation: in prototype, reimplementation in progress
- [ ] househould microsimulation: drawing board

## Introduction
### Static Microsimulation
This refers to a sequence of microsyntheses, seeded with 2011 census data, with marginals from ONS mid-year-estimates (2001-2013) and ONS sub-national population projections (2014-2039).
- limited categories available: gender, age, ethnicity.
- highest geographical resolution is currently limited to MSOA.

### Dynamic Microsimulation
This refers to a stochastic simulation of individual elements (persons or households) in time using a Monte-Carlo approach.
Based on provided fertility, mortality and migration data and guided by static microsimulation above.

## Setup

### Dependencies

- `python3`

The following are specified in `requirements.txt` and should be automatically installed, manual steps are shown below just in case. 

- [UKCensusAPI](https://github.com/virgesmith/UKCensusAPI)
```
pip3 install git+git://github.com/virgesmith/UKCensusAPI.git
```
- [humanleague](https://github.com/virgesmith/humanleague)
```
pip3 install git+git://github.com/virgesmith/humanleague.git
```
NB Ensure you install humanleague version 2 or higher - this package uses features that are not available in earlier versions.

### Installation and Testing
```
./setup.py install
./setup.py test
```
### Running static microsynthesis
```
scripts/run_ssm.py <region(s)> <resolution> <start_year> <end_year> 
```
where region can be a one or more local authorities (or one of England, EnglandWales, GB, UK), specified by ONS/GSS code (e.g. E09000001 for the City of London). Resolution (for now) must be MSOA11. Start and end years must be in the range 2001-2016.
```
scripts/run_microsynth.py E09000001 MSOA11 2001 2039
```
NB Runtime for a medium-sized local authgority for all 39 years is likely to be well over 24h.
