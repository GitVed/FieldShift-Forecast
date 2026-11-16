# Dataset resources

> Status note. This file records how each dataset was fetched and checked. Some rows describe earlier states that later work replaced: the NEX-GDDP-CMIP6 projections now run to 2040 (`data/seed/nex_adjusted_harrow.csv`), SoilGrids values at the cropland field are in `data/seed/soilgrids_field.csv`, and GAEZ values at the Harrow pixel are in `data/seed/gaez_harrow.csv` (see `data/seed/gaez_harrow_NOTES.md`). The README and `docs/EVIDENCE.md` describe what the app uses now.

Location: **42.0356° N, 82.9183° W**, supplied by the user. The physical field boundary remains unverified. All delivered observations and results are **CACHED**, not live measurements or forecasts.

## Datasets used

| Resource and official access | Retained CSVs in `data/seed/` | Coverage and units | Decision |
|---|---|---|---|
| [NASA POWER point API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/), [Harrow download](https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude=-82.9183&latitude=42.0356&start=1981&end=2025&format=CSV) | `power_t2m_harrow_1981_2025.csv`, `power_precip_harrow_1981_2025.csv`, `power_humidity_harrow_1981_2025.csv` | January 1981 to December 2025; 540 months each. Temperature °C, precipitation mm/month, relative humidity %. | Primary climate inputs. Source fields are **T2M, PRECTOTCORR, RH2M**. Precipitation source is mm/day; multiply by the calendar days in each month. No gaps or invalid rows. |
| [NASA POWER north comparison](https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude=-82.9183&latitude=42.5356&start=1981&end=2025&format=CSV) | `power_temperature_north_1981_2025.csv`, `power_precipitation_north_1981_2025.csv`, `power_humidity_north_1981_2025.csv` | January 1981 to December 2025; same units as Harrow. | Distinct requested point 0.5° north; used for spatial trend comparison. |
| [NASA IMERG](https://gpm.nasa.gov/data/imerg) via [POWER daily API](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT&community=AG&longitude=-82.9183&latitude=42.0356&start=19980601&end=20251231&time-standard=UTC&format=JSON) | `imerg_precip_harrow.csv` | June 1998 to December 2025; 331 monthly totals, mm/month, UTC. | Rainfall cross-check. All 10,076 daily values matched the official JSON response, which identifies IMERG and mm/day. Each daily rate is integrated over one day, then summed once. The original CSV's conflicting MERRA-2 label is not trusted. Native IMERG Final Run archive/version was not independently checked. |
| [NASA GLDAS Noah v2.1 monthly 0.25°](https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary), [NASA guide](https://docserver.gesdisc.eosdis.nasa.gov/public/project/hydrology/README_GLDAS2.pdf) | `gldas_soil_moisture_harrow.csv` | January 2000 to December 2025; 312 months × four layers, 1,248 rows; m³/m³. | Adopted soil-moisture source instead of the multi-terabyte SMAP collection. Four native layers: 0 to 10, 10 to 40, 40 to 100, 100 to 200 cm. Internal dates verified, no missing selected values. Source kg/m² divided by 1,000 × layer thickness in metres. |
| [ISRIC SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html), [WCS](https://maps.isric.org/), [original pH VRT](https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt) | `soilgrids_harrow.csv` | Static modeled soil properties; 0 to 5, 5 to 15, 15 to 30 cm. Eighteen diagnostic rows. No observation-year time series. | **Unavailable at the requested point.** All canonical values remain null. WCS zero pH/invalid texture was rejected; the original 250 m pH tile confirms NoData −32768. No neighboring values were substituted. |
| [FAO/IIASA HWSD v2](https://www.fao.org/land-water/resources/tools/databases/hwsd/en), [database ZIP](https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_DB.zip), [raster ZIP](https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_RASTER.zip), [technical report](https://pure.iiasa.ac.at/id/eprint/18595/1/cc3823en.pdf) | `hwsd_soil_harrow.csv` | Static regional soil estimates; seven native layers: 0 to 20, 20 to 40, 40 to 60, 60 to 80, 80 to 100, 100 to 150, 150 to 200 cm. pH, total nitrogen g/kg, organic carbon g/kg, sand/silt/clay %. | **Explicit regional fallback**, mapping unit 3070, component 1, mapped share 100%. All 42 values retain `regional_estimate`. Share is a mapping-unit attribute, not confidence in the field. Units verified against the original database metadata; organic carbon weight % multiplied by ten. Total N is not plant-available N. |

The NASA resources supplied by the user were used: **POWER, IMERG and GLDAS**. SMAP was not required once GLDAS was adopted. GLDAS is a land-surface model product, not a SMAP satellite observation. ERA5-Land was not acquired and is not claimed as an independent soil-moisture validation.

## Grid and quality evidence

- POWER uses coarse regional meteorology. The [NASA MERRA-2 grid specification](https://ntrs.nasa.gov/api/citations/20150019760/downloads/20150019760.pdf) supports inferred nearest centres **42.0, −83.125** for Harrow and **42.5, −83.125** for the buddy. Requests at those centres matched every one of the respective 1,620 parameter-month values. See `data/metadata/power_grid_checks.csv`. The point API echoes request coordinates; its exact upstream cell identifier remains **UNVERIFIED**. Matching records support the selection, not field-scale precision or statistical independence.
- GLDAS containing selected cell centre: **42.125, −82.875**, row 408, column 388, about **10.56 km** from the request point. Source grid centres and selection details are recorded in provenance.
- Missing/fill values, duplicate dates, incomplete months, units, physical screens and soil texture sums are checked. Null soil rows stay null through the database. No interpolation fills a trend.
- `data/seed/quality_report_all.csv` contains extraction checks. Historical statements such as “pending Stage 2” in the original audit describe the earlier run; later processing status is recorded in the provenance readiness section.
- `data/source/imerg_power_full_daily_evidence.csv` preserves the complete official JSON metadata and all values losslessly inside CSV cells. The original JSON response hash is retained in provenance. The original daily IMERG source CSV is also retained, with its header unchanged.

## Dataset files and provenance

- `data/metadata/downloads.csv`: flat inventory of source IDs, exact download URLs, original paths, bytes, hashes and local retention status. It includes attempted/reference resources; their presence does not mean they were used as model observations.
- `data/seed/sources.csv`: full provenance, input/output SHA-256 hashes, grid metadata, transformations, validation evidence and processing history. Nested metadata uses JSON strings **inside CSV cells** so the project retains CSV files rather than separate JSON artifacts.
- `data/source/`: unchanged small source CSVs and verification responses, including the north/centre POWER requests.
- `data/seed/`: validated model-input CSVs, diagnostic missing soil rows and calculated trends.
- `data/metadata/dataset_summary.csv`: row counts, date ranges, units and quality flags for the delivered tables.
- `data/seed/trend_results.csv`: derived climate trend table; source IDs, methods and input hashes are recorded in provenance.

## Resources referenced but not used as numerical inputs

These are still available to the model owner; they are not claimed as completed Dev data analysis:

- [FAO GAEZ v5](https://www.fao.org/gaez/en): downloaded rainfed/high-input historical suitability maps, 2001 to 2020. [Maize](https://storage.googleapis.com/fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES05-SXX30AS/GAEZ-V5.RES05-SXX30AS.HP0120.AGERA5.HIST.MZE.HRLM.tif), [soy](https://storage.googleapis.com/fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES05-SXX30AS/GAEZ-V5.RES05-SXX30AS.HP0120.AGERA5.HIST.SOY.HRLM.tif), [wheat](https://storage.googleapis.com/fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES05-SXX30AS/GAEZ-V5.RES05-SXX30AS.HP0120.AGERA5.HIST.WHE.HRLM.tif). Field suitability values were not extracted; global raster archives were removed during cleanup.
- [OMAFRA Agronomy Guide](https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-en-2022-10-13.pdf): crop requirement fallback. Ved/Vedant must confirm rainfall range periods before using them.
- [NASA challenge resource page supplied by the user](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources). SMAP, Landsat/MODIS, SRTM, ECOSTRESS and other listed sources are not required for these numerical Dev inputs. U.S.-only soil/crop resources do not establish coverage in Harrow, Ontario.

## NASA annual climate outlook data

The Harrow 2026 to 2030 outlook uses [NASA NEX-GDDP-CMIP6 v2](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/) through NASA's THREDDS NetCDF Subset service. Only the nearest point to 42.0356, −82.9183 is requested; global files are not downloaded.

| Item | Dataset details |
|---|---|
| Variables | `tas` temperature (K → °C), `pr` precipitation flux (kg/m²/s × 86,400 → daily mm, summed per month), `hurs` relative humidity (%) |
| Models | ACCESS-CM2, CanESM5, MIROC6, MPI-ESM1-2-LR, MRI-ESM2-0; member r1i1p1f1 |
| Experiments | Historical 1991 to 2014; SSP370 2015 to 2030, matching the existing GAEZ future-period emissions scenario |
| Calibration | Align each model's monthly 1991 to 2014 climatology with POWER: additive temperature/humidity change; precipitation ratio. This is monthly delta-change alignment, not a trained weather model. |
| Comparison | 2015 to 2025 held-out monthly climatologies compared with POWER. Bias and climatology RMSE are recorded; these are not measures of year-specific weather prediction skill. |
| Annual display | May to September temperature/humidity means and rain totals. Median and full spread across complete models; at least three required. Winter-wheat water requirements are not evaluated over this window. |
| Soil | No future soil moisture or changing pH/texture is synthesized. Historical July GLDAS and static HWSD2 remain separate datasets. |
| Physical limits | Source RH excursions within the NASA-documented slight overshoot range are bounded to 0 to 100; counts are retained per source. Adjusted humidity is also bounded. Negative precipitation, missing/duplicate dates, wrong units and wrong point coordinates are rejected. |

`data/seed/nex_monthly_harrow.csv` retains the monthly point extractions for 1991 to 2030. `data/seed/nex_adjusted_harrow.csv` retains aligned 2015 to 2030 monthly model values. `data/metadata/projection_sources.csv` records every actual request URL, response hash, version, grid centre, calendar, units and humidity clipping count. `data/metadata/projection_validation.csv` holds the climatology comparison. Current CSV hashes and calibration policy are recorded in `sources.csv`.

CF calendars and valid days per month are checked before aggregation. The regional source grid is 0.25°; its coverage is not field-scale resolution. A future annual value is an uninitialized climate-model scenario, not a prediction of the weather that will occur in that year. Ensemble spread is not a probability or confidence interval. These data do not establish future yields or profits.

## Satellite imagery used as a basemap

[Esri World Imagery](https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer) supplies satellite/aerial map tiles for geographic context. Attribution: Esri, Vantor, Earthstar Geographics and the GIS User Community. Imagery is not treated as a historical or forecast climate measurement; NASA grid overlays retain their own dates and resolution. Tiles load on demand and are not bundled or exported. If tiles are unavailable, the source grids and data controls remain usable.
