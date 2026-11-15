# FieldShift Forecast

## NASA Space Apps Challenge 2026, Toronto
## Team Tuxedo

**Challenge:** Field Shift: Adapting Farms with NASA Data
**Event:** NASA Space Apps Toronto, Nov 14-15, 2026, Bombardier Centre, Centennial College Downsview, 65 Carl Hall Rd, Toronto, ON M3K 2C1
**Team:** Vedant Soni (owner), Ved Patel, Shlok Mehta, Dev Patel
**Stack:** Python, FastAPI, PostgreSQL, Docker, JavaScript, Leaflet
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

### 4.3 Avenue 2, SoilGrids WCS, soil layer

Source: ISRIC SoilGrids, global, 250 m resolution, 6 depth intervals, 0 to 5, 5 to 15, 15 to 30, 30 to 60, 60 to 100, 100 to 200 cm.

Properties: pH, soil organic carbon, bulk density, coarse fragments, sand, silt, clay, cation exchange capacity, total nitrogen, soil organic carbon density and stock. Modelled from 230,000 plus soil profiles, machine learning, with uncertainty quantified per pixel. Typical R2 0.3 to 0.6 depending on property.

REST API vs WCS:

- REST API: simple point query, GET lat/lon and get JSON back. Temporarily PAUSED by ISRIC, no timeline for restoration. Do not build the demo around live REST calls.
- WCS, Web Coverage Service: raster download, ask for a small bounding box around Harrow, get a GeoTIFF. ISRIC docs say WCS is the best way to obtain a subset and use SoilGrids as input to modelling. Endpoint: https://maps.isric.org/mapserv?map=/map/soilgrids.map

Use: pre-fetch WCS once, in the first hour, for a small Harrow bounding box, save as GeoTIFF / CSV in `data/seed/`, load into Postgres, demo reads from cache. Label it CACHED, modelled, not lab-measured. If WCS fails, fall back to Harrow trial soil, Brookston clay loam, which is ground truth for that site. Never call WCS live during judging.

### 4.4 Avenue 3, US Corn Belt, SSURGO plus NASS, backup only

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

Use: learn the rules, wheat is good when temp is X, rainfall is Y, pH is Z, N/P/K is, and so on. Do not use for Ontario bushels. It is mostly India / tropical crops, plus maize and wheat. It is a suitability classifier, not a Harrow yield dataset.

**Smart Farming Data 2024, SF24**
- 2,200 records, 23 attributes, 22 crop classes
- Adds: soil moisture, soil type, organic matter, irrigation frequency, fertilizer usage, pest pressure, crop density, growth stage, water use efficiency, frost risk, sunlight, wind, CO2

Use: richer training set for Step 1, soil plus climate plus temp, all variables that affect soil and crops.

**Crop Yield Prediction dataset**
- 998,227 rows, 10 attributes, region, soil type, crop, weather, temperature, irrigation, rainfall, yield in tons per hectare
- Use: learn yield vs temp / rain / soil, as a regression check, not as Ontario ground truth

Download all three now, they are under 5 MB total. That is the training set, not a 1 GB download.

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
- FAO / IIASA, suitability index at 1 km, for rice, maize, cassava, soybean, and others, irrigated and rain-fed scenarios
- Use: suitability percent per crop, per place, e.g. maize suitability 78 percent in this cell under rain-fed, 62 percent under warming. That is literally a percent good score per crop, the starting point for the rotation scorer, before adjusting with Harrow trial data.

### 4.7 Prices and costs

- USDA Market News / USDA AMS for commodity prices, corn and soy, state price and date used
- OMAFRA crop budgets for input costs, if a simple number can be found, otherwise state cost as a clearly labelled assumption and show revenue only
- Revenue equals estimated bushels times price. Profit is an estimate with a range, never a single fake precise number.

---

## 5. The model, two steps

### Step 1, predict field conditions

Inputs, all from downloaded files, no live API in demo:

- Soil: SoilGrids WCS, sand / silt / clay, pH, SOC, CEC, N, plus Kaggle N / P / K ranges
- Climate: NASA POWER T2M, precip, humidity, radiation, plus ERA5-Land soil water 0 to 100 cm
- Vegetation: Sentinel-2 NDVI / NDMI time series, MODIS NDVI as backup
- Terrain: SRTM / Copernicus DEM slope

Train a simple Random Forest on Kaggle Crop Recommendation plus SF24 data to learn: given N, P, K, temp, humidity, pH, rainfall, soil moisture, what crop is suitable.

Output Step 1: a field profile, and a suitability percent per crop.

