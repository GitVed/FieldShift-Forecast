# FieldShift Forecast

## NASA Space Apps Challenge 2026, Toronto
## Team Tuxedo

**Challenge:** Field Shift: Adapting Farms with NASA Data
**Event:** NASA Space Apps Toronto, Nov 14-15, 2026, Bombardier Centre, Centennial College Downsview, 65 Carl Hall Rd, Toronto, ON M3K 2C1
**Team:** Vedant Soni (owner), Ved Patel, Shlok Mehta, Dev Patel
**Stack:** Python, FastAPI, SQLite (PostgreSQL optional with Docker), JavaScript, Leaflet
**Submission deadline:** Sunday Nov 15, 2026, 11:59 PM EST
**Presentations and local judging:** Sunday Nov 15, 1:00 PM to 4:00 PM, closing ceremony 4:00 PM to 6:00 PM

---

## 1. Project summary

FieldShift Forecast helps a farmer choose the right crop rotation for the future, not just for last year.

A farmer near Harrow, Ontario has to decide what to plant next in rotation: corn, soy, winter wheat, with red clover as a cover crop. Summers are getting hotter and drier, soil is getting tired, input costs are rising. A wrong rotation is a lost season, lost income, and land that is harder to farm next year.

FieldShift Forecast does three things in one tool:

1. **Detect.** Prove how that exact field has already changed, 2005 to 2025, with NASA data. Temperature, rainfall, soil moisture, and vegetation health, with a real trend test, slope, p-value, confidence, and a buddy check against a nearby cell.
2. **Predict.** Project that trend to 2035. Show the field in a normal year, a dry year, and a 2035 dry year.
3. **Plan.** Recommend three ranked 3-year rotations, scored against the future, not the past, on yield, water, soil, and profit, with a drought stress test and a one-page farmer action plan in plain language.

Pilot field: Harrow / Woodslee, Essex County, Ontario, Brookston clay loam soil.

One user, one decision, one place: a family farmer near Harrow, watching summers get hotter and drier, soil getting tired, and costs rising, deciding what rotation will protect their land for the next 20 years, for their kids to farm.

---

## 2. The problem

Farmers get generic advice, regional averages, and dashboards with no decision.

NASA data can describe regional climate, but it cannot alone tell a farmer how many bushels corn vs soy vs wheat will yield on *their* field, what their soil texture and organic matter are at that spot, or what profit a rotation will make.

That is the Validity gap: a rotation score is only defensible if it is anchored to real field-level soil, real yield evidence, and real prices, not invented from a satellite image alone.

FieldShift Forecast closes that gap by combining NASA climate and vegetation data with three other sources: a published long-term Ontario rotation trial, global soil maps, and crop suitability data from Kaggle, ESA, and FAO.

---

## 3. The solution, in detail

### 3.1 Detect, trend first

For the Harrow field, run a trend test on:

- Temperature, NASA POWER, monthly T2M, 1981 to 2025
- Rainfall, GPM IMERG, monthly precipitation
- Soil moisture, SMAP L4, 9 km, 2015 to present, and GLDAS, 0.25 degree, plus ERA5-Land soil water 0 to 100 cm as a cross-check
- Vegetation health, MODIS NDVI / LST, plus Sentinel-2 NDVI / NDMI at 10 m for field-level detail
- Heat and water use, ECOSTRESS, evapotranspiration and water stress
- Terrain, SRTM / Copernicus DEM, 30 m, elevation and slope

Method: Mann-Kendall test plus Sen's slope, in degrees C per decade, mm per decade, and NDVI units per decade. Deseasonalise first, mask by quality flags. Buddy check: same test on a nearby cell about 0.5 degrees north, and a sensitivity check with start year 1991 instead of 1981. If the trend does not hold nearby, label it inconclusive.

Output: a verdict card. Example format: "Summer temperature up 0.42 C per decade, p equals 0.03, high confidence, confirmed nearby."

### 3.2 Predict, future twin

Project the trend to 2035, as a stress test, not a weather forecast.

Show three scenarios for the same field:

- Normal year, based on 1991 to 2020 baseline
- Dry year, based on real dry years, 2012 and 2021
- 2035 dry year, trend applied to the dry year

Label every projection clearly, with uncertainty. Do not present 2035 as a forecast.

### 3.3 Plan, rotation scorer

Score three ranked 3-year rotations:

- A. Corn, soy, winter wheat
- B. Corn, soy, winter wheat plus red clover underseeded
- C. Corn, soy
- D. Continuous corn or continuous soy, shown as the bad baseline

For each rotation, show:

