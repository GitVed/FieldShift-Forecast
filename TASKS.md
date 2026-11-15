# TASKS

Team Tuxedo, FieldShift Forecast. You can skim this in 5 minutes.

Last updated Sat Nov 14, 2 PM. Building closes 6 PM tonight. After that we work remote.

---

## Who is doing what right now

| Person | Job right now | Branch |
|---|---|---|
| Dev Patel | Check the NASA data, work out how to use it, save CSVs, record sources | `dev/data` |
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
- If a dataset fails, write the fallback in `data/seed/sources.csv` and move on. Do not block the build.

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
| `data/seed/sources.csv`, NASA CSVs, `backend/trend.py`, `backend/db.py`, `docker-compose.yml` | Dev |
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

## D1. Check the NASA data

**Complete with documented limitations.** POWER temperature/rain/humidity, IMERG cross-check, GLDAS four-layer soil moisture and source evidence are cached and validated. Units, internal timestamps, fills, missing months, provenance and output hashes are checked. See [RESOURCES.md](RESOURCES.md).

POWER requested points matched their inferred MERRA-2 centres for all 1,620 parameter-month values each; exact upstream provider cell IDs remain unverified because the API echoes request coordinates. The location is user supplied; field boundaries remain unverified.

## D2. Trend engine

**Complete.** `backend/trend.py` deseasonalises monthly records, applies autocorrelation-corrected Mann–Kendall and elapsed-time Sen slopes, compares the distinct north point and repeats with a 1991 start. Missing/bad records are rejected. Temperature increases consistently; rainfall is inconclusive. Results: `data/seed/trend_results.csv`.

## D3. Soil layer

**Complete using documented fallback.** SoilGrids containing-pixel NoData was verified against the original ISRIC tile. Its 18 diagnostic rows remain null. FAO HWSD mapping unit 3070 supplies 42 explicitly labeled regional-estimate values at seven native depths in `hwsd_soil_harrow.csv`. Total nitrogen is not plant-available nitrogen. Field soil tests remain necessary for field-verified values; the team must accept regional estimates before using them in the model.

## D4. Database and Docker

**Implemented; actual PostgreSQL verified. Docker startup pending on a Docker-enabled machine.** `backend/db.py`, `backend/seed.py`, `Dockerfile` and `docker-compose.yml` provide all six required tables, provenance/hash validation, transactional offline seeding and persistent PostgreSQL storage. Repeated seeding preserves Ved's rotation outputs. Actual PostgreSQL tests loaded 4,819 climate rows, 60 soil rows and 8 trend results without duplication. Docker Compose configuration is validated; this computer has no Docker engine.

## D5. Trend endpoint

**Standalone endpoints complete and tested; final model-app integration pending.** `backend/data_api.py` supplies `/api/trend/{cell_id}` and `/api/series/{cell_id}` with CACHED labels, source URLs, units, grid metadata and quality flags. Tested with SQLite and actual PostgreSQL. Ved's `backend/app.py` is not present; include `make_router()` when that app becomes available. See the integration example in [RESOURCES.md](RESOURCES.md).

## Dev cleanup and review

Python extraction/runtime code, useful tests, source and processed CSVs, original project documentation and necessary runtime configuration are retained. Large raw archives, notebooks and duplicate research reports are removed after provenance preservation. `RESOURCES.md` consolidates dataset links, decisions, limitations, instructions and handoff. No changes were pushed or merged to main.

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
