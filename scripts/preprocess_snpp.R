
# SNPP preprocessing
# Raw subnational population projection data downloaded from:
# https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationprojections/datasets/localauthoritiesinenglandz1/2014based/snppz1population.zip
# Unzip the files (2014 SNPP Population females.csv and 2014 SNPP Population males.csv) to the cache directory
# Run this script


# Make SNPP ages categories the same as census
adjustSnppAge = function(df) {
  
  # AGE_GROUP -> AGE
  colnames(df)[colnames(df) == "AGE_GROUP"] = "AGE"
  
  print(colnames(df))
  # remove non-numeric
  df = df[df$AGE != "All ages",] 
  df$AGE[df$AGE == "90 and over"] = "90"

  # spot-check we preserve correct totals
  total14 = sum(df$X2014)
  total19 = sum(df$X2019)
  total29 = sum(df$X2029)
  total39 = sum(df$X2039)
  
  df$AGE = as.numeric(df$AGE) + 1
  
  # merge ages 85+ 
  years = 2014:2039
  for (y in years)
  {
    col = paste0("X",y) 
    df[df$AGE==86, col] = df[df$AGE==86, col] + df[df$AGE==87, col] + df[df$AGE==88, col] +
      df[df$AGE==89, col] + df[df$AGE==90, col] + df[df$AGE==91, col]
  }
  df = df[df$AGE<87,]
  
  # check total is preserved
  stopifnot(sum(df$X2014) == total14)
  stopifnot(sum(df$X2019) == total19)
  stopifnot(sum(df$X2029) == total29)
  stopifnot(sum(df$X2039) == total39)
  
  return(df)
}


# TODO Wales/Scotland data?

setwd("~/dev/nismod/microsimulation/")
cache_dir = "./cache/"

snpp14m = read.csv(paste0(cache_dir, "2014 SNPP Population males.csv"), stringsAsFactors = F)
snpp14f = read.csv(paste0(cache_dir, "2014 SNPP Population females.csv"), stringsAsFactors = F)

# remove stuff not required
snpp14m$AREA_NAME=NULL
snpp14f$AREA_NAME=NULL
snpp14m$COMPONENT=NULL
snpp14f$COMPONENT=NULL
# use census sex enumeration
snpp14m$SEX=rep(1, nrow(snpp14m))
snpp14f$SEX=rep(2, nrow(snpp14m))

snpp14 = rbind(snpp14m, snpp14f)

# AGE 0-90+ -> 0(1)-85+(86) (to match census)
#snpp14$AGE_GROUP = snpp14$AGE_GROUP + 1
snpp14 = adjustSnppAge(snpp14)

# make col names consistency with MYE/census
colnames(snpp14)[colnames(snpp14) == "AREA_CODE"] = "GEOGRAPHY_CODE"
colnames(snpp14)[colnames(snpp14) == "SEX"] = "GENDER"

write.csv(snpp14, paste0(cache_dir, "snpp2014.csv"), row.names=F)