- Estimated yield in bushels per acre, by crop, with a range
- Revenue per acre, bushels times price, and profit as an estimate with costs stated
- Soil health score, soil organic carbon trajectory, texture, pH
- Water and drought risk score, July soil moisture, heat days, NDVI in dry years
- Overall rotation score, as a percent, with a breakdown

Formula, transparent and auditable:

```
Estimated yield = Harrow trial baseline x rotation multiplier x climate adjustment
Revenue = Estimated yield x commodity price
Overall rotation score = average crop suitability % + rotation benefit - soil penalty
```

Do not use a black-box ML yield predictor. Use a rule-based scorer, with every term traceable to a dataset or a paper.

---

## 4. Datasets

### 4.1 NASA, core, required for Global Judging

| Dataset | What it gives | Use in this project | Access |
|---|---|---|---|
| NASA POWER | Monthly temperature, precipitation, humidity, radiation, 0.5 degree, 1981 to present, no key, AG community | Trend test, T2M, rainfall, heat days | API, free, no key, server-side only |
| SMAP SPL4SMGP | L4 soil moisture, 9 km, 2015 to present | July soil moisture trend | Earthdata Login, pre-fetch only |
| GPM IMERG | Precipitation, 0.1 degree, 2000 to present | Rainfall trend, dry year replay | Earthdata Login, pre-fetch only |
| MODIS MOD13 / MOD11 | NDVI, EVI, LST, 2000 to present | Vegetation health and land temperature trend | Earthdata Login, AppEEARS, pre-fetch only |
| ECOSTRESS | Evapotranspiration, water stress | Heat and water use, stress days | Earthdata, pre-fetch only |
| GLDAS / MERRA-2 | Soil moisture, temperature, 0.25 degree, 1980 to present | Cross-check for SMAP and POWER, soil water | Earthdata, Giovanni, pre-fetch only |
| SRTM | Elevation, 30 m | Slope, erosion risk, terrain | Free, pre-fetch only |
| FIRMS | Fire hotspots, MODIS and VIIRS | Not used in main build, listed as considered and rejected | Free, no key for archives |

All NASA data is pre-fetched and cached in `data/seed/`. Demo reads cache, never calls NASA live during judging. Label every number LIVE, CACHED, or SAMPLE.

### 4.2 Avenue 1, Harrow / Woodslee long-term rotation trial, Ontario, primary yield source

Source: Agriculture and Agri-Food Canada, AAFC, Dr. Craig Drury, Harrow Research and Development Centre, Woodslee, Essex County, Ontario. Long-term rotation trial established 2001, 17 rotations, planted every year, on Brookston clay loam soil. Also a 58-year trial at Woodslee and a 37-year University of Guelph trial at Elora.

Real numbers used, do not invent others:

- Continuous soybeans: 41 bu/ac, 5-year average
- Soy, soy, wheat: 53 bu/ac, plus 30 percent
- Corn, soy, wheat: 64 bu/ac, plus 50 percent
- Continuous corn: 118 bu/ac
- Corn, soy: 154 bu/ac
- Corn, soy, wheat plus red clover: 169 bu/ac, plus 43 percent over continuous corn
- Corn grain yields 38 to 42 percent greater in a 3-year corn, soy, winter wheat rotation, with and without red clover, compared to monoculture corn
- Soybean yields in the same 3-year rotation increased by 51 to 54 percent compared to monoculture soybean
- Soil organic carbon: under 2 percent with continuous soybeans, increased by 16 percent, up to 2.25 percent, in a corn, soy, winter wheat rotation after 17 years
- Across 11 long-term trials in North America, 347 site-years: diverse rotations increased average corn yields by 28 percent over time and across all growing conditions, including drought. In drought years corn yields were 14 to 90 percent greater when corn was grown following other crops in a diversified rotation compared to a simple rotation
- Fertilized continuous corn, 2016 to 2020, 5-year average: 112 bu/ac. Fertilized rotation corn: 188 bu/ac, plus 68 percent. Unfertilized continuous corn: only 17 bu/ac, not sustainable

Use: yield anchor. Anchor to Harrow trial bushels for each rotation, then adjust with NASA climate trend for that field. Show the trial source under every yield number.

### 4.3 SoilGrids WCS, soil layer

Source: ISRIC SoilGrids, global, 250 m resolution, 6 depth intervals, 0 to 5, 5 to 15, 15 to 30, 30 to 60, 60 to 100, 100 to 200 cm.

Properties: pH, soil organic carbon, bulk density, coarse fragments, sand, silt, clay, cation exchange capacity, total nitrogen, soil organic carbon density and stock. Modelled from 230,000 plus soil profiles, machine learning, with uncertainty quantified per pixel. Typical R2 0.3 to 0.6 depending on property.

