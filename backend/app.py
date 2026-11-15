"""FieldShift Forecast API (V4). Owner: Ved.

Reads cached files only. Never calls an external API.

Endpoints, shaped like frontend/sample_data.json (Shlok):
  GET /api/pilot                     -> "pilot"
  GET /api/detect/{cell_id}          -> "detect"   (from Dev's trend_results.csv)
  GET /api/predict/{field_id}        -> "predict"
  GET /api/rotation/{field_id}       -> "plan"     (query: scenario)
Dev's cached-data router is mounted too:
  GET /api/series/{cell_id}, GET /api/trend/{cell_id}

Run from the repo root:  uvicorn backend.app:app
The SQLite cache for Dev's router is built on startup if it is missing.
"""
import csv
import functools
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend import field_profile, rotation, suitability
from backend.provenance import load_manifest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
FIELD_ID = "harrow"
SCENARIOS = ("normal", "dry", "2035_dry")
SCENARIO_ALIASES = {"future": "2035_dry"}          # Shlok's predict id
PREDICT_IDS = {"normal": "normal", "dry": "dry", "2035_dry": "future"}
TRIAL_SITE = {"lat": 42.2167, "lon": -82.7333,
              "source": "https://acsess.onlinelibrary.wiley.com/doi/10.1002/saj2.20000",
              "note": "Woodslee trial site, about 25 km from the pilot point, in a different NASA POWER cell."}
POWER_CELL_SIZE = (0.5, 0.625)  # degrees lat, lon; POWER file header "0.5 x 0.625 degree lat/lon region"


def _db_ready():
    from sqlalchemy import func, select
    from backend import db
    try:
        with db.get_engine().connect() as conn:
            return conn.execute(select(func.count()).select_from(db.trend_runs)).scalar() > 0
    except Exception:
        return False


@asynccontextmanager
async def lifespan(_app):
    if not _db_ready():
        from backend.seed import seed
        seed()
    yield


app = FastAPI(title="FieldShift Forecast API", lifespan=lifespan)

try:
    from backend.data_api import make_router
    app.include_router(make_router())
except Exception as exc:  # Dev's router needs SQLAlchemy; the rest of the API does not
    print(f"Dev's data router not mounted: {exc}")


def _scenario(name):
    name = SCENARIO_ALIASES.get(name, name)
    if name not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"scenario must be one of {SCENARIOS}")
    return name


def _field(field_id):
    if field_id != FIELD_ID:
        raise HTTPException(status_code=404, detail=f"Unknown field_id {field_id}")


@functools.lru_cache(maxsize=1)
def profiles():
    return field_profile.build_scenarios()


@functools.lru_cache(maxsize=1)
def field_config():
    import json
    return json.loads((ROOT / "backend" / "field_config.json").read_text(encoding="utf-8"))


def _fixture_pilot():
    import json
    return json.loads((ROOT / "frontend" / "sample_data.json").read_text(encoding="utf-8"))["pilot"]


def _cell_bounds(cell_id):
    cell = load_manifest(ROOT)["resolved_cells"][cell_id]
    lat, lon = cell["center_latitude"], cell["center_longitude"]
    dlat, dlon = POWER_CELL_SIZE[0] / 2, POWER_CELL_SIZE[1] / 2
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]], (lat, lon)


# ---------- pilot ----------

@app.get("/api/pilot")
def pilot():
    field = field_config()
    fx = _fixture_pilot()
    layers = {k: dict(v) for k, v in fx["layers"].items()}
    for key, cell in (("trend-grid-cell", "power_harrow_point"), ("north-comparison-grid-cell", "power_north_point")):
        bounds, (lat, lon) = _cell_bounds(cell)
        layers[key] = {"status": "CACHED", "bounds": bounds,
                       "description": f"NASA POWER cell centred {lat}, {lon} (0.5 x 0.625 degrees), {cell}"}
    return {
        "field_id": field["field_id"],
        "cell_id": "harrow-power",
        "name": field["name"],
        "region": fx["region"],
        "soil": f"{field['soil_type']} (trial description). Model uses HWSD2 regional soil estimate.",
        "center": {"lat": field["lat"], "lon": field["lon"]},
        "coordinate_status": field["coordinates_status"] + " Field polygon is SAMPLE geometry.",
        "polygon": fx["polygon"],
        "layers": layers,
        "trial_site": TRIAL_SITE,
    }


