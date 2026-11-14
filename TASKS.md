# TASKS

Team Tuxedo, FieldShift Forecast. You can skim this in 5 minutes.

Last updated Sat Nov 14, 2 PM. Building closes 6 PM tonight. After that we work remote.

---

## Who is doing what right now

| Person | Job right now | Branch |
|---|---|---|
| Dev Patel | Check the NASA data, work out how to use it, save CSVs, record sources | `dev/nasa-data` |
| Ved Patel | The model. Model 1 suitability and Model 2 rotation scorer | `ved/model` |
| Shlok Mehta | Interface. Leaflet map, three screens, make it look good | `shlok/ui` |
| Vedant Soni | Not here yet. Takes the Vedant jobs below when he arrives | `vedant/pitch` |
| Whoever finishes first | Avenue 2, optional, at the very end of this file | `avenue-2-global` |

## Ground rules

- No invented numbers. If unsure, write UNVERIFIED and say how to check.
- Label every number LIVE, CACHED, or SAMPLE.
- Pre-fetch and cache. The demo reads cache and never calls an API live.
- Use only the Harrow trial numbers listed in SUMMARY-README.md.
- Put the source under every number on screen.
- If a dataset fails, write the fallback in `data/seed/sources.json` and move on. Do not block the build.

## Git, one branch each

Yes, use separate branches. We have almost no code, and each person mostly edits different files, so conflicts will be rare.

```bash
git checkout main
git pull
git checkout -b ved/model          # use your own branch name
# work, then commit often
git add .
git commit -m "short message"
git push -u origin ved/model
```

When a piece runs, merge it to main in a small chunk.

```bash
git checkout main
git pull
git merge ved/model
git push
```

Then pull main into your branch often with `git pull origin main`.

Rules
- `main` always runs. Do not push broken code to it.
- Avenue 2 code never goes to main without a team check.
- Big raw downloads go in `data/raw/` and stay git-ignored.

Who owns which files, so we do not collide

| Files | Owner |
|---|---|
| `data/seed/sources.json`, NASA CSVs, `backend/trend.py`, `backend/db.py`, `docker-compose.yml` | Dev |
| `backend/suitability.py`, `backend/rotation.py`, `backend/app.py`, `requirements.txt`, `backend/field_config.json`, Kaggle and trial CSVs | Ved |
| `frontend/` | Shlok |
| `README.md`, `SUMMARY-README.md`, pitch and submission files | Vedant |

If you need a change in someone else's file, message them. For `requirements.txt` and `sources.json`, add lines only and tell the owner.

---

## Step 0, setup, everyone, 15 minutes

- [ ] Clone the repo with `git clone https://github.com/GitVed/Tuxedo.git`, then `cd Tuxedo`
- [ ] Create folders with `mkdir -p backend frontend data/seed notebooks`
- [ ] Create your own branch
- [ ] Ved adds a `.gitignore` that ignores `data/raw/`, `.env`, and Python cache files

**Done looks like.** Everyone has the repo open and is on their own branch.

---

# DEV PATEL

## D1. Check the NASA data (do this first)

Goal is to answer two questions. Is the NASA data good to use? How do we use it?

**Files to create**
- `notebooks/01_power_fetch.ipynb`
- `data/seed/power_t2m_harrow_1981_2025.csv`
- `data/seed/power_precip_harrow_1981_2025.csv`
- `data/seed/smap_soil_moisture_harrow.csv`
- `data/seed/imerg_precip_harrow.csv`
- `data/seed/sources.json`
- `data/seed/NASA_CHECK.md` (short notes, what works, what failed, the fallback, how to use each dataset)

**Datasets to fetch**
- NASA POWER monthly, temperature (T2M) and precipitation, community AG, 1981 to 2025, free, no key, server side only
- SMAP SPL4SMGP soil moisture, 2015 to present, needs Earthdata login
- GPM IMERG rainfall, 2000 to present, needs Earthdata login

**Steps**
1. Find Harrow, Essex County, Ontario on a map and write down the latitude and longitude. Mark them UNVERIFIED until Vedant confirms. Do not use Toronto City Hall coordinates.
2. Use this URL pattern for POWER and fill in the Harrow coordinates `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M&community=AG&longitude=LON&latitude=LAT&start=1981&end=2025&format=JSON`
3. Look up the right precipitation parameter name in the POWER docs. Do not guess it.
4. Fetch SMAP and IMERG for the same point. Save CSVs.
5. Check the values. Are they plausible? Any fill values? Any missing months that would break a trend?
6. Run a quick check on a buddy cell about 0.5 degrees north. Does the trend hold there?
7. Note that SMAP starts in 2015, so it is a short record. Say if it is too short to trust.
8. Record every file in `sources.json` with the request URL, retrieval time, units, coordinates, and the grid cell the API resolved.

**Done looks like**
- Four CSVs exist, or a written fallback for any that failed
- Every file has an entry in `sources.json`
- `NASA_CHECK.md` says yes or no for each dataset and how to use it
- Ved and Shlok know the file names and column names