REST API vs WCS:

- REST API: simple point query, GET lat/lon and get JSON back. Temporarily PAUSED by ISRIC, no timeline for restoration. Do not build the demo around live REST calls.
- WCS, Web Coverage Service: raster download, ask for a small bounding box around Harrow, get a GeoTIFF. ISRIC docs say WCS is the best way to obtain a subset and use SoilGrids as input to modelling. Endpoint: https://maps.isric.org/mapserv?map=/map/soilgrids.map

Use: pre-fetch WCS once, in the first hour, for a small Harrow bounding box, save as GeoTIFF / CSV in `data/seed/`, load into Postgres, demo reads from cache. Label it CACHED, modelled, not lab-measured. If WCS fails, fall back to Harrow trial soil, Brookston clay loam, which is ground truth for that site. Never call WCS live during judging.

### 4.4 US Corn Belt, SSURGO plus NASS, Avenue 2 branch only

Do not switch to this as the main pilot. Use only Sunday morning if time allows, to show the method works in two places.

- SSURGO, USDA Soil Data Access: field-scale soil survey for the US, per horizon: texture class, sand / silt / clay, pH, organic matter, available water capacity, Ksat, CEC, bulk density, plus drainage class, hydrologic group, taxonomy, slope. Query via SDA POST https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest, or free wrapper SoilPoint, soilpoint.dev/v1/soil?lat=42.03&lon=-93.65, no key, US only.
- NASS QuickStats: county corn, soy, winter wheat yields in bushels per acre. US average corn 186.5 bu/ac in 2025, soy 53 bu/ac, Illinois corn 214 bu/ac, soy 62.5 bu/ac, Iowa counties corn about 197 to 212 bu/ac, soy about 60 bu/ac.
- Example backup pilot: Story County, Iowa, 42.03, -93.65, SSURGO plus NASS plus NASA POWER.

Why not switch: we lose the Ontario farmer story, Toronto judges, and the Harrow trial rotation numbers, which are stronger than county averages.

### 4.5 Kaggle, suitability training data

**Crop Recommendation Dataset**
https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data

- 2,200 rows, 22 crops, 100 per crop, file 150.03 kB
- Features: Nitrogen, Phosphorus, Potassium, temperature, humidity, pH, rainfall. Target is recommended crop
- Ranges: N 0 to 140, P 5 to 145, K 5 to 205, temp 8.8 to 43.7 C, humidity 14.3 to 99.98 percent, pH 3.5 to 9.9, rainfall 20.2 to 298.6 mm
- Papers using it get Random Forest 93.71 percent accuracy on 22 crops

Use: learn the rules, wheat is good when temp is X, rainfall is Y, pH is Z, N/P/K is, and so on. Do not use for Ontario bushels. It is mostly India / tropical crops. It has maize but no wheat and no soybean. It is a suitability classifier, not a Harrow yield dataset.

**Smart Farming Data 2024, SF24**
- 2,200 records, 23 attributes, 22 crop classes
- Adds: soil moisture, soil type, organic matter, irrigation frequency, fertilizer usage, pest pressure, crop density, growth stage, water use efficiency, frost risk, sunlight, wind, CO2

Use: richer training set for Step 1, soil plus climate plus temp, all variables that affect soil and crops.

**Crop Yield Prediction dataset**
- 998,227 rows, 10 attributes, region, soil type, crop, weather, temperature, irrigation, rainfall, yield in tons per hectare
- Use: learn yield vs temp / rain / soil, as a regression check, not as Ontario ground truth

The two small sets are in `data/seed/`. The Crop Yield set has 998,227 rows, so it stays in `data/raw/` and is not shipped.

### 4.6 ESA / Copernicus, field-level vegetation and land

**Sentinel-2, ESA, via Copernicus Data Space Ecosystem**
https://browser.dataspace.copernicus.eu/

- Sentinel-2A and 2B, 10 m resolution, revisit every 5 days, 13 spectral bands
- Use: NDVI, EVI, NDMI, crop health, drought stress, bare-field periods, at field level, not 250 m to 1 km like MODIS
- NDVI example: healthy 0.72, stressed 0.14. NDMI uses NIR plus SWIR to estimate vegetation water content and crop water stress
- Download plan: Sentinel-2 L2A tiles for Harrow / Essex County, for 10 dates in 2023 to 2025 growing seasons. Each tile about 100 MB, 10 dates about 1 GB. Compute NDVI / NDMI locally, save only the derived CSV, field mean NDVI per date, a few MB, into `data/seed/`. Ship the CSV, not the 1 GB raw.

