# Harrow field explorer

The dashboard has Rotations, My crop and Other crops tabs. It uses the existing DM Sans/Outfit fonts, green palette and satellite basemap. One rotation is visible at a time, with arrows to compare options.

## Run locally

Use Python 3.11, the version documented by the model branch and used by Docker.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Open http://localhost:8001/. SQLite is seeded from cached data on first startup. Docker Compose uses PostgreSQL. Basemap tiles need internet; local libraries, fonts and cached model outputs remain available without tiles.

## What farmers see

- Rotations: crop sequence, rain coverage, expandable evidence. Rankings come from the backend year classification and yield-target checks, not frontend calculations.
- My crop: choose corn, soybean or wheat, optionally enter a target in bu/ac, and compare one option at a time. The selected option shows its historical target result and historical yield range, with no repeated climate-range comparison. Conflicting yield references remain visible as a range and a mixed result, with source details expandable.
- Other crops: Ontario growing status and current/future GAEZ suitability indices. A styled suitability dropdown filters current indices. There is no Ontario checkbox. These crops have no verified rotation yields or revenue estimates.
- Map: the marker says Harrow. Its popup and the pilot polygon popup show latitude and approximate area dimensions only. This remains an illustrative, unsurveyed area; source resolution is unchanged.
- Timeline: 2021–2025 observations and 2026–2040 climate scenarios. Temperature, rain, humidity and July topsoil moisture appear once in a stable metric row. Future soil moisture stays unavailable because no soil-moisture projection is connected.

NASA rain classifies the selected year. Dry-leaning years use the 2012 dry-year order; other years use trial evidence order. Yield-target checks take priority in both. Historical yield references stay fixed, and corn climate ranges change with projected years. Some crop/target combinations retain the same ranking because the evidence or target constraints select the same order. The UI displays the backend order without reshuffling.

Rain coverage means millimetres supplied per 100 mm of estimated need, not a success probability. It excludes irrigation and stored soil water. Winter-wheat water is not assessed with the May–September summer-crop window. GAEZ values describe climate periods, not annual prediction accuracy. Detailed limitations are available through expandable evidence and the single header Sources control.

Add location saves browser-local bookmarks. Locations without connected data show an empty state; Harrow data is never relabeled as another location.

Long-term trends, past-season replay and climate-yield information are collapsed by default in three optional drawers. Past-season rain and the median corn climate scenario use line charts with gradient shading. Charts use the existing API values and show numbers without calculation steps. The map focus caption is removed; carousel arrows sit together in a centered control group.

## Verify

```bash
python -m unittest discover -s tests -v
pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/browser_check.py --url http://127.0.0.1:8001
```

The backend suite has 110 tests. Browser checks cover all tabs, crops, targets, carousel, suitability filtering, concise Harrow popup, layers, history/projections, timeline alignment, playback, retries, blocked basemap tiles, keyboard controls, mobile layout and reduced motion. Screenshots go to ignored `.cache/browser/`.

The interface simplification changes frontend rendering and browser expectations only. Backend models, API response contracts, datasets and calculations remain unchanged from `origin/ved/model` commit `0fcfce8`.
