# FieldShift Forecast

**Help a farmer pick a crop rotation that will survive the future, not just last year.**

Team Tuxedo | NASA Space Apps Toronto 2026 | Challenge "Field Shift: Adapting Farms with NASA Data"

> Full context for teammates and AI assistants is in [SUMMARY-README.md](SUMMARY-README.md). Jobs and owners are in [TASKS.md](TASKS.md).

---

## Stack

| Layer | What we use |
|---|---|
| Backend | Python, FastAPI, PostgreSQL, Docker |
| Machine learning | Python, pandas, scikit-learn Random Forest |
| Frontend | JavaScript, Leaflet, HTML and CSS (no React) |
| Data | NASA POWER, SMAP, IMERG, MODIS, SoilGrids WCS, Sentinel-2, Kaggle CSVs, Harrow trial CSV |
| Golden rule | Pre-fetch and cache all data. The demo reads the cache. No live API calls during judging. |

## Quick facts

| | |
|---|---|
| Team | Vedant Soni (owner), Ved Patel, Shlok Mehta, Dev Patel |
| Event | NASA Space Apps Toronto, Nov 14 to 15, 2026, Bombardier Centre, 65 Carl Hall Rd, Toronto |
| Pilot field | Harrow / Woodslee, Essex County, Ontario, Brookston clay loam |
| Deadline | Sun Nov 15, 11:59 PM EST |
| Judging | Sun 1 to 4 PM, closing ceremony 4 to 6 PM |
| Building hours | Building closes 6 PM Sat and Sun, work continues remote after that |
| Repo | https://github.com/GitVed/Tuxedo.git |

**Status (Sat Nov 14, afternoon).** The repo only has docs so far. No code yet. See TASKS.md for who builds what.

---

## What it does

A farmer near Harrow, Ontario has to decide what to plant next. Summers are getting hotter and drier. Soil is getting tired. Costs are rising. A wrong rotation means a lost season.

FieldShift Forecast does three things.

1. **Detect.** Show how this exact field has already changed, using NASA data. Temperature, rainfall, soil moisture, vegetation health. We run a real trend test and show the slope, the p-value, the confidence, and a check against a nearby cell.
2. **Predict.** Project the trend to 2035 as a stress test, not a weather forecast. Show a normal year, a dry year, and a 2035 dry year.
3. **Plan.** Rank crop rotations in real bushels, soil health, water risk, and profit. Every number shows its source.

---

## The two models

This is the core idea. Everyone on the team should know it.

**Model 1 predicts the condition of the place.**
- Input is soil, climate, and temperature for that field.
- Output is a field profile and a suitability percent for each crop.
- Example (SAMPLE, not real output). Wheat 82 percent, corn 71 percent, soy 88 percent, each with the reason shown.
- Built as a Random Forest trained on the Kaggle crop datasets.

**Model 2 recommends crops and rotation, with reasons backed by data.**
- Input is the suitability percents from Model 1.
- Output is a ranked rotation and why.
- Why this crop, because its ideal temperature, rain, pH, and N/P/K range matches this field.
- Why this rotation, because the Harrow trial shows it beats continuous cropping.
- It is NOT a black box. It is a transparent rule-based scorer. Every percent traces to a dataset or a paper.

```
Overall rotation score = average crop suitability + rotation benefit - soil penalty
Estimated yield        = Harrow trial baseline x rotation multiplier x climate adjustment
Revenue                = Estimated yield x commodity price (price and date stated)
```

Worked example (SAMPLE, shows the formula only).
- Corn, soy, wheat scores 92 percent
- Corn, corn, soy scores 67 percent
- Continuous soy scores 38 percent

---

## Decision locked

**Main branch is Avenue 1, Harrow / Woodslee, Ontario.** This is the demo, the submission, and the pitch. We do not reopen this.

**Avenue 2 is a separate branch called `avenue-2-global`.** It is for popular global areas, starting with the US Corn Belt (Iowa). It is optional. It must never block main. It only merges into main if the whole team agrees on Sunday morning and Avenue 1 already works.

SoilGrids, Kaggle, and ESA data are not separate avenues. They are supporting data inside Avenue 1.

Why Harrow
- Real bushels from a published long-term trial
- Toronto judges get the Ontario farmer story right away
- Numbers are already known and no new API is needed

---

## Data we use

Label every number in the app as **LIVE**, **CACHED**, or **SAMPLE**. For the demo almost everything is CACHED.

| Data | Gives us | Notes |
|---|---|---|
| NASA POWER | Monthly temperature, rain, humidity, radiation | 0.5 degree, 1981 to present, free, no key |
| SMAP | Soil moisture | 9 km, 2015 to present, Earthdata login, short record |
| GPM IMERG | Rainfall | 0.1 degree, 2000 to present, Earthdata login |
| MODIS | NDVI and land temperature | 2000 to present |
| Other NASA | ECOSTRESS, GLDAS / MERRA-2, SRTM | Supporting. FIRMS considered and rejected |
| Harrow trial (AAFC) | Real bushels per rotation, soil carbon | Main yield source. Dr. Craig Drury, Harrow R&D Centre |
| SoilGrids WCS | Sand, silt, clay, pH, soil carbon, N | 250 m, modelled not measured. REST API is paused so we use WCS |
| Kaggle (3 sets) | Crop suitability rules | Mostly India and tropical crops. Not Ontario yield truth |
| Sentinel-2 (ESA) | Field-level NDVI and NDMI | 10 m. We ship small CSVs, never the raw tiles |
| FAO GAEZ v5 | Suitability percent per crop | 1 km baseline |
| ERA5-Land | Soil water cross-check | Cross-check for POWER |