**Sentinel-1, ESA radar**
- 10 m, 6 days, penetrates clouds, soil moisture estimation and flood mapping regardless of weather
- Use: soil moisture when it is cloudy in Ontario and Sentinel-2 cannot see

**ESA WorldCover**
- Global 10 m land cover map, from Sentinel-1 and Sentinel-2, cropland is class 40, 2021 v200, accuracy roughly three quarters of pixels correct per ESA validation
- Use: is this pixel actually cropland, what was planted here before

**ESA WorldCereal**
- 10 m temporary-crop and maize classifications, 2021
- Use: crop history for a field, what was grown there last year

**Copernicus DEM, 30 m, and ERA5-Land, 0.1 degree, 1950 to present**
- DEM for elevation / slope
- ERA5-Land monthly: 2 m Tmax / Tmin, volumetric soil water 0 to 100 cm, total evaporation, runoff, 0.1 degree, monthly, 1950 to present
- Use ERA5-Land as a cross-check to NASA POWER, especially for soil water 0 to 100 cm, which POWER does not give directly

**FAO GAEZ v5**
- FAO / IIASA, suitability index, fetched at 5 arc-minutes (about 9 to 10 km), for rice, maize, cassava, soybean, and others, irrigated and rain-fed scenarios
- Use: suitability percent per crop, per place, e.g. maize suitability 78 percent in this cell under rain-fed, 62 percent under warming. That is literally a percent good score per crop, the starting point for the rotation scorer, before adjusting with Harrow trial data.

### 4.7 Prices and costs

- USDA Market News / USDA AMS for commodity prices, corn and soy, state price and date used
- OMAFRA crop budgets for input costs, if a simple number can be found, otherwise state cost as a clearly labelled assumption and show revenue only
- Revenue equals estimated bushels times price. Profit is an estimate with a range, never a single fake precise number.

---

## 5. The model, two steps

### Model 1, field conditions and crop suitability

Inputs, all from cached files. No live API in the demo.

- Field: a 300 m SAMPLE square of cropland at 42.0337, -82.9287, checked on ESA WorldCover 2021 (95 percent cropland). It replaced the first point, which sat in Harrow town. It is in the same NASA POWER, GLDAS and IMERG cells and the same GAEZ pixel, so the NASA and GAEZ data did not change
- Climate: NASA POWER monthly and daily temperature, rain and humidity, 1981 to 2025, in the POWER cell centred 42.0, -83.125. GPM IMERG rain, 1998 to 2025, is a second NASA rain source
- Soil moisture: GLDAS Noah, 0.25 degree, 0-10, 10-40 and 40-100 cm, 2000 to 2025
- Soil: ISRIC SoilGrids 250 m at the field, 0 to 30 cm, for texture and pH (pH 6.6, sand 37.5, silt 36.1, clay 26.4 percent, modelled). HWSD2 (pH 6.7) is kept as a cross-check
- Soil carbon: the local trial measurement, 2.0 to 2.25 percent (Drury, 2021). The HWSD2 global model shows 6.6 percent. We use the local measurement and do not average them. Sampling depth is not stated in the source
- Crop calendar, OMAFRA Publication 811: corn planted late April and the first half of May; soybeans best before mid May, harvested 3 to 10 days after maturity (mid September to early October); winter wheat best sown mid October in southwestern Ontario (OMAFRA Field Crop Report, 2017). Corn and wheat harvest months were not found as a calendar. May to September is the corn and soybean window only
- Suitability: FAO GAEZ v5 Suitability Index, rain-fed, high input

Scores are 0 to 100 on the GAEZ Suitability Index. They are not a percent chance.

| Crop | Normal (GAEZ 2001-2020) | 2035 view (GAEZ 2021-2040, SSP370) |
|---|---|---|
| Wheat | 97.9 | 97.9 |
| Soybean | 53.7 | 62.6 |
| Maize | 97.9 | 93.5 |

The 2012 dry year keeps the baseline score, because no source gives a crop response for one dry season. It shows the measured stress instead. May to September rain was 317 mm against a 426 mm normal. It was 1.75 C warmer. July topsoil moisture was 0.314 against 0.348.

Checks shown beside each score, never blended into it:
- Rain against FAO crop water need (FAO, Crop Water Needs, Table 5), as a range across POWER and IMERG. Normal year: rain covers 53 to 94 percent of corn need. 2012: 40 to 83 percent
- 2012 stress, measured: May to September rain 55 to 108 mm below normal across IMERG and POWER, degree days above 10 C 1698 against 1438, deeper July soil moisture lower (0.274 against 0.340 at 40-100 cm). Longest dry spells were not longer than normal
- Soil pH against the OMAFRA target for fine-textured soils. 6.7 meets the wheat, soybean and corn targets