**Fallback.** If SMAP or IMERG fail, write it down and move on. Harrow trial plus POWER alone is enough for a demo. The NASA Hydrology Time Series Viewer was reported down Nov 13 to 14, so use POWER and Giovanni directly.

## D2. Trend engine

**Files to create**
- `backend/trend.py`

**Steps**
1. Write Mann-Kendall and Sen's slope. Units are degrees C per decade and mm per decade.
2. Deseasonalise first and mask bad quality values.
3. Add the buddy check on the cell about 0.5 degrees north.
4. Add the sensitivity check with start year 1991 instead of 1981.
5. If the trend does not hold nearby, label it inconclusive.
6. Test on real POWER CSVs. If they are not ready, test on sample data and label it SAMPLE.

**Done looks like.** `python backend/trend.py` prints slope, p-value, confidence, and buddy check result for Harrow.

## D3. SoilGrids soil layer

**Files to create**
- `notebooks/02_soilgrids_wcs.ipynb`
- `data/seed/soilgrids_harrow.csv` (and the GeoTIFF if small)

**Steps**
1. Use WCS, not REST. REST is paused. The endpoint is `https://maps.isric.org/mapserv?map=/map/soilgrids.map`
2. Ask for a small box around Harrow. Get texture (sand, silt, clay), pH, soil organic carbon, and nitrogen if available.
3. Label it CACHED and modelled, not lab-measured.
4. If WCS fails, fall back to the Harrow trial soil, Brookston clay loam, and say so in `sources.json`.

**Done looks like.** CSV exists with a `sources.json` entry, or the fallback is written down.

## D4. Database and Docker

**Files to create**
- `backend/db.py`
- `backend/seed.py` (loads `data/seed/*.csv` into Postgres and checks each file has a source in `sources.json`)
- `docker-compose.yml`

**Tables.** data_sources, grid_cells, monthly_climate, soil_profiles, trend_runs, rotation_scores

**Done looks like.** `docker compose up` starts Postgres and the seed script loads without errors.

## D5. Trend endpoint

Once Ved's `backend/app.py` is merged to main, add `GET /api/trend/{cell_id}` and `GET /api/series/{cell_id}`.

**Done looks like.** The trend endpoint returns slope, p-value, confidence, and the buddy check for Harrow.

---

# VED PATEL

## V1. Training data and trial CSV

**Files to create**
- `data/seed/kaggle_crop_recommendation.csv` (2,200 rows)
- `data/seed/sf24_smart_farming.csv` (2,200 rows)
- `data/seed/harrow_trial_yields.csv`
- `backend/field_config.json` (field name, lat, lon, soil type, trial file, price file)

**Datasets to fetch**
- Kaggle Crop Recommendation, https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset/data
- Smart Farming Data 2024 (SF24)
- Crop Yield Prediction dataset. This one is very large (998,227 rows). Keep it in `data/raw/`, git-ignored. Use it only as a regression check.

**Steps**
1. Download the Kaggle files. Put the two small ones in `data/seed/`.
2. Build `harrow_trial_yields.csv` by hand from the Harrow numbers in SUMMARY-README.md. Add a source column. Do not add numbers that are not on that list.
3. Make the field config. Leave lat and lon as UNVERIFIED until Vedant or Dev confirm them.

**Done looks like.** Files exist. The trial CSV matches the numbers in SUMMARY-README.md exactly.

## V2. Model 1, suitability

**Files to create**
- `backend/suitability.py`
- `notebooks/04_train_suitability.ipynb`

**Steps**
1. Train a Random Forest on Kaggle Crop Recommendation, plus SF24 if it helps.
2. Inputs are N, P, K, temperature, humidity, pH, rainfall. Add soil moisture if SF24 supports it.
3. Output is a suitability percent per crop for wheat, corn, and soy, with the reason for each.
4. Watch the units. Kaggle rainfall runs 20.2 to 298.6 mm, so it is probably not annual totals. Match the period before feeding in Harrow rain. Write down what you decided.
5. Until Dev's data is ready, run on a SAMPLE field profile and label it SAMPLE.

**Done looks like.** `python backend/suitability.py` prints model accuracy, feature importance, and a suitability percent for each crop on a SAMPLE field.

## V3. Model 2, rotation scorer

**Files to create**
- `backend/rotation.py`

**Steps**
1. Score each rotation as average crop suitability, plus rotation benefit, minus soil penalty.
2. Take yield from the Harrow trial CSV, times a rotation multiplier, times a climate adjustment.
3. Set the climate adjustment to 1 (no change) until Dev's trend results exist and the team agrees a rule. Label it an assumption.
4. Revenue is bushels times price. No price has been chosen yet. Leave a clearly labelled placeholder and ask Vedant for the source and date. If costs are not verified, show revenue only.
5. Rotations to score are the ones that have Harrow trial numbers. Show the top 3 plus continuous cropping as the bad baseline.
6. Keep it rule based. No ML yield predictor. Every term must trace to a dataset or paper.

**Done looks like.** Running it on a SAMPLE profile gives ranked rotations with overall percent, bushels per acre, revenue, and a breakdown of why.