Real Harrow numbers are listed in SUMMARY-README.md. Do not invent others.

---

## Why a farmer can trust it

We are not replacing a farmer's experience. We give them 20 years of measured change, 17 years of trial evidence, and a dry-year replay, so they can make the same decision with more evidence.

- We show we know what they know. Continuous soy wears soil out. Corn after corn gets weaker. The Harrow trial proves it.
- We show what they cannot see. Twenty years of trend in one glance, with slope, p-value, and a buddy check.
- We backtest, not just predict. Replay the 2012 drought with real data.
- We show money and risk, not just yield. Revenue, soil carbon, and the downside in a dry year, as a range.
- We make it their data. If a farmer uploads a soil test or yield monitor history, the same engine personalises the scores.
- We are honest about uncertainty. Source under every number. LIVE, CACHED, or SAMPLE labels. Assumptions stated.

---

## Repo layout

```
Tuxedo/
  data/
    seed/         cached data, shipped with the repo
    raw/          big downloads like Sentinel-2 tiles, git-ignored, never shipped
  backend/
    app.py        FastAPI entrypoint
    trend.py      Mann-Kendall, Sen's slope, buddy check
    suitability.py  Model 1
    rotation.py   Model 2
    db.py         Postgres models
  frontend/
    index.html    Leaflet map and Detect / Predict / Plan screens
    map.js
    style.css
  notebooks/
    01_power_fetch
    02_soilgrids_wcs
    03_sentinel2_ndvi
    04_train_suitability
  docker-compose.yml
  requirements.txt
  README.md
  SUMMARY-README.md
  TASKS.md
```

**API endpoints**
- GET /api/pilot
- GET /api/series/{cell_id}
- GET /api/trend/{cell_id}
- GET /api/rotation/{field_id}
- POST /api/refresh (optional)

**Postgres tables**
data_sources, grid_cells, monthly_climate, soil_profiles, trend_runs, rotation_scores

**Leaflet layers**
harrow-field, trend-grid-cell, north-comparison-grid-cell, sentinel2-ndvi

---

## How we work in git

Short version. Full steps are in TASKS.md.

- `main` always runs. Never push broken code to it.
- Each person works on their own branch and merges to main in small pieces.
- Branches are `dev/nasa-data`, `ved/model`, `shlok/ui`, `vedant/pitch`, and optional `avenue-2-global`.
- Pull main into your branch often.
- Never push Avenue 2 code to main without a team check.

---

## Setup

```bash
git clone https://github.com/GitVed/Tuxedo.git
cd Tuxedo
mkdir -p backend frontend data/seed notebooks
```

Once the backend lands, the plan is `docker compose up --build`. The `docker-compose.yml` and `.env.example` do not exist yet.

---

## Limits and honest notes

- Harrow is one soil type at one site. The numbers are real for Harrow. They are not a yield promise for every Ontario farm.
- SoilGrids is modelled, not lab-measured. Label it that way.
- SoilGrids REST is paused. We pre-fetch with WCS and never call it live.
- Kaggle data is mostly India and tropical crops. We use it for suitability rules, not for Ontario bushels.
- SMAP only starts in 2015, so its trend record is short.
- POWER is a coarse grid. Sentinel-2 at 10 m is the field-level check.
- The 2035 view is a trend stress test, not a forecast.
- Profit is an estimate. We state price and date. If costs are not verified we show revenue only.
- The NASA Hydrology Time Series Viewer was reported failing Nov 13 to 14 (HTTP 500). We use POWER and Giovanni directly.
- If any dataset fails, record the fallback in sources.json and move on. Harrow trial plus POWER alone is enough for a demo.

## Going global

We built the method so it can go global. We demo it on Harrow only. Global would be shallow everywhere and deep nowhere, and judges would ask where a bushel number came from for a random spot. Model 1 is portable. Model 2 needs local trial or county yield evidence, so Harrow numbers do not transfer to other places.

**Future work wording for the submission**

We built this on one public soil type, Brookston clay loam at Harrow, and public NASA data. That is the limit of public data. If a farmer uploads their own soil test, or their yield monitor history from their combine, the same engine personalises the scores to their field. The prototype proves the method, the farmer's data makes it theirs.

---

## Sources

- NASA Space Apps 2026 challenge page, https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/
- NASA POWER, https://power.larc.nasa.gov/
- NASA Earthdata (SMAP, IMERG, MODIS, ECOSTRESS, GLDAS, SRTM), https://www.earthdata.nasa.gov/
- AAFC Harrow, Dr. Craig Drury, Woodslee long-term rotation trial
- ISRIC SoilGrids, https://www.isric.org/explore/soilgrids
- Kaggle Crop Recommendation, https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data
- Kaggle Smart Farming Data 2024 (SF24)
- ESA Sentinel-2 via Copernicus Data Space, https://browser.dataspace.copernicus.eu/
- ESA WorldCover and WorldCereal
- FAO GAEZ v5, https://gaez.fao.org/
- USDA SSURGO and NASS QuickStats (Avenue 2 only)

## AI use disclosure

AI tools were used to research datasets, evaluate ideas, and help plan and build. Final solution direction and decisions were made by Team Tuxedo. AI was not used to submit the project. Generated code and data are acknowledged. No NASA branding is used in AI-generated content.

## Licence

NASA data is public domain, cite the source. SoilGrids and ESA WorldCover are CC BY 4.0. GAEZ is free with attribution. Check each Kaggle dataset page. Harrow trial data belongs to AAFC, cite Dr. Craig Drury and AAFC Harrow. Code is MIT unless the repo says otherwise.

Team Tuxedo, NASA Space Apps Toronto 2026.