There is no Random Forest yet. Kaggle and SF24 have no wheat or soybean. They stay for maize and general rules later.

### Model 2, rotations and why

Rule based. No ML yield predictor. Code is `backend/rotation.py`. Evidence is in `docs/EVIDENCE.md`.

- Uses only trial yields with a source link. Corn, Top Crop Manager (Drury, 2021-07-30): continuous 118, corn-soy 154, corn-soy-wheat plus red clover 169 bu/ac. Red clover adds 5 bu/ac, so corn-soy-wheat without clover is 164 bu/ac, marked DERIVED because the article does not print it. Soybean, Drury interview (2021): continuous 41, soy-soy-wheat 53, corn-soy-wheat 64 bu/ac. The article gives about 42 and 63 for 2016-2020
- Long-term trial averages from the same Woodslee trial (Agomoh et al. 2021 for soybean, 2002-2018; Agomoh et al. 2020 for winter wheat, 11 years), converted from t/ha, are shown beside the 5-year figures. They fill every soybean and wheat gap. They are never averaged with the 5-year figures and are not in the trial yield index
- Essex County 2025 winter wheat, 96.9 bu/ac (OMAFA county estimates), is shown as a regional line, not trial evidence. It is not in the trial yield index
- Prices are Grain Farmers of Ontario monthly averages for September 2026. Gross revenue is shown only when every crop yield in the rotation is verified. No profit, because costs are not verified
- Score is the trial yield index: for each crop with a trial yield, trial yield divided by the best trial yield for that crop (corn 169, soybean 64), times 100, then averaged. Crops without a yield are left out and listed
- Trial gains over continuous cropping, shown on each card: corn-soy +30.5 percent, corn-soy-wheat plus clover +43.2 percent (corn); soy-soy-wheat +29.3 percent, corn-soy-wheat +56.1 percent (soybean)
- Soil carbon is its own line, never folded into the score: continuous soybean just under 2 percent, corn-soy-wheat just over 2.25 percent, up 16 percent after 17 years

### You pick the crop, we stress-test it

`GET /api/rotation/harrow?scenario=normal&must_grow=maize&need_bu=160`

- `must_grow` is soybean, maize or wheat. `corn` is accepted as maize. Only rotations containing that crop come back. An unknown crop returns an empty list and a `message`
- Rotations are ranked by the 2012 dry year first (`rank`, same as `rank_dry`), with `rank_normal` beside it. Dry rank uses drought evidence first, then how much of the crop water need 2012 rain covered, then the trial yield index
- Drought evidence: in the worst drought years at US trial sites, maize yielded 14.0 to 88.9 percent more in more diverse rotations than in simpler ones (Bowles et al. 2020; the summary says losses were reduced 14.0 to 89.9 percent). Not Ontario. We show the low end, 14 percent. The paper scores diversity with an index of species, cover crops and rotation length; our corn-plus-two-crops rule is a simplification
- Each card shows the 2012 dry result beside the normal result as a low to high range of crop water need covered by May to September rain
- `need_bu` compares your bu/ac target with every trial figure for that crop in each rotation (5-year and long-term), with the shortfall. It also shows the per-year average over the whole rotation. When only a regional average exists, that is used and labelled
- When a crop is picked, `rank` follows that crop's trial yield (rotations without one come last). With no crop picked, `rank` is the dry-year rank
- `GET /api/crops/harrow` lists the other 21 Kaggle crops, suitability only: GAEZ v5 now and 2035, a Kaggle climate check, Ontario status and any rotation advice, with sources. No bushels or rotations for them
- New fields only: `rank_normal`, `rank_dry`, `score_kind`, `trial_gain_vs_continuous_pct`, `normal`, `dry`, `soil`, `soil_source`, `quantity` on each rotation; `must_grow`, `need_bu`, `message`, `ranking`, `crop_calendar`, `soil_carbon` on the plan. Nothing in Shlok's shape was renamed or removed. The picker on the Plan screen only sets these parameters; all filtering and ranking happen in the backend

The formula is unchanged: overall score = average suitability + rotation benefit - soil penalty. The 12, 10 and 50 point examples in early drafts were SAMPLE only and are not used.

---

## 6. Architecture

