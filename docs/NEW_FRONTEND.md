# Harrow field explorer

Branch: `devs/new-frontend`, checked out directly in the main project directory. No separate worktree folder is needed.

The dashboard opens at `/`, with Recommendations and Priority tabs. Each shows one option at a time, with previous/next arrows and option dots. The basemap uses Esri satellite/aerial imagery with attribution; it is visual context, not a dated forecast image. Its 2021–2030 timeline separates observations from climate projections. Temperature, rain, humidity, July topsoil moisture and static soil profiles share one fixed Harrow display focus. The focus outline does not represent native grid resolution; actual source footprints remain in the API and source records. There is no surveyed field boundary or fabricated spatial heatmap.

## Run locally

From the main project directory, with Python 3.11:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Open `http://localhost:8001/`. First startup seeds SQLite from the cached CSVs. Existing Docker Compose starts the same app with PostgreSQL. Existing API routes remain available at `/docs`.

The new endpoints are:

- `GET /api/timeline/harrow`: history, annual climate projections, model spread, static soil and source-grid footprints.
- `GET /api/recommendations/harrow?year=2026&must_grow=maize&need_bu=150`: year-specific water checks and constrained rotation options. Crop and target are optional; targets require a crop and must be positive finite bu/ac values.

The annual planning order is recomputed for both tabs. Priority target feasibility comes first, then soil pH constraints, current-year rain fit, sourced drought resilience under shortfall or drying-demand flags, period GAEZ suitability and historical trial index. Trial yields and trial index values remain historical references, not annual predictions. Future GAEZ suitability represents 2021–2040 SSP370, not an independently calculated annual crop score. Unavailable projections produce explicit empty states rather than silently falling back to sample data.

Priority supports corn, soybean and wheat. It recommends rotations containing the selected crop, not simultaneous companion planting. Targets compare historical yield references in the year that crop is grown; they are not promises of farm production. Gross revenue references are not profits or future earnings.

## Reproduce supporting data

```bash
python -m scripts.fetch_projections --workers 4
python -m scripts.fetch_frontend_assets
```

Projection acquisition downloads small NASA point subsets into ignored `.cache/nex/`, validates them, and publishes CSVs only with at least three complete models. It is restartable. Libraries and the existing DM Sans/Outfit fonts are vendored locally with licenses; basemap tiles are optional external requests. No NASA request is made during timeline interaction. Dataset details and limitations are in `RESOURCES.md`.

## Verify

```bash
python -m unittest discover -s tests -v
pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/browser_check.py --url http://127.0.0.1:8001
```

Browser checks exercise map/layers, annual scrubbing and keyboard navigation, playback, every Priority crop, target/reset, details/sources, API failure/retry, offline tiles, mobile layout, a consistent map focus, equal metric cards and a single Sources entry. Screenshots are written to ignored `.cache/browser/`.

Controls remain disabled until initial data is loaded. Reduced-motion preferences remove animated transitions; playback starts only on explicit request and pauses when the tab is hidden. Requests are canceled when the year or crop changes to prevent stale results replacing the current view. Nothing is pushed or merged automatically.

## Verification recorded 2026-11-15

- All 88 backend/data tests passed, including the existing model and rotation tests.
- Full Chromium interaction checks passed with the real five-model cache, mobile layout, reduced motion, blocked basemap tiles, failed-API retry and concise water explanations.
- A separate online check loaded all 12 requested map tiles and the local fonts without page errors.
- All 600 original point-response hashes were verified. The delivered CSVs contain 7,200 extracted monthly rows, 2,880 aligned monthly rows and 15 climatology-comparison rows.
- Docker Compose configuration and Python/JavaScript checks passed. Container startup was not rerun on this machine; it has no Docker engine.

The local preview uses port 8001 from the main project directory. Nothing is pushed or merged automatically.

## Annual decision rules

Rain fit is the mean of rain divided by the lower FAO water-need bound for assessed corn/soy crop years, capped at 100 per crop. Repeated crop years are counted. Winter wheat water is not assessed in the May–September window and is explicitly listed as unassessed, never assigned zero water need. This index is not a calibrated probability or yield estimate. Wet and dry years can produce different orders; similar conditions can retain the same order while their evidence and indices change.

