# FieldShift Forecast, full context

> Model 2 update (2026-11-14): Vedant's independent scorer and 14 tests now exist. Default evidence-only mode leaves unsupported overall scores pending; opt-in SAMPLE ranking supports UI development. Three soybean yield references and dated prices are cached. Corn/wheat yields, score calibration, trial/pilot location matching and live model integration remain open. See [Model 2 handoff](docs/MODEL2.md), [evidence audit](docs/EVIDENCE.md), and [presentation drafts](docs/VEDANT_PRESENTATION_DRAFT.md). Older planning claims below are not automatically verified.

This file is the full context for teammates and for any AI assistant helping on the project. If you are an AI, read this whole file before you change anything. Do not start over. Do not invent numbers.

The short, presentable version is README.md. Jobs and owners are in TASKS.md.

Last updated Sat Nov 14, 2026, late night. All four branches are integrated on `ved/model`, not yet on main.

---

## 1. The project in one line

FieldShift Forecast helps a farmer near Harrow, Ontario choose a crop rotation that will survive the future, not just last year. Detect how the field changed, predict it to 2035, then plan a rotation scored in bushels, soil, water, and profit.

- Repo name is FieldShift Forecast
- Repo URL is https://github.com/GitVed/Tuxedo.git
- Team Tuxedo is Vedant Soni (owner), Ved Patel, Shlok Mehta, Dev Patel
- Event is NASA Space Apps Toronto, Nov 14 to 15, 2026, Bombardier Centre, 65 Carl Hall Rd, Toronto
- Challenge to submit under is Field Shift, Adapting Farms with NASA Data
- Submission deadline is Sun Nov 15, 11:59 PM EST
- Presentations and local judging Sun 1 to 4 PM, closing 4 to 6 PM
- Building closes 6 PM Sat and Sun. Work continues remote after 6 PM

## 2. Current status and who is doing what

Integrated on `ved/model`: Dev's cached NASA and soil data, Model 1 on real data, Vedant's Model 2, Shlok's frontend, and the API. 59 tests pass. Not yet on main.

| Person | Current job |
|---|---|
| Dev Patel | Done: POWER, GLDAS, IMERG, HWSD2 cached, trend engine, SQLite and optional Postgres. Open: soil carbon check |
| Ved Patel | Done: Model 1 on real data, API, integration. Now also covering the open evidence items |
| Shlok Mehta | Done: frontend, now wired to the API. Open: offline map tiles, print layout |
| Vedant Soni | Done: Model 2 scorer, evidence audit, prices. Open: corn and wheat yields, pitch angle, submission |

Details are in TASKS.md. We use one git branch per person (`dev/data`, `ved/model`, `shlok/front`, `vedant/model2`) and merge small pieces to main often. Main must always run.

## 3. Two models, the core idea, do not change it

**Model 1 predicts the condition of the place.**
- Input is soil, climate, and temperature for that exact field. Only features we can get for Harrow at demo time. Temperature, rainfall, humidity, pH, nitrogen, soil moisture, soil organic carbon, sand, silt, clay. No P or K
- Output is a field profile and a suitability percent for each crop
- Example (SAMPLE, not real output). Wheat 82 percent, corn 71 percent, soy 88 percent, with the reason for each percent shown

**Model 2 recommends crops and rotation, with why, backed by data.**
- Input is the suitability percents from Model 1
- Output is a ranked rotation and why
- Why this crop, because of its FAO GAEZ suitability index here, its FAO crop water need against measured rain, and its OMAFRA pH target. See section 3c
- Why this rotation, because trial data shows soybeans at 64 bu/ac after corn and wheat against 41 bu/ac in continuous soy (verified). The corn gains are not verified yet. Soil carbon rises from under 2 percent to 2.25 percent. Diverse rotations are 14 to 90 percent better in drought years
- Overall percent is average crop suitability plus rotation benefit minus soil penalty
- Example (SAMPLE). Corn, soy, wheat 92 percent. Corn, corn, soy 67 percent. Continuous soy 38 percent

Model 2 is NOT a black-box ML yield predictor. It is a transparent rule-based scorer. Every percent traces to a dataset or a paper.

```
Overall rotation score = average crop suitability + rotation benefit - soil penalty
Estimated yield        = Harrow trial baseline x rotation multiplier x climate adjustment (from NASA trend)
Revenue                = Estimated yield x commodity price (price and date stated)
```