Example:
- Wheat: 82 percent good here, because temp 18 C, rain 650 mm, pH 6.8 matches its ideal range from Kaggle plus GAEZ
- Corn: 71 percent, because heat days are up
- Soy: 88 percent, because soil moisture and temp fit, and soy fixes nitrogen

### Step 2, predict rotation and why

Do not let the ML model invent rotation yield. Use research papers plus Harrow trial as the rotation rules.

Score per crop equals suitability percent from Step 1.

Rotation score equals average of crop scores, adjusted by rotation benefit from Harrow:

- Soy after corn: plus nitrogen fixation, plus soil benefit
- Wheat after soy: breaks pest / disease cycle, plus soil
- Corn after wheat plus red clover: plus 40 percent corn yield in trial, plus SOC
- Continuous soy / continuous corn: minus penalty, soil depletion, SOC under 2 percent

Worked example:
- Corn, soy, wheat: (71 + 88 + 82) / 3 = 80 percent, plus rotation bonus 12 percent = 92 percent overall, best
- Corn, corn, soy: (71 + 71 + 88) / 3 = 77 percent, minus soil penalty 10 percent = 67 percent overall
- Continuous soy: 88 percent, minus 50 percent penalty = 38 percent overall

Show the breakdown in the demo: wheat is 82 percent good here because temp, rain, pH match, corn is 71 percent because heat days are up, overall rotation is 92 percent because wheat plus soy fix soil and break pests, and Harrow trial shows plus 50 percent soy yield in that rotation.

That is explainable, auditable, and judges can check every percent against a dataset or a paper.

---

## 6. Architecture