# ---------- detect ----------

def _trend_rows():
    with open(SEED / "trend_results.csv", encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["cell_id"] == "power_harrow_point" and r["start_year"] == "1981"]


@app.get("/api/detect/{cell_id}")
def detect(cell_id: str):
    if cell_id not in ("harrow", "harrow-power", "power_harrow_point"):
        raise HTTPException(status_code=404, detail="Unknown cell")
    rows = {r["variable"]: r for r in _trend_rows()}
    t, p = rows["temperature"], rows["precipitation"]
    src = "NASA POWER monthly 1981-2025, Hamed-Rao modified Mann-Kendall and Sen slope (data/seed/trend_results.csv)"

    def trend(row, tid, name, unit):
        return {"id": tid, "name": name, "value": round(float(row["slope_per_decade"]), 2), "unit": unit,
                "p_value": f"{float(row['p_value']):.2g}", "status": "CACHED",
                "verdict": row["verdict"], "source": src}

    return {
        "status": "CACHED",
        "confidence": f"Temperature: {t['confidence']}. Rainfall: {p['confidence']}.",
        "buddy_check": f"Temperature {t['buddy_check']}, rainfall {p['buddy_check']} (cell 0.5 degrees north)",
        "verdict": (f"Temperature {t['verdict']}, {float(t['slope_per_decade']):+.2f} °C per decade since 1981. "
                    f"Rainfall {p['verdict']}."),
        "trends": [
            trend(t, "temperature", "Temperature trend (all months, deseasonalised)", "°C / decade"),
            trend(p, "rainfall", "Rainfall trend (monthly totals)", "mm/month / decade"),
            {"id": "soil_moisture", "name": "July soil moisture trend", "value": None, "unit": "m³/m³ / decade",
             "p_value": None, "status": "UNVERIFIED",
             "source": "No trend computed yet for GLDAS soil moisture (record starts 2000)"},
        ],
        "series": [],
        "source": src,
        "note": "Trend verdicts need significance plus the north-cell and 1991-start checks. Not a forecast.",
    }


# ---------- predict ----------

@app.get("/api/predict/{field_id}")
def predict(field_id: str):
    _field(field_id)
    ps = profiles()
    n = ps["normal"]
    out = []
    for sid in SCENARIOS:
        p = ps[sid]
        prov = p["provenance"]
        sm = prov["soil_moisture_july"]["value"]
        nsm = n["provenance"]["soil_moisture_july"]["value"]
        crops = suitability.score_crops(p, sid)
        out.append({
            "id": PREDICT_IDS[sid],
            "name": p["title"],
            "period": prov["temp_c"]["window"],
            "summary": (f"May-Sep {p['temp_c']:.1f} °C and {p['rain_mm']:.0f} mm rain; "
                        f"July topsoil moisture {sm:.3f} m³/m³" if sm is not None else ""),
            "temp": round(p["temp_c"] - n["temp_c"], 2),
            "rainfall": round(p["rain_mm"] - n["rain_mm"], 1),
            "soil_moisture": None if sm is None or nsm is None else round(sm - nsm, 3),
            "status": "CACHED",
            "source": "NASA POWER monthly (temperature, rain), GLDAS (soil moisture), change vs 1991-2020",
            "notes": [prov[k]["note"] for k in ("temp_c", "rain_mm", "soil_moisture_july") if prov[k]["note"]],
            "crops": {c: {"score": v["percent"], "source": v["source"], "scenario_applied": v["scenario_applied"],
                          "water": v["checks"]["water"]} for c, v in crops.items()},
        })
    return {
        "status": "CACHED",
        "note": ("Adjustments are changes from the 1991-2020 normal year. The 2035 view is a stress test, "
                 "not a forecast. The May-Sep window is UNVERIFIED."),
        "scenarios": out,
        "dry_year_check": field_profile.dry_year_check(),
    }