```
FieldShift Forecast
├── data/
│   ├── seed/                 # Cached data, shipped with the repo
│   │   ├── power_*_harrow_1981_2025.csv   # POWER temperature, rain, humidity (Dev)
│   │   ├── power_*_north_1981_2025.csv    # Buddy cell 0.5 degrees north (Dev)
│   │   ├── gldas_soil_moisture_harrow.csv # GLDAS, four layers (Dev)
│   │   ├── imerg_precip_harrow.csv        # IMERG rain cross-check (Dev)
│   │   ├── hwsd_soil_harrow.csv           # HWSD2 regional soil (Dev)
│   │   ├── soilgrids_harrow.csv           # All rows invalid at this point (Dev)
│   │   ├── trend_results.csv              # Mann-Kendall and Sen slope (Dev)
│   │   ├── sources.csv                    # Dev's provenance manifest
│   │   ├── gaez_harrow.csv                # GAEZ v5, three periods (Ved)
│   │   ├── kaggle_crop_recommendation.csv # 2,200 rows (Ved)
│   │   ├── sf24_smart_farming.csv         # 2,200 rows, 23 columns (Ved)
│   │   ├── model1_sources.json            # Sources for Ved's files
│   │   ├── harrow_trial_yields.csv        # Trial claims with verification column (Vedant)
│   │   └── model2_prices.json             # Dated GFO prices (Vedant)
│   └── raw/                  # Big downloads, git-ignored
├── backend/
│   ├── app.py                # FastAPI entrypoint, serves the frontend too
│   ├── field_profile.py      # Harrow profile and scenarios from cached CSVs
│   ├── suitability.py        # Model 1, GAEZ index plus water and pH checks
│   ├── rotation.py           # Model 2, evidence-gated rotation scorer
│   ├── trend.py, seed.py, db.py, data_api.py   # Dev's trend engine and cache
│   └── data_pipeline.py      # Dev's data processing
├── frontend/                 # index.html, map.js, style.css, sample_data.json
├── tests/                    # 93 tests
├── docs/                     # EVIDENCE.md, MODEL2.md
├── Dockerfile, docker-compose.yml   # Optional
└── requirements.txt
```

### Backend, FastAPI

- GET /api/pilot, pilot field, coordinates, soil, real POWER grid cells, trial site
- GET /api/detect/{cell_id}, trend verdict for the Detect screen
- GET /api/predict/{field_id}, normal, 2012 dry and 2035 dry scenarios
- GET /api/rotation/{field_id}?scenario=&must_grow=&need_bu=, rotations with the trial yield index, crop, dry and normal ranks, every yield figure, revenue, soil line and quantity check, each with its arithmetic
- GET /api/crops/{field_id}, other crops, suitability only
- GET /api/trend/{cell_id} and GET /api/series/{cell_id}, Dev's raw trend and monthly series

### Database

SQLite in `.cache/` by default, built from the cached CSVs on first start. PostgreSQL is optional with Docker. Tables: data_sources, grid_cells, monthly_climate, soil_profiles, trend_runs, rotation_scores.

### Frontend, Leaflet

Layers, named exactly:
- harrow-field, polygon, Brookston clay loam
- trend-grid-cell, POWER 0.5 degree cell for Harrow
- north-comparison-grid-cell, buddy check cell, about 0.5 degrees north
- sentinel2-ndvi, field-level NDVI, CACHED

Screens: Detect, Predict, Plan. Bundle demo geometry plus a lightweight basemap locally so the demo works offline.

---

## 7. Two-day build plan

### Saturday Nov 14

**10:00 AM to 12:00 PM, Detect core**
- Ved, data: POWER fetch for Harrow, save raw JSON and CSV, record request URL and timestamp in sources.json. SoilGrids WCS fetch for Harrow box, save GeoTIFF / CSV. Kaggle CSVs downloaded.
- Dev, backend / statistics: FastAPI skeleton, Postgres tables, trend.py, Mann-Kendall plus Sen's slope, test on POWER T2M.
- Shlok, interface: Leaflet map, Harrow field polygon, trend grid cell layer, Detect screen with verdict card.
- Vedant, science / pitch: Harrow trial numbers into harrow_trial_yields.csv, verify every number against source, draft pitch.

**12:00 PM to 6:00 PM, in building, plus remote after 6:00 PM**
- Ved: Sentinel-2 NDVI derived CSV, SMAP / IMERG pre-fetch, GAEZ suitability for Harrow.
- Dev: suitability.py, Random Forest trained on Kaggle plus SF24, rotation.py scorer, profit engine, API endpoints for rotation.
- Shlok: Predict screen, 2035 scenarios, Plan screen, rotation cards in bushels plus profit, with breakdown.
- Vedant: demo script, submission draft, Assumptions and Limitations slide, future expansion slide.

**6:00 PM, building closes, work continues remotely**
- Remote session, 6:00 PM to 11:00 PM: integrate, test offline demo, rehearse 90-second demo, fix bugs, freeze data.

### Sunday Nov 15