```
FieldShift Forecast
├── data/
│   ├── seed/                 # Pre-fetched, cached data, shipped with repo
│   │   ├── power_t2m_harrow_1981_2025.csv
│   │   ├── power_precip_harrow_1981_2025.csv
│   │   ├── smap_soil_moisture_harrow.csv
│   │   ├── modis_ndvi_harrow.csv
│   │   ├── sentinel2_ndvi_harrow.csv      # Derived, field mean per date, few MB
│   │   ├── soilgrids_harrow.csv           # WCS derived, texture, pH, SOC
│   │   ├── harrow_trial_yields.csv        # Hand-built from AAFC trial
│   │   ├── kaggle_crop_recommendation.csv # 2,200 rows, 150 kB
│   │   ├── sf24_smart_farming.csv         # 2,200 rows, 23 cols
│   │   └── sources.json                    # Request URL, retrieval time, units, coordinates, grid cell
│   └── raw/                  # 1 GB Sentinel-2 tiles, git-ignored, do not ship
├── backend/
│   ├── app.py                # FastAPI entrypoint
│   ├── trend.py              # Mann-Kendall, Sen's slope, buddy check
│   ├── suitability.py        # Random Forest, Kaggle + SF24, GAEZ
│   ├── rotation.py           # Rotation scorer, Harrow multipliers, profit
│   └── db.py                 # Postgres models
├── frontend/
│   ├── index.html            # Leaflet map, Detect / Predict / Plan screens
│   ├── map.js                # Layers: harrow-field, trend-grid-cell, north-comparison-cell
│   └── style.css
├── notebooks/
│   ├── 01_power_fetch.ipynb
│   ├── 02_soilgrids_wcs.ipynb
│   ├── 03_sentinel2_ndvi.ipynb
│   └── 04_train_suitability.ipynb
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### Backend, FastAPI

- GET /api/pilot, returns pilot field, Harrow, coordinates, soil, baseline
- GET /api/series/{cell_id}, returns monthly time series for a variable
- GET /api/trend/{cell_id}, returns Sen's slope, Mann-Kendall p-value, confidence, buddy check
- GET /api/rotation/{field_id}, returns 3 ranked rotations, with yield, revenue, soil, water, overall percent, and breakdown
- POST /api/refresh, optional, promote refreshed cache only after validation

### Database, Postgres

- data_sources, id, name, url, retrieved_at, units, licence
- grid_cells, id, lat, lon, resolved_grid_lat, resolved_grid_lon, source
- monthly_climate, cell_id, year, month, t2m, precip, humidity, radiation
- soil_profiles, field_id, sand, silt, clay, ph, soc, cec, nitrogen, source
- trend_runs, cell_id, variable, start_year, end_year, slope_per_decade, p_value, confidence, method
- rotation_scores, field_id, rotation_name, crop_1, crop_2, crop_3, yield_bu_ac, revenue_per_ac, soil_score, water_score, overall_percent

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

- Vedant Soni, science and pitch, Harrow trial verification, demo narrative, submission
- Ved Patel, data, POWER, SoilGrids, Sentinel-2, Postgres seed cache, trend engine
- Dev Patel, backend and statistics, FastAPI, Mann-Kendall, suitability model, rotation scorer
- Shlok Mehta, interface, Leaflet, Detect / Predict / Plan screens, demo flow

---

## 8. Demo script, 90 seconds

**0 to 15 seconds, open**
Toronto view, zoom to Harrow field. "This is a real farm field near Harrow, Ontario. This farmer has to choose a rotation that will still work in 2035."

**15 to 35 seconds, Detect**
Click the field. Show trend verdict: "Summer temperature up, July soil moisture down, NDVI dropping in dry years. Here is the slope, the p-value, and the buddy check nearby. This is not one hot summer, it is a trend."

**35 to 55 seconds, Predict**
Show 2035 dry year. "In 2035, continuous corn collapses in a dry year. Corn, soy, wheat survives."

**55 to 75 seconds, Plan**
Show 3 ranked rotations in bushels and profit. "Corn, soy, wheat: 64 bu/ac soy in trial, plus 50 percent over continuous soy, soil carbon up to 2.25 percent, overall 92 percent. Here is why, wheat is 82 percent good here, soy is 88 percent, corn is 71 percent, and the rotation fixes soil."

**75 to 90 seconds, close**
Read the evidence sentence. "A Harrow farmer using this rotation, based on 20 years of NASA data and 17 years of AAFC trial data, can expect higher yield in a dry year, healthier soil, and higher revenue. That is FieldShift Forecast."

---

## 9. 30-second pitch

A farmer near Harrow, Ontario has to pick a rotation that will work in 2035, not just last year. FieldShift Forecast proves how their field has already changed with NASA data, projects it to 2035, then recommends a rotation scored in real bushels, soil health, and profit, anchored to a 17-year AAFC trial at Harrow. Corn, soy, wheat, with red clover, is 92 percent overall, because it survives dry years and rebuilds soil. That is a plan a farmer can trust, and a farm their kids can still farm.

---

## 10. Assumptions, limitations, and future work

Assumptions and limitations, to show in the demo and in the submission:

- Harrow trial is one soil type, Brookston clay loam, at one site. Numbers are real for Harrow, not a yield promise for every farm in Ontario.
- SoilGrids is modelled, R2 0.3 to 0.6, not lab-measured. Use it for texture and SOC, label it modelled.
- SoilGrids REST API is paused. WCS was used as a pre-fetch, not a live call. Demo reads cache.
- Kaggle Crop Recommendation and SF24 are mostly India / tropical crops, plus maize and wheat. They are used to learn suitability rules, not as Ontario yield truth. Harrow trial is the yield anchor.
- GAEZ suitability is 1 km, not field-level. Use it as a baseline percent, then adjust with Harrow and Sentinel-2.
- POWER grid is 0.5 degree lat by 0.625 degree lon. A Harrow point selects regional data, not a field microclimate. Sentinel-2 at 10 m is the field-level check.
- Profit is an estimate. Revenue equals bushels times price, with price and date stated. Input costs are a stated assumption from OMAFRA budgets, or revenue only if costs are not verified.
- 2035 projection is a trend stress test, not a weather forecast. Show uncertainty and range.
- Hydrology Time Series Viewer was reported failing Nov 13 to 14, 2026, HTTP 500. We used Giovanni and POWER directly as a fallback.

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
- PostgreSQL 15 or later, or Docker
- Node, optional, for frontend build
- Kaggle account, for Crop Recommendation and SF24 CSVs, free
- NASA Earthdata Login, for SMAP, GPM, MODIS pre-fetch, free
- Copernicus Data Space Ecosystem account, for Sentinel-2, free

### Quick start

```bash
git clone https://github.com/vedantjsoni/NASA-Space-APPS.git
cd NASA-Space-APPS
cp .env.example .env
docker compose up --build
# Backend on http://localhost:8000
# Frontend on http://localhost:3000
# Postgres on localhost:5432
```

### Seed data only, no live calls in demo

```bash
python backend/seed.py
# Loads data/seed/*.csv into Postgres
# Verifies every file has a source in data/seed/sources.json
```

### Train suitability model

```bash
python notebooks/04_train_suitability.py
# Trains Random Forest on Kaggle Crop Recommendation + SF24
# Saves model to backend/models/suitability.pkl
# Prints accuracy and feature importance
```

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