# ---------- plan ----------

ROTATION_DISPLAY = {
    "corn-soy-wheat plus red clover": ("corn-soy-wheat-clover", "Corn → Soy → Winter wheat + red clover",
                                       ["Corn", "Soy", "Winter wheat + red clover"]),
    "corn-soy-wheat": ("corn-soy-wheat", "Corn → Soy → Winter wheat", ["Corn", "Soy", "Winter wheat"]),
    "corn-soy": ("corn-soy", "Corn → Soy", ["Corn", "Soy"]),
    "soy-soy-wheat": ("soy-soy-wheat", "Soy → Soy → Wheat", ["Soy", "Soy", "Wheat"]),
}
BASELINE_ROTATIONS = ("continuous soybean", "continuous corn")
CROP_DISPLAY = {"corn": "Corn", "soybean": "Soy", "wheat": "Wheat"}


def _yields(result):
    out = []
    for crop in dict.fromkeys(result["crops"]):
        ref = (result.get("yield_references") or {}).get(crop)
        if ref:
            out.append({"crop": CROP_DISPLAY[crop], "bu_ac": ref["value"], "status": "CACHED",
                        "source": f"{ref['source']} ({ref['period']})"})
        else:
            out.append({"crop": CROP_DISPLAY[crop], "bu_ac": None, "status": "UNVERIFIED",
                        "source": "No verified yield for this crop in this rotation (docs/EVIDENCE.md)"})
    return out


def _revenue(result):
    v = result["revenue_per_ac"]
    return f"{v:.0f} CAD/ac/yr gross" if isinstance(v, (int, float)) else None


def _reason(result, scenario):
    b = result["breakdown"]
    parts = []
    if b["average_suitability"] is not None:
        parts.append(f"Average crop suitability {b['average_suitability']:.1f} (GAEZ index, {scenario} view).")
    else:
        parts.append("Not scored: a crop in this rotation has no suitability value.")
    rev = result["revenue_per_ac"]
    if not isinstance(rev, (int, float)):
        parts.append(f"Revenue: {rev}.")
    parts.append("No overall score: rotation benefit and soil penalty weights are not calibrated "
                 "(Model 2 evidence-only policy).")
    return " ".join(parts)


@app.get("/api/rotation/{field_id}")
def rotation_scores(field_id: str, scenario: str = Query("normal")):
    _field(field_id)
    scenario = _scenario(scenario)
    suit = suitability.score_crops(profiles()[scenario], scenario)
    results = {r["name"]: r for r in rotation.rank_rotations(suit, scenario=scenario, label="CACHED")}
    rotations = []
    for name, (rid, display, crops) in ROTATION_DISPLAY.items():
        res = results[name]
        rotations.append({
            "id": rid, "name": display, "crops": crops,
            "rank": res["rank"], "score": res["overall_percent"],
            "soil_score": None, "water_score": None,
            "revenue": _revenue(res), "profit": None,
            "yields": _yields(res), "reason": _reason(res, scenario),
            "status": "CACHED",
        })
    baseline_yields = []
    for name in BASELINE_ROTATIONS:
        for y in _yields(results[name]):
            baseline_yields.append({**y, "crop": f"Continuous {y['crop'].lower()}"})
    prices = rotation.load_prices()
    price_note = ", ".join(f"{c} {p['value']:.2f} CAD/bu" for c, p in prices.items())
    first = next(iter(prices.values()))
    return {
        "status": "CACHED",
        "prices_verified": True,
        "method": (f"Scenario: {scenario}. Suitability is the GAEZ index (Model 1). Yields are verified trial "
                   f"references only, from the Woodslee trial about 25 km from the pilot point. Prices: "
                   f"{price_note}, {first['period']} Ontario averages ({first['source']}). "
                   "Revenue is gross and shown only when every crop yield is verified. No profit: costs are not verified."),
        "rotations": rotations,
        "baseline": {"id": "continuous", "name": "Continuous cropping comparator", "yields": baseline_yields},
    }


# Serve the frontend on the same origin so ?api=1 works: /frontend/
app.mount("/frontend", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