**8:00 AM to 1:00 PM**
- 8:00 to 10:00 AM: final build, Iowa backup field if time allows, polish UI, export farmer action plan PDF.
- 10:00 AM to 12:00 PM: rehearsal, dry run, check submission checklist, record demo video if needed.
- 12:00 PM: lunch, final check.
- 1:00 PM to 4:00 PM: team presentations and local judging.
- 4:00 PM to 6:00 PM: closing ceremony, local awards.
- 11:59 PM: project submission deadline.

### Team roles

Current owners and jobs are in TASKS.md. The plan above was the starting plan.

---

## 8. Demo script, 90 seconds

Every claim below is produced by the current build. Check it again before the demo.

**0 to 15 seconds, open**
Toronto view, zoom to the Harrow area. "This farmer near Harrow, Ontario has to choose a rotation that will still work in 2035."

**15 to 35 seconds, Detect**
"Temperature here is up 0.75 C per decade since 1981. The cell to the north agrees, and so does a 1991 start. Rainfall shows no clear trend, and July soil moisture is not significant yet. We say that too."

**35 to 55 seconds, Predict**
"Replay 2012, a real dry year. Two NASA rain datasets agree it was drier: 55 to 108 mm less summer rain. It was much hotter, 1698 degree days against 1438, and the deep soil was drier in July. Rain covered 40 to 83 percent of what corn needs. Add the warming trend for 2035 and it is 3.5 C above normal. FAO's own 2035 view lowers corn from 97.9 to 93.5."

**55 to 75 seconds, Plan**
"Pick the crop you must grow. Say corn. Only rotations with corn come back, ranked by corn's trial yield. Corn after soybean and wheat with red clover gave 169 bu/ac, against 118 in continuous corn, 43 percent more. In drought years at US trial sites, diverse rotations gave corn at least 14 percent more. Tell us you need 160 bu/ac and corn-soy, at 154, falls 6 short. That is per acre in a corn year, one year in three. Open 'Show the math' and every number traces to its source."

**75 to 90 seconds, close**
"We are not replacing your experience. We give you 45 years of measured change, a real dry-year replay, and trial evidence with a source under every number."

---

## 9. 30-second pitch

A farmer near Harrow, Ontario has to pick a rotation that will work in 2035, not just last year. FieldShift Forecast shows how the area has already changed with NASA data, replays the 2012 drought, stress-tests 2035, and compares rotations using a long-term AAFC trial with a source under every number. That is evidence a farmer can check.

---

## 10. Assumptions, limitations, and future work

Assumptions and limitations, to show in the demo and in the submission:

- The trial is at Woodslee, about 26 km from the field and in a different POWER grid cell. Trial numbers are evidence for the area, not a yield promise for this field.
- The field is a 300 m SAMPLE square of cropland from ESA WorldCover, not a surveyed farm field.
- Soil texture and pH are SoilGrids modelled values at the field, not a field soil test. Soil carbon uses the local trial measurement, 2.0 to 2.25 percent, not the HWSD2 global model value of 6.6 percent. Sampling depth is not stated in the trial source.
- Kaggle Crop Recommendation and SF24 are mostly India and tropical crops. They have maize but no wheat or soybean. They are not used for scores yet.
- GAEZ is a 5 arc-minute grid, about 9 to 10 km, not field level. Its scores are a suitability index, not a percent.
- POWER is a 0.5 by 0.625 degree grid. It describes the region, not a field microclimate.
- May to September is the corn and soybean window from the OMAFRA 2017 calendar as supplied (not checked here). Winter wheat grows late August to July, so its water check is not computed.
- The 2035 view applies the measured temperature trend to 2012. Rain is not extrapolated because its trend is inconclusive. It is a stress test, not a forecast.
- Corn-soy-wheat corn (164 bu/ac) is derived from two stated figures. Five-year and long-term trial averages cover different years and are shown side by side. Trial yields are historical, not a forecast. Revenue is gross, with a dated price. There is no profit figure. The trial site is a point, Woodslee, 42 degrees 13 minutes N, 82 degrees 44 minutes W.
- Kaggle and SF24 are used only for a climate check on other crops. Their rows are mostly from India, and rainfall is not used because its period is unknown.
- Hydrology Time Series Viewer was reported failing Nov 13 to 14, 2026, HTTP 500. We used POWER and GLDAS directly.

Future work, the limited-data framing:

> We built this on one public soil type, Brookston clay loam at Harrow, and public NASA data. That is the limit of public data. If a farmer uploads their own soil test, or their yield monitor history from their combine, the same engine personalises the scores to their field, their soil, their yields. The prototype proves the method, the farmer's data makes it theirs.