Open item. The rule for the climate adjustment is not defined yet. Until the team agrees one, use 1 (no change) and label it an assumption.

## 3b. Model 1 fix, decided Sat Nov 14, 2:45 PM

Problem. The Kaggle Crop Recommendation set has maize but no wheat and no soybean. SoilGrids has nitrogen but no P or K.

Decision
- FAO GAEZ is the main source for wheat, soybean, and maize suitability. Fetch it for the Harrow point, rain-fed, save to `data/seed/gaez_harrow.csv` with a suitability percent per crop
- Kaggle is secondary, for maize and general rules only. Never use it for wheat or soy
- Check the SF24 crop labels first. Do not assume wheat or soy are in it
- Drop P and K from Model 1. Inputs are temperature, rainfall, humidity, pH, nitrogen, soil moisture, soil organic carbon, sand, silt, clay
- If GAEZ is slow, use OMAFRA ranges as a rule-based fallback and label them as ranges, not model output
- Do not invent wheat or soy training data. If a crop is not in GAEZ or Kaggle, say so in the code and do not score it

Harrow point, provided by Ved. 42.0356, -82.9183. Vedant to confirm.

OMAFRA ranges, provided by Ved, UNVERIFIED until Vedant checks the source
- Wheat. pH 6.0 to 7.5, moisture 350 to 650 mm, optimum temperature 10 to 25 C
- Soybean. pH 6.0 to 7.0, moisture 450 to 700 mm, development temperature 20 to 30 C
- Maize. No range supplied yet. Get one from OMAFRA or do not score it by this fallback
- Confirm which period the mm values cover

Catches to keep in mind
- GAEZ gives one number per crop at a point. That is a lookup baseline, not training data. A Random Forest needs many rows
- A fixed GAEZ number will not change in the dry-year and 2035 views. Range fit scores will, because they use temperature and rain
- Kaggle nitrogen is kg/ha, so do not mix it with SoilGrids nitrogen. Kaggle also has no soil moisture, organic carbon, or texture
- How to download GAEZ is UNVERIFIED. Check the GAEZ data portal

## 3c. Model 1 method, decided Sat Nov 14 evening

This replaces the OMAFRA range fallback in 3b. Vedant's evidence audit (docs/EVIDENCE.md) found no source for those temperature and rain ranges.

- Normal year score is the GAEZ v5 Suitability Index, 2001-2020, rain-fed, high input
- 2035 score is GAEZ v5, 2021-2040, SSP370 ensemble. It is FAO's own future-climate suitability
- The 2012 dry year keeps the baseline score and shows measured stress beside it. No source gives a crop response for one dry season
- Beside each score: May to September rain against the FAO crop water need, and soil pH against the OMAFRA target. These are shown, never blended into the score
- Scenarios come from Dev's data. Normal is 1991-2020. Dry is 2012. 2035 dry is 2012 plus the measured temperature trend. Rain is not extrapolated because its trend is inconclusive
- Field moved Sat Nov 14 night from 42.0356, -82.9183 (Harrow town, built-up) to 42.0337, -82.9287, a 300 m SAMPLE square that is 95 percent cropland on ESA WorldCover 2021. Same POWER, GLDAS and IMERG cells and the same GAEZ pixel, so cached data is unchanged. The trial site is about 26 km away at Woodslee, in a different POWER cell. Say so wherever trial numbers appear
- Soil texture and pH come from SoilGrids 250 m at the field (valid there, unlike the town point). Soil carbon comes from the trial, 2.0 to 2.25 percent
- Rain uses two NASA sources, POWER and IMERG, shown as a range. 2012 was 55 to 108 mm drier than normal and much hotter, but dry spells were not longer
- Long-term trial averages (Agomoh et al. 2020, 2021) are shown beside the 5-year trial figures and never averaged with them. Essex 2025 winter wheat is a regional line only
- Bowles et al. 2020 drought result is from US sites only. Say so

## 4. Decision locked, Avenue 1 Harrow is main

We chose ONE main avenue to fill the missing dataset gap. Avenue 1 is Harrow / Woodslee, Ontario, on the main branch. Do not reopen the main decision.

