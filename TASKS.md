# TASKS

Team Tuxedo, FieldShift Forecast. You can skim this in 5 minutes.

Last updated Sat Nov 14, 2 PM. Building closes 6 PM tonight. After that we work remote.

---

## Who is doing what right now

| Person | Job right now | Branch |
|---|---|---|
| Dev Patel | Check the NASA data, work out how to use it, save CSVs, record sources | `dev/nasa-data` |
| Ved Patel | Model 1 suitability (V2), field config, FastAPI skeleton (V4) | `ved/model` |
| Shlok Mehta | Interface. Leaflet map, three screens, make it look good | `shlok/ui` |
| Vedant Soni | Here now. Model 2 rotation scorer (V3) first, with the number checks in VS1 that block it. Pitch and submission later | `vedant/pitch` |
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
| `backend/suitability.py`, `backend/app.py`, `requirements.txt`, `backend/field_config.json`, Kaggle, SF24 and GAEZ CSVs | Ved |
| `backend/rotation.py`, `data/seed/harrow_trial_yields.csv` (Vedant fixes the UNVERIFIED rows, tells Ved) | Vedant |
| `frontend/` | Shlok |
| `README.md`, `SUMMARY-README.md`, pitch and submission files | Vedant |

If you need a change in someone else's file, message them. For `requirements.txt` and `sources.json`, add lines only and tell the owner.

---

## Gaps found in review, and what we decided

These are places where the plan does not connect yet. Talk about them early. They are cheap now and expensive tonight.

1. **Model 1 had no wheat or soy data. Decided Sat 2:45 PM.** GAEZ is the main source. OMAFRA ranges are the fallback. Kaggle is maize and general rules only. See V2 and section 3b in SUMMARY-README.md.
2. **N, P, K.** SoilGrids has nitrogen but no P or K. P and K are dropped from Model 1. Kaggle nitrogen is kg/ha, so it is not mixed with SoilGrids nitrogen.
3. **The Predict screen has no owner.** Normal year, dry year, 2035 dry year, and the 2012 dry-year replay all need logic. Proposal is that Dev's `trend.py` outputs adjusted temperature and rain for each scenario, and Ved's `/api/rotation/{field_id}` takes a `scenario` option. Climate then flows through Model 1 (temperature and rain change the suitability), so the bushel climate adjustment can stay at 1.
4. **Postgres is optional for the demo.** Ved's `app.py` reads the CSVs in `data/seed/` with pandas first. Dev adds Postgres only if there is time and Docker behaves.
5. **NDVI is a stretch goal.** The Sentinel-2 download is about 1 GB and slow. If skipped, the `sentinel2-ndvi` layer shows SAMPLE data, clearly labelled.

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
1. Use the Harrow point 42.0356, -82.9183 (provided by Ved). Mark it UNVERIFIED until Vedant confirms. Do not use Toronto City Hall coordinates.
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
3. Make the field config with lat 42.0356 and lon -82.9183. Mark them UNVERIFIED until Vedant confirms.

**Done looks like.** Files exist. The trial CSV matches the numbers in SUMMARY-README.md exactly.

## V2. Model 1, suitability

**Decision, Sat 2:45 PM.** GAEZ is the main source for wheat, soybean, and maize. Kaggle is secondary, for maize and general rules only. Never use Kaggle for wheat or soy.

**Files to create**
- `data/seed/gaez_harrow.csv` (suitability percent per crop, rain-fed, at the Harrow point, with source)
- `backend/suitability.py`
- `notebooks/04_train_suitability.ipynb`

**Steps**
1. Check the SF24 crop labels first. Do not assume wheat or soy are in it.
2. Fetch FAO GAEZ v5 for 42.0356, -82.9183, rain-fed, for wheat, soybean, and maize. How to download is UNVERIFIED, check the GAEZ data portal.
3. Model 1 inputs are only what we can get for Harrow at demo time. Temperature, rainfall, humidity, pH, nitrogen, soil moisture, soil organic carbon, sand, silt, clay. No P or K.
4. If GAEZ is slow, use the OMAFRA ranges below as a rule-based fallback. Label them ranges, not model output.
   - Wheat, pH 6.0 to 7.5, moisture 350 to 650 mm, optimum temperature 10 to 25 C
   - Soybean, pH 6.0 to 7.0, moisture 450 to 700 mm, development temperature 20 to 30 C
   - Maize, no range supplied yet. Get one from OMAFRA or do not score it by this fallback
   - These were supplied by Ved and are UNVERIFIED until Vedant checks the source