## V4. FastAPI skeleton

**Files to create**
- `backend/app.py`
- `requirements.txt`

**Endpoints.** `GET /api/pilot` and `GET /api/rotation/{field_id}`. Dev adds the trend ones later.

**Steps**
1. Agree the JSON shape with Shlok. Use `frontend/sample_data.json` from S1 as the starting point.
2. Return SAMPLE data first, then switch to the real models.

**Done looks like.** `GET /api/rotation/harrow` returns ranked rotations with percent and bushels.

---

# SHLOK MEHTA

## S1. Skeleton with sample data

**Files to create**
- `frontend/index.html`
- `frontend/map.js`
- `frontend/style.css`
- `frontend/sample_data.json` (the JSON shape you expect from the API)

**Steps**
1. Leaflet map zoomed to Harrow. Use a placeholder field polygon labelled SAMPLE until the real one is confirmed.
2. Add layers with these exact names, `harrow-field`, `trend-grid-cell`, `north-comparison-grid-cell`, `sentinel2-ndvi`.
3. Three screens, Detect, Predict, Plan, running on sample data.
4. Detect shows a verdict card with slope, p-value, and confidence.
5. Plan shows rotation cards with bushels, revenue, soil, water, and overall percent with a breakdown.
6. Share `sample_data.json` with Ved and Dev early so the API matches it.

**Done looks like.** Open the page, click the field, and see Detect, Predict, and Plan.

## S2. Make it look good

Do not wait for real data.

- Clean layout and a calm farm-friendly look
- A small badge on every number showing LIVE, CACHED, or SAMPLE
- A source line under every number
- Show ranges and uncertainty, not single fake numbers
- Plain language a farmer would understand
- Bundle the demo geometry and a light basemap locally so it works offline

**Done looks like.** A teammate who has never seen it can follow Detect to Predict to Plan without help.

## S3. Wire to the API

Swap sample data for `GET /api/pilot`, `/api/trend/{cell_id}`, and `/api/rotation/{field_id}` once they exist.

**Done looks like.** The same screens work from the API with the badges showing CACHED.

## S4. Farmer action plan PDF (Sunday)

One page, plain language, exported from the Plan screen.

---

# VEDANT SONI (starts when he arrives)

## VS1. Verify the numbers

Check every Harrow number against its source and put the link under each one. Check these ones first.

- Corn, soy, wheat soy yield is listed as 64 bu/ac and plus 50 percent, but continuous soy is 41. Does that add up?
- Corn gains show up as 38 to 42 percent, 43 percent, and 68 percent. Confirm which base and which period each one uses.
- Soy gain listed as 51 to 54 percent. Confirm it.
- Confirm the Harrow field choice and its latitude and longitude, and tell Dev and Ved.
- Pick a price source and date for corn, soy, and wheat. Do not make one up.

**Done looks like.** Every number on a slide has a source link, or is marked UNVERIFIED.

## VS2. Demo script and pitch

- 90 second demo script, Detect, Predict, Plan, close
- 30 second pitch
- Use the farmer trust language from README.md
- Do not claim results the model has not produced

## VS3. Submission

- Submission draft ready to paste
- Assumptions and Limitations slide
- Future work slide, use the wording in README.md
- AI use disclosure, already in README.md

**Done looks like.** Demo script rehearsed once. Submission draft ready to paste.

---

# EVERYONE

## Step 6, integrate, Sat night, remote after 6 PM

- [ ] Swap sample data for real cached data
- [ ] Test the offline demo
- [ ] Fix bugs and freeze the data
- [ ] Rehearse the 90 second demo, record it if needed

## Step 7, Sunday, 8 AM to 1 PM

- [ ] Final build and UI polish
- [ ] Farmer action plan PDF
- [ ] Rehearsal and dry run
- [ ] Submission checklist
- [ ] 1 PM presentations and local judging, 4 PM closing, 11:59 PM submission deadline

---

# STEP 8, AVENUE 2 (OPTIONAL, ONLY IF TIME)

Do not block main. Do not assign this as a main job. Give it to whoever finishes their main job first, one person only.

**Branch**

```bash
git checkout -b avenue-2-global
git push origin avenue-2-global
```

**Steps**
1. Copy main code onto the branch. Do not touch main.
2. Swap the field config to Story County, Iowa, 42.03, -93.65.
3. Fetch soil from SSURGO using SoilPoint, `soilpoint.dev/v1/soil?lat=42.03&lon=-93.65`. No key, US only.
4. Fetch NASS county yields for Iowa and check them against the source.
5. Recalibrate Model 2 with Iowa numbers. Do not reuse Harrow bushels.
6. Re-run the backtest on the 2012 dry year for Iowa.
7. If no Iowa trial numbers can be verified, show suitability percent only, from GAEZ plus SoilGrids, with no bushels claimed, and label it clearly.

**Done looks like.** Avenue 2 demo works on the branch with Iowa numbers and sources. Main is untouched.

**Merge rule.** Only merge to main if the team agrees on Sunday morning and Avenue 1 already works.