Avenue 2 is not dropped. It is a separate branch we can work on if we have time. Keep it out of main until Avenue 1 is done and demoable.

- `main` is Avenue 1 Harrow only. This is the demo, the submission, and the pitch
- Branch `avenue-2-global` is Avenue 2, popular global areas, starting with US Corn Belt Iowa as the test case
- Work on Avenue 2 only after Step 6 integration is done, or by one person in parallel who is not blocking main
- Never push Avenue 2 code to main without a team check
- SoilGrids WCS is not a competing avenue. It is the soil layer inside Avenue 1
- Kaggle and ESA are supporting data inside Avenue 1

Why Harrow
- Real bushels in Ontario on Brookston clay loam from a published long-term trial
- Toronto judges get the Ontario farmer story right away
- Buildable today, numbers already known, no new API to learn

## 5. Avenue 1, the Harrow trial, main yield source

Source is Agriculture and Agri-Food Canada (AAFC), Dr. Craig Drury, Harrow Research and Development Centre, Woodslee, Essex County, Ontario. The trial started in 2001, has 17 rotations, is planted every year, and sits on Brookston clay loam. There is also a 58-year trial at Woodslee and a 37-year University of Guelph trial at Elora.

Use these exact numbers. Do not invent others.

- Continuous soybeans, 41 bu/ac, 5-year average
- Soy, soy, wheat, 53 bu/ac, plus 30 percent
- Corn, soy, wheat, 64 bu/ac, plus 50 percent
- Continuous corn, 118 bu/ac
- Corn, soy, 154 bu/ac
- Corn, soy, wheat plus red clover, 169 bu/ac, plus 43 percent over continuous corn
- Corn grain yields are 38 to 42 percent greater in a 3-year corn, soy, winter wheat rotation, with and without red clover, compared to monoculture corn
- Soybean yields in the same 3-year rotation are 51 to 54 percent greater than monoculture soybean
- Soil organic carbon is under 2 percent with continuous soybeans. It rose 16 percent, up to 2.25 percent, in a corn, soy, winter wheat rotation after 17 years
- Across 11 long-term trials in North America (347 site-years), diverse rotations increased average corn yields by 28 percent over time and across all growing conditions, including drought. In drought years corn yields were 14 to 90 percent greater in a diversified rotation than in a simple rotation
- Fertilized continuous corn, 2016 to 2020, was 112 bu/ac. Fertilized rotation corn was 188 bu/ac, plus 68 percent. Unfertilized continuous corn was only 17 bu/ac

Use the trial as the yield anchor. Show the trial source under every yield number.

**Numbers Vedant must verify.** These need a check against the source.
- Soy at 64 bu/ac is called plus 50 percent, but continuous soy is 41. That does not obviously match
- Corn gains appear as 38 to 42, 43, and 68 percent. These may use different bases and periods

## 6. SoilGrids, REST is paused, WCS works

- REST API is a simple point query. ISRIC has paused it with no restore date. Do not build the demo on live REST calls
- WCS is a raster download. Ask for a small box around Harrow and get a GeoTIFF. ISRIC says WCS is the best way to get a subset. Endpoint is https://maps.isric.org/mapserv?map=/map/soilgrids.map
- SoilGrids is global, 250 m, 6 depths. It gives pH, soil organic carbon, bulk density, coarse fragments, sand, silt, clay, CEC, total nitrogen, and SOC density and stock
- It is modelled from 230,000 plus profiles, with typical R2 of 0.3 to 0.6

How to use it
- Pre-fetch WCS once in the first hour for a small Harrow box
- Save as GeoTIFF or CSV in `data/seed/` and load into Postgres. The demo reads cache
- Label it CACHED, modelled, not lab-measured
- If WCS fails, fall back to Harrow trial soil, Brookston clay loam
- Never call WCS live during judging

## 7. NASA datasets, Dev is verifying this now

All NASA data is pre-fetched and cached. The demo reads the cache and never calls NASA live.

