# TASKS

Team Tuxedo, FieldShift Forecast. You can skim this in 5 minutes.

Last updated Sat Nov 14, evening. Building closes 6 PM tonight. After that we work remote.

---

## Status, Sat evening

Everything is integrated on `ved/model`: `dev/data`, `vedant/model2` and `shlok/front` are merged in. 59 tests pass. It is not on main yet.

Run it: `pip install -r requirements.txt`, then `python -m uvicorn backend.app:app --port 8765`, then open http://localhost:8765/frontend/?api=1

**Done**
- Dev's cached POWER, GLDAS, IMERG and HWSD2 data, trend engine, SQLite cache. Windows path fix and `harrow-power` alias added during the merge
- Model 1 on real data, sourced only (SUMMARY-README 3c). Scenarios: 1991-2020 normal, 2012 dry, 2035 dry
- Model 2 by Vedant, verified soybean yields, dated GFO prices
- API: `/api/pilot`, `/api/detect`, `/api/predict`, `/api/rotation`, plus Dev's `/api/trend` and `/api/series`
- Frontend wired to the API. Plan reloads per scenario. Real POWER cells and the trial site on the map
- README demo script rewritten so every claim matches what the build produces

**Still open, needs a person**
1. Corn and wheat trial yields with a citable source. Without them most rotation cards show "not available"
2. Rotation benefit and soil penalty weights with a source. Without them the overall score stays pending
3. Soil carbon: HWSD2 shows about 6.6 percent, the trial shows 2 to 2.25 percent. Explain or pick one
4. A crop calendar source for the May to September window
5. A real field polygon, or keep the SAMPLE polygon and say so
6. Pitch angle, slides and submission
7. Team check, then merge `ved/model` to main

---

## Who is doing what right now

| Person | Job right now | Branch |
|---|---|---|
| Dev Patel | Check the NASA data, work out how to use it, save CSVs, record sources | `dev/data` |
| Ved Patel | Model 1 suitability (V2), field config, FastAPI skeleton (V4) | `ved/model` |
| Shlok Mehta | Interface. Leaflet map, three screens, make it look good | `shlok/front` |
| Vedant Soni | Here now. Model 2 rotation scorer (V3) first, with the number checks in VS1 that block it. Pitch and submission later | `vedant/pitch` |
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
| `backend/suitability.py`, `backend/app.py`, `requirements.txt`, `data/seed/sources.json` (model data entries), `backend/field_config.json`, Kaggle, SF24 and GAEZ CSVs | Ved |
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