Next steps, in order:
1. Farmer-uploaded soil test, N, P, K, pH, SOC, to replace SoilGrids modelled values
2. Yield monitor history, to replace Harrow trial anchor with field-specific bushels
3. More pilot fields, Elora and Ridgetown, same method, different soil and climate
4. Irrigation and market price scenarios, what if wheat price drops, what if it is a wet year
5. One-page printable farmer action plan, in plain language, with dates and what to watch for in July

---

## 11. Judging criteria, how we score

General Space Apps judging: Impact, Creativity, Validity, Relevance, Presentation, 1 to 5 each.

- Impact: Ontario farmer, food security, soil health for the next generation, drought resilience
- Creativity: Trend Detective as the engine inside Field Shift, future twin to 2035, rotation scored in real bushels
- Validity: NASA trend with Mann-Kendall and buddy check, Harrow trial bushels with source, SoilGrids labelled modelled, assumptions stated, no invented numbers
- Relevance: Field Shift challenge, NASA data required, Canadian agriculture, Harrow pilot
- Presentation: 90-second Detect, Predict, Plan demo, one farmer, one decision, one place, transparent scores

---

## 12. Setup

### Prerequisites

- Python 3.11 or later
- Docker, optional, only for PostgreSQL
- Kaggle, Earthdata and Copernicus accounts are only needed to refetch data. The cached data is in the repo

### Quick start

```bash
git clone https://github.com/GitVed/Tuxedo.git
cd Tuxedo
pip install -r requirements.txt
python -m uvicorn backend.app:app --port 8765
# Open http://localhost:8765/frontend/?api=1
# The SQLite cache builds itself on first start. No live API calls.
```

Use any free port. On some machines port 8000 is already taken.

The app opens at http://localhost:8765/ (Dev's frontend). Screens: Outlook (climate, trend card, map), Rotations (ordered by trial evidence), My crop (target check) and Other crops (suitability only). New API routes from Dev: `/api/timeline/harrow` and `/api/recommendations/harrow?year=2026&must_grow=soybean&need_bu=60`. Recommendations put trial evidence first; the year changes the rain-fit check, not the order. Browser check: `python tests/browser_check.py --url http://127.0.0.1:8765/`.

### Tests

```bash
python -m pytest tests
```

### Optional, PostgreSQL with Docker

```bash
POSTGRES_PASSWORD=choose-one docker compose up --build
```

### Random Forest

Not built. Kaggle and SF24 have no wheat or soybean. See TASKS.md.

---

## 13. Sources, cite every number

- NASA Space Apps Toronto 2026, Field Shift challenge page, https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/
- NASA POWER, https://power.larc.nasa.gov/
- SMAP, GPM IMERG, MODIS, ECOSTRESS, GLDAS, SRTM, NASA Earthdata, https://www.earthdata.nasa.gov/
- AAFC Harrow, Dr. Craig Drury, Woodslee long-term rotation trial, 2001 to present, Essex County, Ontario
- ISRIC SoilGrids, https://www.isric.org/explore/soilgrids, WCS https://maps.isric.org/mapserv?map=/map/soilgrids.map
- Kaggle Crop Recommendation Dataset, https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data
- Kaggle Smart Farming Data 2024, SF24
- ESA Sentinel-2, Copernicus Data Space Ecosystem, https://browser.dataspace.copernicus.eu/
- ESA WorldCover, https://worldcover2021.esa.int/
- ESA WorldCereal, https://worldcereal.earth/
- FAO GAEZ v5, https://gaez.fao.org/
- USDA SSURGO, https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest
- USDA NASS QuickStats, https://quickstats.nass.usda.gov/
- USDA Market News, https://www.ams.usda.gov/market-news

---

## 14. AI use disclosure

AI tools were used to research datasets, evaluate ideas, and help plan and build. The final solution direction and decisions were made by Team Tuxedo.

AI tools used: Muse, ChatGPT, Claude. AI was used for dataset research, idea evaluation, build planning, and code assistance. AI was not used to submit the project on behalf of the team. Generated code and data are acknowledged in the submission. No NASA branding is used in AI-generated content. AI-generated images or video, if any, are watermarked.

The team did a 12-minute team exercise in its own words to originate and refine the final idea, changed the pilot field, crops, and demo flow, and made the final build decisions.

---

## 15. Licence and credits

Data licences:
- NASA data, public domain, free use, cite source
- SoilGrids, CC BY 4.0
- ESA WorldCover, CC BY 4.0
- GAEZ, FAO, free use with attribution
- Kaggle datasets, as per Kaggle licence, check each dataset page
- Harrow trial data, AAFC, cite Dr. Craig Drury and AAFC Harrow

Code: MIT, unless otherwise stated in the repo.

Team Tuxedo, NASA Space Apps Toronto 2026.