- NASA POWER, monthly temperature, precipitation, humidity, radiation. 0.5 degree, 1981 to present, free, no key, community AG, server side only. Used for the trend test
- SMAP SPL4SMGP, L4 soil moisture, 9 km, 2015 to present, Earthdata login, pre-fetch only
- GPM IMERG, precipitation, 0.1 degree, 2000 to present, Earthdata login, pre-fetch only
- MODIS MOD13 and MOD11, NDVI, EVI, land surface temperature, 2000 to present, Earthdata login, AppEEARS, pre-fetch only
- ECOSTRESS, evapotranspiration and water stress, Earthdata, pre-fetch only
- GLDAS and MERRA-2, soil moisture and temperature, 0.25 degree, 1980 to present, Giovanni, pre-fetch only
- SRTM, elevation, 30 m, free, pre-fetch only
- FIRMS fire hotspots, considered and rejected, not in the main build

POWER URL pattern, fill in the Harrow coordinates, not Toronto City Hall
`https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M&community=AG&longitude=LON&latitude=LAT&start=1981&end=2025&format=JSON`

Trend method
- Mann-Kendall test plus Sen's slope, in degrees C per decade, mm per decade, and NDVI per decade
- Deseasonalise first and mask by quality flags
- Buddy check, run the same test on a cell about 0.5 degrees north
- Sensitivity check with start year 1991 instead of 1981
- If the trend does not hold nearby, label it inconclusive

Known issues
- The Hydrology Time Series Viewer was reported failing Nov 13 to 14, 2026 (HTTP 500). Use Giovanni and POWER directly
- SMAP only starts in 2015, so any trend on it is based on a short record

Dev's check, step by step
1. Can we fetch POWER for Harrow, 1981 to 2025, temperature and precipitation, and save CSV?
2. Can we fetch SMAP and IMERG for Harrow and save CSV?
3. Are the values plausible, with no fill values and no missing months that break the trend?
4. Does the trend hold in the buddy cell?
5. If any dataset fails, note the fallback in `sources.json` and move on. Harrow trial plus POWER alone is enough for a demo

## 8. Kaggle datasets

**Crop Recommendation Dataset**, https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data
- 2,200 rows, 22 crops, 100 per crop, 150.03 kB
- Features are N, P, K, temperature, humidity, pH, rainfall. Target is the recommended crop
- Ranges are N 0 to 140, P 5 to 145, K 5 to 205, temperature 8.8 to 43.7 C, humidity 14.3 to 99.98 percent, pH 3.5 to 9.9, rainfall 20.2 to 298.6 mm
- Papers report 93.71 percent Random Forest accuracy on the 22 crops
- Use it to learn suitability rules. Do NOT use it for Ontario bushels. It is mostly India and tropical crops. The 22 crops include maize but NOT wheat or soybean (checked against papers that list the crop labels)

**Smart Farming Data 2024 (SF24)**
- 2,200 records, 23 attributes, 22 crop classes
- Adds soil moisture, soil type, organic matter, irrigation frequency, fertilizer usage, pest pressure, crop density, growth stage, water use efficiency, frost risk, sunlight, wind, and CO2
- Use as a richer training set for Model 1

**Crop Yield Prediction dataset**
- 998,227 rows, 10 attributes. Region, soil type, crop, weather, temperature, irrigation, rainfall, yield in tons per hectare
- Use as a regression check only, not Ontario ground truth
- Note, a file this size is not "under 5 MB". Keep it in `data/raw/`, git-ignored

Watch the units. Kaggle rainfall tops out near 299 mm, so it is probably a shorter period than a year. Match the period before feeding in Harrow rainfall.

## 9. ESA and Copernicus datasets, and the 1 GB idea

Mentor advice is to download a large dataset once and use it locally instead of making API calls. Do that, compute derived CSVs, ship only the small CSVs, and never ship the raw files.

- **Sentinel-2** via Copernicus Data Space, https://browser.dataspace.copernicus.eu/. 10 m, revisit every 5 days, 13 bands. Gives NDVI, EVI, NDMI, crop health, and drought stress at field level. Example NDVI is healthy 0.72 and stressed 0.14. Plan is L2A tiles for Harrow / Essex County on 10 dates in the 2023 to 2025 growing seasons, about 100 MB per tile and about 1 GB total. Compute NDVI and NDMI locally and save only the field mean per date into `data/seed/`
- **Sentinel-1** radar. 10 m, 6 days, sees through cloud. Use for soil moisture when Sentinel-2 cannot see
- **ESA WorldCover**. Global 10 m land cover, cropland is class 40, 2021 v200, roughly three quarters correct. Use to check a pixel is really cropland
- **ESA WorldCereal**. 10 m temporary-crop and maize maps, 2021. Use for crop history
- **Copernicus DEM** (30 m) for elevation and slope
- **ERA5-Land** (0.1 degree, 1950 to present). Monthly max and min temperature, soil water 0 to 100 cm, evaporation, runoff. Use as a cross-check on POWER, especially soil water, which POWER does not give directly
- **FAO GAEZ v5**. FAO / IIASA, 1 km suitability index for maize, soybean, and others, irrigated and rain-fed. Gives a percent good score per crop per place, the starting point for Model 2 before Harrow adjustment