Temperature and humidity form a seasonal-mean drying-demand proxy using [FAO-56 saturation-pressure equation 11](https://www.fao.org/4/x0490e/x0490e07.htm). It is not daily VPD or evapotranspiration. Above-reference proxy values or below-reference observed July moisture activate the existing sourced drought-resilience tie-break. Future missing moisture is not replaced with a baseline. These are transparent planning rules, not fitted crop-response coefficients.

A supplied yield target prioritizes rotations with a supporting historical yield that meets the target. Known misses follow by shortfall; unsupported yield references come last. Increasing a soybean target from 50 to 60 bu/ac changes the preferred option in the cached 2025 profile. Targets remain comparisons with trial history, not production guarantees.

## Frontend revision verification

The code is checked out in the main project directory on `devs/new-frontend`; the earlier nested worktree was removed after the source was copied and verified. Both tabs now recompute planning order from the selected annual profile. Regression checks cover wet/dry rank changes and the soybean 50/60 bu/ac target change. The visible rain-coverage explanation changes with the year; immutable trial yields are compared by rotation ID. Carousel arrows and dots show one of three options, and slider-thumb/cursor/year-label centers are checked on desktop and mobile. Temperature uses blue-to-red, rainfall violet, humidity teal and soil moisture brown-to-blue; static soil has a texture legend. Locate controls were removed.

## Interface simplification

The header uses a text-only FieldShift wordmark and a native location dropdown. Harrow is the sole data-connected location; Add location opens a plain dropdown form and saves browser-local bookmarks. Saved locations have an explicit no-data state until datasets are connected. Print, account/avatar and duplicate Sources controls have been removed. A single header Sources button opens short Data, How we rank and Limits tabs with a discreet scrollbar only when needed.

The metric row always contains temperature, rainfall, humidity and July soil moisture in the same order and equal-size cards. Future soil moisture is explicitly unavailable. Climate values are not repeated in map cards or recommendation-side summary boxes. Soil properties have a separate static profile view.

A fixed focus rectangle around Harrow provides consistent framing for all layers. It is a display area, not a surveyed field or native source grid, and does not improve the underlying regional data resolution. Native footprint metadata remains unchanged.

The primary recommendation replaces the opaque /100 rain-fit number with rain coverage and a plain quantity explanation: a range of 50–89 percent means roughly 50–89 mm of regional rain for each 100 mm the assessed crops may need. Range causes, omitted wheat water, irrigation and soil-storage limits remain explicit. Similar future rankings are genuine outputs of the existing rain-first rule: all five future median rain totals remain below the lower FAO need bounds; the wet 2021 case and crop/target constraints are covered by regression tests. No rotations are shuffled to force a different answer.

Repeated future matches reflect a limitation of the rain-led planning policy, not a cached frontend response. The current ranking does not independently calibrate year-specific heat damage or repeated-soybean soil/disease penalties; historical trial evidence remains a separate input.

## Full-width workspace and supported targets

The left rail is removed and Sources is in the header. The map and recommendations share aligned top and bottom edges, and the map-layer and Recommendations/Priority control rows align. A full-width metrics row sits below both panels. Crop selection and the timeline retain their previous state when switching modes. Minor helper copy is removed; major missing-data notices remain.

Add location uses an ordinary anchored white form, not a modal or blurred overlay. Name and latitude/longitude are validated and stored in browser localStorage. Selecting a custom bookmark hides the Harrow dashboard and shows a clear not-connected state. Return to Harrow restores its view; no Harrow numbers are relabeled as another location. No remote data acquisition or account is implied.

Crop-target support is derived from the actual verified/derived trial references. Wheat currently has no supported yield reference, so its target field is hidden/disabled and a prominent explanation is shown. Compatible wheat rotations are still displayed. The annual recommendations endpoint rejects an unsupported wheat target with HTTP 422 rather than silently ranking unknown yields. If supported wheat references are added later, the UI can enable targets from the returned capability metadata. Legacy model routes retain their contracts.

Future soil-moisture values remain null: the connected NEX projection cache contains temperature, rain and humidity, not a soil-moisture model. Cached GLDAS observations end in 2025. This is a connected-data limitation, not a claim that NASA stopped producing observations. The unavailable view states that reason and links back to historical measurements.

Verification includes 88 backend/data tests plus Chromium checks for panel/control-row alignment, no rail, all supported crop controls, wheat-target rejection, saved-location isolation, form cancel/return, stable metrics, sources, map layers, timeline, retries and mobile layout.
