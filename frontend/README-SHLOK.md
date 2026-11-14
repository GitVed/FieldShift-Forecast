# FieldShift Forecast | Shlok's frontend

This deliverable implements S1 (frontend skeleton), most of S2 (visual polish), an S3 integration adapter, and a print-ready starter for S4. It does **not** claim that the sample map is a surveyed field, that any NASA trend is confirmed, or that estimated revenue and 2035 projections have been calculated.

## Run the prototype

From the repository root:

```powershell
python -m http.server 5500
```

Open http://localhost:5500/frontend/ in your browser. Do **not** double-click `index.html`, since browsers may block loading `sample_data.json` from file://.

The map loads Leaflet 1.9.4 from a CDN (requires internet). If Leaflet cannot load, an offline schematic is displayed, and the Detect/Predict/Plan screens remain usable. Actual basemap tiles require internet, so this is NOT a fully bundled offline Leaflet/basemap implementation. For a fully offline judging demo, vendor Leaflet and an appropriately licensed basemap/tile set before the event.

## Your four owned files

- `index.html`: page structure, sidebar, map container, content areas.
- `style.css`: visual styling and responsive layout.
- `map.js`: screen navigation, Leaflet map, sample rendering, scenario switching, layer toggle and API integration.
- `sample_data.json`: THE expected data contract. Give this to Ved and Dev now.

## Connect to the API

Current default: `sample_data.json`. For an experimental API mode, open `http://localhost:5500/frontend/?api=1` using a SAME-ORIGIN backend or configured reverse proxy. It calls `/api/pilot`, `/api/trend/harrow-power`, `/api/rotation/harrow`. If an endpoint fails, the UI stays in sample mode. Model endpoints must return objects matching the `pilot`, `detect`, and `plan` sub-objects inside `sample_data.json`, respectively. A `predict` endpoint and a real time-series schema are still pending agreement. CORS/proxy config is needed if the backend runs on port 8000 and the UI on port 5500; don't call the backend through a separate origin without that configuration.

Ask Ved and Dev to **agree on schema** before changing it. The pilot needs `field_id`, `cell_id`, `center: {lat,lon}`, `polygon`; detect needs `verdict`, `status`, `confidence`, `buddy_check`, `trends[]`; plan needs `rotations[]`, `baseline`. All numeric measurements need a `source` and validity `status`.

## Next actions to make the project judge-ready

1. Have Vedant confirm exact field coordinates / polygon. Replace sample geometry only after confirmation.
2. Have Dev provide validated NASA trend API; never place guessed slopes or p-values in the demo.
3. Have Ved provide model rotation output and sourced yields/prices, plus climate stress-test output; verify schema.
4. Vendor Leaflet and offline map tiles if a truly offline geographical map is mandatory. In the meantime the schematic supports the demo flow.
5. Test by clicking field → Detect, Predict scenarios, Plan rotation cards; check on mobile.
6. Run browser print from Plan to make a starter summary. This is **not yet** a polished one-page PDF export; adjust print styles and source attribution after real data arrives.

## Known scientific limits

The trial values in the sample were transcribed from the team's source brief and are explicitly `UNVERIFIED` pending source checks. Ranking, trend numbers, future values, prices, revenue and profit are intentionally null. `center` and `polygon` are approximate SAMPLE geometry for the Harrow region, not measured coordinates of a particular farm. Rectangle layers are schematic and not NASA actual pixel footprints.

## Git workflow

```bash
git checkout main
git pull origin main
git checkout -b shlok/ui  # or git checkout shlok/ui if the branch exists
# Copy these frontend files into the repo's frontend/ folder
git add frontend/
git commit -m "Build FieldShift Detect Predict Plan frontend sample demo"
git push -u origin shlok/ui
```

Do not merge until a teammate has reviewed it and the demo runs on `main`.
