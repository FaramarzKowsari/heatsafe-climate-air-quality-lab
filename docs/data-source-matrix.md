# Data Source Matrix

| Source | Implemented mode | Credentials | Primary scientific role | Important boundary |
|---|---|---|---|---|
| NOAA CDO GHCND | API foundation | Token | Station climate observations | Request windows and datatype units must be explicit |
| EPA AQS | API foundation | Email + key | Regulatory monitoring observations | Preserve methods, durations and qualifiers |
| EEA Air Quality | Local Parquet normalizer | Download selected by user | European station measurements | Preserve validation/verification status and archive checksum |
| NASA FIRMS | Area API foundation | MAP_KEY | Active-fire context | Detection does not prove smoke impact |
| ERA5-Land | Request specification | CDS credentials | Gridded reanalysis | Reanalysis is not station observation |
| Türkiye MGM | Registry only | To be verified | Weather and climate | No undocumented endpoint |
| Türkiye Air Quality | Registry only | To be verified | Monitoring observations | No undocumented endpoint |