## 10. Why a farmer would trust this

An experienced farmer will not take a model at face value. They know their land, satellite data is coarse, the model has never farmed a season, and if it is wrong they lose the season, not us.

Our answer, in this order
1. Show we know what they know. Continuous soy wears soil out. Corn after corn gets weaker. The Harrow trial shows it, 41 bu/ac for continuous soy, 118 bu/ac for continuous corn, and soil carbon under 2 percent
2. Show what they cannot see. Twenty years of trend in one glance, temperature, July soil moisture, and NDVI in dry years, with slope, p-value, and buddy check
3. Backtest, do not just predict. Replay 2012, a real drought year. The trial says corn in a diverse rotation did 14 to 90 percent better than in a simple one
4. Show money and risk, not only yield. Revenue is bushels times price with price and date stated, plus soil carbon trajectory, plus the downside in a dry year. Show a range, not a single fake number
5. Make it their data. If a farmer uploads a soil test or yield monitor history, the same engine personalises the scores
6. Be honest about uncertainty. Source under every number, LIVE / CACHED / SAMPLE labels, assumptions stated

**Pitch line.** We are not replacing your experience. We are giving you 20 years of measured change, 17 years of trial evidence, and a dry-year replay, so you can make the same decision you would make, but with more evidence.

**Future work wording for the submission**

We built this on one public soil type, Brookston clay loam at Harrow, and public NASA data. That is the limit of public data. If a farmer uploads their own soil test, or their yield monitor history from their combine, the same engine personalises the scores to their field. The prototype proves the method, the farmer's data makes it theirs.

## 11. Avenue 2, global, optional branch

Avenue 2 means picking a popular, data-rich global area and giving a recommendation there with the same two models.

Can we do it globally
- Suitability, technically yes. SoilGrids, GAEZ, ERA5-Land, POWER, and Sentinel-2 are all global, so you could click any spot and get a suitability percent
- Credible yield, no, not in a weekend. Bushels for a rotation on that soil, rotation evidence, prices, costs, varieties, pests, and local rules only exist where there is a long-term trial like Harrow or a county system like NASS in the US

The one place where it almost works is the US Corn Belt, Iowa and Illinois. SSURGO soil at field level, NASS county bushels, CDL crop history at 30 m, and PRISM climate all line up. It is one US region, not any global spot.

Model 1 is portable. Same code, same Random Forest, new latitude and longitude, new fetches. Model 2 keeps the same formula, but the yield anchor, rotation multipliers, and prices must be replaced. Harrow numbers do NOT transfer to Iowa or anywhere else.

Build with a field config file so swapping a place is a config change, not a rewrite. The config holds field name, lat, lon, soil type, trial file, and price file.

Avenue 2 work, only if time, in order
1. Create branch `avenue-2-global`, copy main code, do not touch main
2. Swap the config to Story County, Iowa, 42.03, -93.65. Fetch SSURGO through SoilPoint, `soilpoint.dev/v1/soil?lat=42.03&lon=-93.65` (no key, US only), plus NASS county yields. Check any Iowa figures against the source before use
3. Recalibrate Model 2 with Iowa numbers and re-run the 2012 dry-year backtest
4. Show it as a second validation field in the pitch, not the main demo, unless the team agrees Sunday morning
5. If no Iowa trial numbers can be verified, show suitability percent only, from GAEZ plus SoilGrids, with no bushels, clearly labelled

Decision. Do Harrow deep, not global shallow. Build the method so it can go global, say that in the pitch, demo it on Harrow only.

## 12. Stack, structure, API