5. Kaggle can only learn from features it has, which are temperature, humidity, pH, and rainfall. Its nitrogen is kg/ha, so do not mix it with SoilGrids nitrogen. Use it for maize and general rules only.
6. If a crop is not in GAEZ or Kaggle and has no range, say so in the code and do not score it. Never invent training data.
7. Print which source each crop percent came from, GAEZ, range fallback, or Kaggle.
8. Until Dev's data is ready, run on a SAMPLE field profile and label it SAMPLE.

**Watch out**
- GAEZ gives one number per crop at a point. That is a lookup baseline, not training data. A Random Forest needs many rows.
- A fixed GAEZ number will not change in the dry-year and 2035 views. A range fit score will, because it uses temperature and rain. Decide early how Predict will use this.

**Done looks like.** `python backend/suitability.py` prints a percent per crop for Harrow with the source named, and says plainly which crops are not scored.

## V3. Model 2, rotation scorer (owner is now Vedant)

**Contract between Model 1, Model 2 and the API.** Agreed so Ved and Vedant can work at the same time.
- Crop names are `wheat`, `soybean`, `corn`. Model 1 and GAEZ say `maize`, and some docs say `soy`. `rotation.py` maps `maize` to `corn` and `soy` to `soybean`.
- Input is the dict that `suitability.score_crops(profile, scenario)` returns. Each crop has `percent` (a number, or `None` if not scored) and `source`.
- `rotation.rank_rotations(suitability, scenario="normal")` returns a list of rotations. Each has `name`, `crops`, `status` (`scored`, `not scored`, or `pending rules`), `not_scored_crops`, `overall_percent` (or `None`), `breakdown`, `yield_bu_ac` per crop (or `UNVERIFIED`), `revenue_per_ac` (or `price not chosen`) and a `label` (LIVE, CACHED or SAMPLE).
- Each crop also has `scenario_applied`. In dry and 2035 views it is `false` for a crop with no verified range (maize for now). Its number is then the GAEZ baseline, labelled "GAEZ baseline, dry scenario not applied". `rank_rotations` must pass this through so a rotation using that crop is shown as partly baseline.
- GAEZ values are the Suitability Index (0 to 100, rain-fed high input, 2001-2020), not a literal percent. Range fit is a different scale. See `data/seed/gaez_harrow_NOTES.md`.
- A rotation containing a crop with no percent is `not scored`. It is never dropped and never given an invented score.
- `app.py` (Ved) only calls `rank_rotations`. Only Vedant edits `rotation.py`. Only Ved edits `suitability.py`.
- The `scenario` option goes to Model 1. Model 2 does not change it.

**Vedant, start here**
1. Get the skeleton. It is on Ved's branch until it is merged. Run `git fetch` then `git checkout -b vedant/model2 origin/ved/model`.
2. Run `python backend/rotation.py`. You will see six rotations on SAMPLE data.
3. Open `data/seed/harrow_trial_yields.csv`. Fix the rows marked UNVERIFIED using the AAFC source (VS1). Put a source link in each row you fix. Tell Ved what you changed.
4. Decide the rules in the open questions below. Write each rule as a comment at the top of `rotation.py`, with the source or the trial numbers it comes from. If it has no source, mark it SAMPLE.
5. Fill in the `breakdown`, `yield_bu_ac` and `overall_percent` fields. Keep the output shape the same, so Ved's `app.py` and Shlok's screens do not break.
6. Keep "not scored" for any rotation with a crop that has no percent. Do not invent a number.
7. Revenue stays "price not chosen" until you pick a price source and date (VS1).
8. Only edit `rotation.py` and the trial CSV. Do not edit `suitability.py`, `app.py` or `field_config.json`. Message Ved if you need a change there.
9. Commit small and often. Tell Ved when a piece runs.

**Done looks like.** `python backend/rotation.py` prints ranked rotations with overall percent, bushels per acre, revenue (or "price not chosen"), and a breakdown. Every number has a source, or is marked SAMPLE or UNVERIFIED.

**Open questions for Vedant, in order**
1. Which crop each trial number is for (53, 64, 154), and per-crop bushels. Wheat has no yield in the docs.
2. How rotation benefit and soil penalty derive from trial numbers. The 12, 10 and 50 percent in the README are SAMPLE examples only.
3. Whether red clover counts in the average. It has no suitability source.
4. The climate adjustment rule. Stays at 1 until agreed.

**Files to create**
- `backend/rotation.py` (skeleton exists, no scoring rules yet)

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
- Confirm the Harrow point 42.0356, -82.9183 and tell Dev and Ved.
- Check the OMAFRA ranges Ved supplied for wheat and soybean against the OMAFRA source, and find a maize range. Confirm what period the mm values cover.
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
