# gaez_harrow.csv notes

Fetched by Ved on 2026-11-14 from FAO GAEZ v5 (file codes in `source_url`).

- **What the number is.** GAEZ Suitability Index (SI), 0 to 100. It is not a percent. Management is rain-fed, high input. `suitability_class` is the GAEZ class for that value.
- **Resolution.** RES05, 5 arc-minutes, about 9 to 10 km. This is not field level and not 1 km.
- **Point.** 42.0356, -82.9183 (UNVERIFIED until Vedant confirms). Read as the nearest pixel, Harrow row 575 col 1164. No interpolation.
- **Repeated 97.91.** Not a fetch error. The cells around Harrow are 9600 to 10000, and wheat and maize are often identical in GAEZ. Keep the values.
- **Baseline period.** 2001-2020. This is what `backend/suitability.py` reads. Decided by Ved.
- **Other periods.** 1981-2000 is a historical comparison only. Soy was 75.81, then 53.71 in 2001-2020, then 62.55 in 2021-2040 SSP370. The 2021-2040 SSP370 rows are not used as the scenario score. Range fit drives the dry and 2035 scenarios.
- **Dry and 2035 views.** Maize has no OMAFRA range yet, so its dry-view number is the GAEZ baseline, labelled "GAEZ baseline, dry scenario not applied".
- **Licence.** FAO, free with attribution.