**Stack**
- Backend, Python, FastAPI, PostgreSQL, Docker
- ML, Python, pandas, scikit-learn Random Forest
- Frontend, JavaScript, Leaflet, HTML and CSS, no React
- Data, NASA POWER, SMAP, IMERG, MODIS, SoilGrids WCS, Sentinel-2, Kaggle CSVs, Harrow trial CSV

**Repo structure**
- `data/seed/` cached data shipped with the repo
- `data/raw/` big downloads, git-ignored, never shipped
- `backend/` app.py, trend.py, suitability.py, rotation.py, db.py
- `frontend/` index.html, map.js, style.css
- `notebooks/` 01_power_fetch, 02_soilgrids_wcs, 03_sentinel2_ndvi, 04_train_suitability
- docker-compose.yml, requirements.txt, README.md, SUMMARY-README.md, TASKS.md

**FastAPI endpoints, named exactly**
- GET /api/pilot
- GET /api/series/{cell_id}
- GET /api/trend/{cell_id}
- GET /api/rotation/{field_id}
- POST /api/refresh (optional)

**Postgres tables.** data_sources, grid_cells, monthly_climate, soil_profiles, trend_runs, rotation_scores

**Leaflet layers.** harrow-field, trend-grid-cell, north-comparison-grid-cell, sentinel2-ndvi

## 13. Rules for everyone, including AI assistants

- Do not invent bushels, soil values, prices, coordinates, or dataset codes. If unsure, write UNVERIFIED, say how to check, and give the fallback
- Label every number LIVE, CACHED, or SAMPLE
- Pre-fetch and cache. The demo reads cache and never calls an API live
- Keep README.md and TASKS.md in plain language, short sentences, no em dashes
- Do not reopen the Harrow-as-main decision
- Do not merge Avenue 2 into main without a team check
- Do not commit big raw files. Use `data/raw/`
- Ask before making large structural changes

## 14. Open items

- Field is a SAMPLE cropland square at 42.0337, -82.9287 (section 3c). The trial site is about 26 km away
- Prices are chosen: Grain Farmers of Ontario, September 2026 (docs/EVIDENCE.md)
- Corn yields are sourced (Top Crop Manager 2021), soybean and wheat have 5-year and long-term trial figures. See docs/VERIFY.md
- Rotation benefit and soil penalty weights have no source, so the overall rotation score stays pending
- The climate adjustment for yield stays 1. Climate shows through Model 1 and the stress facts instead
- Soil carbon decided: use the trial's 2.0 to 2.25 percent, not HWSD2's 6.6 percent
- Crop calendar now quotes OMAFRA Pub 811. Corn and wheat harvest months were not found as a calendar
- July soil moisture trend is not significant (2000 to 2025). Do not claim it is falling

## 14b. Gaps found in review, Sat 2 PM

- Model 1 wheat and soy gap and the P and K gap are decided. See section 3b
- The Predict screen (normal, dry, 2035 dry, and the 2012 replay) had no owner. See TASKS.md
- Postgres and Docker add risk and are not needed for the demo to work. Read the CSVs with pandas first
- Sentinel-2 and MODIS NDVI and GAEZ fetches have no owner. Treat NDVI as a stretch goal

## 15. Demo flow, 90 seconds, outline only

Vedant writes the full script. The flow is below.
1. Open on Toronto, zoom to the Harrow field. The farmer has to pick a rotation that still works in 2035
2. Detect. Click the field, show the trend verdict with slope, p-value, and buddy check
3. Predict. Show the 2035 dry-year view as a stress test
4. Plan. Show ranked rotations with bushels, revenue, soil, and why
5. Close with the evidence sentence and the farmer data future work

Claims in the demo must come from what the model actually produces and from the trial numbers above.

## 16. AI use disclosure

AI tools were used to research datasets, evaluate ideas, and help plan and build. Final solution direction and decisions were made by Team Tuxedo. AI was not used to submit the project. Generated code and data are acknowledged. No NASA branding is used in AI-generated content.

## 17. Licences and credits

NASA data is public domain, cite the source. SoilGrids and ESA WorldCover are CC BY 4.0. GAEZ is free with attribution. Check each Kaggle dataset page. Harrow trial data belongs to AAFC, cite Dr. Craig Drury and AAFC Harrow. Code is MIT unless the repo says otherwise.

Team Tuxedo, NASA Space Apps Toronto 2026.
